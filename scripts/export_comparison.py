"""Export aggregate public comparison statistics from a completed lexical report."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def export(path):
    raw = path.read_bytes()
    report = json.loads(raw)
    catalog = json.loads((ROOT / 'corpus/catalog.json').read_text())
    group = report['groups']['archive-ocr']
    if report['run'] != catalog['run'] or group['paired_pages'] != catalog['scans']:
        raise ValueError('Comparison must cover the published run and every scan')
    summary = {
        'schema': 1, 'run': report['run'], 'paired_scans': group['paired_pages'],
        'baseline': 'Page-mapped Internet Archive OCR derivative; not verified PDF-embedded text',
        'original': group['original'], 'glm': group['glm'],
        'word_count_increase_pct': 100 * (group['glm']['total_words'] / group['original']['total_words'] - 1),
        'recognized_word_increase_pct': 100 * (group['glm']['recognized_words'] / group['original']['recognized_words'] - 1),
        'scored_at': report['created'], 'report_sha256': hashlib.sha256(raw).hexdigest(),
        'dictionary_sha256': report['dictionary']['sha256'],
        'note': 'Lexical word counts differ from whitespace token counts. Dictionary recognition is not transcription accuracy or recall; repetition, omissions and invented text remain possible.'
    }
    (ROOT / 'corpus/comparison.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    export(parser.parse_args().report)
