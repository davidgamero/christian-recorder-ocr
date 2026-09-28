# christian recorder ocr

**[check out the results first →](https://davidgamero.github.io/christian-recorder-ocr/)**

[original source catalog — penn](https://onlinebooks.library.upenn.edu/webbin/serial?id=christrecordame) · [browse volumes + archived originals](https://davidgamero.github.io/christian-recorder-ocr/volumes/) · [methods + caveats](https://davidgamero.github.io/christian-recorder-ocr/about/)

2,376 scans, 44 volumes, 21.1 million word tokens. 121.4 mb of extracted text from *the christian recorder*, the african methodist episcopal church's newspaper. searchable on github pages, with links back to the scans.

search links keep your query in `?q=…`. open a result to highlight exact matches and jump between them. quoted phrases stay together; word variants found by search may not have exact highlights.

the sticky reading bar opens the archived original. paragraph labels show progress through extracted text and the saved crop's leaf/column—not physical page percentage or verified word coordinates. filters start collapsed on mobile; volumes are grouped by year.

## results table

same chunked inputs, two checked excerpts. lower error is better.

| approach | character error | word error | request seconds/page | takeaway |
|---|---:|---:|---:|---|
| tesseract, fixed chunks | 5.88% | 26.64% | 88–124 | useful baseline; lots of broken words |
| deepseek flash | 0.52% | 3.28% | 79–93 | strong on chunks; whole pages repeated |
| paddleocr-vl-1.6 | 0.78% | 4.51% | 129–189 | good small crops; some chunk/column repetition |
| **glm-ocr** | **0.52%** | **3.28%** | 153–180 | **selected for the local archive run** |

speed test, same 44 chunks/headers, two repeats:

| runtime | wall time | speedup |
|---|---:|---:|
| 4 requests, eager | 92.0s | 1× |
| 8 requests, eager | 57.6s | 1.60× |
| **4 requests, cuda graphs** | **26.8s** | **3.43×** |

final run: **all 2,376 scans processed**, zero failed pages, **435 scans with output flags**. finished doesn't mean flawless. pilot accuracy covers only 244 reference words, not full-page recall. request times are summed latency; deepseek used two concurrent calls, initial local tests used one.

## how we got here

**loop repair update:** a full audit found 434 high-loop candidates among 60,065 chunks. source-confirmed repeated poems/ads are preserved. the site now labels suspect passages and adds a model-loop filter. **442 targeted repairs are queued**, waiting for a successful sglang/vllm benchmark and gpu restoration. published text is not replaced yet. the repair worker checks crop geometry, splits into smaller pieces, cancels strong streaming loops and stops after two retry rounds, keeping every attempt and source coordinate.

**1. start with tesseract.** learned a column template, aligned curved gutters, and tried overlapping strips. kept source coordinates so every reading could be checked against the image.

**2. try vision models.** compared whole pages, columns, chunks and reference crops. whole-page inputs lost tiny text and generated repetition. short column chunks plus a separate masthead worked best. glm matched deepseek's aggregate pilot score locally on a 24 gb rtx 3090.

**3. fix the spread mistake.** the first archive run treated landscape book spreads as separator cards. bad crops, bad repetition. stopped at 292 scans. rebuilt around separate leaves, printed-rule gutters, sloped mastheads and bounded chunks, then started a fresh run.

**4. keep the gpu busy.** prepared upcoming pages while decoding current ones, shared the chunk queue across pages, and enabled decode cuda graphs. gpu utilization went from roughly 30% to 95%. the checked excerpt scores stayed the same; some individual readings still changed slightly.

**5. keep the evidence.** saved original archive ocr separately, tracked word frequencies and repetition, and reviewed 300 priority word types with ai reviewers. names, historical spelling and ad codes aren't automatically gibberish. dictionary-valid words can still be wrong.

**6. publish it.** static html + pagefind 1.5.2. search runs in your browser. original ocr loads on demand and stays out of the search index. full build: **455.5 mb**, including **96.2 mb of search data**. images stay at internet archive.

## source details

- penn's [serial catalog](https://onlinebooks.library.upenn.edu/webbin/serial?id=christrecordame) led us to the archived volumes. every scan page and search result links back to the original.
- downloaded jp2 bundles slowly: one connection, 512 kib/s, 15-second pauses, checksums and backoff. actual files totaled 2,376 scans, one fewer than the metadata estimate.
- scan numbers include separator cards and sometimes two printed pages. **they aren't printed newspaper page numbers.** year labels come from source metadata; unknown dates stay undated.
- the comparison text is archive's page-mapped ocr derivative, not a verified copy of each pdf text layer. source member names and hashes are published with each scan.
- model: `zai-org/GLM-OCR`, revision `2e85a62840ccac27daa451df36c736c4636b8628`; vllm `0.28.0`, bf16, preparation v4, `Text Recognition:` prompt. earlier pages used eager execution; later pages used cuda graphs. exact public model metadata is in `corpus/catalog.json`.

## build / publish

python 3.12+, node 22+:

```sh
npm ci
npm test
npm run build
```

push to `main` → github actions builds and deploys pages. select **settings → pages → github actions** when setting up a fork. builds use `/christian-recorder-ocr/`; change `BASE_PATH` for another path.

local preview:

```sh
BASE_PATH=/ npm run build
npm run serve
# http://localhost:8080
```

refresh from the recorder research workspace:

```sh
python3 scripts/export_corpus.py --data /path/to/andrew-newspaper/data
python3 scripts/export_positions.py --data /path/to/andrew-newspaper/data
python3 scripts/export_loop_audit.py --data /path/to/andrew-newspaper/data
python3 scripts/export_comparison.py /path/to/data/lexical-comparison/glm-full-archive-v4-20260925/report.json
# optional: regenerate source-derived teaching figures (requires pillow)
python3 scripts/export_visuals.py --data /path/to/andrew-newspaper/data
```

`src/assets/` holds styles, scripts and svg diagrams; `src/content/` holds page copy. `corpus/` stores checksummed text snapshots, `scripts/` builds them, and `.github/workflows/pages.yml` publishes the site. builds don't contact archive or run a model. private reviewer data, credentials and machine paths aren't exported.

optional browser checks (playwright + chromium): `python3 tests/browser_smoke.py` and `python3 tests/mobile_audit.py`. the mobile audit covers 40 views at 320/390/430/768px: search, filters, reading controls, original ocr, source details, volume browsing, project and 404. checks include overflow, primary touch targets and highlighted text staying below the sticky bar.

the front-page stats compare all 2,376 matched scans: **19% more lexical word tokens**, **55% more dictionary-recognized tokens**, and unrecognized forms falling from **25.1% to 2.1%**. the baseline is archive ocr, not verified pdf-embedded text. these measure coverage, not correctness. five small svg diagrams tell the story: scan → layout → chunks → parallel ocr → search. real crop overlays live on the project page; neither view claims word-level alignment.

## use it as a finding aid

**check the scan before quoting.** missing text, wrong names, repetition and plausible invented readings remain possible. this is an independent research edition, not an official penn, archive or ame publication. historical wording is reproduced without endorsement; consult source records for rights and provenance.

[report a problem](https://github.com/davidgamero/christian-recorder-ocr/issues) with the scan id and passage location.
