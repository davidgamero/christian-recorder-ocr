"""Export aggregate OCR-health evidence without source text or reviewer records."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def export(data):
    def read(relative):
        path = data / relative
        raw = path.read_bytes()
        return json.loads(raw), hashlib.sha256(raw).hexdigest()

    health, health_sha = read('evaluations/ocr-health-v1/report.json')
    judge, judge_sha = read('evaluations/glm-text-judge-v1/report.json')
    probes, probes_sha = read('evaluations/glm-text-judge-v1/probe-report.json')
    catalog = json.loads((ROOT / 'corpus/catalog.json').read_text())
    if health['new'] != catalog['run']:
        raise ValueError('Health results must match the published edition')
    result = {
        'schema': 1, 'date': '2026-09-29', 'run': health['new'], 'baseline_run': health['old'],
        'regions': health['groups']['all_original_regions'],
        'targeted': health['groups']['targeted'],
        'baseline_bow_disagreement': health['baseline_bow_disagreement'],
        'baseline_disagreement_change': health['baseline_disagreement_change'],
        'page_repetition_percentage_point_change': health['page_repetition_percentage_point_change'],
        'dictionary_sha256': health['dictionary_sha256'],
        'judge': {k: judge[k] for k in ('requests', 'valid_responses', 'summaries')},
        'prompt_controls': probes['summary'],
        'report_hashes': {'health': health_sha, 'judge': judge_sha, 'prompt_controls': probes_sha},
        'notes': health['notes'] + judge['notes'],
        'sources': [
            {'title': 'OCR-D quality assurance', 'url': 'https://ocr-d.de/en/spec/ocrd_eval'},
            {'title': 'olmOCR-Bench methodology', 'url': 'https://github.com/allenai/olmocr/tree/main/olmocr/bench'},
            {'title': 'OmniDocBench', 'url': 'https://arxiv.org/abs/2412.07626'},
            {'title': 'GLM-OCR model card', 'url': 'https://huggingface.co/zai-org/GLM-OCR#prompt-limited'},
        ],
    }
    (ROOT / 'corpus/health.json').write_text(json.dumps(result, indent=2) + '\n')
    print('Exported aggregate health results for', result['run'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, required=True)
    export(parser.parse_args().data)
