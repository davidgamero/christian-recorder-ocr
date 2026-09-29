# christian recorder ocr

### old newspapers. searchable text. original scans.

**[search the archive →](https://davidgamero.github.io/christian-recorder-ocr/)**

[browse volumes](https://davidgamero.github.io/christian-recorder-ocr/volumes/) · [the project](https://davidgamero.github.io/christian-recorder-ocr/about/) · [research notebook](https://davidgamero.github.io/christian-recorder-ocr/research/) · [originals at penn](https://onlinebooks.library.upenn.edu/webbin/serial?id=christrecordame)

<!-- corpus-summary-start -->
2,376 scans, 44 volumes, 20.85 million word tokens. 120.4 mb of extracted text from *the christian recorder*, the african methodist episcopal church's newspaper. searchable on github pages, with links back to the scans.
<!-- corpus-summary-end -->

> a finding aid, not a verified transcription. check the original scan before quoting.

## read & explore

- **search a name, place or phrase.** use quotes for phrases; queries follow you into the reading view.
- **follow the source.** the sticky reading bar opens the original scan. existing archive ocr is available for comparison.
- **keep your place.** paragraph links show progress through extracted text and saved crop identities, not verified word coordinates.
- **browse by year.** mobile filters start collapsed; every volume has a scan-by-scan index.

## what changed

the v5 repair pass reduced generation failures. a follow-up study compared the **same 60,065 original regions**, joining replacement subcrops before scoring.

| health indicator | original v4 | published v5 |
|---|---:|---:|
| high-repetition regions | 434 | **178** |
| token-limit failures | 439 | **182** |
| repeated-phrase footprint | 3.47% | **1.55%** |
| dictionary-missing share | 2.124% | 2.130% |
| tokens longer than 30 characters | 142 | 173 |

**59% fewer high-repetition regions; 58.5% fewer token-limit failures.** dictionary coverage barely moved, and some indicators worsened. the repairs were screened for loops and truncation, so those gains aren't independent proof of transcription accuracy.

### can a local model catch bad extractions?

| experiment | result | takeaway |
|---|---|---|
| glm-ocr · text with 1, 2 or 3 columns of context | **0/171 evidence-supported judgments** | copied placeholders or continued text; more context didn't help |
| simpler glm prompts · synthetic controls | yes/no said “yes” to everything; ten usable json answers all said “no issue” | valid formatting isn't discrimination |
| qwen3-vl-4b · crop images | caught 5/5 multi-column test crops; missed 2 clipped crops; flagged 0/22 singles | promising geometry signal, with ad/table false alarms in a separate audit |
| kev-4b · text-only repair review | 12 of 13 outputs called readable still had source-visible defects | readability doesn't establish fidelity |

these are different, small experiments—not a shared leaderboard. the primary glm test used 53 real targets and four synthetic controls at three context sizes. column labels describe geometry; earlier repair judgments were ai scan-grounded reviews, not human transcription gold.

**next useful measurements:** source-verified phrase presence, reading order, and character/word error on representative transcriptions. cheap repetition checks and image-based layout review remain complementary.

[full methods, definitions & sources →](https://davidgamero.github.io/christian-recorder-ocr/research/) · [aggregate health data](corpus/health.json)

---

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

original v4 run: **all 2,376 scans processed**, zero failed pages, **435 scans with output flags**. the current snapshot includes the targeted v5 pass below. finished doesn't mean flawless. pilot accuracy covers only 244 reference words, not full-page recall. request times are summed latency; deepseek used two concurrent calls, initial local tests used one.

## the repair pass

<!-- reprocessing-start -->
**targeted v5 update:** reprocessed **6,445 chunks across 1,496 scans**: all 464 known-failure and 5,981 multiple-warning candidates. **4,189 replacements selected; 2,256 originals retained with unresolved flags.** the new dataset is `glm-full-archive-v5-20260929`.

| check | original v4 | published v5 |
|---|---:|---:|
| response chunks | 60,065 | 70,084 |
| high repetition candidates | 434 | 178 |
| scans with high repetition | 377 | 169 |
| repeated-phrase footprint | 3.47% | 1.55% |
| scans with output/unresolved flags | 435 | 1,169 |

new crops use detected printed rules, up to 900 pixels of height, and bounded streaming recognition. unresolved wide geometry, errors, empty output, repetition and suspicious volume changes keep the prior text. flags now also include unresolved rerun candidates, so the flag counts aren't a like-for-like accuracy comparison. source-confirmed repeated poems and ads stay intact. the repetition filter and search index were rebuilt from this snapshot. these are automatic diagnostics, not measured transcription accuracy.
<!-- reprocessing-end -->

an earlier 442-candidate loop repair passed many automatic checks, but source review found clipped columns and omissions. we kept those attempts separate. the new pass reads the original scan pixels and cuts at detected, possibly tilted, printed rules. an equal-width fallback was discarded after a preview showed it cutting through text. missing gutters, clipped exterior edges and reading order still need source review; clean output is not proof of completeness.

## how we got here

**1. start with tesseract.** learned a column template, aligned curved gutters, and tried overlapping strips. kept source coordinates so every reading could be checked against the image.

**2. try vision models.** compared whole pages, columns, chunks and reference crops. whole-page inputs lost tiny text and generated repetition. short column chunks plus a separate masthead worked best. glm matched deepseek's aggregate pilot score locally on a 24 gb rtx 3090.

**3. fix the spread mistake.** the first archive run treated landscape book spreads as separator cards. bad crops, bad repetition. stopped at 292 scans. rebuilt around separate leaves, printed-rule gutters, sloped mastheads and bounded chunks, then started a fresh run.

**4. keep the gpu busy.** prepared upcoming pages while decoding current ones, shared the chunk queue across pages, and enabled decode cuda graphs. gpu utilization went from roughly 30% to 95%. the checked excerpt scores stayed the same; some individual readings still changed slightly.

**5. keep the evidence.** saved original archive ocr separately, tracked word frequencies and repetition, and reviewed 300 priority word types with ai reviewers. names, historical spelling and ad codes aren't automatically gibberish. dictionary-valid words can still be wrong.

**6. publish it.** static html + pagefind 1.5.2. search runs in your browser. original ocr loads on demand and stays out of the search index. images stay at internet archive. every dataset refresh rebuilds paragraph offsets, repetition labels, comparison statistics and search.

## source details

- penn's [serial catalog](https://onlinebooks.library.upenn.edu/webbin/serial?id=christrecordame) led us to the archived volumes. every scan page and search result links back to the original.
- downloaded jp2 bundles slowly: one connection, 512 kib/s, 15-second pauses, checksums and backoff. actual files totaled 2,376 scans, one fewer than the metadata estimate.
- scan numbers include separator cards and sometimes two printed pages. **they aren't printed newspaper page numbers.** year labels come from source metadata; unknown dates stay undated.
- the comparison text is archive's page-mapped ocr derivative, not a verified copy of each pdf text layer. source member names and hashes are published with each scan.
- model: `zai-org/GLM-OCR`, revision `2e85a62840ccac27daa451df36c736c4636b8628`; vllm `0.28.0`, bf16, v4 preparation with targeted v5 source-region recropping, `Text Recognition:` prompt. earlier pages used eager execution; later pages and the targeted rerun used cuda graphs. exact public model metadata is in `corpus/catalog.json`.

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
python3 scripts/export_corpus.py --data /path/to/andrew-newspaper/data --run glm-full-archive-v5-20260929
python3 scripts/export_positions.py --data /path/to/andrew-newspaper/data
python3 scripts/export_loop_audit.py --data /path/to/andrew-newspaper/data
python3 scripts/export_comparison.py /path/to/data/lexical-comparison/glm-full-archive-v5-20260929/report.json
python3 scripts/export_health.py --data /path/to/andrew-newspaper/data
python3 scripts/update_results_readme.py
# optional: regenerate source-derived teaching figures (requires pillow)
python3 scripts/export_visuals.py --data /path/to/andrew-newspaper/data
```

`src/assets/` holds styles, scripts and svg diagrams; `src/content/` holds page copy. `corpus/` stores checksummed text snapshots, `scripts/` builds them, and `.github/workflows/pages.yml` publishes the site. builds don't contact archive or run a model. private reviewer data, credentials and machine paths aren't exported.

optional browser checks (playwright + chromium): `python3 tests/browser_smoke.py` and `python3 tests/mobile_audit.py`. the mobile audit covers 48 views at 320/390/430/768px: search, filters, reading controls, original ocr, source details, volume browsing, project, research and 404. checks include overflow, primary touch targets, expandable research methods and highlighted text staying below the sticky bar.

<!-- comparison-start -->
the front-page stats compare all 2,376 matched scans: **18% more lexical word tokens**, **54% more dictionary-recognized tokens**, and unrecognized forms falling from **25.1% to 2.1%**.
<!-- comparison-end -->
the baseline is archive ocr, not verified pdf-embedded text. these measure dictionary coverage, not correctness. five small svg diagrams tell the story: scan → layout → chunks → parallel ocr → search. real v4 crop overlays live on the project page; neither view claims word-level alignment.

## use it as a finding aid

**check the scan before quoting.** missing text, wrong names, repetition and plausible invented readings remain possible. this is an independent research edition, not an official penn, archive or ame publication. historical wording is reproduced without endorsement; consult source records for rights and provenance.

[report a problem](https://github.com/davidgamero/christian-recorder-ocr/issues) with the scan id and passage location.
