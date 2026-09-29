"""Export an allowlisted, deterministic public snapshot from Recorder artifacts.

No credentials, machine paths, reviewer names, private references or images.
Each volume is a gzip JSON file to keep Git history and clean-clone builds small.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(path.read_text())


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def export(data, run):
    inventory = read(run / "dataset.json")
    status = read(run / "status.json")
    if status["status"] != "complete" or status["done"] != len(inventory["pages"]):
        raise ValueError("Export requires a complete run; keep partial snapshots explicit")
    destination = ROOT / "corpus"
    destination.mkdir(exist_ok=True)
    catalog = {"schema": 1, "run": run.name, "sources": [], "scans": 0, "text_bytes": 0,
               "word_tokens": 0, "flagged_scans": 0,
               "numbering": "One-based scan sequence within each source bundle; not printed pagination. A scan can contain two pages.",
               "model": {"name": "zai-org/GLM-OCR", "revision": "2e85a62840ccac27daa451df36c736c4636b8628",
                         "vllm": "0.28.0", "image_digest": "sha256:61fc8a896b0a4fbbbdc063bc4b0dbc25ce98e02b5050c24aeb7830ac02039b14",
                         "preparation_version": 4, "scheduler": "Initial eager four-way; later cross-page queue and decode CUDA graphs. Original per-page artifacts retain exact session provenance."}}
    reprocess = data / 'reprocessing/multiple-warnings-v2/assembly.json'
    if reprocess.exists() and read(reprocess)['output_run'] == run.name:
        catalog['reprocessing'] = read(reprocess)
        queue=read(reprocess.with_name('queue.json'))
        catalog['reprocessing'].update(queue_sha256=sha(reprocess.with_name('queue.json')),
            source_run=queue['source_run'],policy=queue['policy'],
            targeted_chunks=len(queue['tasks']),targeted_scans=len({t['page_id'] for t in queue['tasks']}),
            note='Automated selection, not human-verified correction. Unresolved candidates retain original text with flags; all prior artifacts preserved in the research workspace.')
        catalog['model']['scheduler'] += ' Targeted v5 source-footprint recropping: up to 900px height, tilted printed-rule cuts, streaming loop cancellation; unresolved wide regions retain prior text.'
    for source_id, source in sorted(inventory["sources"].items()):
        if not re.fullmatch(r"[A-Za-z0-9_-]+", source_id):
            raise ValueError("Unsafe source ID")
        metadata = read(data / "archive" / source_id / "metadata.json").get("metadata", {})
        years = re.findall(r"(?<!\d)(18\d{2})(?!\d)", source_id)
        if not years:
            years = re.findall(r"18\d{2}", str(metadata.get("date", "")))
        year_label = "–".join(dict.fromkeys(years)) or "Undated volume"
        volume = {"id": source_id, "title": "The Christian Recorder", "year": year_label,
                  "year_basis": "Archive identifier/date metadata; not per-issue date verification",
                  "archive_url": source["url"], "bundle_sha256": source["bundle_sha256"], "pages": []}
        for page in sorted((p for p in inventory["pages"] if p["source_id"] == source_id), key=lambda p:p["number"]):
            path = run / "pages" / page["id"] / "result.json"
            result = read(path)
            if result["source_sha256"] != page["sha256"]:
                raise ValueError("Source hash mismatch")
            baseline_path = data / "source-text" / source_id / "archive-ocr" / f"p{page['number']:04d}.json"
            baseline = read(baseline_path) if baseline_path.exists() else None
            if baseline and baseline["source_page"] != page["source_page"]:
                raise ValueError("Original OCR leaf mismatch")
            public = {"id": page["id"], "number": page["number"], "source_page": page["source_page"],
                      "image_sha256": page["sha256"], "width": page["width"], "height": page["height"],
                      "result_sha256": sha(path), "status": result["status"], "text": result["text"],
                      "flags": result.get("flagged", {}), "layout_flags": result.get("layout_flags", []),
                      "errors": result.get("errors", []), "chunks": result["chunks"],
                      "reprocessing": result.get("reprocessing"),
                      "original": {"kind": baseline["kind"], "text": baseline["text"],
                                   "artifact_sha256": baseline["provenance"]["sha256"]} if baseline else None}
            volume["pages"].append(public)
            catalog["scans"] += 1
            catalog["word_tokens"] += len(result["text"].split())
            catalog["text_bytes"] += len(result["text"].encode())
            catalog["flagged_scans"] += bool(public["flags"])
        output = destination / f"{source_id}.json.gz"
        content = json.dumps(volume, ensure_ascii=False, separators=(",", ":")).encode()
        output.write_bytes(gzip.compress(content, compresslevel=9, mtime=0))
        catalog["sources"].append({k:volume[k] for k in ("id", "title", "year", "year_basis", "archive_url", "bundle_sha256")} |
                                  {"scans": len(volume["pages"]), "file": output.name, "sha256": sha(output)})
    (destination / "catalog.json").write_text(json.dumps(catalog, indent=2, ensure_ascii=False) + "\n")
    print({k:v for k,v in catalog.items() if k not in {"sources", "model"}})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--run", default="glm-full-archive-v4-20260925")
    args = parser.parse_args()
    export(args.data, args.data / "parse-runs" / args.run)
