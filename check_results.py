"""Sanity checks on the outputs of analysis.py (run it first). Run: python check_results.py
Re-derives the key numbers from the saved files without reusing analysis.py code; exits 1 if any check fails."""
import os, sys, numpy as np, pandas as pd
os.chdir(os.path.dirname(os.path.abspath(__file__)))
fails = []
def check(cond, msg):
    print(("PASS " if cond else "FAIL ") + msg)
    if not cond: fails.append(msg)
df = pd.read_csv("data/clean_monthly_2015_2026.csv", parse_dates=["Time"]).set_index("Time")
pr = pd.read_csv("results/backtest_predictions.csv", parse_dates=["date"])
met = pd.read_csv("results/model_metrics_backtest.csv")
fc = pd.read_csv("results/forecast_nov2026_oct2027.csv", parse_dates=["date"])
check(df.notna().all().all() and df.index.is_monotonic_increasing and (df.index.to_series().diff().dropna().dt.days.between(28, 31)).all(),
      "clean data: no missing values, consecutive months")
check(((df >= 0) & (df <= 100)).all().all(), "clean data: values within 0-100")
# metrics recomputed from the saved backtest predictions
for (s, m), g in pr.groupby(["series", "model"]):
    row = met[(met.series == s) & (met.model == m)].iloc[0]
    mae, rmse = (g.actual - g.pred).abs().mean(), np.sqrt(((g.actual - g.pred) ** 2).mean())
    check(abs(mae - row.MAE) < .006 and abs(rmse - row.RMSE) < .006 and len(g) == 36, f"metrics {s} / {m}")
check((pr.apply(lambda r: df.loc[r.date, r.series], axis=1) == pr.actual).all(), "backtest actuals match the data")
w = pr.groupby("fold").date.agg(["min", "max"])
check(all(w["max"].iloc[i] < w["min"].iloc[i + 1] for i in range(len(w) - 1)) and w["max"].iloc[-1] == df.index[-1],
      "test windows are consecutive and end at the last month")
# no leakage: naive forecast = last value before each test window; seasonal naive = same month a year earlier
nv = pr[pr.model == "Naive"]
check((nv.apply(lambda r: df.loc[w.loc[r.fold, "min"] - pd.DateOffset(months=1), r.series], axis=1) == nv.pred).all(),
      "naive uses only data before the test window")
sn = pr[pr.model.str.contains("baseline")]
check((sn.apply(lambda r: df.loc[r.date - pd.DateOffset(months=12), r.series], axis=1) == sn.pred).all(), "seasonal naive = value 12 months earlier")
# final forecast: lowest-MAE model, 12 months after the data, 80% band = +/- 1.28 x RMSE clipped to 0-100
best = pr.assign(e=(pr.actual - pr.pred).abs()).groupby(["series", "model"]).e.mean().groupby(level=0).idxmin().map(lambda t: t[1])
check((fc.groupby("series").model.first() == best).all(), "forecast uses the lowest-MAE model")
for s, g in fc.groupby("series"):
    r = met[(met.series == s) & (met.model == best[s])].RMSE.iloc[0]
    check(len(g) == 12 and g.date.iloc[0] == df.index[-1] + pd.DateOffset(months=1), f"{s}: 12-month horizon starts after the data")
    check(np.allclose(g.lo80, np.maximum(0, g.forecast - 1.28 * r), atol=.11) and np.allclose(g.hi80, np.minimum(100, g.forecast + 1.28 * r), atol=.11),
          f"{s}: 80% range")
print(f"\n{len(fails)} failed" if fails else "\nAll checks passed")
sys.exit(1 if fails else 0)
