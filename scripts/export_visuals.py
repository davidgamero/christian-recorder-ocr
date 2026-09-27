"""Create three small teaching figures from a real saved extraction (requires Pillow)."""
import argparse
from html import escape
import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def export(data):
    identity = 'christianrecorder_1868_v8_no16_to_28-p003'
    run = data / 'parse-runs/glm-full-archive-v4-20260925'
    folder = run / 'pages' / identity
    manifest = json.loads((folder / 'manifest.json').read_text())
    inventory = json.loads((run / 'dataset.json').read_text())
    page = next(p for p in inventory['pages'] if p['id'] == identity)
    output = ROOT / 'assets/figures'
    output.mkdir(parents=True, exist_ok=True)
    with Image.open(data / page['image']) as im:
        im = im.convert('RGB')
        im.thumbnail((720, 950))
        im.save(output / 'scan.jpg', quality=78, optimize=True)
    width, height = im.size
    def svg(name, shapes, title):
        content = f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img"><title>{escape(title)}</title><image href="scan.jpg" width="{width}" height="{height}"/>{shapes}</svg>'
        # Inline the JPEG so an SVG used in <img> has no external resource dependency.
        import base64
        content = content.replace('href="scan.jpg"', 'href="data:image/jpeg;base64,' + base64.b64encode((output/'scan.jpg').read_bytes()).decode() + '"')
        (output / name).write_text(content)
    layout = manifest['leaves'][0]['layout']
    shapes = ''
    for c in range(layout['columns'] + 1):
        points = ' '.join(f'{edges[c]*width:.2f},{y*height:.2f}' for y, edges in zip(layout['ys'],layout['boundaries']))
        shapes += f'<polyline points="{points}" stroke="#1f6c54" stroke-width="2.5" fill="none"/>'
    y = layout['body_start'] * height
    shapes += f'<path d="M0 {y}H{width}" stroke="#295faf" stroke-width="4"/>'
    svg('columns.svg', shapes, 'Saved column boundary proposals in green; masthead cutoff in blue.')
    selected = next(t for t in manifest['tasks'] if t['id']=='leaf-0-chunk-3-0-0')
    shapes = ''
    for task in manifest['tasks']:
        if task['mode'] != 'chunks':
            continue
        points = ' '.join(f'{x*width:.2f},{y*height:.2f}' for x,y in task['polygon'])
        highlight = task['id'] == selected['id']
        shapes += f'<polygon points="{points}" fill="{ "#a43923" if highlight else "#d8a54b"}" fill-opacity="{.45 if highlight else .12}" stroke="#a43923" stroke-width="1.4"/>'
    svg('chunks.svg', shapes, 'Saved short OCR chunks, with one example highlighted in red.')
    crop_path = folder / 'images' / Path(selected['image']).name
    with Image.open(crop_path) as crop:
        crop = crop.convert('RGB')
        crop.thumbnail((480, 1500))
        crop.save(output / 'chunk.jpg',quality=88,optimize=True)
    response = json.loads((folder / 'responses' / f"{selected['id']}.json").read_text())
    (output/'provenance.json').write_text(json.dumps({'page_id':identity,'source_sha256':page['sha256'],
        'task_id':selected['id'],'input_sha256':selected['image_sha256'],'polygon':selected['polygon'],
        'layout_flags':layout['flags'],'excerpt':response['text'][:550],
        'note':'Real saved crop-level geometry; not verified word-level alignment. Detected boundaries may cross text.'},indent=2)+'\n')
    print('Exported source-derived figures:',output)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data',type=Path,required=True)
    export(parser.parse_args().data)
