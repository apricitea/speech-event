# speech-event

Event study measuring whether BBRI (Bank Rakyat Indonesia) CEO-speech news
coincides with abnormal stock price moves, plus a local-LLM sentiment pass
over the scraped articles. Built on public Yahoo Finance price data and
public news content.

## Pipeline

1. **Price data** (`notebooks/crawl-stockprice.ipynb`) — pulls BBRI and IHSG
   (Jakarta Composite Index) daily prices via `yfinance`, fits a market-model
   regression (`BBRI return ~ IHSG return`), and flags days where the actual
   return deviates from the model's prediction by more than 2 standard
   deviations as abnormal-return days.
2. **News scraping** (`notebooks/crawl-news.ipynb`) — searches for BRI-CEO-related
   keywords, scrapes matching articles, and stores them in Postgres.
3. **Event alignment** (`notebooks/event-analysis.ipynb`) — joins abnormal-return
   days against article publish dates to find news days that line up with
   unusual price moves.
4. **Sentiment scoring** (`notebooks/sentiment-analysis.ipynb`) — runs each
   article through a local LLM (Ollama, `llama3`) to classify sentiment on a
   7-point scale (Very Negative → Very Positive, plus Not Relevant for
   keyword-search noise), extract the main topic, and summarize the content.
5. **Dashboard** (`Home.py` + `pages/`) — Streamlit app to browse prices,
   articles, event-study flags, and sentiment scores interactively.

## Method note

The abnormal-return flagging is a standard market-model event study (CAPM-style
single-factor regression against the index), not a trained predictive model —
this is a study of what happened around news days historically, not a
forecast.

## Stack

Python · pandas · statsmodels (OLS) · yfinance · Streamlit · Plotly ·
PostgreSQL (Supabase) · SQLAlchemy · Ollama (llama3)

## Setup

```bash
poetry install
cp .env.example .env  # fill in your own Postgres credentials
streamlit run Home.py
```

Requires a running Postgres instance (schema: `public.textual_data`) and a
local Ollama daemon with `llama3` pulled for the sentiment notebook.

---

## Data provenance

`notebooks/**/*.csv` contains article text scraped from Indonesian news publishers
(including kompas.com, republika.co.id, bisnis.com and infobanknews.com) together with
daily price history for BBRI and the IHSG sourced from Yahoo Finance.

The article text belongs to its respective publishers and the price data to its provider.
Neither is **our work**, no licence is asserted over either, and both are committed only so
that the event study can be reproduced without re-crawling. The analysis code is ours (MIT).
