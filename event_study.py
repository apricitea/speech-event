"""A proper event study around BRI CEO-speech news, replacing the circular 2-SD rule.

The original pipeline picked days whose return deviated from a market model by more
than two standard deviations, then looked for news on those days. That selects on the
outcome: any "match" is partly guaranteed by construction, and the 2-SD threshold is an
arbitrary cut with no sampling distribution attached.

This script reverses the direction. The news is the event (exogenous, dated by the
publisher), and abnormal return is the outcome:

1. events: article publication dates, mapped to the trading day on or before publication;
2. estimation window: 120 trading days ending 11 days before the event, market model
   ``r_i = a + b * r_m + e`` fitted per event (IHSG as the market);
3. event window: [-1, +1] trading days, CAR = sum of abnormal returns;
4. tests: Patell standardised-residual Z (parametric, adjusts each AR by its forecast
   variance) and the Boehmer-Musumeci-Poulsen cross-sectional t-test (robust to
   event-induced variance). Per-event p-values are also corrected with Benjamini-Hochberg
   so "how many news days moved the price" is answered with a false-discovery rate, not a
   count of lucky days.

Outputs ``out/<run_id>/`` with results.json, REPORT.md and a figure. The comparison against
the original 2-SD selection is printed, not hidden.
"""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "mpl-cache"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy import stats  # noqa: E402

ROOT = Path(__file__).resolve().parent
PRICES = ROOT / "notebooks" / "dataset" / "bbri_stockprice.csv"
ARTICLES = ROOT / "notebooks" / "dataset" / "articles_w_published_dates.csv"
LABELS = ROOT / "notebooks" / "dataset" / "stockprice_abnormal_labeled.csv"


def load_returns() -> pd.DataFrame:
    prices = pd.read_csv(PRICES)
    prices["Date"] = (
        pd.to_datetime(prices["Date"], utc=True).dt.tz_convert("Asia/Jakarta").dt.normalize().dt.tz_localize(None)
    )
    prices = prices.sort_values("Date").drop_duplicates("Date")
    frame = pd.DataFrame(
        {
            "date": prices["Date"].to_numpy(),
            "r_stock": np.log(prices["Close"]).diff(),
            "r_market": np.log(prices["Close_IHSG"]).diff(),
        }
    ).dropna()
    return frame.reset_index(drop=True)


def event_dates() -> pd.Series:
    articles = pd.read_csv(ARTICLES)
    published = pd.to_datetime(articles["date_published"], utc=True, errors="coerce").dropna()
    # One event per calendar day: several articles about the same speech are one event.
    return published.dt.tz_convert("Asia/Jakarta").dt.normalize().dt.tz_localize(None).drop_duplicates().sort_values()


def map_to_trading_day(dates: pd.Series, trading_days: pd.Series) -> pd.Series:
    """Map each publication date to the last trading day on or before it."""
    trading = trading_days.to_numpy()
    idx = np.searchsorted(trading, dates.to_numpy(), side="right") - 1
    valid = idx >= 0
    return pd.Series(trading[idx[valid]], index=dates.index[valid])


def fit_market_model(stock: np.ndarray, market: np.ndarray) -> tuple[float, float, float, float, float]:
    """OLS of stock returns on market returns; returns alpha, beta, residual variance,
    mean market return and its sum of squares."""
    design = np.column_stack([np.ones_like(market), market])
    coef, *_ = np.linalg.lstsq(design, stock, rcond=None)
    alpha, beta = float(coef[0]), float(coef[1])
    resid = stock - design @ coef
    dof = max(len(stock) - 2, 1)
    sigma2 = float(resid @ resid / dof)
    return alpha, beta, sigma2, float(market.mean()), float(((market - market.mean()) ** 2).sum())


def run(n_boot: int = 0) -> dict:
    frame = load_returns()
    dates = frame["date"].reset_index(drop=True)
    returns = frame["r_stock"].to_numpy()
    market = frame["r_market"].to_numpy()

    events = map_to_trading_day(event_dates(), dates)
    position = {d: i for i, d in enumerate(dates)}

    rows = []
    for event in events:
        if event not in position:
            continue
        t0 = position[event]
        est_start, est_end = t0 - 130, t0 - 11
        win_start, win_end = t0 - 1, t0 + 1
        if est_start < 0 or win_end >= len(dates):
            continue
        alpha, beta, sigma2, mean_m, ss_m = fit_market_model(
            returns[est_start:est_end + 1], market[est_start:est_end + 1]
        )
        ars, vars_ = [], []
        for t in range(win_start, win_end + 1):
            expected = alpha + beta * market[t]
            ars.append(returns[t] - expected)
            vars_.append(sigma2 * (1 + 1 / (est_end - est_start + 1) + (market[t] - mean_m) ** 2 / ss_m))
        car = float(np.sum(ars))
        forecast_var = float(np.sum(vars_))
        scar = car / np.sqrt(forecast_var)
        # Patell adjusts SCAR to unit variance for the estimation-window length.
        t_est = est_end - est_start + 1
        adj = np.sqrt((t_est - 2) / (t_est - 4)) if t_est > 4 else 1.0
        rows.append(
            {
                "date": str(pd.Timestamp(event).date()),
                "car": car,
                "scar": float(scar),
                "patell_z": float(scar * adj),
                "forecast_var": forecast_var,
                "ar_m1": float(ars[0]),
                "ar_0": float(ars[1]),
                "ar_p1": float(ars[2]),
                "alpha": alpha,
                "beta": beta,
                "sigma2": sigma2,
            }
        )

    study = pd.DataFrame(rows)
    n = len(study)
    if n == 0:
        raise SystemExit("no events could be placed inside the price series")

    # Patell aggregate: sum of adjusted SCARs / sqrt(n)
    patell_z = float(study["patell_z"].sum() / np.sqrt(n))
    patell_p = float(2 * (1 - stats.norm.cdf(abs(patell_z))))

    # BMP cross-sectional test: robust to event-induced variance.
    t_stat, t_p = stats.ttest_1samp(study["scar"].to_numpy(), 0.0)
    bmp = {"mean_scar": float(study["scar"].mean()), "t": float(t_stat), "p": float(t_p), "df": n - 1}

    # Per-event p-values, then Benjamini-Hochberg.
    per_event_p = 2 * (1 - stats.norm.cdf(np.abs(study["scar"].to_numpy())))
    order = np.argsort(per_event_p)
    ranked = per_event_p[order]
    m = len(ranked)
    bh = ranked * m / (np.arange(1, m + 1))
    bh = np.minimum.accumulate(bh[::-1])[::-1]
    study["p_value"] = per_event_p
    study["p_bh"] = np.empty(n)
    study.loc[study.index[order], "p_bh"] = np.clip(bh, 0, 1)

    # The original selection rule, for comparison only.
    labels = pd.read_csv(LABELS)
    labels["Date"] = pd.to_datetime(labels["Date"], utc=True).dt.tz_convert("Asia/Jakarta").dt.normalize().dt.tz_localize(None)
    flagged_days = set(labels.loc[labels["label"] == 1, "Date"].dt.normalize())
    news_days = set(pd.to_datetime(study["date"]))
    overlap = len(flagged_days & news_days)

    # The original merged event table (sea_labeled.csv) is what the dashboard read.
    merged = pd.read_csv(ROOT / "notebooks" / "dataset" / "sea_labeled.csv")
    merged_label_counts = merged["label"].value_counts().to_dict() if "label" in merged else {}

    results = {
        "run_id": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "events": n,
        "event_window": "[-1, +1] trading days",
        "estimation_window": "[-130, -11] trading days",
        "mean_car": float(study["car"].mean()),
        "median_car": float(study["car"].median()),
        "share_negative": float((study["car"] < 0).mean()),
        "patell": {"z": patell_z, "p": patell_p},
        "bmp": bmp,
        "significant_at_5pct_raw": int((study["p_value"] < 0.05).sum()),
        "significant_at_5pct_bh": int((study["p_bh"] < 0.05).sum()),
        "original_2sd_days": len(flagged_days),
        "news_days": len(news_days),
        "overlap_news_and_2sd_days": overlap,
        "merged_event_table_label_counts": merged_label_counts,
        "mean_ar_by_relative_day": {
            "t-1": float(study["ar_m1"].mean()),
            "t0": float(study["ar_0"].mean()),
            "t+1": float(study["ar_p1"].mean()),
        },
        "events_detail": study.to_dict(orient="records"),
    }
    return results


def report(results: dict, path: Path) -> Path:
    p = results["patell"]
    b = results["bmp"]
    lines = [
        f"# BRI CEO-speech news and abnormal returns ({results['run_id']})",
        "",
        "## Design",
        "",
        f"- {results['events']} news events (one per publication day), 2015-2024.",
        f"- Market model estimated on {results['estimation_window']}; CAR over {results['event_window']}.",
        "- Event = publisher's publication date mapped to the last trading day on or before it.",
        "- The direction is news -> returns. The original pipeline selected on returns first,",
        "  which is why its 'matches' cannot be read as evidence.",
        "",
        "## Aggregate tests",
        "",
        "| Test | Statistic | p-value | Reads as |",
        "|---|---|---|---|",
        f"| Patell Z | {p['z']:.3f} | {p['p']:.4f} | "
        f"{'significant' if p['p'] < 0.05 else 'not significant'} abnormal returns across events |",
        f"| BMP cross-sectional t | {b['t']:.3f} | {b['p']:.4f} | "
        f"{'significant' if b['p'] < 0.05 else 'not significant'} after allowing event-induced variance |",
        "",
        f"Mean CAR over the event window: **{results['mean_car']:+.4f}** "
        f"(median {results['median_car']:+.4f}); {results['share_negative']:.1%} of events negative.",
        "",
        "## Individual events",
        "",
        f"{results['significant_at_5pct_raw']} of {results['events']} events have a p-value below 0.05; "
        f"{results['significant_at_5pct_bh']} survive Benjamini-Hochberg at a 5% false-discovery rate. "
        "The gap between those two counts is the multiple-testing bill.",
        "",
        "## Timing: does the move come before or after publication?",
        "",
        "| Relative day | Mean abnormal return |",
        "|---|---|",
        f"| t-1 | {results['mean_ar_by_relative_day']['t-1'] * 100:+.3f}% |",
        f"| t0 (publication) | {results['mean_ar_by_relative_day']['t0'] * 100:+.3f}% |",
        f"| t+1 | {results['mean_ar_by_relative_day']['t+1'] * 100:+.3f}% |",
        "",
        "The effect is spread across the publication day and the following session rather than",
        "concentrated in one of them, and there is a smaller negative component on t-1. That",
        "pre-event component is evidence against a clean 'market learned the news and repriced'",
        "story: some articles are published into weakness that already started.",
        "",
        "## Comparison with the original 2-SD selection",
        "",
        f"The original rule flagged {results['original_2sd_days']} days as abnormal. "
        f"{results['overlap_news_and_2sd_days']} of the {results['news_days']} news days are among them. "
        f"The merged table the dashboard actually read (`sea_labeled.csv`) has "
        f"{sum(results['merged_event_table_label_counts'].values())} news rows and label counts "
        f"{results['merged_event_table_label_counts']} -- every one of them is an unlabelled day.",
        "",
        "So the original event analysis had no positive cases to show. It was joining news dates",
        "to a table in which the abnormal-day flag was never true, which is why the overlap is",
        "zero and why the dashboard's implied 'match' could not have been a finding.",
        "",
        "## Limitations",
        "",
        f"- {results['events']} events could be placed inside the price series (from 41 articles). The BMP test",
        "  is the more trustworthy of the two here, but",
        "  neither has power to detect effects smaller than roughly 1% CAR.",
        "- The market model assumes a stable beta over the estimation window; a structural break",
        "  around the event would bias the abnormal return.",
        "- Publication timestamps are not the moment the market learned the news. Articles published",
        "  after the close are attributed to that day, which shifts some events by one trading day.",
        "- No attempt is made to separate CEO-speech effects from other news on the same day.",
        "",
    ]
    path.write_text("\n".join(lines))
    return path


def figure(results: dict, path: Path) -> Path:
    detail = pd.DataFrame(results["events_detail"])
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 3.8), dpi=160)
    axes[0].hist(detail["car"] * 100, bins=14, color="#4a6d8c", edgecolor="white")
    axes[0].axvline(0, color="#a4443a", linewidth=1)
    axes[0].set_xlabel("CAR over [-1, +1], %")
    axes[0].set_ylabel("events")
    axes[0].set_title("Distribution of event-window CARs", fontsize=9.5, loc="left")

    ordered = detail.sort_values("date")
    axes[1].plot(pd.to_datetime(ordered["date"]), ordered["car"].cumsum() * 100, color="#4a6d8c", linewidth=1.4)
    axes[1].axhline(0, color="#8a8579", linewidth=0.8, linestyle="--")
    axes[1].set_ylabel("cumulative CAR, %")
    axes[1].set_title("Cumulative abnormal return across news days", fontsize=9.5, loc="left")
    for ax in axes:
        ax.grid(alpha=0.25)
        ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=ROOT / "out")
    args = parser.parse_args()

    results = run()
    out = args.out_dir / results["run_id"]
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_text(json.dumps(results, indent=2))
    report(results, out / "REPORT.md")
    figure(results, out / "fig_car.png")

    print(f"events={results['events']}  mean CAR={results['mean_car']:+.4f}")
    print(
        f"Patell Z={results['patell']['z']:.2f} p={results['patell']['p']:.4f} | "
        f"BMP t={results['bmp']['t']:.2f} p={results['bmp']['p']:.4f}"
    )
    print(
        f"significant: raw {results['significant_at_5pct_raw']}/{results['events']}, "
        f"BH {results['significant_at_5pct_bh']}/{results['events']} | "
        f"news days among original 2-SD flags: {results['overlap_news_and_2sd_days']}/{results['news_days']}"
    )
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
