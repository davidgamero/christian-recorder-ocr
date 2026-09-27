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
<body><a class="skip" href="#main">Skip to content</a><header class="masthead"><a class="brand" href="{url()}">The Christian Recorder</a>
<div class="edition"><span>A searchable newspaper archive</span><nav aria-label="Main"><a href="{url('#search')}">Search</a><a href="{url('volumes/')}">Volumes</a><a href="{url('about/')}">The project</a><a href="https://onlinebooks.library.upenn.edu/webbin/serial?id=christrecordame">Originals ↗</a></nav></div></header>
<main id="main">{body}</main><footer>Machine-transcribed. Check the scan before quoting. <a href="{url('about/')}">Methods</a> · <a href="https://github.com/davidgamero/christian-recorder-ocr">GitHub</a></footer></body></html>'''


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
    comparison = json.loads((ROOT / 'corpus/comparison.json').read_text())
    if comparison['paired_scans'] != catalog['scans'] or comparison['run'] != catalog['run']:
        raise ValueError('Comparison statistics do not match the published corpus')
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
                original = f'''<p>Archive’s existing OCR for this scan—not a verified PDF text layer.</p>
<button class="load-original" data-url="{url(f'scans/{identity}/original.txt')}">Load original text</button><pre class="original-text" aria-live="polite"></pre>'''
            body = f'''<div class="breadcrumb"><a href="{url('volumes/')}">Volumes</a> / <a href="{url(f'volumes/{sid}/')}">{e(year)}</a> / Scan {page['number']}</div>
<h1 class="scan-title">{e(year)} · Scan {page['number']}</h1><span hidden data-pagefind-meta="title">{e(title)}</span><p class="notice">Machine-transcribed · {quality} · Check against the scan.</p>
<span data-pagefind-meta="archive_scan[url]" url="{e(viewer)}" hidden></span><span data-pagefind-meta="archive_volume[url]" url="{e(volume['archive_url'])}" hidden></span>
<p class="actions"><a href="{e(viewer)}" rel="noopener">View original scan ↗</a><a href="{e(member)}" rel="noopener">Original JP2 ↗</a>
<a href="{e(volume['archive_url'])}">Archived volume ↗</a><a href="https://onlinebooks.library.upenn.edu/webbin/serial?id=christrecordame">Penn source catalog ↗</a>
<a href="text.txt" download>Download text</a><a href="provenance.json">Provenance JSON</a></p><p>{navigation}</p>
<details><summary>Source identity and quality details</summary><p><code>(image:extracted:page:{page['number']})</code></p>
<dl class="facts"><dt>Volume</dt><dd data-pagefind-filter="Volume">{e(sid)}</dd><dt>Year</dt><dd data-pagefind-filter="Year">{e(year)}</dd>
<dt>Status</dt><dd data-pagefind-filter="Quality">{quality}</dd><dt>Dimensions</dt><dd>{page['width']} × {page['height']}</dd></dl>
<p>Scan positions include cards and two-page spreads—not printed page numbers.</p>
<p>Original member: <code>{e(page['source_page'])}</code></p><p>Output flags: {e(flags)}</p><p>Layout flags: {e(', '.join(page['layout_flags']) or 'none')}</p>
<p>Source SHA-256: <code>{page['image_sha256']}</code></p></details>
<article data-pagefind-body><h2 id="transcription">GLM transcription</h2>{transcription(page['text'])}</article>
<section data-pagefind-ignore><h2>Compare existing OCR</h2>{original}</section><p>{navigation}</p>'''
            write(f'scans/{identity}/index.html', shell(title, body))
        write(f'volumes/{sid}/index.html', shell(label, f'<h1>{e(year)}</h1><p>{e(sid)}</p><p>{e(volume["year_basis"])}</p><p><a href="{e(volume["archive_url"])}">Source volume at Internet Archive ↗</a> · <a href="https://onlinebooks.library.upenn.edu/webbin/serial?id=christrecordame">Penn serial catalog ↗</a></p><ol class="scan-list">'+"".join(links)+'</ol>'))
    volume_list = '<ul class="volume-list">' + "".join(cards) + '</ul>'
    write('volumes/index.html', shell('Browse volumes', '<h1>Browse the archive</h1><p>44 source bundles, ordered by year label. Unknown dates remain explicitly undated.</p>'+volume_list))
    original_stats, glm_stats = comparison['original'], comparison['glm']
    figure = json.loads((ROOT / 'assets/figures/provenance.json').read_text())
    home = f'''<section id="search" class="search-front" aria-label="Search the newspaper archive">
<h1 class="search-heading">Search the archive</h1>
<pagefind-config bundle-path="{url('pagefind/')}" base-url="{BASE}" excerpt-length="35"></pagefind-config>
<pagefind-input placeholder="Search a name, place, or phrase…"></pagefind-input>
<p class="search-hint">{catalog['scans']:,} scans · {len(catalog['sources'])} volumes · Use “quotes” for phrases.</p>
<div class="filters"><pagefind-filter-dropdown filter="Year" label="Year"></pagefind-filter-dropdown><pagefind-filter-dropdown filter="Quality" label="Quality flags"></pagefind-filter-dropdown><pagefind-filter-dropdown filter="Volume" label="Volume"></pagefind-filter-dropdown></div>
<pagefind-summary></pagefind-summary><pagefind-results hide-sub-results>
<script type="text/pagefind-template"><li class="search-result"><h3><a href="{{{{ url | safeUrl }}}}">{{{{ meta.title }}}}</a></h3><p>{{{{+ excerpt +}}}}</p><p class="result-sources"><a href="{{{{ meta.archive_scan | safeUrl }}}}">Original scan ↗</a> · <a href="{{{{ meta.archive_volume | safeUrl }}}}">Archived volume ↗</a></p></li></script>
</pagefind-results>
<noscript>Full-text search requires JavaScript. <a href="{url('volumes/')}">Browse every volume and transcription without JavaScript.</a></noscript></section>
<section class="extraction-stats" aria-labelledby="stats-title"><div class="section-heading"><h2 id="stats-title">A clearer record</h2><span>New GLM extraction vs. existing Archive OCR</span></div>
<div class="stat-columns"><div><strong>+{comparison['word_count_increase_pct']:.0f}%</strong><h3>More text to search</h3><p>{original_stats['total_words']/1e6:.1f}m → {glm_stats['total_words']/1e6:.1f}m word tokens</p></div>
<div><strong>+{comparison['recognized_word_increase_pct']:.0f}%</strong><h3>More recognized words</h3><p>{original_stats['recognized_words']/1e6:.1f}m → {glm_stats['recognized_words']/1e6:.1f}m dictionary matches</p></div>
<div><strong>{original_stats['unrecognized_pct']:.1f}% → {glm_stats['unrecognized_pct']:.1f}%</strong><h3>Fewer unrecognized forms</h3><p>Share absent from the word list</p></div></div>
<p class="fine-print">Same {comparison['paired_scans']:,} scans. Dictionary coverage isn’t accuracy; names, omissions and repetition need review. <a href="{url('about/#comparison')}">How we measured ↗</a></p></section>
<section class="process"><div class="section-heading"><h2>From scan to search</h2><a href="{url('about/#extraction')}">Inside the process →</a></div>
<div class="process-grid"><figure><a href="{url('assets/figures/columns.svg')}"><img src="{url('assets/figures/columns.svg')}" width="720" height="947" loading="lazy" alt="Newspaper scan with saved green column boundaries and a blue masthead cutoff"></a><figcaption><b>01 / Find the columns</b><span>Separate mastheads and follow the gutters.</span></figcaption></figure>
<figure><a href="{url('assets/figures/chunks.svg')}"><img src="{url('assets/figures/chunks.svg')}" width="720" height="947" loading="lazy" alt="The same scan divided into short column chunks, with one highlighted in red"></a><figcaption><b>02 / Read smaller chunks</b><span>Keep small print legible to the model.</span></figcaption></figure>
<figure><div class="alignment"><img src="{url('assets/figures/chunk.jpg')}" width="480" height="1500" loading="lazy" alt="Actual image crop sent to GLM"><div><span class="alignment-arrow" aria-hidden="true">→</span><p>{e(figure['excerpt'][:280])}…</p></div></div><figcaption><b>03 / Keep the source link</b><span>OCR text points back to its crop—not individual words.</span></figcaption></figure></div>
<p class="fine-print">Real extraction example; boundaries are machine proposals. <a href="{url('scans/'+figure['page_id']+'/')}">Read this scan ↗</a></p></section>
<section class="front-notes"><div><h2>Read the source</h2><p>The AME Church’s newspaper, machine-transcribed for discovery. Every result links to its original scan.</p><a href="https://onlinebooks.library.upenn.edu/webbin/serial?id=christrecordame">Penn’s source catalog ↗</a></div>
<div><h2>Browse the volumes</h2><p>Explore by year or source bundle. Scan numbers follow the archive, not printed pagination.</p><a href="{url('volumes/')}">All 44 volumes →</a></div>
<div><h2>A working edition</h2><p>{catalog['flagged_scans']:,} scans have output flags. Check the image before quoting.</p><a href="{url('about/')}">The experiments →</a></div></section>'''
    write('index.html', shell('Search the archive', home, search=True))
    about = (ROOT / 'content/about.html').read_text()
    about = about.replace('<!-- extraction-figures -->', f'<div class="process-grid"><figure><img src="{url("assets/figures/columns.svg")}" alt="Column proposals and masthead cutoff"><figcaption>Detected columns · green gutters, blue masthead.</figcaption></figure><figure><img src="{url("assets/figures/chunks.svg")}" alt="Source-mapped OCR chunk polygons"><figcaption>Short chunks · the model receives one crop at a time.</figcaption></figure></div><p><a href="{url("assets/figures/provenance.json")}">Figure provenance and saved crop polygon</a> · <a href="{url("scans/"+figure["page_id"]+"/")}">Example transcription and original scan</a></p>')
    write('about/index.html', shell('Methods, findings and limitations', about))
    write('.nojekyll', '')
    write('404.html', shell('Page not found', f'<h1>Page not found</h1><p><a href="{url()}">Search or browse the archive.</a></p>'))
    write('catalog.json', json.dumps(catalog, indent=2, ensure_ascii=False))
    write('comparison.json', json.dumps(comparison, indent=2))
    print(f"Generated {catalog['scans']} scans, {len(catalog['sources'])} volumes at {BASE}")


if __name__ == '__main__':
    main()
