"""Real touch/mobile audit of every static page type and main reading flows."""
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path
import json
import threading

from playwright.sync_api import sync_playwright
from browser_smoke import Handler, ROOT, PREFIX


def main():
    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(Handler, directory=str(ROOT / '_site')))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{server.server_port}{PREFIX}/'
    report = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            for width, height in ((320,568), (390,844), (430,932), (768,1024)):
                context = browser.new_context(viewport={'width':width,'height':height}, is_mobile=True, has_touch=True, device_scale_factor=1)
                page = context.new_page()
                errors = []
                page.on('pageerror',lambda e:errors.append(str(e)))
                def audit(name):
                    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), (width,name,'overflow')
                    targets=page.locator('nav a, .reading-toolbar .actions a, .sticky-original, #match-prev, #match-next, summary, .load-original').evaluate_all('''els=>els.filter(e=>e.getClientRects().length).map(e=>({text:e.textContent.trim(),width:e.getBoundingClientRect().width,height:e.getBoundingClientRect().height})).filter(e=>e.height<43)''')
                    report.append({'viewport':width,'page':name,'small_targets':targets})
                    assert not targets,(width,name,targets)
                page.goto(base)
                page.locator('pagefind-input input').wait_for()
                assert page.locator('#search-filters').evaluate('(e)=>e.open') == (width>700)
                audit('home')
                page.locator('#search-filters summary').tap()
                page.locator('#search-filters summary').tap()
                page.locator('pagefind-input input').fill('Wilberforce')
                page.locator('pagefind-results').scroll_into_view_if_needed()
                page.locator('.search-result').first.wait_for(timeout=60000)
                assert not page.locator('#project-intro').evaluate('(e)=>e.open')
                audit('results')
                page.locator('.search-result h3 a').first.tap()
                page.locator('.query-match').first.wait_for()
                bar=page.locator('#match-navigation').bounding_box()
                assert bar['height']<height*.42,(width,'sticky bar too tall',bar)
                page.locator('#match-next').tap()
                count=page.locator('#match-count').inner_text()
                assert count.startswith('2 of '),count
                mark=page.locator('.current-match').bounding_box()
                bar=page.locator('#match-navigation').bounding_box()
                assert mark['y'] >= bar['y']+bar['height']-2,(width,'match obscured')
                audit('scan-query')
                page.screenshot(path=f'/tmp/recorder-reading-{width}.png')
                page.locator('.original-comparison summary').tap()
                page.locator('.load-original').tap()
                page.wait_for_function("document.querySelector('.load-original').textContent.includes('loaded')")
                audit('original-ocr')
                page.locator('.source-details summary').tap()
                audit('source-details')
                page.goto(page.url.split('?')[0])
                audit('scan-no-query')
                page.goto(base+'volumes/')
                audit('volumes')
                page.locator('.volume-list a').first.tap()
                page.locator('.scan-list').wait_for()
                audit('volume')
                page.goto(base+'about/')
                audit('about')
                page.screenshot(path=f'/tmp/recorder-about-{width}.png',full_page=True)
                page.goto(base+'research/')
                audit('research')
                assert page.locator('.experiment-result > strong').inner_text()=='0 / 171'
                assert page.locator('#health tbody tr').count()==6
                for summary in page.locator('.research-detail summary').all():
                    summary.tap()
                audit('research-expanded')
                page.screenshot(path=f'/tmp/recorder-research-{width}.png',full_page=True)
                page.goto(base+'404.html')
                audit('404')
                assert not errors,errors
                context.close()
            browser.close()
    finally:
        server.shutdown()
    Path('/tmp/recorder-mobile-audit.json').write_text(json.dumps(report,indent=2))
    print(f'PASS: {len(report)} mobile views; touch targets, overflow, sticky matches, OCR, browsing, 404')


if __name__=='__main__':
    main()
