"""Export verified text offsets to saved OCR crop/column identities."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def export(data):
    catalog = json.loads((ROOT / 'corpus/catalog.json').read_text())
    run = data / 'parse-runs' / catalog['run']
    positions = {}
    for source in catalog['sources']:
        volume = json.loads(gzip.decompress((ROOT / 'corpus' / source['file']).read_bytes()))
        for page in volume['pages']:
            folder = run / 'pages' / page['id']
            manifest = json.loads((folder / 'manifest.json').read_text())
            tasks = sorted(manifest['tasks'], key=lambda t:t['order'])
            parts, spans, offset = [], [], 0
            for task in tasks:
                row = json.loads((folder / 'responses' / (task['id'] + '.json')).read_text())
                text = row.get('text', '')
                leaf = next((x for x in manifest.get('leaves', []) if x['id'] == task.get('leaf_id')), None)
                spans.append({'start':offset, 'end':offset + len(text), 'task':task['id'],
                              'leaf':task.get('leaf_id'), 'column':task.get('column'),
                              'region_label':task.get('region_label'),
                              'kind': 'header' if task['mode'] == 'header' else 'sparse' if leaf and leaf['kind'] != 'newspaper' else 'column',
                              'leaf_count':len(manifest.get('leaves', []))})
                parts.append(text)
                offset += len(text) + 1
            if '\n'.join(parts) != page['text']:
                raise ValueError(f"Published text and crop assembly differ: {page['id']}")
            positions[page['id']] = {'text_sha256':hashlib.sha256(page['text'].encode()).hexdigest(), 'spans':spans}
    payload = json.dumps(positions, separators=(',', ':')).encode()
    (ROOT / 'corpus/positions.json.gz').write_bytes(gzip.compress(payload, mtime=0))
    print(f'Verified crop offsets for {len(positions)} scans')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, required=True)
    export(parser.parse_args().data)
