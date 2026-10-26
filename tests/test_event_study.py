"""Tests for the event-study machinery.

The market model and the trading-day mapping are the two places where a silent error would
change every number in the report, so they are tested against data with a known answer.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from event_study import fit_market_model, map_to_trading_day, run


def test_market_model_recovers_known_coefficients():
    rng = np.random.default_rng(0)
    market = rng.normal(0, 0.01, 500)
    alpha_true, beta_true = 0.0003, 1.25
    stock = alpha_true + beta_true * market + rng.normal(0, 0.002, 500)
    alpha, beta, sigma2, mean_m, ss_m = fit_market_model(stock, market)
    assert alpha == pytest.approx(alpha_true, abs=5e-4)
    assert beta == pytest.approx(beta_true, abs=0.05)
    assert sigma2 > 0
    assert mean_m == pytest.approx(market.mean())
    assert ss_m == pytest.approx(((market - market.mean()) ** 2).sum())


def test_mapping_uses_the_last_trading_day_on_or_before_publication():
    trading = pd.Series(pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-05"]))
    published = pd.Series(pd.to_datetime(["2024-01-04", "2024-01-05", "2024-01-01"]))
    mapped = map_to_trading_day(published, trading)
    # 4 Jan (Thursday, market shut) -> 3 Jan; 5 Jan -> 5 Jan; before the series -> dropped.
    assert list(mapped) == [pd.Timestamp("2024-01-03"), pd.Timestamp("2024-01-05")]


def test_study_produces_a_finite_aggregate_and_respects_the_event_window():
    results = run()
    assert results["events"] > 0
    assert np.isfinite(results["mean_car"])
    assert np.isfinite(results["patell"]["z"])
    assert 0.0 <= results["patell"]["p"] <= 1.0
    assert results["event_window"] == "[-1, +1] trading days"
    for row in results["events_detail"]:
        assert row["car"] == pytest.approx(row["ar_m1"] + row["ar_0"] + row["ar_p1"])


def test_estimate_car_is_zero_when_the_stock_tracks_the_market():
    from event_study import estimate_car

    rng = np.random.default_rng(1)
    market = rng.normal(0, 0.01, 400)
    stock = 2.0 * market  # beta 2, alpha 0, no idiosyncratic move
    estimate = estimate_car(stock, market, 200)
    assert estimate is not None
    assert abs(estimate["car"]) < 1e-10


def test_estimate_car_picks_up_an_injected_shock():
    from event_study import estimate_car

    rng = np.random.default_rng(2)
    market = rng.normal(0, 0.01, 400)
    stock = market.copy()
    stock[200] += 0.05  # a 5% abnormal move on the event day
    estimate = estimate_car(stock, market, 200)
    assert estimate is not None
    assert 0.04 < estimate["car"] < 0.06


def test_estimate_car_refuses_windows_that_do_not_fit():
    from event_study import estimate_car

    market = np.zeros(400)
    stock = np.zeros(400)
    assert estimate_car(stock, market, 100) is None   # estimation window starts before zero
    assert estimate_car(stock, market, 399) is None   # event window runs past the end
