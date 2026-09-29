"""Optional real-browser verification of the full generated project-subpath site.

Requires Playwright + Chromium; build the default project-subpath site first.
"""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json
import threading
import time
from urllib.parse import urlsplit, parse_qs

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
            comparison=json.loads((ROOT/'corpus/comparison.json').read_text())
            assert f"+{comparison['word_count_increase_pct']:.0f}%" in page.locator('.stat-columns').inner_text()
            assert f"+{comparison['recognized_word_increase_pct']:.0f}%" in page.locator('.stat-columns').inner_text()
            assert page.locator('.pipeline-story figure').count() == 5
            assert page.locator('#stats-title').inner_text() == 'What is this?'
            assert page.locator('#search-filters').evaluate('(el)=>el.open')
            assert all('/assets/diagrams/' in src for src in page.locator('.pipeline-story img').evaluate_all('(imgs)=>imgs.map(i=>i.src)'))
            page.screenshot(path='/tmp/recorder-home-desktop.png', full_page=True)
            page.set_viewport_size({'width': 390, 'height': 844})
            page.reload()
            page.locator('pagefind-input input').wait_for()
            assert not page.locator('#search-filters').evaluate('(el)=>el.open')
            page.locator('#search-filters summary').click()
            assert page.locator('#search-filters').evaluate('(el)=>el.open')
            page.locator('#search-filters summary').click()
            assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
            assert page.locator('pagefind-input input').bounding_box()['y'] < 350
            page.screenshot(path='/tmp/recorder-home-mobile.png', full_page=True)
            page.set_viewport_size({'width': 1400, 'height': 1000})
            start = time.monotonic()
            page.locator('pagefind-input input').fill('Wilberforce')
            page.locator('pagefind-results').scroll_into_view_if_needed()
            page.locator('.search-result').first.wait_for(timeout=60000)
            assert not page.locator('#project-intro').evaluate('(el)=>el.open')
            print(f'First search result in {time.monotonic()-start:.2f}s')
            link = page.locator('.search-result h3 a').first
            href = link.get_attribute('href')
            assert parse_qs(urlsplit(page.url).query).get('q') == ['Wilberforce']
            assert parse_qs(urlsplit(href).query).get('q') == ['Wilberforce']
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
            assert page.locator('.paragraph-position').count() > 0
            assert 'through text' in page.locator('.paragraph-position').first.inner_text()
            assert page.locator('.sticky-original').get_attribute('href').startswith('https://archive.org/details/')
            page.locator('.query-match').first.wait_for()
            assert page.locator('#match-count').inner_text().startswith('1 of ')
            if page.locator('.query-match').count() > 1:
                page.locator('#match-next').click()
                assert page.locator('#match-count').inner_text().startswith('2 of ')
                page.locator('#match-prev').click()
                assert page.locator('#match-count').inner_text().startswith('1 of ')
            page.reload()
            page.locator('.query-match').first.wait_for()
            assert page.locator('.current-match').count() == 1
            assert not any(r.endswith('/original.txt') for r in requests)
            assert page.locator('.reading-toolbar .actions a').count() == 2
            page.locator('.original-comparison summary').click()
            page.locator('.load-original').click()
            page.wait_for_function("document.querySelector('.load-original').textContent.includes('loaded')")
            assert page.locator('.original-text').inner_text().strip()
            page.set_viewport_size({'width': 390, 'height': 844})
            assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
            assert not errors, errors
            assert not any('archive.org' in r for r in requests), 'No automatic third-party image requests expected'
            page.goto(base + '?q=%22female%20doctors%22')
            page.locator('pagefind-results').scroll_into_view_if_needed()
            page.locator('.search-result').first.wait_for(timeout=60000)
            assert page.locator('pagefind-input input').input_value() == '"female doctors"'
            page.locator('.search-result h3 a').first.click()
            page.locator('.query-match').first.wait_for()
            assert 'female doctors' in page.locator('.query-match').first.inner_text().lower()
            page.goto(page.url.split('?')[0] + '?q=zzzzunmatchabletoken')
            assert page.locator('#match-count').inner_text() == '0 matches'
            assert page.locator('#match-next').is_disabled()
            page.goto(page.url.split('?')[0])
            assert page.locator('#match-navigation').is_visible()
            assert page.locator('.sticky-original').is_visible()
            assert not page.locator('.query-tools').is_visible()
            page.goto(base + 'volumes/')
            assert page.locator('.year-group h2').first.inner_text() == '1854–1855'
            assert page.locator('.year-group h2').last.inner_text() == 'Undated volume'
            assert page.locator('.volume-list a').count() == 44
            assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
            page.locator('.volume-list a').first.click()
            assert 'No output flags' not in page.locator('.scan-list').inner_text()
            browser.close()
            print('PASS: search query URLs, highlights/next/previous, reload, phrases, filters, source links, lazy text, mobile')
    finally:
        server.shutdown()


if __name__ == '__main__':
    main()
