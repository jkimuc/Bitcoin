"""Optional browser smoke test; requires Playwright and a local Chromium browser."""
from pathlib import Path
import json
import shutil
import threading
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from functools import partial
from playwright.sync_api import sync_playwright
ROOT = Path(__file__).resolve().parent
server = ThreadingHTTPServer(('127.0.0.1',0), partial(SimpleHTTPRequestHandler,directory=str(ROOT)))
threading.Thread(target=server.serve_forever,daemon=True).start()
url=f'http://127.0.0.1:{server.server_port}/index.html'
with sync_playwright() as p:
    chromium = shutil.which('chromium') or shutil.which('google-chrome')
    browser = p.chromium.launch(headless=True, executable_path=chromium, args=['--no-sandbox'])
    page = browser.new_page(viewport={'width':1440,'height':1000}, accept_downloads=True)
    errors, requests = [], []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.on('request', lambda r: requests.append(r.url))
    page.goto(url)
    page.context.set_offline(True)
    page.wait_for_function("document.documentElement.dataset.ready === 'true'",timeout=60000)
    assert page.locator('.js-plotly-plot').count()==3
    assert page.locator('#forecast').inner_text()=='$12,797,820'
    page.get_by_text('Independent regression and back-transformation audit',exact=True).click()
    assert 'PASSED' in page.locator('#verification-summary').inner_text()
    assert '16.364785440062' in page.locator('#verified-equation').inner_text()
    assert page.locator('#verified-intervals tr').count()==3
    page.get_by_text('Independent regression and back-transformation audit',exact=True).click()
    assert page.locator('#source-checks tr').count()==9
    assert page.get_by_text('Part 2 checklist · all seven dashboard components').count()==1
    assert page.locator('#pinned-source').get_attribute('href').startswith('https://raw.githubusercontent.com/coinmetrics/data/f1a36afb962731c387bb03982758ab0103063da5/')
    page.select_option('#window','Since 2020')
    page.wait_for_function("document.getElementById('forecast').textContent === '$470,381'")
    page.select_option('#band','iid')
    page.check('#overlay')
    page.select_option('#scale','log')
    page.wait_for_function("document.getElementById('usd-chart').layout.yaxis.type === 'log' && document.getElementById('usd-chart').data.length === 6")
    # Exercise native Plotly zoom, then restore with a different fit control.
    page.evaluate("Plotly.relayout('log-chart', {'xaxis.range':['2020-01-01','2026-01-01']})")
    assert page.evaluate("document.getElementById('log-chart').layout.xaxis.range[0]")=='2020-01-01'
    for name in ['prices_daily.csv','results.json','fitted_and_forecast_daily.csv','holdout_predictions.csv','analysis.py','calculation_verification.json','source_checks.json','upstream_pin.json','network_findings.json']:
        with page.expect_download() as info:
            page.get_by_role('button',name=name,exact=True).click()
        download=info.value
        actual=Path(download.path()).read_bytes()
        expected_path=ROOT/name if name=='analysis.py' else ROOT/'data'/'audit'/name if name in ['calculation_verification.json','source_checks.json','upstream_pin.json','network_findings.json'] else ROOT/'data'/name
        expected=expected_path.read_bytes()
        assert actual==expected, name
    page.select_option('#window','Full history')
    page.select_option('#band','hac')
    page.uncheck('#overlay')
    page.select_option('#scale','linear')
    page.wait_for_function("document.getElementById('usd-chart').data.length === 1")
    page.screenshot(path=str(ROOT/'dashboard-desktop.png'),full_page=True)
    page.set_viewport_size({'width':390,'height':844})
    page.wait_for_timeout(500)
    assert not page.evaluate('document.documentElement.scrollWidth > innerWidth'), 'Mobile page overflow'
    page.locator('details').evaluate_all('(items) => items.forEach(item => item.open = true)')
    assert not page.evaluate('document.documentElement.scrollWidth > innerWidth'), 'Expanded mobile audit overflow'
    page.locator('details').evaluate_all('(items) => items.forEach(item => item.open = false)')
    page.screenshot(path=str(ROOT/'dashboard-mobile.png'),full_page=True)
    assert not errors, errors
    assert not [r for r in requests if r.startswith('http') and not r.startswith(f'http://127.0.0.1:{server.server_port}/')], 'Unexpected external requests'
    report = dict(status='passed', browser=browser.version, protocol='local HTTP, then browser offline', file_url_limit='Managed browser policy blocks file:// navigation; file opening could not be directly tested here', external_requests=0,
        checks=['3 charts rendered','fit period changes numerical output','HAC/IID selector','USD logarithmic axis','forecast overlay', 'Plotly zoom','9 embedded downloads match exported files','current independent calculation audit','9 source checks and 7-component checklist','immutable source link','390px mobile layout, including expanded audit details','no JavaScript errors'])
    (ROOT/'data'/'browser_validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    browser.close()
server.shutdown()
