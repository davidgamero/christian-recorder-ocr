# The Christian Recorder — searchable OCR research archive

**Site:** https://davidgamero.github.io/christian-recorder-ocr/  
**Original source catalog:** [The Online Books Page, University of Pennsylvania](https://onlinebooks.library.upenn.edu/webbin/serial?id=christrecordame)

A static, searchable edition of machine-extracted text from **2,376 scans across
44 source bundles** of *The Christian Recorder*, the newspaper of the African
Methodist Episcopal Church. Search names, places, articles and advertisements,
then open the original scan to verify the reading.

This repository contains the exported corpus, source provenance, static-site
generator and GitHub Pages publishing workflow. It requires **no inference API,
database server or credentials** to build or search. The experimental GPU/OCR
framework remains in the parent research workspace; this is its portable public
publication snapshot, not a complete redistribution of that runtime.

## Sources and navigation

- [Penn serial catalog](https://onlinebooks.library.upenn.edu/webbin/serial?id=christrecordame): starting point for the collection.
- Original volumes and scans are hosted by **Internet Archive**. Every volume
  page links to its archived record. Every transcription and search result links
  to the corresponding archived scan; transcription pages also link to the
  original JP2 ZIP member and Penn's catalog.
- `corpus/catalog.json` records every source identifier, Archive URL, compressed
  corpus checksum and original bundle SHA-256.
- A scan's `provenance.json` records its image/result hashes, dimensions, original
  member name, model identity, flags and source links.

Scan positions are one-based within each bundle and include separator cards.
**They are not printed newspaper page numbers.** One scan may contain two printed
pages. Archive viewer links use the JP2 member's explicit leaf suffix rather than
assuming `scan number - 1`. Missing year metadata remains “Undated volume”; years
in identifiers/date metadata are volume labels, not verified issue dates.

## Completed corpus

| Measure | Value |
|---|---:|
| Source bundles | 44 |
| Actual JP2 scans | 2,376 |
| Downloaded compressed bundles | ~2.11 GB |
| GLM transcription text, counted once | 121,383,823 bytes (~121.4 MB) |
| Whitespace-separated word tokens | 21,127,105 |
| Scans with recorded output flags | 435 |
| Failed pages in the completed v4 run | 0 |

The initial metadata inventory advertised 2,377 images. Inspection of the verified
ZIP files found 2,376: `christianrecorder_1864_v4_no14_to_26` has 51 JP2 members
rather than 52. No nonexistent page was invented to reconcile the count.

**All pages processed does not mean all text is correct.** Counts include model
repetition and other OCR defects. The original images are the authority.

## How we arrived at this extraction approach

### 1. CPU baseline and layout experiments

We started with Tesseract and a learned seven-column template from training layout
annotations. Local gutter alignment, curved-column unwarping, overlapping strips,
line ownership and source coordinates improved the extraction/review workflow.
Training selected preprocessing and layout parameters; it did **not** fine-tune
neural model weights. Original train/validation/test groups were source-separated.

### 2. Vision models on identical inputs

We compared DeepSeek Flash, local GLM-OCR and local PaddleOCR-VL-1.6 using the same
saved PNGs. Input strategies were whole pages, full columns, short column chunks
with a separate header, and isolated reference crops.

| Chunks + header | Character error | Word error | Summed request seconds/page | Truncated calls |
|---|---:|---:|---:|---:|
| DeepSeek Flash, saved API experiment | 0.52% | 3.28% | 79–93 | 0/44 |
| **GLM-OCR, RTX 3090** | **0.52%** | **3.28%** | 153–180 | **0/44** |
| PaddleOCR-VL-1.6, RTX 3090 | 0.78% | 4.51% | 129–189 | 1/44 |
| Linux Tesseract, identical fixed chunks | 5.88% | 26.64% | 88–124 | n/a |

These scores cover **two previously inspected, provisional reference excerpts
(244 words)** inside assembled page output. They use reference-assisted excerpt
matching, **not complete-page recall**. Four isolated crops (395 words) separately
gave CER of 0.37% DeepSeek, 0.58% Paddle, 1.11% GLM and 4.20% Linux Tesseract.

Whole-page vision requests generated severe repetition and often hit output-token
limits. Short chunks preserve small-print detail and bound the scope of failures.
GLM's reliable chunk behavior made it the local candidate. Paddle's default
~1-megapixel image budget shrank whole pages more aggressively. The Linux fixed-
chunk diagnostic differs from the production overlapping-strip Tesseract pipeline.
DeepSeek used two concurrent API calls; initial local tests were sequential, so
summed request times are not equivalent wall-time throughput measurements.

### 3. A failed full-archive layout assumption, then preparation v4

The initial full run reused a classifier that treated landscape scans as separator
cards. In fact, many scans are book spreads. Full-width horizontal strips crossed
multiple newspaper columns and produced repetition. We stopped after 292 scans,
retained the evidence, and created a fresh run.

The published **v4** run uses:
- Interior text-density classification and local-contrast binding detection.
- Separate left/right leaves where appropriate.
- Printed-rule gutter proposals, adaptive column counts and sloped masthead cuts.
- Source-resolution grayscale column crops, approximately 1.2 MP / up to 1,800 px
  high, with cuts snapped toward nearby light rows.
- Explicit source polygons, minimum crop dimensions, bounded requests and flags
  for empty/repetitive/truncated output.

The user accepted this output as a useful research/search upgrade. It is still
uncorrected: spanning advertisements, broken/curved rules, unusual layouts and
blank areas remain difficult. The two user-transcribed development crops favored
GLM over Archive OCR, but uncertain reference characters prevent treating those
scores as independently verified accuracy.

### 4. Parallelism and CUDA graphs

On an RTX 3090 with 24 GiB VRAM, a controlled test used 44 fixed chunks/headers
and two repeats per configuration:

| Configuration | Mean two-page wall time | Relative throughput |
|---|---:|---:|
| Four active requests, eager execution | 92.0s | 1.00× |
| Eight active requests, eager execution | 57.6s | 1.60× |
| **Four active requests, decode CUDA graphs** | **26.8s** | **3.43×** |

CUDA graphs replay the repeated GPU decode operations with less CPU launch
overhead. Sampled GPU utilization rose from ~30% to ~95%. All 264 benchmark calls
completed without errors/truncation, and checked excerpt scores stayed unchanged;
some output strings differed slightly between runs. This is not proof of identical
full-page accuracy. Graphs plus eight active requests was not tested/deployed.

We also added one-page preparation in parallel with GPU inference, a bounded
three-page look-ahead and a shared four-request chunk queue across pages. Completed
pages were reused rather than re-extracted. The final run therefore includes
earlier eager sessions and later graph-accelerated sessions.

### Runtime identity

- Model: [`zai-org/GLM-OCR`](https://huggingface.co/zai-org/GLM-OCR)
- Model/tokenizer revision: `2e85a62840ccac27daa451df36c736c4636b8628`
- vLLM `0.28.0`, Transformers `5.15.1`, Torch `2.13.0+cu130`
- Image digest: `sha256:61fc8a896b0a4fbbbdc063bc4b0dbc25ce98e02b5050c24aeb7830ac02039b14`
- BF16, 32K context, 70% GPU allocation, four active sequences
- Prompt: `Text Recognition:`; temperature 0, seed 0
- Prefix/image processor caching disabled during controlled performance tests
- Later decode graph config: `{"mode":0,"cudagraph_mode":"FULL_DECODE_ONLY","cudagraph_capture_sizes":[1,2,4,8]}`

## Original OCR, word dictionaries and comparison limits

The local original PDF's searchable layer was preserved using `pdftotext` with
one call per page. The full native-JP2 archive instead has an existing **Archive
DjVu XML OCR derivative**, mapped to JP2 members through explicit leaf filenames.
It is **not asserted to be identical to the corresponding PDF text layer**.

This site includes that Archive OCR as an optional per-scan comparison, fetched
only when requested. Search indexes **only GLM transcription**, avoiding duplicate
hits from originals, metadata and navigation.

The research workspace also built frequency inventories using a checksum-pinned
[wiki100k list](https://gist.github.com/thisiswei/4c1f7ccad5b589e0e3f7), recognized/
unrecognized word percentages, volume-sensitive scores and repeated-eight-word
sequence checks. AI reviewers examined 300 priority word types and an independent
audit. Historical words, personal/place names and advertising codes often explain
dictionary misses; dictionary-valid substitutions can still be wrong. These
screening metrics do not measure transcription correctness or missing-line recall.
Those large experimental dictionaries/reviewer records are not published here.

## Build and publish

Requirements: **Python 3.12+ and Node.js 22+**.

```sh
npm ci
npm test
npm run build
```

This generates `_site/`, runs pinned **Pagefind 1.5.2**, checks every local link,
verifies the 2,376 scan count and enforces a 950 MB artifact budget. The first full
build measured **455.5 MB total**, including a **96.2 MB Pagefind bundle**—within
GitHub Pages' 1 GB published-site limit. Pagefind indexed 2,376 documents and
236,037 distinct indexed terms. This is distinct from the 21.1m token count.

To preview locally at the domain root:

```sh
BASE_PATH=/ npm run build
npm run serve
# http://localhost:8080
```

Default builds use `/christian-recorder-ocr/`, including all internal links and
Pagefind's bundle/result base URL. For GitHub Pages, choose **Settings → Pages →
Source: GitHub Actions**. The checked-in `.github/workflows/pages.yml` builds on
push to `main` and manual dispatch, uploads the generated artifact, and deploys
with `pages:write` and OIDC permissions. Generated HTML/index files are not checked
into Git; the workflow rebuilds from the versioned corpus snapshot.

### Refresh the public corpus snapshot

From a machine with the original Recorder workspace:

```sh
python3 scripts/export_corpus.py \
  --data /path/to/andrew-newspaper/data \
  --run glm-full-archive-v4-20260925
npm run build
```

The exporter requires a completed run and validates image/result identity. It
uses an allowlist of public fields; machine paths, endpoint addresses, credentials,
reviewer names and user reference transcriptions are excluded. Each volume is a
deterministic gzip JSON file, ~100 MB total compressed snapshot including original
OCR. Clean-clone builds do not contact Archive or rerun models. Refreshing replaces
the snapshot; preserve research revisions and avoid treating changed output as
the same experiment.

## Repository layout

```text
corpus/                 Versioned compressed per-volume text and public metadata
scripts/export_corpus.py  Export from private/local research artifacts
scripts/build.py        Generate HTML, original-text downloads and provenance
scripts/check_site.py   Check count, links and artifact size
assets/                 Site styling and on-demand original OCR loader
content/about.html      Public methods and findings
tests/                  Escaping, source-link and project-subpath tests
.github/workflows/      Build and GitHub Pages deployment
```

## Responsible use and corrections

This is an independent research edition, not an official Penn/Archive/AME
publication. Historical wording can be offensive; reproducing it does not endorse
it. Original historical issues are from the nineteenth century; consult linked
source records for item-specific rights and provenance. No claim of ownership is
made over the original newspaper. No blanket license for third-party source
material is implied by this repository.

Before quoting, inspect the linked scan. Report issues with the **source ID,
scan number, original member/leaf, and passage location**. Better future evaluation
needs independently checked transcriptions, full-column/page coverage labels and
boundary/reading-order assessment. A clean-looking sentence or dictionary hit is
not evidence that the model read it correctly.
