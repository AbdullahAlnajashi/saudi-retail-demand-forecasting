"""IS 366 Project 1 - Google Trends retail demand (Saudi Arabia). Run: python analysis.py
Needs: pandas numpy scipy scikit-learn matplotlib. Input: data/google_trends_SA_raw.csv"""
import json, os, numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from scipy.optimize import minimize
from sklearn.linear_model import Ridge
os.chdir(os.path.dirname(os.path.abspath(__file__)))   # paths below are relative to this script's folder
NAMES = {"ايفون": "iPhone", "عطور": "Perfume", "Deep fryer": "Deep fryer", "شنطة": "Bag", "حطب": "Firewood"}
START, H, M = "2015-01-01", 12, 12
# ---------- 1. load + clean ----------
raw = pd.read_csv("data/google_trends_SA_raw.csv", parse_dates=["Time"], dtype=str).rename(columns=NAMES).set_index("Time")
lt1 = int(raw.eq("<1").sum().sum())                    # Google writes "<1" for values between 0 and 1
raw = raw.replace("<1", "0.5").apply(pd.to_numeric, errors="coerce")   # any other non-numeric text -> missing
audit = {"rows": len(raw), "first": str(raw.index.min().date()), "last": str(raw.index.max().date()),
         "missing": int(raw.isna().sum().sum()), "lt1_set_to_0.5": lt1, "duplicate_dates": int(raw.index.duplicated().sum()),
         "gaps": int((pd.date_range(raw.index.min(), raw.index.max(), freq="MS").difference(raw.index)).size),
         "out_of_range": int(((raw < 0) | (raw > 100)).sum().sum())}
raw = raw[~raw.index.duplicated()].sort_index().asfreq("MS")   # one row per month; gaps become missing rows
audit["filled_by_interpolation"] = int(raw.isna().sum().sum())
raw = raw.interpolate(limit_direction="both")
df = raw.loc[START:].astype(float)           # modelling window 2015-01 .. 2026-10
audit["model_rows"] = len(df)
audit["zero_share_pre2015"] = raw.loc[:"2014-12"].eq(0).mean().round(2).to_dict()
audit["zero_share_2015plus"] = df.eq(0).mean().round(2).to_dict()
df.to_csv("data/clean_monthly_2015_2026.csv")
# ---------- 2. descriptive ----------
desc = pd.DataFrame({"mean_2015_2026": df.mean(), "max": df.max(), "peak_month": df.idxmax().dt.strftime("%Y-%m"),
                     "mean_last12": df.iloc[-12:].mean(), "mean_prev12": df.iloc[-24:-12].mean()}).round(2)
desc["yoy_change_%"] = ((desc.mean_last12 / desc.mean_prev12.replace(0, np.nan) - 1) * 100).round(1)  # n/a if prior year is 0
desc["rank_last12"] = desc.mean_last12.rank(ascending=False, method="min").astype(int)
desc.to_csv("results/descriptive_summary.csv")
annual = df.groupby(df.index.year).mean().round(1); annual.to_csv("results/annual_average.csv")
full = df.loc[:"2025-12"]
ratio = full.div(full.groupby(full.index.year).transform("mean"))
ratio = ratio.where(full.gt(0).groupby(full.index.year).transform("sum") >= 3)  # skip years with <3 non-zero months (e.g. one stray 1 -> ratio 12)
sidx = ratio.groupby(full.index.month).mean().round(2)
sidx.index.name = "month"; sidx.to_csv("results/seasonal_index.csv")
corr = df.corr().round(2); corr.to_csv("results/correlation.csv")
# ---------- 3. models ----------
def snaive(y, h): return np.array([y[len(y) - M + (i % M)] for i in range(h)])
def naive(y, h): return np.repeat(y[-1], h)
def _hw(p, y, ret=False):
    a, b, g, phi = p; n = len(y)
    l = y[:M].mean(); t = (y[M:2 * M].mean() - y[:M].mean()) / M; s = list(y[:M] - l); sse = 0.0
    for i in range(n):
        f = l + phi * t + s[i % M]; e = y[i] - f; sse += e * e
        l, t, s[i % M] = l + phi * t + a * e, phi * t + b * e, s[i % M] + g * e
    return (l, t, s, n) if ret else sse
def hw(y, h):
    best = min((minimize(_hw, x0, args=(y,), bounds=[(0, 1)] * 3 + [(.8, .98)], method="L-BFGS-B")
                for x0 in ([.3, .05, .2, .9], [.1, .01, .1, .95], [.6, .1, .4, .85])), key=lambda r: r.fun)
    l, t, s, n = _hw(best.x, y, True); phi = best.x[3]
    return np.clip([l + sum(phi ** j for j in range(1, k + 1)) * t + s[(n + k - 1) % M] for k in range(1, h + 1)], 0, 100)
def _feat(hist, month):
    return [hist[-1], hist[-2], hist[-3], hist[-12]] + [1.0 * (month == k) for k in range(1, 12)]
def ridge(y, h, idx_end):
    X, Y = [], []
    for i in range(12, len(y)):
        X.append(_feat(list(y[:i]), (idx_end - pd.DateOffset(months=len(y) - 1 - i)).month)); Y.append(y[i])
    mdl = Ridge(alpha=5.0).fit(X, Y); hist = list(y); out = []
    for k in range(1, h + 1):
        m = (idx_end + pd.DateOffset(months=k)).month; v = float(np.clip(mdl.predict([_feat(hist, m)])[0], 0, 100))
        out.append(v); hist.append(v)
    return np.array(out)
MODELS = {"Naive": lambda y, h, e: naive(y, h), "Seasonal naive (baseline)": lambda y, h, e: snaive(y, h),
          "Holt-Winters (damped, additive)": lambda y, h, e: hw(y, h), "Ridge on lags + month": ridge}
folds = [df.index[-37], df.index[-25], df.index[-13]]      # last training month of each fold; test windows 2023-11..24-10, 2024-11..25-10, 2025-11..26-10
rows, preds = [], []
for c in df.columns:
    for mname, f in MODELS.items():
        P, A = [], []
        for k, cut in enumerate(folds):
            tr = df.loc[:cut, c].values; te = df[c].iloc[df.index.get_loc(cut) + 1: df.index.get_loc(cut) + 1 + H]
            p = f(tr, H, cut); P += list(p); A += list(te.values)
            preds += [{"series": c, "model": mname, "fold": k + 1, "date": d, "actual": a, "pred": q} for d, a, q in zip(te.index, te.values, p)]
        P, A = np.array(P), np.array(A); nz = A > 0
        rows.append({"series": c, "model": mname, "MAE": np.abs(A - P).mean(), "RMSE": np.sqrt(((A - P) ** 2).mean()),
                     "MAPE_%": (np.abs((A - P)[nz] / A[nz]).mean() * 100) if df[c].iloc[-36:].mean() >= 5 else np.nan})
met = pd.DataFrame(rows); pr = pd.DataFrame(preds)
best = met.loc[met.groupby("series").MAE.idxmin()].set_index("series").model.to_dict()   # select on unrounded MAE
met = met.round(2)
base = met[met.model.str.contains("baseline")].set_index("series").MAE
met["MAE_vs_baseline_%"] = ((met.MAE / met.series.map(base) - 1) * 100).round(1)
met.to_csv("results/model_metrics_backtest.csv", index=False); pr.to_csv("results/backtest_predictions.csv", index=False)
# ---------- 4. final forecast (Nov 2026 - Oct 2027) ----------
fidx = pd.date_range(df.index[-1] + pd.DateOffset(months=1), periods=H, freq="MS"); fc = []
for c in df.columns:
    y = df[c].values; p = MODELS[best[c]](y, H, df.index[-1]); rm = met[(met.series == c) & (met.model == best[c])].RMSE.iloc[0]
    for d, v in zip(fidx, p):
        fc.append({"series": c, "date": d, "forecast": round(v, 1), "lo80": round(max(0, v - 1.28 * rm), 1),
                   "hi80": round(min(100, v + 1.28 * rm), 1), "model": best[c]})
fc = pd.DataFrame(fc); fc.to_csv("results/forecast_nov2026_oct2027.csv", index=False)
# ---------- 5. figures ----------
plt.rcParams.update({"figure.dpi": 130, "axes.spines.top": False, "axes.spines.right": False, "font.size": 9})
fig, ax = plt.subplots(2, 1, figsize=(8, 6), sharex=True)
for c in ["iPhone", "Perfume", "Bag"]: ax[0].plot(df.index, df[c], label=c, lw=1.2)
for c in ["Deep fryer", "Firewood"]: ax[1].plot(df.index, df[c], label=c, lw=1.2)
ax[0].set_title("Search interest, Saudi Arabia (index 0-100, common scale)"); ax[1].set_title("Low-volume terms (same scale)")
for a in ax: a.legend(frameon=False); a.set_ylabel("Interest index")
plt.tight_layout(); plt.savefig("figures/fig1_trends.png"); plt.close()
ax = annual.plot(kind="bar", figsize=(8, 3.8), width=.8); ax.set_title("Annual average search interest"); ax.set_xlabel(""); ax.legend(frameon=False, ncol=5)
plt.tight_layout(); plt.savefig("figures/fig2_annual.png"); plt.close()
fig, ax = plt.subplots(figsize=(7, 3.2)); im = ax.imshow(sidx.T.values, cmap="YlOrRd", aspect="auto"); ax.set_yticks(range(5)); ax.set_yticklabels(sidx.columns)
ax.set_xticks(range(12)); ax.set_xticklabels(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]); ax.set_title("Seasonal index (1.0 = average month)")
for i in range(5):
    for j in range(12): ax.text(j, i, f"{sidx.values[j, i]:.1f}", ha="center", va="center", fontsize=7)
plt.colorbar(im); plt.tight_layout(); plt.savefig("figures/fig3_seasonality.png"); plt.close()
fig, ax = plt.subplots(1, 3, figsize=(10, 3), sharey=False)
for a, c in zip(ax, ["iPhone", "Perfume", "Bag"]):
    s = pr[(pr.series == c) & (pr.model == best[c]) & (pr.fold == 3)]; b = pr[(pr.series == c) & pr.model.str.contains("baseline") & (pr.fold == 3)]
    a.plot(df.index[-48:], df[c].iloc[-48:], color="k", lw=1.2, label="Actual"); a.plot(s.date, s.pred, color="C3", lw=1.5, label="Best model"); a.plot(b.date, b.pred, "--", color="C0", lw=1, label="Baseline")
    a.set_title(f"{c}: last 12 months (test)"); a.tick_params(axis="x", rotation=30)
ax[0].legend(frameon=False); plt.tight_layout(); plt.savefig("figures/fig4_backtest.png"); plt.close()
fig, ax = plt.subplots(1, 3, figsize=(10, 3))
for a, c in zip(ax, ["iPhone", "Perfume", "Bag"]):
    f = fc[fc.series == c]; a.plot(df.index[-60:], df[c].iloc[-60:], color="k", lw=1.2, label="Actual (history)")
    a.plot(f.date, f.forecast, color="C3", lw=1.5, label="Forecast"); a.fill_between(f.date, f.lo80, f.hi80, color="C3", alpha=.15, label="80% range"); a.set_title(f"{c}: forecast to Oct 2027"); a.tick_params(axis="x", rotation=30)
ax[0].legend(frameon=False); plt.tight_layout(); plt.savefig("figures/fig5_forecast.png"); plt.close()
# ---------- 6. dashboard data ----------
dash = {"hist": {c: {"d": [d.strftime("%Y-%m") for d in df.index], "v": df[c].tolist()} for c in df.columns},
        "bt": {c: {"d": [d.strftime("%Y-%m") for d in pr[(pr.series == c) & (pr.fold == 3) & pr.model.str.contains("baseline")].date],
                   "a": pr[(pr.series == c) & (pr.fold == 3) & pr.model.str.contains("baseline")].actual.tolist(),
                   "base": pr[(pr.series == c) & (pr.fold == 3) & pr.model.str.contains("baseline")].pred.round(1).tolist(),
                   "best": pr[(pr.series == c) & (pr.fold == 3) & (pr.model == best[c])].pred.round(1).tolist()} for c in df.columns},
        "fc": {c: {"d": fc[fc.series == c].date.dt.strftime("%Y-%m").tolist(), "f": fc[fc.series == c].forecast.tolist(),
                   "lo": fc[fc.series == c].lo80.tolist(), "hi": fc[fc.series == c].hi80.tolist(), "model": best[c]} for c in df.columns},
        "seas": {c: [None if pd.isna(v) else v for v in sidx[c]] for c in df.columns}, "annual": {"y": [int(i) for i in annual.index], **{c: annual[c].tolist() for c in df.columns}},
        "desc": json.loads(desc.reset_index().rename(columns={"index": "series"}).to_json(orient="records")),   # NaN -> null
        "metrics": met.fillna(-1).to_dict("records"), "best": best}
with open("results/dashboard_data.json", "w") as f: json.dump(dash, f)
with open("results/data_quality_audit.json", "w") as f: json.dump(audit, f, indent=1)
print(json.dumps(audit, indent=1)); print(desc.to_string()); print(annual.to_string()); print(sidx.to_string()); print(corr.to_string())
print(met.to_string()); print("BEST", best); print(fc[fc.date.isin([fidx[0], fidx[5], fidx[-1]])].to_string())
