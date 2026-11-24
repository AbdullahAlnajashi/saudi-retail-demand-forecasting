# IS 366 Project 1 - Google Trends retail demand forecasting (Saudi Arabia)

**Dataset (No. 18):** Google Trends "Interest over time", Saudi Arabia, monthly, Jan 2004 - Oct 2026, terms: ايفون (iPhone), عطور (perfume), Deep fryer, شنطة (bag), حطب (firewood). Exported 3 Nov 2026 from https://trends.google.com/trends/explore. Search interest is a *proxy* for demand, not sales. Data is governed by Google's Terms of Service.

## How to reproduce
1. `pip install -r requirements.txt`
2. Keep this folder structure; `data/google_trends_SA_raw.csv` is the raw export. The scripts can be run from any working directory.
3. `python analysis.py` - cleans data, runs descriptive analytics, backtests 4 models, forecasts Nov 2026 - Oct 2027, writes `data/clean_monthly_2015_2026.csv`, `results/*`, `figures/*`. Google's `<1` values are read as 0.5; missing months are filled by linear interpolation (both counted in `results/data_quality_audit.json`).
4. `python build_dashboard.py` - builds `dashboard.html`. Open it in a browser (needs internet for the Chart.js library).
5. `python check_results.py` - optional sanity checks on the outputs (metrics, no leakage, forecast ranges).

Works in Google Colab: upload the folder, then run both scripts.

## Re-downloading the data
trends.google.com/trends/explore -> Location: Saudi Arabia, Time: 2004 - present -> add the 5 terms as comparisons -> download the "Interest over time" CSV and save it as `data/google_trends_SA_raw.csv`. Re-downloads can differ slightly because Google samples the data.

## Contents
| File | Purpose |
|---|---|
| analysis.py | Full pipeline (cleaning, descriptive, models, forecast, figures) |
| build_dashboard.py / dashboard.html | Decision-support prototype (Deliverable 4) |
| check_results.py | Sanity checks on the outputs |
| requirements.txt | Python dependencies |
| data/ | Raw export and cleaned monthly data (2015-2026) |
| results/ | Metrics, forecasts, seasonal index, annual averages, audit |
| figures/ | fig1-fig5 PNG charts |
| 01_dataset_approval_submission.md | Deliverable 1 text |

## Method summary
Window Jan 2015 - Oct 2026 (142 months). Models: naive, seasonal naive (baseline), damped additive Holt-Winters (own implementation), Ridge on lags + month. Expanding-window backtest, three 12-month test windows; metrics MAE, RMSE, MAPE (MAPE skipped for low-volume series). Best MAE model per product is refitted on all data for the 12-month forecast; 80% ranges = forecast +/- 1.28 x backtest RMSE (approximate).
