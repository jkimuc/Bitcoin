# Bitcoin: history and the November 2030 horizon

A self-contained, interactive HTML research dashboard. Open **index.html** in a modern desktop or mobile browser. It bundles Plotly, daily observations, model output and audit downloads; it requires no CDN, API key, web server or internet connection. Only optional external source links need internet.

## View the finished website

The chat's file viewer may display HTML source. **Download and extract the project ZIP first**, then open the extracted `bitcoin-dashboard/index.html` with your browser (for example, use the browser's Open File command). This does not require Python or internet access.

For a local browser preview, install Python 3 if needed, open a terminal in the extracted folder and run:

```bash
python preview.py
```

On Windows, `py preview.py` is an alternative. The launcher serves the actual HTML with a `text/html` content type and opens your default browser. Keep its terminal open while viewing; stop it with Ctrl+C. No packages need installing. If the default port is busy, use `python preview.py --port 8001`.

This preview runs on your computer. The cloud onboarding environment does not expose a public web preview or port-forwarding service, so this package does not include a hosted preview URL. None of the model results or dashboard design is changed by the launcher.

## What is included

- Daily Coin Metrics `PriceUSD`: **5,789 observations, July 18, 2010–May 23, 2026**.
- An interactive dollar-price chart (linear by default), a natural-log price chart with OLS regression and selectable 95% mean-trend confidence bands, and a chronological holdout chart.
- Fit-period sensitivity controls, optional dollar-chart forecast overlay, native zoom, hover, range buttons and PNG export.
- A November **1**, 2030 estimate; November 30 is also reported in the methodology. These are dated point estimates, not a monthly average.
- Classical IID and Newey–West HAC (90 lags) mean-log trend intervals, transformed back to dollars. A separate IID single-observation prediction interval illustrates the distinction between trend estimation and price uncertainty.
- Offline downloads of the cleaned prices, model results, daily full-history model predictions, holdout predictions and Python analysis script.

## What the calculation actually says

The full-history OLS model predicts a conditional median of **$12,797,820** on November 1, 2030. Its conditional 95% HAC trend band is approximately **$4,994,014–$32,796,105**, and its IID prediction interval is approximately **$1,031,829–$158,731,932**.

**These are not credible calibrated market-price probabilities.** Residuals are strongly dependent (lag-1 correlation about 0.9993); constant exponential growth is a poor structural assumption. Restricting the fit to 2020 onward changes the point estimate to **$470,381**. A model fit only through 2020 predicted **$10,220,751** on May 23, 2026 versus an actual **$76,620**. Its nominal 95% IID prediction interval covered only **26.9%** of the 1,969 withheld daily observations. The dashboard displays these weaknesses prominently rather than presenting the extrapolation as a reliable target.

## Data provenance and verification limits

Original data: https://raw.githubusercontent.com/coinmetrics/data/master/csv/btc.csv

Provider and documentation: https://github.com/coinmetrics/data and https://docs.coinmetrics.io/asset-metrics/market/price

Downloaded October 27, 2026. The unchanged original CSV is retained in `data/coinmetrics_btc.csv`; its SHA-256 is:

```
06495ff8e643432e6948b7b4686ce44fc106217287dabdc1b38351d9ddec46c3
```

The download has 6,351 rows, including 562 rows without PriceUSD. Those missing-price rows are excluded, not filled. All 5,789 usable observations are finite and positive, with unique timestamps and uninterrupted daily coverage. No pre-series prices are invented. The 2010 start date is the earliest usable date in this source, not a certification that no earlier historical quotes exist. Early thin-market data should be treated cautiously.

The available archive still ends **May 23, 2026**, 157 days before the analysis date. A fresh download was identical. Requests to the live Coin Metrics Community API (including its catalog), Coinbase Exchange, FRED's Coinbase series, Yahoo BTC-USD and CryptoDataDownload's Bitstamp series all failed at **proxy CONNECT with HTTP 403**, before provider HTTP responses. The configured network policy is restricted and omits these provider hosts. This is an environment access blocker, not proof that reliable October prices are unavailable. No later data or cross-provider validation could be verified, so no unvalidated splice or synthetic extension was made.

The GitHub commit-metadata API was also blocked, but **native Git access worked**. Resolving `refs/heads/master` yielded commit **f1a36afb962731c387bb03982758ab0103063da5**. Downloading the exact [commit-pinned CSV](https://raw.githubusercontent.com/coinmetrics/data/f1a36afb962731c387bb03982758ab0103063da5/csv/btc.csv) reproduced the retained source bytes and SHA-256. This pins provenance; it does not certify market-wide execution prices or independently validate provider accuracy.

To retry newer data with the same methodology, allow `community-api.coinmetrics.io` in environment network settings. For an independent overlap check, `api.exchange.coinbase.com` would permit retrying public Coinbase Exchange candles. Access would enable verification, not guarantee coverage. No provider credentials were shown to be missing. As of October 27, only completed daily intervals through October 26 under a UTC day-start label should be included; the full month of October is not yet complete.

The longest span verified here remains July 18, 2010–May 23, 2026. This is the usable span of the verified Coin Metrics archive, not a claim that no earlier reliable quotes or newer reliable series exist anywhere. Exact endpoints, failures, network findings and upstream pin are preserved under `data/audit/`.

Coin Metrics makes these data available under **CC BY-NC 4.0**: https://creativecommons.org/licenses/by-nc/4.0/. The provider's downloaded README is included as `data/SOURCE_README.md`. Attribute Coin Metrics and observe the noncommercial restriction when reusing or distributing its data. This project does not relicense the underlying data or bundled Plotly code.

## Reproduce the analysis and build

Requires Python 3.12 (tested with 3.12.14).

```bash
cd /path/to/Bitcoin
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python analysis.py
```

Windows activation: `.venv\Scripts\activate`.

After installing the pinned requirements, analysis and HTML generation run entirely from the bundled files without network access. The script regenerates `index.html` and numerical outputs. It deliberately does not refresh the historical source implicitly. Updating the source requires recording new provenance and revalidating the dated coverage messages in the template.

For the independent second-pass calculation audit:

```bash
python -m pip install -r requirements-audit.txt
python verify_calculations.py
python analysis.py
```

The verifier independently parses the raw CSV with the standard library and uses **statsmodels 0.14.6**, without importing the dashboard's fit routines. It compares all three regressions, residual variance, R², classical covariance and Student-t intervals, Newey–West HAC covariance and normal intervals, all chart endpoints, every daily full-history exported value, and the historical holdout. It separately checks natural-log back-transforms using `math.exp`. Results and tolerances are saved in `data/audit/calculation_verification.json`. On this snapshot, all checks passed; the full-history coefficient difference was below 6e-15 and HAC covariance difference below 9e-16. The HTML embeds an independent "passed" report only when its input hash and numerical-output fingerprint match the current calculation.

For the full-history fit, `alpha = 1.7341007178898267`, `beta = 0.7210710558323071` per year, and `t(2030-11-01) = 20.290212183436` years. Thus `mu = 16.364785440061567` and `exp(mu) = $12,797,820.488576526` in the independent computation (differences from the production output are floating-point roundoff). Classical 95% mean-log CI: 16.2694781278–16.4600927523 (USD $11,634,416–$14,077,562). HAC 95% mean-log CI: 15.4237505702–17.3058203099 (USD $4,994,014–$32,796,105). IID 95% prediction interval: 13.8468435068–18.8827273733 (USD $1,031,829–$158,731,932).

The transform is **exp(mu)**, not `10**mu`. This is a geometric-mean trend, and a median under the stated log-error assumption. It is not an arithmetic expected dollar price. A hypothetical IID lognormal mean would require `exp(mu + sigma_squared/2)` (about $29.16m here); this adds an unvalidated distributional assumption and is intentionally not the dashboard's point forecast.

The statistical model is `ln(P) = alpha + beta * t + error`, where `t` is elapsed calendar days from July 18, 2010 divided by 365.25. Every included daily observation has equal weight. OLS uses NumPy least squares and is independently checked against SciPy `linregress`. Classical covariance is `s² (X'X)^-1`, with `s² = SSE/(n-2)` and Student-t critical values. HAC uses a Newey–West sandwich, Bartlett weights, 90 daily lags, an `n/(n-2)` correction and asymptotic normal critical values. Exponentiation preserves endpoint order. No lognormal mean correction is applied: the dollar point is an exponentiated fitted log value (a model median under zero-median symmetric log errors), not a mean price.

The selected mean-log band does not include future observation noise. The IID prediction interval adds residual variance but is not robust to the observed dynamics. HAC does not make a nonstationary trend predictive, and a 90-lag choice does not cover all long-memory behavior. Intervals are pointwise, conditional on the model, not simultaneous bands or market-calibrated probabilities.

A chronological holdout fits only through December 31, 2020 and evaluates every available later day without refitting. This is one disclosed split, not a tuned or comprehensive backtesting exercise.

## Files

| File | Purpose |
| --- | --- |
| `index.html` | Finished self-contained dashboard; open this file |
| `preview.py` | Standard-library local server that opens the rendered dashboard in your default browser |
| `analysis.py` | Statistical analysis, validation assertions, numerical exports and HTML generation |
| `dashboard_template.html` | Editable HTML/CSS/JavaScript template; run analysis.py after edits |
| `requirements.txt` | Pinned numerical and chart dependencies |
| `data/coinmetrics_btc.csv` | Unmodified downloaded source |
| `data/prices_daily.csv` | Clean daily date, USD price and natural log |
| `data/results.json` | Provenance, versions, model coefficients/covariances, all three fit scenarios, chart arrays, target intervals and holdout metrics |
| `data/fitted_and_forecast_daily.csv` | Full-history fit only; daily log and USD trend bands and prediction intervals through November 30, 2030 |
| `data/holdout_predictions.csv` | Held-out daily actuals, pre-2021 model predictions and IID prediction endpoints |
| `data/validation_report.txt` | Numerical checks and summarized calculation results |
| `data/browser_validation.json` | Browser smoke-test outcome and its limitations |
| `verify_browser.py` | Optional Playwright smoke test; not needed to use the dashboard |
| `verify_calculations.py` | Independent statsmodels audit; never imports the production fitting routines |
| `requirements-audit.txt` | Optional pinned dependencies for independent numerical verification |
| `check_sources.py` | Non-destructive public-source recheck; never replaces or appends model input |
| `data/audit/source_checks.json` | Exact public-source URLs and observed responses/proxy failures |
| `data/audit/upstream_pin.json` | Native-Git upstream commit, immutable CSV URL and byte/hash match |
| `data/audit/network_findings.json` | Configured network restriction, diagnostic limits and required hosts |
| `data/audit/calculation_verification.json` | Independent coefficients, all target intervals, differences, tolerances and output fingerprint |
| `data/requirements_checklist.json` | Mapping of the seven requested requirements to HTML content, with coverage limitation |
| `data/verification_summary.md` | Human-readable data and calculation audit |

## Validation

The analysis validates positive finite prices, unique dates and complete daily coverage; independently compares coefficients against SciPy; checks HAC covariance positive semidefiniteness, interval ordering, back-transform consistency and CSV export row count.

Chromium smoke tests rendered three charts, changed fitting windows and confidence estimators, enabled the forecast overlay and log-dollar axis, exercised Plotly zoom, checked all nine download payloads against the exported files, and verified a 390px mobile layout with no JavaScript errors. The audit sections, nine source-check results, immutable link and seven-component checklist were also checked. No external network requests were made. The browser was switched offline after loading from a local HTTP server, and all tested controls and downloads continued working.

**Direct `file://` testing was blocked by this environment's managed Chromium URL policy.** No policy was changed or bypassed. The HTML contains its own libraries and data, has no fetches or external asset dependencies, and is designed for opening directly. The file-opening path itself was not directly verified here; this limitation is also recorded in the browser validation report.

Optional browser test (requires Playwright and an installed Chromium):

```bash
python -m pip install playwright
python verify_browser.py
```

The original HTML layout and chart design are retained. All seven requested components are present: daily historical data; interactive dollar prices; natural-log prices; log-linear regression with 95% confidence bands; a November 2030 dollar forecast; reliability/uncertainty discussion; and sources/methodology. Historical coverage remains limited to the verified snapshot; current October coverage is explicitly **not** claimed.

To rerun public source availability checks without replacing the input:

```bash
python check_sources.py --output /tmp/bitcoin-source-recheck
```

Review candidate data before use; a replacement provider requires matching UTC date conventions and USD units, checking overlap discrepancies, gaps, duplication and licensing. Do not blindly append exchange closes to an aggregate reference-price series.

This test temporarily serves the project on a random local port, switches the browser offline, and exits after validation. Browser screenshots are generated locally by the test and are not required to use the project.
