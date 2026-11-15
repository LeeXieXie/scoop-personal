$ErrorActionPreference = 'Stop'
$manifest = Get-Content -LiteralPath (Join-Path $PSScriptRoot '../bucket/jcode-desktop.json') -Raw | ConvertFrom-Json
$expected = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'jcode-desktop-checkver.json') -Raw | ConvertFrom-Json
if (($manifest.checkver | ConvertTo-Json -Depth 20 -Compress) -cne ($expected | ConvertTo-Json -Depth 20 -Compress)) {
    throw 'Jcode Desktop checkver changed; review its Python adapter too.'
}
if ($manifest.checkver.github -ne 'https://api.github.com/repos/1jehuang/jcode-desktop/releases?per_page=100') {
    throw 'Use the published release API through Scoop GitHub mode for authentication.'
}

function New-DesktopRelease([string] $Version, [string] $Published = '2026-11-14T00:00:00Z') {
    [pscustomobject]@{
        tag_name = "desktop-v$Version"
        draft = $false
        prerelease = $Version.Contains('-')
        published_at = $Published
        assets = @("Jcode-$Version-windows-x86_64.zip", "Jcode-$Version-windows-aarch64.zip", 'SHA256SUMS-windows', 'SHA256SUMS-windows-aarch64') | ForEach-Object {
            [pscustomobject]@{ name = $_; state = 'uploaded'; size = 1 }
        }
    }
}

function Assert-Detection($Releases, [string] $Version) {
    $page = ConvertTo-Json -InputObject @($Releases) -Depth 20 -Compress
    $output = @(Invoke-Command ([scriptblock]::Create($manifest.checkver.script -join "`r`n")))
    if ($output.Count -ne 1 -or $output[0] -cne $Version) {
        throw "Expected release '$Version', got '$($output -join ', ')'."
    }
    $match = [regex]::Match($output[0], $manifest.checkver.regex)
    if (!$match.Success -or $match.Groups[1].Value -cne $Version) { throw 'Full release suffix lost.' }
    foreach ($arch in @('64bit', 'arm64')) {
        $target = $manifest.autoupdate.architecture.$arch
        $url = $target.url.Replace('$version', $Version)
        $directory = $target.extract_dir.Replace('$version', $Version)
        $suffix = if ($arch -eq '64bit') { 'x86_64' } else { 'aarch64' }
        $expectedName = "Jcode-$Version-windows-$suffix"
        if ($directory -cne $expectedName -or !$url.EndsWith("/desktop-v$Version/$expectedName.zip")) {
            throw "Release suffix lost in $arch download/extraction mapping."
        }
    }
}

foreach ($version in @('0.6.6-beta.1', '0.6.6-beta.10', '0.6.6-rc.1', '0.6.6')) {
    Assert-Detection @(New-DesktopRelease $version) $version
}
$older = New-DesktopRelease '0.6.6-beta.17'
# An unpublished beta.18 can remain in Atom; it is absent from this API list.
Assert-Detection @($older) '0.6.6-beta.17'
foreach ($missing in 0..3) {
    $newer = New-DesktopRelease '0.6.6-beta.18' '2026-11-15T00:00:00Z'
    $missingName = $newer.assets[$missing].name
    $newer.assets = @($newer.assets | Where-Object { $_.name -cne $missingName })
    Assert-Detection @($newer, $older) '0.6.6-beta.17'
}
foreach ($case in @('draft', 'unpublished', 'wrong-tag', 'empty', 'uploading')) {
    $newer = New-DesktopRelease '0.6.6-beta.18' '2026-11-15T00:00:00Z'
    switch ($case) {
        'draft' { $newer.draft = $true }
        'unpublished' { $newer.published_at = $null }
        'wrong-tag' { $newer.tag_name = 'v9.9.9' }
        'empty' { $newer.assets[0].size = 0 }
        'uploading' { $newer.assets[0].state = 'new' }
    }
    Assert-Detection @($newer, $older) '0.6.6-beta.17'
}
$newer = New-DesktopRelease '0.6.6-beta.18' '2026-11-15T00:00:00Z'
Assert-Detection @($older, $newer) '0.6.6-beta.18'

# A failed API response or no usable release must still surface as an error.
$incomplete = New-DesktopRelease '0.6.6-beta.18'
$incomplete.assets = @($incomplete.assets | Select-Object -Skip 1)
$incompletePage = ConvertTo-Json -InputObject @($incomplete) -Depth 20 -Compress
foreach ($page in @($null, '[]', '{}', '{"message":"API rate limit exceeded"}', 'invalid json', $incompletePage)) {
    $failed = $false
    try { Invoke-Command ([scriptblock]::Create($manifest.checkver.script -join "`r`n")) | Out-Null } catch { $failed = $true }
    if (!$failed) { throw 'Missing or invalid release data must fail explicitly.' }
}
Write-Output 'PASS: Jcode Desktop selects published releases with complete Windows assets, preserves prereleases, and surfaces API failures.'
