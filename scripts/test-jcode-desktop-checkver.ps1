$ErrorActionPreference = 'Stop'
$manifest = Get-Content -LiteralPath (Join-Path $PSScriptRoot '../bucket/jcode-desktop.json') -Raw | ConvertFrom-Json
$cases = @(
    @{ Version = '0.6.6-beta.1'; Previous = '0.6.5' },
    @{ Version = '0.6.6-beta.10'; Previous = '0.6.6-beta.2' },
    @{ Version = '0.6.6-rc.1'; Previous = '0.6.6-beta.10' },
    @{ Version = '0.6.6'; Previous = '0.6.6-rc.1' }
)
foreach ($case in $cases) {
    $feed = @"
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>https://github.com/1jehuang/jcode-desktop/releases/tag/desktop-v$($case.Version)</id>
    <content>Older notes mention /releases/tag/desktop-v9.9.9</content>
  </entry>
  <entry><id>https://github.com/1jehuang/jcode-desktop/releases/tag/desktop-v$($case.Previous)</id></entry>
</feed>
"@
    $match = [regex]::Match($feed, $manifest.checkver.regex)
    if (!$match.Success -or $match.Groups[1].Value -ne $case.Version) {
        throw "Expected full release version '$($case.Version)', got '$($match.Groups[1].Value)'."
    }
    foreach ($arch in @('64bit', 'arm64')) {
        $target = $manifest.autoupdate.architecture.$arch
        $url = $target.url.Replace('$version', $match.Groups[1].Value)
        $directory = $target.extract_dir.Replace('$version', $match.Groups[1].Value)
        $suffix = if ($arch -eq '64bit') { 'x86_64' } else { 'aarch64' }
        $expectedName = "Jcode-$($case.Version)-windows-$suffix"
        if ($directory -ne $expectedName -or !$url.EndsWith("/desktop-v$($case.Version)/$expectedName.zip")) {
            throw "Release suffix lost in $arch download/extraction mapping."
        }
    }
}
if ([regex]::IsMatch('<content>/releases/tag/desktop-v9.9.9</content>', $manifest.checkver.regex)) {
    throw 'Historical links in release notes must not select a version.'
}
Write-Output 'PASS: Jcode Desktop release detection preserves beta/RC versions, accepts stable releases, and ignores release-note links.'
