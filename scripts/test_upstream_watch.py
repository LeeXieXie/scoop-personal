import json
import re
import tempfile
import unittest
from pathlib import Path
import upstream_watch as w


class WatchTests(unittest.TestCase):
    def test_mixed_ready_error_and_unknown_regex(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, 'renamed.json').write_text(json.dumps({'version': '1.0.0', 'checkver': {'github': 'https://github.com/a/b'}, 'autoupdate': {'url': 'https://github.com/a/b/releases/download/v$version/a.zip'}}))
            Path(d, 'unknown.json').write_text(json.dumps({'version': '1.0.0', 'checkver': {'script': ['no']}}))
            response = json.dumps({'tag_name': 'v2.0.0', 'assets': [{'name': 'a.zip', 'state': 'uploaded', 'size': 1}]})
            report = w.scan(Path(d), lambda url: response)
            self.assertTrue(report['needs_update'])
            self.assertEqual(report['errors'], 1)
            self.assertEqual([r['status'] for r in report['results']], ['ready', 'error'])
        with self.assertRaises(ValueError):
            w.discover({'checkver': {'url': 'https://example.com', 'regex': '(a)(b)'}}, lambda url: 'ab')

    def test_deepseek_harness_package_id(self):
        manifest_path = Path('bucket/deepseek-harness.json')
        self.assertTrue(manifest_path.is_file(), 'Use the official deepseek-harness manifest filename')
        self.assertFalse(Path('bucket/dshdesktop.json').exists(), 'Do not retain a second active desktop package')
        manifest = json.loads(manifest_path.read_text())
        self.assertEqual(manifest['shortcuts'], [['DeepSeek Harness.exe', 'DeepSeek Harness']])
        self.assertIn('/dshdesktop-', manifest['architecture']['64bit']['url'])
        self.assertIn('/dshdesktop-$version-', manifest['autoupdate']['architecture']['64bit']['url'])

    def test_renamed_community_repositories(self):
        for name, repository, digest in [
            ('deepseek-harness', 'LeeXieXie/deepseek-harness', '9a6fa842d68cffb5558d314fd142a31f54627f0d48baed8974b42f5e008f1003'),
            ('zcode', 'LeeXieXie/ZCode', '441d65585aaad2ec72fdc3841a2af405ef0eed63d79470650466ece06045fb19'),
        ]:
            manifest = json.loads(Path('bucket', name + '.json').read_text())
            base = 'https://github.com/' + repository
            self.assertEqual(manifest['homepage'], base)
            self.assertTrue(manifest['checkver']['url'].startswith(base + '/releases/latest'))
            self.assertEqual(manifest['architecture']['64bit']['hash'], digest)
            self.assertTrue(manifest['architecture']['64bit']['url'].startswith(base + '/releases/download/'))
            self.assertTrue(manifest['autoupdate']['architecture']['64bit']['url'].startswith(base + '/releases/download/'))
        zcode = json.loads(Path('bucket/zcode.json').read_text())
        self.assertEqual(zcode['checkver'], json.loads(Path('scripts/zcode-checkver.json').read_text()))
        changed = json.loads(json.dumps(zcode))
        changed['checkver']['script'].append('unreviewed change')
        with self.assertRaisesRegex(ValueError, 'adapter review required'):
            w.discover(changed, lambda url: self.fail('Unreviewed scripts must fail before fetching'))

    def test_versions(self):
        for old, new in [('1.9.0', '1.10.0'), ('1.0.0-beta.2', '1.0.0-beta.10'), ('1.0.0-rc.1', '1.0.0'), ('3.16.2.20261020062305-upstream.abc', '3.16.2.20261021062305-upstream.def')]:
            self.assertGreater(w.compare(new, old), 0)
            self.assertLess(w.compare(old, new), 0)
        self.assertEqual(w.compare('1.0.0', '1.0.0'), 0)

    def test_unknown_and_isolation(self):
        with tempfile.TemporaryDirectory() as d:
            for name in ['a', 'b']:
                Path(d, name + '.json').write_text(json.dumps({'version': '1', 'checkver': {'script': ['unknown']}}))
            report = w.scan(Path(d), lambda url: '')
            self.assertEqual(len(report['results']), 2)
            self.assertEqual(report['errors'], 2)

    def test_assets(self):
        release = {'assets': [{'name': 'a', 'state': 'uploaded', 'size': 1}]}
        self.assertTrue(w.assets_ready(release, {'a'}))
        self.assertFalse(w.assets_ready(release, {'a', 'b'}))
        release['assets'][0]['size'] = 0
        self.assertFalse(w.assets_ready(release, {'a'}))

    def test_stable_and_rollback(self):
        manifest = {'version': '2.0.0', 'checkver': {'github': 'https://github.com/a/b'}, 'autoupdate': {'url': 'https://github.com/a/b/releases/download/v$version/a.zip'}}
        result = w.check('x', manifest, lambda url: json.dumps({'tag_name': 'v1.0.0', 'assets': []}))
        self.assertEqual(result['status'], 'upstream_older')

    def test_atom_first_including_prerelease(self):
        m = json.loads(Path('bucket/jcode-desktop.json').read_text())
        version, fields, release = w.discover(m, lambda url: '<feed><id>https://github.com/1jehuang/jcode-desktop/releases/tag/desktop-v0.7.0-beta.1</id></feed>')
        self.assertEqual(version, '0.7.0-beta.1')

    def test_deepseek_harness_community_versions(self):
        m = json.loads(Path('bucket/deepseek-harness.json').read_text())
        rule = m['checkver']
        # Scoop's default GitHub regex accepts digits/dots only. The manifest
        # must override it to retain the RC suffix and community build number.
        pattern = rule.get('regex', r'/releases/tag/(?:v|V)?([\d.]+)')
        for version in ['0.2.1-rc.3.20261024.1', '0.2.1-rc.3.20261024.2', '0.2.1.20261025.1']:
            page = '<a href="/LeeXieXie/deepseek-harness/releases/tag/v' + version + '">Release</a>'
            match = re.search(pattern, page)
            self.assertIsNotNone(match)
            self.assertEqual(match[1], version)
            found, fields, release = w.discover(m, lambda url: page)
            self.assertEqual(found, version)
        self.assertGreater(w.compare('0.2.1-rc.3.20261024.2', m['version']), 0)

    def test_full_bucket_and_npm_readiness(self):
        manifests = {p.stem: json.loads(p.read_text()) for p in Path('bucket').glob('*.json')}
        responses = {}
        for name, m in manifests.items():
            version = m['version']
            rule = m['checkver']
            fields = {}
            if 'github' in rule:
                endpoint = 'https://api.github.com/repos/' + rule['github'].split('github.com/')[1] + '/releases/latest'
                tag = 'v' + version
            elif name == 'deepseek-harness':
                responses[rule['url']] = '<a href="/LeeXieXie/deepseek-harness/releases/tag/v' + version + '">Release</a>'
                endpoint = 'https://api.github.com/repos/LeeXieXie/deepseek-harness/releases/tags/v' + version
                tag = 'v' + version
            elif name == 'jcode-desktop':
                responses[rule['url']] = '<id>https://github.com/1jehuang/jcode-desktop/releases/tag/desktop-v' + version + '</id>'
                endpoint = 'https://api.github.com/repos/1jehuang/jcode-desktop/releases/tags/desktop-v' + version
                tag = 'desktop-v' + version
            elif name == 'zcode':
                fields = {'matchAppversion': '3.16.2', 'matchCommit': '3c5b22764937'}
                tag = 'v3.16.2-upstream.3c5b22764937'
                endpoint = 'https://api.github.com/repos/LeeXieXie/ZCode/releases/latest'
                responses[rule['url']] = json.dumps({'upstream': {'repository': 'zai-org/ZCode', 'sha': '3c5b22764937' + '0'*28, 'version': '3.16.2', 'date': '2026-10-20T06:23:05Z'}})
            else:
                responses[rule['url']] = json.dumps({'version': version})
                for arch in m['autoupdate']['architecture'].values():
                    url = arch['hash']['url'].replace('$version', version)
                    responses[url] = json.dumps({'version': version, 'dist': {'integrity': 'sha512-YQ==', 'tarball': arch['url'].replace('$version', version)}})
                continue
            names = {url.rsplit('/', 1)[1] for url in w.required_urls(m, version, fields)}
            if name == 'zcode':
                names.add('build-provenance.json')
            if 'magpie' in name:
                names |= {'magpie-windows-amd64.exe', 'magpie-windows-arm64.exe', 'magpie-cli-windows-amd64.exe', 'magpie-cli-windows-arm64.exe', 'SHA256SUMS'}
            responses[endpoint] = json.dumps({'tag_name': tag, 'assets': [{'name': n, 'state': 'uploaded', 'size': 1} for n in names]})
        report = w.scan(Path('bucket'), responses.__getitem__)
        self.assertEqual(len(report['results']), len(manifests))
        self.assertEqual(report['errors'], 0, report)
        self.assertTrue(all(r['status'] == 'current' for r in report['results']), report)
        responses['https://registry.npmjs.org/@opencode/cli-windows-arm64/' + manifests['opencode2']['version']] = '{}'
        report = w.scan(Path('bucket'), responses.__getitem__)
        self.assertEqual(next(r for r in report['results'] if r['package'] == 'opencode2')['status'], 'not_ready')

    def test_dispatch_gates_and_error_isolation(self):
        calls = []
        def run(*args):
            calls.append(args)
            return '[]'
        self.assertEqual(w.dispatch({'needs_update': False, 'errors': 1}, 'master', run), 'not_needed')
        self.assertFalse(calls)
        self.assertEqual(w.dispatch({'needs_update': True, 'errors': 1}, 'master', run), 'dispatched')
        self.assertEqual(calls[-1], ('workflow', 'run', 'excavator.yml', '--ref', 'master'))
        calls.clear()
        def queued(*args):
            calls.append(args)
            return '[{"status":"queued"}]'
        self.assertEqual(w.dispatch({'needs_update': True}, 'master', queued), 'already_running')
        self.assertEqual(len(calls), 1)

    def test_invalid_provenance(self):
        m = json.loads(Path('bucket/zcode.json').read_text())
        with self.assertRaises(ValueError):
            w.discover(m, lambda url: json.dumps({'upstream': {'repository': 'evil', 'sha': 'a'*40, 'version': '1.0.0', 'date': '2026-01-01T00:00:00Z'}}))


if __name__ == '__main__':
    unittest.main()
