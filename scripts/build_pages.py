"""Build the static Pages frontend; optional backend URL is public, never a key."""
import argparse
import json
import re
import shutil
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def build(output, base_path='/Essay-Marking-System/', api_base=''):
    from app import demo
    base_path = '/' + base_path.strip('/') + '/' if base_path.strip('/') else '/'
    if not re.fullmatch(r'/[A-Za-z0-9_./-]*/', base_path) and base_path != '/':
        raise ValueError('base path must be a URL path')
    if '..' in base_path.split('/'):
        raise ValueError('base path may not contain parent traversal')
    api_base = api_base.rstrip('/')
    if api_base:
        parsed = urlparse(api_base)
        if (parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password
                or parsed.path or parsed.query or parsed.fragment):
            raise ValueError('backend must be an HTTPS origin without credentials, query, or path')
    output = Path(output).resolve()
    # Never remove an existing directory; overwrite only generated public files.
    if output == ROOT or ROOT in output.parents and output.relative_to(ROOT).parts[0] in ['static','examples','tests','scripts','.git']:
        raise ValueError('output must be a separate publication directory')
    output.mkdir(parents=True, exist_ok=True)
    shutil.copytree(ROOT / 'static', output / 'static', dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns('index.html', 'sw.js', 'wenmo-original.png'))
    html = (ROOT / 'static/index.html').read_text()
    html = html.replace('href="/"', f'href="{base_path}"').replace('"/static/', f'"{base_path}static/')
    (output / 'index.html').write_text(html)
    for path in (output / 'static').glob('*.js'):
        text = path.read_text().replace("'/static/", f"'{base_path}static/").replace('"/static/', f'"{base_path}static/')
        text = text.replace("register('/sw.js')", f"register('{base_path}sw.js')")
        path.write_text(text)
    config = {'mode':'pages', 'basePath':base_path, 'apiBase':api_base}
    (output / 'static/site-config.js').write_text('window.WENMO_SITE = ' + json.dumps(config) + ';\n')
    manifest = json.loads((ROOT / 'static/manifest.webmanifest').read_text())
    manifest.update(id=base_path, scope=base_path, start_url=base_path)
    for icon in manifest['icons']:
        icon['src'] = base_path + icon['src'].lstrip('/')
    (output / 'static/manifest.webmanifest').write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    (output / 'examples').mkdir(exist_ok=True)
    for genre in ['narrative','argumentative']:
        (output / 'examples' / f'{genre}.json').write_text(json.dumps(demo(genre), ensure_ascii=False))
    worker = (ROOT / 'static/sw.js').read_text()
    worker = worker.replace("'/'", repr(base_path)).replace("'/static/", f"'{base_path}static/")
    worker = worker.replace("'/api/demo/narrative'", repr(base_path + 'examples/narrative.json'))
    worker = worker.replace("'/api/demo/argumentative'", repr(base_path + 'examples/argumentative.json'))
    worker = worker.replace("'wenmo-public-", "'wenmo-pages-public-")
    (output / 'sw.js').write_text(worker)
    (output / '.nojekyll').touch()
    print(f'Built Pages site at {output}; path={base_path}; backend={"configured" if api_base else "not configured"}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default=str(ROOT / 'docs'))
    parser.add_argument('--base-path', default='/Essay-Marking-System/')
    parser.add_argument('--api-base', default='')
    args = parser.parse_args()
    build(args.output, args.base_path, args.api_base)
