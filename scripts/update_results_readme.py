"""Refresh delimited README results from the exported, matching dataset."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def main():
    catalog=json.loads((ROOT/'corpus/catalog.json').read_text())
    comparison=json.loads((ROOT/'corpus/comparison.json').read_text())
    audit=json.loads((ROOT/'corpus/loop-audit.json').read_text())
    assert catalog['run']==comparison['run']==audit['run']
    rerun=catalog['reprocessing']
    outcomes=rerun['outcomes']
    path=ROOT/'README.md'
    text=path.read_text()
    sections={
        'corpus-summary':f"{catalog['scans']:,} scans, {len(catalog['sources'])} volumes, {catalog['word_tokens']/1e6:.2f} million word tokens. {catalog['text_bytes']/1e6:.1f} mb of extracted text from *the christian recorder*, the african methodist episcopal church's newspaper. searchable on github pages, with links back to the scans.",
        'reprocessing':f"""**targeted v5 update:** reprocessed **{rerun['targeted_chunks']:,} chunks across {rerun['targeted_scans']:,} scans**: all 464 known-failure and 5,981 multiple-warning candidates. **{outcomes['selected_chunks']:,} replacements selected; {outcomes['retained_candidates']:,} originals retained with unresolved flags.** the new dataset is `{catalog['run']}`.

| check | original v4 | published v5 |
|---|---:|---:|
| response chunks | 60,065 | {audit['audited_chunks']:,} |
| high repetition candidates | 434 | {audit['high_candidate_chunks']:,} |
| scans with high repetition | 377 | {audit['high_candidate_scans']:,} |
| repeated-phrase footprint | 3.47% | {audit['repeated_phrase_pct']:.2f}% |
| scans with output/unresolved flags | 435 | {catalog['flagged_scans']:,} |

new crops use detected printed rules, up to 900 pixels of height, and bounded streaming recognition. unresolved wide geometry, errors, empty output, repetition and suspicious volume changes keep the prior text. flags now also include unresolved rerun candidates, so the flag counts aren't a like-for-like accuracy comparison. source-confirmed repeated poems and ads stay intact. the repetition filter and search index were rebuilt from this snapshot. these are automatic diagnostics, not measured transcription accuracy.""",
        'comparison':f"the front-page stats compare all {comparison['paired_scans']:,} matched scans: **{comparison['word_count_increase_pct']:.0f}% more lexical word tokens**, **{comparison['recognized_word_increase_pct']:.0f}% more dictionary-recognized tokens**, and unrecognized forms falling from **{comparison['original']['unrecognized_pct']:.1f}% to {comparison['glm']['unrecognized_pct']:.1f}%**."
    }
    for name,body in sections.items():
        start=f'<!-- {name}-start -->'
        end=f'<!-- {name}-end -->'
        before,rest=text.split(start,1)
        _,after=rest.split(end,1)
        text=before+start+'\n'+body+'\n'+end+after
    path.write_text(text)


if __name__=='__main__':
    main()
