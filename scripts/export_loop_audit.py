"""Export public loop findings, never repair guesses or local paths."""
import argparse
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def export(data):
    audit=json.loads((data/'audits/repetition-v4/report.json').read_text())
    reviews=json.loads((data/'audits/repetition-v4/inspection.json').read_text())['reviews']
    decisions={(r['page_id'],r['task_id']):r['classification'] for r in reviews}
    pages={}
    for candidate in audit['candidates']:
        if candidate['severity']!='high':
            continue
        state=decisions.get((candidate['page_id'],candidate['task_id']),'possible_model_loop')
        if state=='printed_repetition':
            continue
        pages.setdefault(candidate['page_id'],{})[candidate['task_id']]={
            'status':state,'repeated_pct':candidate['redundant_phrase_pct'],
            'finish_reason':candidate['finish_reason']}
    result={'schema':1,'run':audit['run'],'audited_chunks':audit['totals']['chunks'],
            'high_candidate_chunks':audit['totals']['high_chunks'],'high_candidate_scans':audit['high_pages'],
            'repeated_phrase_pct':audit['redundant_phrase_pct'],'targeted_repair_chunks':442,
            'repair_status':'Queued; waiting for a successful engine benchmark and restored GPU workload. Published text is not yet replaced.',
            'pages':pages,'note':'Automated candidates, not blanket deletion rules; source-confirmed repeated poems/ads excluded from page labels.'}
    (ROOT/'corpus/loop-audit.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data',type=Path,required=True)
    export(parser.parse_args().data)
