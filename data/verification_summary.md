# Verification of the existing Bitcoin dashboard

Updated October 27, 2026. The existing project, original daily input, dashboard layout and regression specification are retained. The numerical forecast did not change. The update adds independently verified provenance and calculations, exact access diagnostics, offline audit downloads and a seven-requirement checklist.

## Historical coverage

A fresh Coin Metrics archive download is byte-for-byte identical to the existing input. It still has 5,789 usable daily PriceUSD observations, July 18, 2010–May 23, 2026, without gaps, duplicate dates or nonpositive prices. The retained raw source has 6,351 rows; 562 missing-price rows are excluded. No prices were invented, forward-filled or spliced from a provider with unverified comparability.

Native Git resolved the upstream master ref to `f1a36afb962731c387bb03982758ab0103063da5`. A download at the immutable CSV URL matched the original SHA-256 `06495ff8e643432e6948b7b4686ce44fc106217287dabdc1b38351d9ddec46c3`. See `audit/upstream_pin.json`.

The live Coin Metrics timeseries/catalog requests, Coinbase Exchange candles, FRED Coinbase page/CSV, Yahoo BTC-USD and CryptoDataDownload Bitstamp daily file were refused during proxy CONNECT with HTTP 403, before an origin HTTP response. The configured restricted allowlist omits these hosts. This is an environment access blocker; it does not demonstrate that October data is missing at the providers or unreliable. Exact requested URLs/errors are in `audit/source_checks.json`; findings and follow-up hosts are in `audit/network_findings.json`. GitHub commit-metadata API requests were also blocked, but native Git provided the immutable pin.

It is not possible in this environment to verify or safely append newer daily prices under those access conditions. The verified span is not claimed to be the globally longest reliable Bitcoin series. To retry the same methodology, permit `community-api.coinmetrics.io`; an independent exchange overlap check would also require `api.exchange.coinbase.com`. No provider token was shown to be missing. At the October 27 analysis date, only completed daily intervals through October 26 under a UTC day-start convention should be included. New access would enable verification, not guarantee coverage.

## Independent numerical audit

`verify_calculations.py` uses the standard-library CSV parser, math.log/math.exp, and statsmodels 0.14.6 without importing the production fit/predict code. All checks passed for the three fit windows, covariances, target intervals, every daily full-history output and holdout. See `audit/calculation_verification.json` for exact values, tolerances and model-output fingerprint.

- Full-history alpha: 1.7341007178898267.
- Beta per 365.25-day year: 0.7210710558323071.
- Time on November 1, 2030: 20.290212183436 years since July 18, 2010.
- Fitted natural log: 16.364785440061567.
- Dollar value: exp(mu) = $12,797,820.48857653.

| Interval at November 1, 2030 | Log lower | Log upper | USD lower | USD upper |
| --- | ---: | ---: | ---: | ---: |
| 95% classical mean-log CI | 16.269478127796 | 16.460092752327 | $11,634,415.62 | $14,077,562.17 |
| 95% HAC mean-log CI | 15.423750570208 | 17.305820309915 | $4,994,014.09 | $32,796,104.79 |
| 95% IID prediction interval | 13.846843506822 | 18.882727373301 | $1,031,828.99 | $158,731,931.72 |

The classical mean-log CI uses Student-t(n−2) with s²(X′X)⁻¹. HAC uses a Newey–West sandwich with 90 daily lags, Bartlett weights, n/(n−2) correction, and the 1.95996398454 normal critical value. The IID single-observation prediction interval additionally includes residual variance. Exponentiating each log endpoint is correct because exp is monotone; exponentiating mu gives a geometric-mean trend, or a median under the stated zero-median log-error assumption. It does not give the arithmetic expected USD price. A hypothetical IID lognormal mean would require exp(mu+s²/2), about $29.16m; that unsupported assumption is not used for the dashboard point.

The large point estimate results from extrapolating roughly 105.7% constant annual trend growth across a series beginning at pennies. This is not a unit/base conversion error, but the growth assumption is empirically poor. Residual lag-1 correlation is about 0.9993. A since-2020 fit gives about $470k instead; the pre-2021 fit predicted $10.22m at the holdout endpoint versus a $76,620 observation. Only 26.9% of holdout observations lay inside its nominal 95% IID prediction interval. Neither confidence estimator makes these probabilities calibrated for Bitcoin in 2030.

## Seven requested components

1. **Historical daily Bitcoin prices — implemented with disclosed coverage limit.** 5,789 consecutive daily Coin Metrics PriceUSD observations, 2010-07-18 to 2026-05-23. October extension unverified because proxy denied newer-source requests.
2. **Interactive actual-price dollar graph — implemented and browser-tested.** Hover, zoom, date ranges, linear/log dollar axis; actuals shown by default.
3. **Natural logarithm graph — implemented and browser-tested.** Daily ln(PriceUSD) rather than log10.
4. **Log-price linear regression and 95% confidence band — implemented and independently verified.** OLS; selectable classical IID Student-t and Newey–West HAC 90-lag normal mean-log intervals, with independently verified covariance and endpoints.
5. **November 2030 forecast converted to USD — implemented and independently verified.** 2030-11-01 dated estimate exp(16.364785440061567) = 12,797,820.488576526 USD under full-history fit, with November 30 also reported.
6. **Reliability and uncertainty — implemented.** Confidence vs prediction intervals, sample-window sensitivity, residual dependence, holdout failure and explicit lack of calibrated future-price probabilities.
7. **Data sources and methodology — implemented.** Coin Metrics attribution and license; immutable Git commit URL; raw CSV SHA-256; data exclusion rules; formulas; independent audit downloads; documented network limitations.

All seven components are present in the final HTML; verified current-October coverage is not claimed. The HTML checklist repeats this limitation. The raw input, sources, license, cleaned data, daily model outputs, exact calculation audit and source-access evidence are included in the project.

## Browser validation

Updated Chromium tests pass for charts, all controls, zoom, nine embedded downloads, the current independent-audit status, immutable source link, nine source-check entries, seven-component checklist and 390px mobile layout. Testing used a local HTTP server and then disabled browser networking, with no external requests. Direct file:// testing remains blocked by managed browser URL policy; no policy was changed. The HTML bundles libraries, data and audit evidence inline and is designed to open as a standalone file.
