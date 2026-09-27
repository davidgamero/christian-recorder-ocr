"""Optional real-browser verification of the full generated project-subpath site.

Requires Playwright + Chromium; build the default project-subpath site first.
"""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading
import time
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
PREFIX = '/christian-recorder-ocr'


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith(PREFIX + '/'):
            self.path = self.path[len(PREFIX):]
        return super().do_GET()

    def log_message(self, *args):
        pass


def main():
    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(Handler, directory=str(ROOT / '_site')))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{server.server_port}{PREFIX}/'
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={'width': 1400, 'height': 1000})
            errors, requests = [], []
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.on('request', lambda r: requests.append(r.url))
            page.goto(base)
            page.locator('pagefind-input input').wait_for()
            assert page.locator('pagefind-input input').bounding_box()['y'] < 350
            assert '+19%' in page.locator('.stat-columns').inner_text()
            assert '+55%' in page.locator('.stat-columns').inner_text()
            assert page.locator('.process-grid figure').count() == 3
            page.screenshot(path='/tmp/recorder-home-desktop.png', full_page=True)
            page.set_viewport_size({'width': 390, 'height': 844})
            assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
            assert page.locator('pagefind-input input').bounding_box()['y'] < 350
            page.screenshot(path='/tmp/recorder-home-mobile.png', full_page=True)
            page.set_viewport_size({'width': 1400, 'height': 1000})
            start = time.monotonic()
            page.locator('pagefind-input input').fill('Wilberforce')
            page.locator('pagefind-results').scroll_into_view_if_needed()
            page.locator('.search-result').first.wait_for(timeout=60000)
            print(f'First search result in {time.monotonic()-start:.2f}s')
            link = page.locator('.search-result h3 a').first
            href = link.get_attribute('href')
            assert urlsplit(href).path.startswith(PREFIX + '/scans/'), href
            assert page.locator('.result-sources a').first.get_attribute('href').startswith('https://archive.org/details/')
            # Verify an exact phrase and a restrictive year filter via the real index.
            result = page.evaluate('''async () => {
                const pf = await import('/christian-recorder-ocr/pagefind/pagefind.js');
                await pf.options({baseUrl:'/christian-recorder-ocr/'});
                const phrase = await pf.search('"female doctors"');
                const filtered = await pf.search('church', {filters:{Year:'1868'}});
                const item = await filtered.results[0].data();
                return {phrase:phrase.results.length, filtered:filtered.results.length, year:item.filters.Year};
            }''')
            assert result['phrase'] > 0 and result['filtered'] > 0 and '1868' in result['year'], result
            page.goto(base.rstrip('/') + href[len(PREFIX):] if href.startswith(PREFIX) else href)
            page.locator('.transcription').wait_for()
            assert not any(r.endswith('/original.txt') for r in requests)
            page.locator('.load-original').click()
            page.wait_for_function("document.querySelector('.load-original').textContent.includes('loaded')")
            assert page.locator('.original-text').inner_text().strip()
            page.set_viewport_size({'width': 390, 'height': 844})
            assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
            assert not errors, errors
            assert not any('archive.org' in r for r in requests), 'No automatic third-party image requests expected'
            browser.close()
            print('PASS: project-subpath search, phrase/year filtering, source links, lazy original text, mobile')
    finally:
        server.shutdown()


if __name__ == '__main__':
    main()
