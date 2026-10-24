"""Read-only by default. Interpret the bucket's supported Scoop detection rules.
Unsupported rules fail explicitly rather than guessing or executing PowerShell.
"""
import argparse
import datetime as dt
import functools
import json
import os
from pathlib import Path
import re
import subprocess
import urllib.request


def gh(*args):
    return subprocess.check_output(['gh', *args], text=True, encoding='utf-8', timeout=45)


@functools.lru_cache(maxsize=None)
def fetch(url):
    if url.startswith('https://api.github.com/'):
        return gh('api', url.removeprefix('https://api.github.com/'))
    with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'scoop-upstream-watch'}), timeout=30) as response:
        return response.read().decode('utf-8')


def compare(a, b):
    def parts(value):
        match = re.fullmatch(r'(\d+(?:\.\d+)*)(?:-([0-9A-Za-z.-]+))?(?:\+[0-9A-Za-z.-]+)?', value)
        if not match:
            raise ValueError('Unsupported version: ' + value)
        core = tuple(map(int, match[1].split('.')))
        pre = tuple((0, int(x)) if x.isdigit() else (1, x) for x in (match[2] or '').split('.'))
        return core, match[2] is None, pre
    x, y = parts(a), parts(b)
    return (x > y) - (x < y)


def discover(m, get):
    rule = m['checkver']
    if not isinstance(rule, dict):
        raise ValueError('Unsupported checkver type')
    if set(rule) == {'github'}:
        repo = rule['github'].removeprefix('https://github.com/')
        if not re.fullmatch(r'[\w.-]+/[\w.-]+', repo):
            raise ValueError('Invalid GitHub repository')
        release = json.loads(get('https://api.github.com/repos/' + repo + '/releases/latest'))
        if release.get('draft') or release.get('prerelease'):
            raise ValueError('Latest stable endpoint returned non-stable release')
        return release['tag_name'].removeprefix('v'), {}, release
    if set(rule) == {'url', 'jsonpath'} and rule['jsonpath'] == '$.version':
        return json.loads(get(rule['url']))['version'], {}, None
    if set(rule) == {'url', 'regex'}:
        match = re.search(rule['regex'], get(rule['url']))
        if not match or match.lastindex != 1:
            raise ValueError('checkver regex must produce one version capture')
        return match[1], {}, None
    # This adapter deliberately recognizes only the reviewed provenance rule.
    if set(rule) == {'url', 'script', 'regex'} and rule['url'] == 'https://github.com/LeeXieXie/ZCode/releases/latest/download/build-provenance.json':
        expected = json.loads((Path(__file__).parent / 'zcode-checkver.json').read_text(encoding='utf-8-sig'))
        if rule != expected:
            raise ValueError('ZCode checkver changed, adapter review required')
        release = json.loads(get('https://api.github.com/repos/LeeXieXie/ZCode/releases/latest'))
        upstream = json.loads(get(rule['url']))['upstream']
        if upstream['repository'] != 'zai-org/ZCode' or not re.fullmatch('[a-f0-9]{40}', upstream['sha']) or not re.fullmatch(r'\d+\.\d+\.\d+', upstream['version']):
            raise ValueError('Invalid ZCode release provenance')
        date = dt.datetime.fromisoformat(upstream['date'].replace('Z', '+00:00'))
        if date.tzinfo is None:
            raise ValueError('Provenance date requires timezone')
        fields = {'matchAppversion': upstream['version'], 'matchCommit': upstream['sha'][:12]}
        if release['tag_name'] != 'v' + fields['matchAppversion'] + '-upstream.' + fields['matchCommit']:
            raise ValueError('Provenance does not match latest release tag')
        version = upstream['version'] + '.' + date.astimezone(dt.timezone.utc).strftime('%Y%m%d%H%M%S') + '-upstream.' + fields['matchCommit']
        return version, fields, release
    raise ValueError('Unsupported checkver rule: ' + repr(rule))


def expand(template, fields):
    for key, value in sorted(fields.items(), key=lambda pair: -len(pair[0])):
        template = template.replace('$' + key, value)
    if '$' in template:
        raise ValueError('Unsupported autoupdate variable: ' + template)
    return template.split('#', 1)[0]


def required_urls(m, version, fields):
    auto = m['autoupdate']
    urls = set()
    for arch in auto.get('architecture', {'all': auto}).values():
        values = dict(fields, version=version)
        url = expand(arch['url'], values)
        urls.add(url)
        values['baseurl'] = url.rsplit('/', 1)[0]
        hash_rule = arch.get('hash', auto.get('hash', {}))
        if isinstance(hash_rule, dict) and 'url' in hash_rule:
            urls.add(expand(hash_rule['url'], values))
    return urls


def assets_ready(release, names):
    ready = {a['name'] for a in release.get('assets', []) if a.get('state') == 'uploaded' and a.get('size', 0) > 0}
    return names <= ready


def check(name, m, get):
    version, fields, release = discover(m, get)
    result = {'package': name, 'current': m['version'], 'upstream': version, 'status': 'current', 'detail': ''}
    order = compare(version, m['version'])
    if order < 0:
        result['status'] = 'upstream_older'
        return result
    urls = required_urls(m, version, fields)
    groups = {}
    npm_tarballs = {
        expand(arch['hash']['url'], dict(fields, version=version)): expand(arch['url'], dict(fields, version=version))
        for arch in m['autoupdate'].get('architecture', {}).values()
        if isinstance(arch.get('hash'), dict) and arch['hash'].get('url', '').startswith('https://registry.npmjs.org/')
    }
    for url in urls:
        match = re.fullmatch(r'https://github.com/([^/]+/[^/]+)/releases/download/([^/]+)/([^/]+)', url)
        if match:
            repo, tag, asset = match.groups()
            groups.setdefault((repo, tag), set()).add(asset)
        elif url.startswith('https://registry.npmjs.org/'):
            if url.endswith('.tgz'):
                continue
            metadata = json.loads(get(url))
            if metadata.get('version') != version or not metadata.get('dist', {}).get('integrity', '').startswith('sha512-') or metadata.get('dist', {}).get('tarball') != npm_tarballs.get(url):
                result.update(status='not_ready', detail='npm architecture metadata incomplete: ' + url)
                return result
        else:
            raise ValueError('Unsupported asset URL: ' + url)
    for (repo, tag), names in groups.items():
        candidate = release
        if candidate is None or candidate.get('tag_name') != tag:
            from urllib.parse import quote
            candidate = json.loads(get('https://api.github.com/repos/' + repo + '/releases/tags/' + quote(tag, safe='')))
        if repo == 'yetone/magpie-releases':
            names |= {'magpie-windows-amd64.exe', 'magpie-windows-arm64.exe', 'magpie-cli-windows-amd64.exe', 'magpie-cli-windows-arm64.exe', 'SHA256SUMS'}
        if repo == 'LeeXieXie/ZCode':
            names.add('build-provenance.json')
        if candidate.get('draft') or not assets_ready(candidate, names):
            result.update(status='not_ready', detail='Required uploaded nonempty assets: ' + ', '.join(sorted(names)))
            return result
    result['status'] = 'ready' if order > 0 else 'current'
    return result


def scan(bucket, get=fetch):
    results = []
    for path in sorted(bucket.glob('*.json')):
        manifest = {}
        try:
            manifest = json.loads(path.read_text(encoding='utf-8-sig'))
            results.append(check(path.stem, manifest, get))
        except Exception as error:
            results.append({'package': path.stem, 'current': manifest.get('version'), 'upstream': None, 'status': 'error', 'detail': str(error)})
    if not results:
        raise ValueError('No bucket manifests found')
    return {'results': results, 'needs_update': any(r['status'] == 'ready' for r in results), 'errors': sum(r['status'] == 'error' for r in results)}


def dispatch(report, branch, run=gh):
    if not report['needs_update']:
        return 'not_needed'
    runs = json.loads(run('run', 'list', '--workflow', 'excavator.yml', '--branch', branch, '--limit', '100', '--json', 'status'))
    if any(r['status'] != 'completed' for r in runs):
        return 'already_running'
    run('workflow', 'run', 'excavator.yml', '--ref', branch)
    return 'dispatched'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bucket', type=Path, default=Path('bucket'))
    parser.add_argument('--output', type=Path)
    parser.add_argument('--dispatch', action='store_true')
    parser.add_argument('--branch', default=os.environ.get('DEFAULT_BRANCH', 'master'))
    args = parser.parse_args()
    report = scan(args.bucket)
    if args.dispatch:
        try:
            report['dispatch'] = dispatch(report, args.branch)
        except Exception as error:
            report['dispatch'] = str(error)
            report['errors'] += 1
    text = json.dumps(report, indent=2)
    print(text)
    if args.output:
        args.output.write_text(text + '\n', encoding='utf-8')
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as summary:
            summary.write('## Upstream Watch\n\n| Package | Current | Upstream | Status | Detail |\n|---|---|---|---|---|\n')
            for row in report['results']:
                summary.write('| ' + ' | '.join(str(row[k]).replace('|', '\\|').replace('\n', ' ') for k in ['package', 'current', 'upstream', 'status', 'detail']) + ' |\n')
            summary.write('\nDispatch: ' + report.get('dispatch', 'read-only') + '\n')
    return int(report['errors'] > 0)


if __name__ == '__main__':
    raise SystemExit(main())
