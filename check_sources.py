"""Non-destructive public-source availability check. Never replaces the model input.
Requires no third-party packages. Rerun results describe the new check, not the
original audit; prior reports can be preserved by choosing --output elsewhere.
"""
from pathlib import Path
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

URLS = {
    'coinmetrics_archive':'https://raw.githubusercontent.com/coinmetrics/data/master/csv/btc.csv',
    'coinmetrics_live':'https://community-api.coinmetrics.io/v4/timeseries/asset-metrics?assets=btc&metrics=PriceUSD&frequency=1d&start_time=2026-05-20&end_time=2026-10-27&page_size=1000',
    'coinmetrics_catalog':'https://community-api.coinmetrics.io/v4/catalog-all/asset-metrics?assets=btc&metrics=PriceUSD',
    'coinbase_candles':'https://api.exchange.coinbase.com/products/BTC-USD/candles?granularity=86400&start=2026-05-20T00%3A00%3A00Z&end=2026-10-27T00%3A00%3A00Z',
    'fred_coinbase':'https://fred.stlouisfed.org/graph/?id=CBBTCUSD',
    'fred_coinbase_csv':'https://fred.stlouisfed.org/graph/graph.csv?id=CBBTCUSD&cosd=2026-05-20&coed=2026-10-27',
    'yahoo_daily':'https://query1.finance.yahoo.com/v8/finance/chart/BTC-USD?range=1y&interval=1d',
    'bitstamp_daily':'https://www.cryptodatadownload.com/cdd/Bitstamp_BTCUSD_d.csv',
    'github_commit':'https://api.github.com/repos/coinmetrics/data/commits?path=csv/btc.csv&per_page=1',
}
def run(output):
    output.mkdir(parents=True,exist_ok=True)
    def check(item):
        name,url=item
        try:
            try:
                r=urlopen(Request(url,headers={'User-Agent':'BitcoinDashboardAudit/1.0'}),timeout=30)
            except HTTPError as e:
                r=e
            with r:
                content=r.read()
                result=dict(name=name,url=url,status=r.status,bytes=len(content),sha256=hashlib.sha256(content).hexdigest(),http_date=r.headers.get('Date'),last_modified=r.headers.get('Last-Modified'),content_type=r.headers.get('Content-Type'))
                if r.status==200:
                    ext='csv' if name in ['coinmetrics_archive','fred_coinbase_csv','bitstamp_daily'] else 'txt'
                    (output/(name+'.'+ext)).write_bytes(content)
                else:
                    result['error_excerpt']=content.decode('utf-8',errors='replace')[:600]
                return result
        except (URLError,TimeoutError,OSError) as e:
            return dict(name=name,url=url,error=str(e))
    with ThreadPoolExecutor(max_workers=6) as executor:
        results=list(executor.map(check,URLS.items()))
    report=dict(checked_as_of='2026-10-27',executed_at_utc=datetime.now(timezone.utc).isoformat(),checks=results)
    (output/'source_checks.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path(__file__).resolve().parent/'data'/'audit')
    run(parser.parse_args().output)
