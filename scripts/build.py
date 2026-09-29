"""Generate portable HTML from the checked-in, checksum-verified corpus."""
import gzip
from collections import defaultdict
import hashlib
from html import escape as e
import json
import os
from pathlib import Path
import re
import shutil
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
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
<body class="{'home' if search else 'interior'}"><a class="skip" href="#main">Skip to content</a><header class="masthead"><a class="brand" href="{url()}">The Christian Recorder</a>
<div class="edition"><span>A searchable newspaper archive</span><nav aria-label="Main"><a href="{url('#search')}">Search</a><a href="{url('volumes/')}">Volumes</a><a href="{url('about/')}">The project</a><a href="https://onlinebooks.library.upenn.edu/webbin/serial?id=christrecordame">Originals ↗</a></nav></div></header>
<main id="main">{body}</main><footer>Machine-transcribed. Check the scan before quoting. <a href="{url('about/')}">Methods</a> · <a href="https://github.com/davidgamero/christian-recorder-ocr">GitHub</a></footer></body></html>'''


def transcription(text, position=None, loop_tasks=None):
    # OCR is untrusted text, never Markdown/HTML. Keep line breaks verbatim.
    if position is None:
        return '<div class="transcription">' + e(text) + '</div>'
    if hashlib.sha256(text.encode()).hexdigest() != position['text_sha256']:
        raise ValueError('Text position metadata is stale')
    parts = []
    n = 0
    for span in position['spans']:
        chunk = text[span['start']:span['end']]
        for paragraph in re.finditer(r'\S[\s\S]*?(?=\n\s*\n|\Z)', chunk):
            n += 1
            progress = round(100 * (span['start'] + paragraph.start()) / max(1, len(text)))
            leaf = f"Leaf {int(span['leaf'].split('-')[-1])+1} · " if span.get('leaf') and span['leaf_count'] > 1 else ''
            location = span.get('region_label') or ('Masthead' if span['kind'] == 'header' else 'Sparse region' if span['kind'] == 'sparse' else f"Column {span['column']+1}" if span['column'] is not None else 'Source crop')
            label = f'{progress}% through text · {leaf}{location}'
            loop = (loop_tasks or {}).get(span.get('task'))
            warning = '<span class="loop-warning" data-pagefind-ignore>Possible model loop · check the original</span>' if loop else ''
            parts.append(f'<div class="ocr-paragraph" id="p{n}"><a class="paragraph-position" data-pagefind-ignore href="#p{n}" title="Position in extracted text; column from saved crop geometry">{e(label)}</a>{warning}<div class="paragraph-text">{e(paragraph[0])}</div></div>')
    return '<div class="transcription">' + '\n\n'.join(parts) + '</div>'


def source_links(volume, page):
    leaf = re.search(r"_(\d+)\.jp2$", page["source_page"], re.I)
    viewer = volume["archive_url"] + (f"/page/n{int(leaf[1])}/mode/1up" if leaf else "")
    member = f'https://archive.org/download/{volume["id"]}/{volume["id"]}_jp2.zip/' + quote(page["source_page"], safe="/")
    return viewer, member


def volume_label(identity):
    issue = re.search(r'(?:new_)?no_?(\d+)(?:_to_?|_)(\d+)$', identity)
    if issue:
        return f"Issues {issue[1]}–{issue[2]}"
    bound = re.search(r'christianrecordephil_(.+)$', identity)
    return f"Bound volume {bound[1]}" if bound else "Collected issues"


def volume_sort(source):
    year = re.search(r'\d{4}', source['year'])
    issue = re.search(r'no_?(\d+)', source['id'])
    return (int(year[0]) if year else 9999, source['year'], int(issue[1]) if issue else 0, source['id'])


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    shutil.copytree(SRC / "assets", OUT / "assets")
    catalog = json.loads((ROOT / "corpus/catalog.json").read_text())
    comparison = json.loads((ROOT / 'corpus/comparison.json').read_text())
    loop_audit = json.loads((ROOT / 'corpus/loop-audit.json').read_text())
    if loop_audit['run'] != catalog['run']:
        raise ValueError('Loop audit does not match published corpus')
    positions = json.loads(gzip.decompress((ROOT / 'corpus/positions.json.gz').read_bytes()))
    if comparison['paired_scans'] != catalog['scans'] or comparison['run'] != catalog['run']:
        raise ValueError('Comparison statistics do not match the published corpus')
    cards = defaultdict(list)
    for source in sorted(catalog["sources"], key=volume_sort):
        path = ROOT / "corpus" / source["file"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != source["sha256"]:
            raise ValueError(f"Corpus checksum mismatch: {path.name}")
        volume = json.loads(gzip.decompress(path.read_bytes()))
        sid, year = volume["id"], volume["year"]
        short_label = volume_label(sid)
        label = f"{year} · {short_label}"
        cards[year].append(f'<li><a href="{url(f"volumes/{sid}/")}">{e(short_label)}</a><small>{len(volume["pages"])} scans</small></li>')
        links = []
        for i, page in enumerate(volume["pages"]):
            identity = page["id"]
            quality = "Flagged output" if page["flags"] or page["errors"] else "No output flags"
            loop_tasks = loop_audit['pages'].get(identity, {})
            viewer, member = source_links(volume, page)
            title = f'{year} · {short_label} · Scan {page["number"]}'
            flag_badge = '<span class="flag-badge">Flagged</span>' if page['flags'] or page['errors'] else ''
            links.append(f'<li><a href="{url(f"scans/{identity}/")}">Scan {page["number"]}</a>{flag_badge}</li>')
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
            body = f'''<div class="breadcrumb"><a href="{url('volumes/')}">Volumes</a> / <a href="{url(f'volumes/{sid}/')}">{e(label)}</a></div>
<div class="reading-heading"><h1 class="scan-title">Scan {page['number']}</h1>{flag_badge}</div><span hidden data-pagefind-meta="title">{e(title)}</span>
<span data-pagefind-meta="archive_scan[url]" url="{e(viewer)}" hidden></span><span data-pagefind-meta="archive_volume[url]" url="{e(volume['archive_url'])}" hidden></span>
<div class="reading-toolbar"><p class="actions"><a href="{e(viewer)}" rel="noopener">Original scan ↗</a><a href="text.txt" download>Download text</a></p><nav aria-label="Scan navigation">{navigation}</nav></div>
<div class="reading-options"><details class="source-details"><summary>Source & quality</summary><p><code>(image:extracted:page:{page['number']})</code></p>
<p class="actions"><a href="{e(member)}">Original JP2 ↗</a><a href="{e(volume['archive_url'])}">Archived volume ↗</a><a href="https://onlinebooks.library.upenn.edu/webbin/serial?id=christrecordame">Penn catalog ↗</a><a href="provenance.json">Provenance JSON</a></p>
<dl class="facts"><dt>Volume</dt><dd data-pagefind-filter="Volume">{e(sid)}</dd><dt>Year</dt><dd data-pagefind-filter="Year">{e(year)}</dd>
<dt>Status</dt><dd data-pagefind-filter="Quality">{quality}</dd><dt>Dimensions</dt><dd>{page['width']} × {page['height']}</dd></dl>
<p data-pagefind-filter="Loop audit">{'Possible model loop' if loop_tasks else 'No high-loop candidate'}</p>
<p>Scan positions include cards and two-page spreads—not printed page numbers.</p>
<p>Original member: <code>{e(page['source_page'])}</code></p><p>Output flags: {e(flags)}</p><p>Layout flags: {e(', '.join(page['layout_flags']) or 'none')}</p>
<p>{e('Targeted rerun: '+str(len((page.get('reprocessing') or {}).get('selected_parent_chunks',[])))+' parent chunks replaced; '+str(len((page.get('reprocessing') or {}).get('retained_parent_chunks',[])))+' retained for review.' if page.get('reprocessing') else 'Original v4 extraction.')}</p>
<p>Source SHA-256: <code>{page['image_sha256']}</code></p></details>
<details class="original-comparison" data-pagefind-ignore><summary>Compare original OCR</summary>{original}</details></div>
<aside id="match-navigation" class="match-navigation" data-pagefind-ignore aria-label="Reading tools">
<a class="sticky-original" href="{e(viewer)}" target="_blank" rel="noopener">Open original archive document ↗</a>
<span class="query-tools" hidden>
<span>Find: <strong id="match-query"></strong></span><span id="match-count" role="status" aria-live="polite"></span>
<button id="match-prev" type="button">← Previous</button><button id="match-next" type="button">Jump to next →</button>
<a id="back-to-search" href="{url('#search')}">Back to results</a><span id="match-note"></span></span></aside>
<article data-pagefind-body><h2 id="transcription" class="reading-label">GLM transcription</h2>{transcription(page['text'], positions[identity], loop_tasks)}</article>
<nav class="bottom-pagination" aria-label="Continue reading">{navigation}</nav>'''
            write(f'scans/{identity}/index.html', shell(title, body))
        count_flagged = sum(bool(p['flags'] or p['errors']) for p in volume['pages'])
        write(f'volumes/{sid}/index.html', shell(label, f'<div class="breadcrumb"><a href="{url("volumes/")}">All volumes</a></div><h1>{e(label)}</h1><p class="volume-meta">{len(volume["pages"])} scans · {count_flagged} flagged · <a href="{e(volume["archive_url"])}">Archived original ↗</a></p><p class="fine-print">Scan positions, not printed page numbers. Unflagged text is still unverified.</p><details><summary>Source details</summary><p>{e(sid)}</p><p>{e(volume["year_basis"])}</p><a href="https://onlinebooks.library.upenn.edu/webbin/serial?id=christrecordame">Penn catalog ↗</a></details><ol class="scan-list">'+"".join(links)+'</ol>'))
    year_links = ' · '.join(f'<a href="#year-{i}">{e(year)}</a>' for i,year in enumerate(cards))
    volume_list = ''.join(f'<section class="year-group" id="year-{i}"><h2>{e(year)}</h2><ul class="volume-list">'+''.join(entries)+'</ul></section>' for i,(year,entries) in enumerate(cards.items()))
    write('volumes/index.html', shell('Browse volumes', '<h1>Browse the archive</h1><p class="volume-meta">44 volumes · 2,376 scans</p><nav class="year-jumps" aria-label="Jump to year">'+year_links+'</nav>'+volume_list))
    original_stats, glm_stats = comparison['original'], comparison['glm']
    figure = json.loads((SRC / 'assets/figures/provenance.json').read_text())
    steps = [
        ('scan', 'Start with the scan', 'Keep the original page and its source ID.'),
        ('layout', 'Find the reading order', 'Separate leaves, mastheads and columns.'),
        ('chunks', 'Cut readable pieces', 'Small crops preserve the tiny print.'),
        ('ocr', 'Read in parallel', 'Four GLM requests; CUDA graphs speed decoding.'),
        ('search', 'Search & check', 'Rejoin the text. Every result links to the scan.'),
    ]
    story = '<ol class="pipeline-story">' + ''.join(
        f'<li><figure><img src="{url("assets/diagrams/" + name + ".svg")}" width="240" height="160" loading="lazy" alt="{e(title + ": " + caption)}">'
        f'<figcaption><b><span class="step-number">{i:02d}</span> {e(title)}</b><span>{e(caption)}</span></figcaption></figure></li>'
        for i, (name, title, caption) in enumerate(steps, 1)) + '</ol>'
    home = f'''<section id="search" class="search-front" aria-label="Search the newspaper archive">
<h1 class="search-heading">Search the archive</h1>
<pagefind-config bundle-path="{url('pagefind/')}" base-url="{BASE}" excerpt-length="35"></pagefind-config>
<pagefind-input placeholder="Search a name, place, or phrase…"></pagefind-input>
<p class="search-hint">{catalog['scans']:,} scans · {len(catalog['sources'])} volumes · Use “quotes” for phrases.</p>
<details id="search-filters" class="search-filters"><summary>Filters <span>Year, quality & volume</span></summary><div class="filters"><pagefind-filter-dropdown filter="Year" label="Year"></pagefind-filter-dropdown><pagefind-filter-dropdown filter="Quality" label="Quality flags"></pagefind-filter-dropdown><pagefind-filter-dropdown filter="Loop audit" label="Model loops"></pagefind-filter-dropdown><pagefind-filter-dropdown filter="Volume" label="Volume"></pagefind-filter-dropdown></div></details>
<pagefind-summary></pagefind-summary><pagefind-results hide-sub-results>
<script type="text/pagefind-template"><li class="search-result"><h3><a href="{{{{ url | safeUrl }}}}">{{{{ meta.title }}}}</a></h3><p>{{{{+ excerpt +}}}}</p><p class="result-sources"><a href="{{{{ meta.archive_scan | safeUrl }}}}">Original scan ↗</a> · <a href="{{{{ meta.archive_volume | safeUrl }}}}">Archived volume ↗</a></p></li></script>
</pagefind-results>
<noscript>Full-text search requires JavaScript. <a href="{url('volumes/')}">Browse every volume and transcription without JavaScript.</a></noscript></section>
<details id="project-intro" class="extraction-stats" open><summary><h2 id="stats-title">What is this?</h2><span>Project & extraction results</span></summary><div class="intro-body">
<p>This project improves optical character recognition (OCR) to extract text from archived newspapers and make it searchable.</p>
<div class="stat-columns"><div><strong>+{comparison['word_count_increase_pct']:.0f}%</strong><h3>More text to search</h3><p>{original_stats['total_words']/1e6:.1f}m → {glm_stats['total_words']/1e6:.1f}m word tokens</p></div>
<div><strong>+{comparison['recognized_word_increase_pct']:.0f}%</strong><h3>More recognized words</h3><p>{original_stats['recognized_words']/1e6:.1f}m → {glm_stats['recognized_words']/1e6:.1f}m dictionary matches</p></div>
<div><strong>{original_stats['unrecognized_pct']:.1f}% → {glm_stats['unrecognized_pct']:.1f}%</strong><h3>Fewer unrecognized forms</h3><p>Share absent from the word list</p></div></div>
<p class="fine-print">Same {comparison['paired_scans']:,} scans. Dictionary coverage isn’t accuracy; names, omissions and repetition need review. <a href="{url('about/#comparison')}">How we measured ↗</a></p>
<p class="fine-print">{e(loop_audit['repair_status'])} <a href="{url('about/#loop-repair')}">Rerun details ↗</a></p>
{story}
<p class="fine-print">Illustrated workflow; crop links, not verified word coordinates. {catalog['flagged_scans']:,} scans have output flags. <a href="{url('about/#extraction')}">Real crop overlays ↗</a></p></div></details>'''
    write('index.html', shell('Search the archive', home, search=True))
    about = (SRC / 'content/about.html').read_text()
    if catalog.get('reprocessing'):
        changes = catalog['reprocessing']['outcomes']
        about = about.replace('<!-- reprocessing-summary -->', f"<p>{changes['selected_chunks']:,} parent chunks replaced after automatic checks; {changes['retained_candidates']:,} retained with unresolved flags. Current published text: {catalog['text_bytes']/1e6:.1f} MB / {catalog['word_tokens']/1e6:.2f} million whitespace-separated tokens. This is not human-verified correction.</p>")
    about = about.replace('<!-- extraction-figures -->', f'<div class="process-grid"><figure><img src="{url("assets/figures/columns.svg")}" alt="Column proposals and masthead cutoff"><figcaption>Detected columns · green gutters, blue masthead.</figcaption></figure><figure><img src="{url("assets/figures/chunks.svg")}" alt="Source-mapped OCR chunk polygons"><figcaption>Short chunks · the model receives one crop at a time.</figcaption></figure></div><p><a href="{url("assets/figures/provenance.json")}">Figure provenance and saved crop polygon</a> · <a href="{url("scans/"+figure["page_id"]+"/")}">Example transcription and original scan</a></p>')
    write('about/index.html', shell('Methods, findings and limitations', about))
    write('.nojekyll', '')
    write('404.html', shell('Page not found', f'<h1>Page not found</h1><p><a href="{url()}">Search or browse the archive.</a></p>'))
    write('catalog.json', json.dumps(catalog, indent=2, ensure_ascii=False))
    write('comparison.json', json.dumps(comparison, indent=2))
    write('loop-audit.json', json.dumps(loop_audit, indent=2))
    print(f"Generated {catalog['scans']} scans, {len(catalog['sources'])} volumes at {BASE}")


if __name__ == '__main__':
    main()
