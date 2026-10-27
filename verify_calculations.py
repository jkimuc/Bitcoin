"""Independently audit analysis.py outputs using statsmodels, stdlib CSV and math.
Run analysis.py first. This verifier never imports its fitting/prediction routines.
"""
from pathlib import Path
import csv
from datetime import date
import hashlib
import json
import math
import numpy as np
import statsmodels.api as sm
from statsmodels.stats.sandwich_covariance import cov_hac
from scipy.stats import norm, t
import statsmodels

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'
results=json.loads((DATA/'results.json').read_text())
with (DATA/'coinmetrics_btc.csv').open(newline='') as f:
    raw=list(csv.DictReader(f))
observations=[]
for row in raw:
    if row['PriceUSD']:
        d=date.fromisoformat(row['time'])
        price=float(row['PriceUSD'])
        assert math.isfinite(price) and price>0
        observations.append((d,price,math.log(price)))
observations.sort()
assert len({d for d,p,y in observations})==len(observations)
assert all((observations[i][0]-observations[i-1][0]).days==1 for i in range(1,len(observations)))
assert len(observations)==results['provenance']['price_rows']
origin=observations[0][0]
target=date(2030,11,1)
def x_for(dates):
    return np.array([[1.,(d-origin).days/365.25] for d in dates])
x0=x_for([target])
checks=[]
for name,scenario in results['scenarios'].items():
    sample=[o for o in observations if o[0]>=date.fromisoformat(scenario['start'])]
    X=x_for([o[0] for o in sample]); y=np.array([o[2] for o in sample])
    fit=sm.OLS(y,X).fit()
    pred=fit.get_prediction(x0).summary_frame(alpha=.05).iloc[0]
    hac=cov_hac(fit,nlags=90,use_correction=True)
    hac_var=float((x0@hac@x0.T).item())
    hac_se=math.sqrt(hac_var)
    mu=float(pred['mean'])
    calc=dict(mu=mu,iid_low=float(pred['mean_ci_lower']),iid_high=float(pred['mean_ci_upper']),
        hac_low=mu-norm.ppf(.975)*hac_se,hac_high=mu+norm.ppf(.975)*hac_se,
        prediction_low=float(pred['obs_ci_lower']),prediction_high=float(pred['obs_ci_upper']))
    np.testing.assert_allclose(fit.params,scenario['model']['beta'],rtol=1e-11,atol=1e-11)
    np.testing.assert_allclose(fit.cov_params(),scenario['model']['iid'],rtol=1e-10,atol=1e-12)
    np.testing.assert_allclose(hac,scenario['model']['hac'],rtol=1e-10,atol=1e-12)
    np.testing.assert_allclose([fit.scale,fit.rsquared],[scenario['model']['sigma2'],scenario['model']['r2']],rtol=1e-11)
    for k,v in calc.items():
        np.testing.assert_allclose(v,scenario['target_log'][k],rtol=1e-11,atol=1e-11)
        # math.exp is an independent back-transform, not 10**x, or exp(x+variance/2).
        np.testing.assert_allclose(math.exp(v),scenario['target_usd'][k],rtol=1e-10)
    dates=[date.fromisoformat(d) for d in scenario['dates']]
    grid=fit.get_prediction(x_for(dates)).summary_frame(alpha=.05)
    Xgrid=x_for(dates)
    grid_hac_se=np.sqrt(np.einsum('ij,jk,ik->i',Xgrid,hac,Xgrid))
    grid_expected=dict(mu=grid['mean'],iid_low=grid['mean_ci_lower'],iid_high=grid['mean_ci_upper'],
        prediction_low=grid['obs_ci_lower'],prediction_high=grid['obs_ci_upper'],
        hac_low=grid['mean']-norm.ppf(.975)*grid_hac_se,hac_high=grid['mean']+norm.ppf(.975)*grid_hac_se)
    for key,value in grid_expected.items():
        np.testing.assert_allclose(value,scenario[key],rtol=1e-10,atol=1e-11)
    if name=='Full history':
        full_fit=fit
    checks.append(dict(scenario=name,n=int(fit.nobs),alpha=float(fit.params[0]),beta_per_year=float(fit.params[1]),
        sigma_squared=float(fit.scale),r_squared=float(fit.rsquared),target_time_years=float(x0[0,1]),
        target_log=calc,target_usd={k:math.exp(v) for k,v in calc.items()},
        target_se_iid=float(pred['mean_se']),target_se_hac=hac_se,
        student_t_critical=float(t.ppf(.975,fit.df_resid)),normal_critical=float(norm.ppf(.975)),
        max_abs_beta_difference=float(np.max(np.abs(fit.params-scenario['model']['beta']))),
        max_abs_hac_cov_difference=float(np.max(np.abs(hac-scenario['model']['hac']))),
        illustrative_iid_lognormal_mean_usd=math.exp(mu+fit.scale/2)))
# Independently check every exported full-history daily value, including both bands.
with (DATA/'fitted_and_forecast_daily.csv').open(newline='') as f: daily=list(csv.DictReader(f))
Xf=x_for([date.fromisoformat(r['date']) for r in daily])
fp=full_fit.get_prediction(Xf).summary_frame(alpha=.05)
fhac=cov_hac(full_fit,nlags=90,use_correction=True)
hse=np.sqrt(np.einsum('ij,jk,ik->i',Xf,fhac,Xf))
expected=dict(mu=fp['mean'].to_numpy(),iid_low=fp['mean_ci_lower'].to_numpy(),iid_high=fp['mean_ci_upper'].to_numpy(),
    hac_low=fp['mean'].to_numpy()-norm.ppf(.975)*hse,hac_high=fp['mean'].to_numpy()+norm.ppf(.975)*hse,
    prediction_low=fp['obs_ci_lower'].to_numpy(),prediction_high=fp['obs_ci_upper'].to_numpy())
for k,v in expected.items():
    np.testing.assert_allclose([float(r['log_'+k]) for r in daily],v,rtol=1e-9,atol=1e-10)
    np.testing.assert_allclose([float(r['usd_'+('median' if k=='mu' else k)]) for r in daily],np.exp(v),rtol=1e-9)
# Independently reproduce the holdout and its interval coverage.
train=[o for o in observations if o[0]<=date(2020,12,31)]
test=[o for o in observations if o[0]>date(2020,12,31)]
btf=sm.OLS([o[2] for o in train],x_for([o[0] for o in train])).fit()
btp=btf.get_prediction(x_for([o[0] for o in test])).summary_frame(alpha=.05)
actual=np.array([o[1] for o in test]); actual_log=np.array([o[2] for o in test]); median=np.exp(btp['mean'].to_numpy())
btcalc=dict(n=len(test),last_prediction_usd=float(median[-1]),last_actual_usd=float(actual[-1]),
    median_absolute_percentage_error=float(np.median(np.abs(median-actual)/actual)*100),
    iid_prediction_interval_coverage=float(np.mean((actual_log>=btp['obs_ci_lower'])&(actual_log<=btp['obs_ci_upper']))*100),
    log_rmse=float(np.sqrt(np.mean((actual_log-btp['mean'].to_numpy())**2))))
for k,v in btcalc.items():np.testing.assert_allclose(v,results['holdout'][k],rtol=1e-10)
checked_outputs_sha256=hashlib.sha256(json.dumps({k:results[k] for k in ['target_date','year_length_days','hac_lags','scenarios','holdout']},sort_keys=True,separators=(',',':')).encode()).hexdigest()
report=dict(checked_outputs_sha256=checked_outputs_sha256,status='passed',as_of='2026-10-27',independent_library='statsmodels '+statsmodels.__version__,
    tolerances=dict(coefficients_rtol=1e-11,coefficients_atol=1e-11,covariance_rtol=1e-10,covariance_atol=1e-12,target_log_rtol=1e-11,target_log_atol=1e-11,target_usd_rtol=1e-10,daily_export_rtol=1e-9,daily_export_log_atol=1e-10),
    input_sha256=hashlib.sha256((DATA/'coinmetrics_btc.csv').read_bytes()).hexdigest(),
    target_date=target.isoformat(),checks=['All three OLS fits, residual variance and R²','Classical OLS covariance and Student-t mean confidence intervals',
        'Newey–West HAC covariance: 90 lags, Bartlett weights, finite-sample correction','HAC asymptotic normal mean confidence intervals',
        'Student-t IID single-observation prediction intervals','Natural-log to USD conversion with math.exp for every target endpoint',
        'All exported daily full-history model values and intervals','All scenario chart means and every confidence/prediction endpoint','Chronological holdout predictions, error and coverage'],
    scenarios=checks,export_daily_rows=len(daily),holdout=btcalc,
    interpretation='Arithmetic is correct. exp(E[ln P|t]) is a geometric-mean trend, and a median only under the stated log-error assumption. It is not E[P|t]. Correct arithmetic does not validate exponential growth or calibrate future-price probabilities.')
(DATA/'audit'/'calculation_verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
