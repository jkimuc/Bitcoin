"""Reproduce the offline Bitcoin dashboard from the bundled, unmodified source CSV."""
from pathlib import Path
import base64
import hashlib
import json
import platform
import numpy as np
import pandas as pd
import scipy
from scipy.stats import t, norm, linregress
import plotly
from plotly.offline import get_plotlyjs

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data'
TARGET = pd.Timestamp('2030-11-01')
AS_OF = pd.Timestamp('2026-10-27')
RAW_URL = 'https://raw.githubusercontent.com/coinmetrics/data/master/csv/btc.csv'
raw = DATA / 'coinmetrics_btc.csv'
source = pd.read_csv(raw)
# Audit files are local evidence, never a reason to silently refresh or splice data.
def audit_file(name):
    path = DATA / 'audit' / name
    return json.loads(path.read_text()) if path.exists() else None
upstream_pin = audit_file('upstream_pin.json')
if upstream_pin and upstream_pin.get('matches_original'):
    assert upstream_pin['sha256'] == hashlib.sha256(raw.read_bytes()).hexdigest()
source['time'] = pd.to_datetime(source['time'], errors='raise')
assert not source.time.duplicated().any(), 'Duplicate source timestamps'
available = source.loc[source.PriceUSD.notna(), ['time', 'PriceUSD']].copy()
assert np.isfinite(available.PriceUSD).all() and (available.PriceUSD > 0).all()
assert (available.time <= AS_OF).all(), 'Unexpected future observations'
available = available.sort_values('time').reset_index(drop=True)
assert available.time.diff().dropna().eq(pd.Timedelta(days=1)).all(), 'Daily coverage has gaps'
available.columns = ['date', 'price_usd']
available['ln_price'] = np.log(available.price_usd)
available.to_csv(DATA / 'prices_daily.csv', index=False, float_format='%.12g')
ORIGIN = available.date.min()

def design(dates):
    years = np.asarray((pd.DatetimeIndex(dates) - ORIGIN).days, dtype=float) / 365.25
    return np.column_stack([np.ones(len(years)), years])

def fit(frame):
    X = design(frame.date)
    y = frame.ln_price.to_numpy()
    beta = np.linalg.lstsq(X, y, rcond=None)[0]
    residual = y - X @ beta
    n, k = X.shape
    inv = np.linalg.inv(X.T @ X)
    sigma2 = float(residual @ residual / (n-k))
    # Newey-West: Bartlett weights, fixed 90 daily lags, finite-sample n/(n-k).
    scores = X * residual[:, None]
    meat = scores.T @ scores
    lag = min(90, n-1)
    for j in range(1, lag+1):
        cross = scores[j:].T @ scores[:-j]
        meat += (1-j/(lag+1)) * (cross + cross.T)
    hac = inv @ meat @ inv * n/(n-k)
    check = linregress(X[:, 1], y)
    assert np.allclose(beta, [check.intercept, check.slope], atol=1e-9)
    assert np.linalg.eigvalsh(hac).min() >= -1e-10
    return dict(beta=beta, iid=sigma2*inv, hac=hac, sigma2=sigma2, n=n,
                r2=float(1-residual@residual/np.sum((y-y.mean())**2)),
                lag1=float(np.corrcoef(residual[:-1], residual[1:])[0,1]),
                dw=float(np.sum(np.diff(residual)**2)/np.sum(residual**2)),
                rmse_log=float(np.sqrt(np.mean(residual**2))))

def predict(model, dates):
    X = design(dates)
    mu = X @ model['beta']
    se_iid = np.sqrt(np.einsum('ij,jk,ik->i', X, model['iid'], X))
    se_hac = np.sqrt(np.maximum(0, np.einsum('ij,jk,ik->i', X, model['hac'], X)))
    tc = t.ppf(.975, model['n']-2)
    zi = norm.ppf(.975)
    ps = np.sqrt(model['sigma2']+se_iid**2)
    return dict(mu=mu, iid_low=mu-tc*se_iid, iid_high=mu+tc*se_iid,
                hac_low=mu-zi*se_hac, hac_high=mu+zi*se_hac,
                prediction_low=mu-tc*ps, prediction_high=mu+tc*ps)

def serial(v):
    if isinstance(v, np.ndarray): return v.tolist()
    if isinstance(v, np.generic): return v.item()
    raise TypeError(type(v).__name__)

scenarios = {}
forecast_dates = pd.date_range(ORIGIN, '2030-11-30', freq='D')
chart_dates = pd.date_range(ORIGIN, '2030-11-30', freq='14D').union(pd.DatetimeIndex([available.date.max(), TARGET, pd.Timestamp('2030-11-30')])).sort_values()
for name, start in [('Full history', ORIGIN), ('Since 2015', pd.Timestamp('2015-01-01')), ('Since 2020', pd.Timestamp('2020-01-01'))]:
    frame = available[available.date >= start]
    model = fit(frame)
    pred = predict(model, chart_dates)
    target = {k: float(v[0]) for k, v in predict(model, [TARGET]).items()}
    november_end = float(np.exp(predict(model, [pd.Timestamp('2030-11-30')])['mu'][0]))
    scenarios[name] = dict(start=frame.date.min().strftime('%Y-%m-%d'), end=frame.date.max().strftime('%Y-%m-%d'),
        model=model, target_log=target, target_usd={k: float(np.exp(v)) for k,v in target.items()}, november_end_usd=november_end,
        dates=chart_dates.strftime('%Y-%m-%d').tolist(), **{k:v.tolist() for k,v in pred.items()})
full = scenarios['Full history']['model']
allpred = predict(full, forecast_dates)
out = pd.DataFrame({'date': forecast_dates.strftime('%Y-%m-%d')})
for k,v in allpred.items():
    out['log_'+k] = v
    out['usd_'+('median' if k=='mu' else k)] = np.exp(v)
out.to_csv(DATA / 'fitted_and_forecast_daily.csv', index=False, float_format='%.12g')
# A real holdout: fit only through 2020, then predict every observed day after it.
train = available[available.date <= '2020-12-31']
held = available[available.date > '2020-12-31']
btmodel = fit(train)
btp = predict(btmodel, held.date)
btmed = np.exp(btp['mu'])
backtest = dict(train_end='2020-12-31', test_start=str(held.date.min().date()), test_end=str(held.date.max().date()),
    n=len(held), last_prediction_usd=float(btmed[-1]), last_actual_usd=float(held.price_usd.iloc[-1]),
    median_absolute_percentage_error=float(np.median(np.abs(btmed-held.price_usd)/held.price_usd)*100),
    iid_prediction_interval_coverage=float(np.mean((held.ln_price>=btp['prediction_low']) & (held.ln_price<=btp['prediction_high']))*100),
    log_rmse=float(np.sqrt(np.mean((held.ln_price-btp['mu'])**2))))
pd.DataFrame({'date':held.date, 'actual_usd':held.price_usd, 'forecast_median_usd':btmed,
    'iid_prediction_low_usd':np.exp(btp['prediction_low']), 'iid_prediction_high_usd':np.exp(btp['prediction_high'])}).to_csv(DATA/'holdout_predictions.csv', index=False)
provenance = dict(provider='Coin Metrics Community data archive', metric='PriceUSD', url=RAW_URL,
    source_readme='https://github.com/coinmetrics/data', retrieved_on='2026-10-27',
    sha256=hashlib.sha256(raw.read_bytes()).hexdigest(), raw_rows=len(source), price_rows=len(available),
    first_date=str(ORIGIN.date()), last_date=str(available.date.max().date()), missing_days=0, duplicate_dates=0,
    missing_price_rows_excluded=int(source.PriceUSD.isna().sum()),
    upstream_commit=upstream_pin['commit'] if upstream_pin else None,
    pinned_url=upstream_pin['pinned_url'] if upstream_pin else None,
    license='CC BY-NC 4.0 — attribution and noncommercial use required',
    limitations='Rechecked snapshot still ends May 23, 2026, with identical source bytes. Live Coin Metrics, Coinbase, FRED, Yahoo and CryptoDataDownload requests failed at proxy CONNECT (403), consistent with missing host allowlisting, before provider responses. October data availability and independent cross-provider validation therefore remain unverified, not disproven. Git master was resolved through native Git and the commit-pinned CSV matches the original SHA-256. Early thin-market values are provider estimates, not universally executable prices.')
results = dict(provenance=provenance, target_date='2030-11-01', target_definition='Start-of-month dated estimate, not a monthly average or guaranteed settlement price',
    year_length_days=365.25, hac_lags=90, scenarios=scenarios, holdout=backtest,
    versions=dict(python=platform.python_version(), numpy=np.__version__, pandas=pd.__version__, scipy=scipy.__version__, plotly=plotly.__version__))
results['source_extension_audit'] = audit_file('source_checks.json')
results['network_findings'] = audit_file('network_findings.json')
verification = audit_file('calculation_verification.json')
checked_outputs_sha256 = hashlib.sha256(json.dumps({k: results[k] for k in ['target_date','year_length_days','hac_lags','scenarios','holdout']}, sort_keys=True, separators=(',', ':'), default=serial).encode()).hexdigest()
if verification and verification.get('input_sha256') == provenance['sha256'] and verification.get('checked_outputs_sha256') == checked_outputs_sha256:
    results['independent_verification'] = verification
else:
    results['independent_verification'] = {'status': 'not-current', 'note': 'Run verify_calculations.py, then analysis.py to embed a current independent audit.'}
(DATA/'results.json').write_text(json.dumps(results, indent=2, default=serial)+'\n')
# Numerical and export checks (independent slope/intercept check runs in fit).
assert full['n'] == len(available) > 5000
for scenario in scenarios.values():
    p=scenario['target_log']
    assert p['hac_low'] < p['mu'] < p['hac_high']
    assert p['prediction_low'] < p['iid_low'] < p['mu'] < p['iid_high'] < p['prediction_high']
    assert np.isclose(np.log(scenario['target_usd']['mu']), p['mu'])
assert len(pd.read_csv(DATA/'fitted_and_forecast_daily.csv')) == len(forecast_dates)

payload = dict(results=results, actual_dates=available.date.dt.strftime('%Y-%m-%d').tolist(), prices=available.price_usd.tolist(), logs=available.ln_price.tolist(),
    holdout=dict(dates=held.date.dt.strftime('%Y-%m-%d').tolist(), actual=held.price_usd.tolist(), predicted=btmed.tolist()))
downloads = {}
for label, path in [('prices_daily.csv',DATA/'prices_daily.csv'), ('results.json',DATA/'results.json'), ('fitted_and_forecast_daily.csv',DATA/'fitted_and_forecast_daily.csv'), ('holdout_predictions.csv',DATA/'holdout_predictions.csv'), ('analysis.py',ROOT/'analysis.py')]:
    downloads[label] = base64.b64encode(path.read_bytes()).decode()
for name in ['calculation_verification.json', 'source_checks.json', 'upstream_pin.json', 'network_findings.json']:
    path = DATA/'audit'/name
    if path.exists(): downloads[name] = base64.b64encode(path.read_bytes()).decode()
template = (ROOT/'dashboard_template.html').read_text()
html = template.replace('/*__PLOTLY__*/', get_plotlyjs()).replace('/*__PAYLOAD__*/', json.dumps(payload, default=serial)).replace('/*__DOWNLOADS__*/', json.dumps(downloads))
(ROOT/'index.html').write_text(html)
print(json.dumps(dict(provenance=provenance, targets={k:v['target_usd'] for k,v in scenarios.items()}, diagnostics={k:v for k,v in full.items() if not isinstance(v,np.ndarray)}, holdout=backtest),indent=2))
print('PASS: coverage, positive prices, independent regression, HAC covariance, interval order, exponentiation, CSV roundtrip.')
