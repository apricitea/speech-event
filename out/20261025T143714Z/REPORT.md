# BRI CEO-speech news and abnormal returns (20261025T143714Z)

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

## Comparison with the original 2-SD selection

The original rule flagged 263 days as abnormal. 0 of the 26 news days are among them. That overlap is the number the old dashboard implicitly treated as a finding. Under a proper
event study it is neither necessary nor sufficient: an event can move the price without
crossing 2 SD on the day, and a 2-SD day can have no news at all.

## Limitations

- 41 events is a small sample. The BMP test is the more trustworthy of the two here, but
  neither has power to detect effects smaller than roughly 1% CAR.
- The market model assumes a stable beta over the estimation window; a structural break
  around the event would bias the abnormal return.
- Publication timestamps are not the moment the market learned the news. Articles published
  after the close are attributed to that day, which shifts some events by one trading day.
- No attempt is made to separate CEO-speech effects from other news on the same day.
