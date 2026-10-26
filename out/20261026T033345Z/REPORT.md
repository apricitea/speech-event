# BRI CEO-speech news and abnormal returns (20261026T033345Z)

## Design

- 26 news events (one per publication day), 2015-2024.
- Market model estimated on [-130, -11] trading days; CAR over [-1, +1] trading days.
- Event = publisher's publication date mapped to the last trading day on or before it.
- The direction is news -> returns. The original pipeline selected on returns first,
  which is why its 'matches' cannot be read as evidence.

## Aggregate tests

| Test | Statistic | p-value | Reads as |
|---|---|---|---|
| Patell Z | -2.839 | 0.0045 | significant abnormal returns across events |
| BMP cross-sectional t | -3.240 | 0.0034 | significant after allowing event-induced variance |

Mean CAR over the event window: **-0.0123** (median -0.0093); 76.9% of events negative.

## Individual events

1 of 26 events have a p-value below 0.05; 1 survive Benjamini-Hochberg at a 5% false-discovery rate. The gap between those two counts is the multiple-testing bill.

## Placebo tests: are news dates special?

1,000 placebo samples of 26 random trading dates each, drawn without replacement from the eligible range and put through the identical
market-model and CAR code (seed recorded in the manifest).

| Measure | Value |
|---|---|
| Observed mean CAR | -1.228% |
| Placebo mean CAR (sd) | -0.016% (0.523) |
| Placebo 2.5th–97.5th percentile | -1.055% to +0.993% |
| Empirical two-sided p | 0.0230 |
| Percentile of the observed value | 1.0 |

The observed mean CAR sits **outside the 95% placebo band**: 1.0% of 1,000 random-date samples fall at or below it (empirical two-sided p = 0.023). News dates are therefore extreme relative to arbitrary dates, though less decisively than the parametric tests imply.

A news day is not automatically an informative event: an effect of this size could in
principle have come from dates chosen at random, which is what this null tests.

## Timing: does the move come before or after publication?

| Relative day | Mean abnormal return |
|---|---|
| t-1 | -0.387% |
| t0 (publication) | -0.501% |
| t+1 | -0.340% |

The effect is spread across the publication day and the following session rather than
concentrated in one of them, and there is a smaller negative component on t-1. That
pre-event component is evidence against a clean 'market learned the news and repriced'
story: some articles are published into weakness that already started.

## Comparison with the original 2-SD selection

The original rule flagged 263 days as abnormal. 0 of the 26 news days are among them. The merged table the dashboard actually read (`sea_labeled.csv`) has 32 news rows and label counts {0: 32} -- every one of them is an unlabelled day.

So the original event analysis had no positive cases to show. It was joining news dates
to a table in which the abnormal-day flag was never true, which is why the overlap is
zero and why the dashboard's implied 'match' could not have been a finding.

## Limitations

- 26 events could be placed inside the price series (from 41 articles). The BMP test
  is the more trustworthy of the two here, but
  neither has power to detect effects smaller than roughly 1% CAR.
- The market model assumes a stable beta over the estimation window; a structural break
  around the event would bias the abnormal return.
- Publication timestamps are not the moment the market learned the news. Articles published
  after the close are attributed to that day, which shifts some events by one trading day.
- No attempt is made to separate CEO-speech effects from other news on the same day.
