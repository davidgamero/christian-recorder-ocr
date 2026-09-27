"""Generate portable HTML from the checked-in, checksum-verified corpus."""
import gzip
import hashlib
from html import escape as e
import json
import os
from pathlib import Path
import re
import shutil
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "_site"
BASE = "/" + os.environ.get("BASE_PATH", "/christian-recorder-ocr/").strip("/") + "/"
if BASE == "//":
    BASE = "/"


def url(path=""):
    return BASE + path.lstrip("/")


def write(path, content):
    target = OUT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def shell(title, body, *, search=False):
    assets = (f'<link href="{url("pagefind/pagefind-component-ui.css")}" rel="stylesheet">'
              f'<script src="{url("pagefind/pagefind-component-ui.js")}" type="module"></script>') if search else ""
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)} · Christian Recorder OCR</title><meta name="description" content="Searchable machine transcriptions of The Christian Recorder, with links to original scans and OCR research notes.">
<link rel="stylesheet" href="{url('assets/style.css')}">{assets}<script src="{url('assets/site.js')}" defer></script></head>
<body><a class="skip" href="#main">Skip to content</a><header><a class="brand" href="{url()}">The Christian Recorder <small>OCR research archive</small></a>
<nav aria-label="Main"><a href="{url('#search')}">Search</a><a href="{url('volumes/')}">Browse volumes</a><a href="{url('about/')}">Methods & findings</a><a href="https://github.com/davidgamero/christian-recorder-ocr">GitHub</a></nav></header>
<main id="main">{body}</main><footer>Machine transcription—not an authoritative edition. Check the original scan before quoting. <a href="{url('about/')}">Read the limitations</a>.</footer></body></html>'''


def transcription(text):
    # OCR is untrusted text, never Markdown/HTML. Keep line breaks verbatim.
    return '<div class="transcription">' + e(text) + '</div>'


def source_links(volume, page):
    leaf = re.search(r"_(\d+)\.jp2$", page["source_page"], re.I)
    viewer = volume["archive_url"] + (f"/page/n{int(leaf[1])}/mode/1up" if leaf else "")
    member = f'https://archive.org/download/{volume["id"]}/{volume["id"]}_jp2.zip/' + quote(page["source_page"], safe="/")
    return viewer, member


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    shutil.copytree(ROOT / "assets", OUT / "assets")
    catalog = json.loads((ROOT / "corpus/catalog.json").read_text())
    cards = []
    for source in catalog["sources"]:
        path = ROOT / "corpus" / source["file"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != source["sha256"]:
            raise ValueError(f"Corpus checksum mismatch: {path.name}")
        volume = json.loads(gzip.decompress(path.read_bytes()))
        sid, year = volume["id"], volume["year"]
        label = f"{year} · {sid}"
        cards.append(f'<li><a href="{url(f"volumes/{sid}/")}"><strong>{e(year)}</strong><span>{e(sid)}</span></a><small>{len(volume["pages"])} scans</small></li>')
        links = []
        for i, page in enumerate(volume["pages"]):
            identity = page["id"]
            quality = "Flagged output" if page["flags"] or page["errors"] else "No output flags"
            viewer, member = source_links(volume, page)
            title = f'{year} — Scan {page["number"]} — {sid}'
            links.append(f'<li><a href="{url(f"scans/{identity}/")}">Scan {page["number"]}</a> <small>{quality}</small></li>')
            prev = volume["pages"][i-1] if i else None
            following = volume["pages"][i+1] if i+1 < len(volume["pages"]) else None
            navigation = " · ".join('<a href="' + url('scans/' + p['id'] + '/') + '">' + text + '</a>' for p,text in ((prev,"← Previous scan"),(following,"Next scan →")) if p)
            flags = ', '.join(sorted({f for values in page["flags"].values() for f in values})) or "None recorded"
            metadata = {k:v for k,v in page.items() if k not in {"text", "original"}}
            metadata.update(source_id=sid, year=year, model=catalog["model"], original_kind=page["original"]["kind"] if page["original"] else None,
                            catalog_url="https://onlinebooks.library.upenn.edu/webbin/serial?id=christrecordame",
                            archive_volume_url=volume["archive_url"], archive_scan_url=viewer, archive_jp2_url=member)
            write(f'scans/{identity}/text.txt', page["text"])
            write(f'scans/{identity}/provenance.json', json.dumps(metadata, indent=2, ensure_ascii=False))
            original = "<p>No mapped original OCR baseline available.</p>"
            if page["original"]:
                write(f'scans/{identity}/original.txt', page["original"]["text"])
                original = f'''<p>Existing Archive OCR derivative, mapped to this JP2 leaf. Not verified as identical to a PDF text layer; not ground truth.</p>
<button class="load-original" data-url="{url(f'scans/{identity}/original.txt')}">Load original OCR text</button><pre class="original-text" aria-live="polite"></pre>'''
            body = f'''<div class="breadcrumb"><a href="{url('volumes/')}">Volumes</a> / <a href="{url(f'volumes/{sid}/')}">{e(year)}</a> / Scan {page['number']}</div>
<h1 data-pagefind-meta="title">{e(title)}</h1><p class="notice">Uncorrected GLM-OCR transcription. {quality}. No output flags does not mean verified accuracy.</p>
<span data-pagefind-meta="archive_scan[url]" url="{e(viewer)}" hidden></span><span data-pagefind-meta="archive_volume[url]" url="{e(volume['archive_url'])}" hidden></span>
<dl class="facts"><dt>Volume</dt><dd data-pagefind-filter="Volume">{e(sid)}</dd><dt>Year label</dt><dd data-pagefind-filter="Year">{e(year)}</dd>
<dt>Output status</dt><dd data-pagefind-filter="Quality">{quality}</dd><dt>Scan dimensions</dt><dd>{page['width']} × {page['height']}</dd></dl>
<p>Scan numbers include separator cards and may represent two printed pages. They are not printed newspaper pagination.</p>
<p class="actions"><a href="{e(viewer)}" rel="noopener">View original scan ↗</a><a href="{e(member)}" rel="noopener">Original JP2 ↗</a>
<a href="{e(volume['archive_url'])}">Archived volume ↗</a><a href="https://onlinebooks.library.upenn.edu/webbin/serial?id=christrecordame">Penn source catalog ↗</a>
<a href="text.txt" download>Download text</a><a href="provenance.json">Provenance JSON</a></p><p>{navigation}</p>
<details><summary>Source identity and quality details</summary><p><code>(image:extracted:page:{page['number']})</code></p>
<p>Original member: <code>{e(page['source_page'])}</code></p><p>Output flags: {e(flags)}</p><p>Layout flags: {e(', '.join(page['layout_flags']) or 'none')}</p>
<p>Source SHA-256: <code>{page['image_sha256']}</code></p></details>
<article data-pagefind-body><h2 id="transcription">GLM transcription</h2>{transcription(page['text'])}</article>
<section data-pagefind-ignore><h2>Compare existing OCR</h2>{original}</section><p>{navigation}</p>'''
            write(f'scans/{identity}/index.html', shell(title, body))
        write(f'volumes/{sid}/index.html', shell(label, f'<h1>{e(year)}</h1><p>{e(sid)}</p><p>{e(volume["year_basis"])}</p><p><a href="{e(volume["archive_url"])}">Source volume at Internet Archive ↗</a> · <a href="https://onlinebooks.library.upenn.edu/webbin/serial?id=christrecordame">Penn serial catalog ↗</a></p><ol class="scan-list">'+"".join(links)+'</ol>'))
    volume_list = '<ul class="volume-list">' + "".join(cards) + '</ul>'
    write('volumes/index.html', shell('Browse volumes', '<h1>Browse the archive</h1><p>44 source bundles, ordered by year label. Unknown dates remain explicitly undated.</p>'+volume_list))
    home = f'''<section class="hero"><p class="eyebrow">African American history · searchable newspaper scans</p><h1>The Christian Recorder</h1>
<p>Explore a machine-transcribed archive of the newspaper published by the African Methodist Episcopal Church. Search names, places, articles and advertisements, then follow the source scan.</p>
<p><a href="https://onlinebooks.library.upenn.edu/webbin/serial?id=christrecordame">Original source catalog · University of Pennsylvania ↗</a></p>
<div class="stats"><span><b>{catalog['scans']:,}</b> scans</span><span><b>{len(catalog['sources'])}</b> volumes</span><span><b>{catalog['word_tokens']/1e6:.1f}m</b> word tokens</span></div></section>
<p class="notice">Research edition: spelling errors, omissions and repetition remain. {catalog['flagged_scans']:,} scans have output flags. Search is an aid to discovery, not proof of transcription accuracy.</p>
<section id="search"><h2>Search the transcriptions</h2><p>Try a name or place, or a phrase in quotation marks. Search indexes GLM text only; original OCR and metadata are excluded.</p>
<pagefind-config bundle-path="{url('pagefind/')}" base-url="{BASE}" excerpt-length="35"></pagefind-config>
<pagefind-input placeholder="Search names, places, and newspaper text…"></pagefind-input>
<div class="filters"><pagefind-filter-dropdown filter="Year" label="Year / period"></pagefind-filter-dropdown><pagefind-filter-dropdown filter="Quality" label="Output flags"></pagefind-filter-dropdown><pagefind-filter-dropdown filter="Volume" label="Volume"></pagefind-filter-dropdown></div>
<pagefind-summary></pagefind-summary><pagefind-results hide-sub-results>
<script type="text/pagefind-template"><li class="search-result"><h3><a href="{{{{ url | safeUrl }}}}">{{{{ meta.title }}}}</a></h3><p>{{{{+ excerpt +}}}}</p><p class="result-sources"><a href="{{{{ meta.archive_scan | safeUrl }}}}">Original scan ↗</a> · <a href="{{{{ meta.archive_volume | safeUrl }}}}">Archived volume ↗</a></p></li></script>
</pagefind-results>
<noscript>Full-text search requires JavaScript. <a href="{url('volumes/')}">Browse every volume and transcription without JavaScript.</a></noscript></section>
<section><h2>Browse by source volume</h2>{volume_list}</section>'''
    write('index.html', shell('Search the archive', home, search=True))
    about = (ROOT / 'content/about.html').read_text()
    write('about/index.html', shell('Methods, findings and limitations', about))
    write('.nojekyll', '')
    write('404.html', shell('Page not found', f'<h1>Page not found</h1><p><a href="{url()}">Search or browse the archive.</a></p>'))
    write('catalog.json', json.dumps(catalog, indent=2, ensure_ascii=False))
    print(f"Generated {catalog['scans']} scans, {len(catalog['sources'])} volumes at {BASE}")


if __name__ == '__main__':
    main()
