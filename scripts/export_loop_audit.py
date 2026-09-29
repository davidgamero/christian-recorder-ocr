"""Export public loop findings, never repair guesses or local paths."""
import argparse
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def export(data):
    catalog=json.loads((ROOT/'corpus/catalog.json').read_text())
    version='v5' if catalog.get('reprocessing') else 'v4'
    audit=json.loads((data/f'audits/repetition-{version}/report.json').read_text())
    if audit['run'] != catalog['run']:
        raise ValueError('Run the repetition audit for the published run first')
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
    status='Published text includes targeted source-region reprocessing; unresolved candidates retain earlier text and flags.' if version=='v5' else 'Original v4 output; targeted repairs are stored separately.'
    result={'schema':1,'run':audit['run'],'audited_chunks':audit['totals']['chunks'],
            'high_candidate_chunks':audit['totals']['high_chunks'],'high_candidate_scans':audit['high_pages'],
            'repeated_phrase_pct':audit['redundant_phrase_pct'],
            'repair_status':status,
            'pages':pages,'note':'Automated candidates, not blanket deletion rules; source-confirmed repeated poems/ads excluded from page labels.'}
    (ROOT/'corpus/loop-audit.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data',type=Path,required=True)
    export(parser.parse_args().data)
