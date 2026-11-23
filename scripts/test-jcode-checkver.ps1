$ErrorActionPreference = 'Stop'
$json = Get-Content -LiteralPath (Join-Path $PSScriptRoot '../bucket/jcode.json') -Raw | ConvertFrom-Json
$json.version = '1.0.3'
$script = [scriptblock]::Create($json.checkver.script -join "`r`n")

function New-JcodeRelease([string] $Version) {
    [pscustomobject]@{
        tag_name = "v$Version"
        draft = $false
        prerelease = $false
        published_at = '2026-11-23T00:00:00Z'
        assets = @('jcode-windows-x86_64.tar.gz', 'jcode-windows-aarch64.tar.gz', 'SHA256SUMS') | ForEach-Object {
            [pscustomobject]@{ name = $_; state = 'uploaded'; size = 1 }
        }
    }
}

function Assert-Detection($Releases, [string] $Expected) {
    $page = ConvertTo-Json -InputObject @($Releases) -Depth 20 -Compress
    $output = @(Invoke-Command $script)
    if ($output.Count -ne 1 -or $output[0] -cne $Expected -or $output[0] -cnotmatch $json.checkver.regex) {
        throw "Expected release '$Expected', got '$($output -join ', ')'."
    }
}

$current = New-JcodeRelease '1.0.3'
$older = New-JcodeRelease '1.0.0'
$linuxOnly = New-JcodeRelease '1.1.2'
$linuxOnly.assets = @([pscustomobject]@{ name = 'jcode-linux-x86_64.tar.gz'; state = 'uploaded'; size = 1 }, $linuxOnly.assets[2])
Assert-Detection @($linuxOnly, $current, $older) '1.0.3'
Assert-Detection @($linuxOnly, $older) '1.0.3'
Assert-Detection @() '1.0.3'
Assert-Detection @($linuxOnly, (New-JcodeRelease '1.9.0'), (New-JcodeRelease '1.10.0')) '1.10.0'

foreach ($case in @('missing-x64', 'missing-arm64', 'missing-checksums', 'empty', 'uploading', 'draft', 'unpublished', 'prerelease', 'prerelease-tag')) {
    $newer = New-JcodeRelease '1.2.0'
    switch ($case) {
        'missing-x64' { $newer.assets = $newer.assets[1, 2] }
        'missing-arm64' { $newer.assets = $newer.assets[0, 2] }
        'missing-checksums' { $newer.assets = $newer.assets[0, 1] }
        'empty' { $newer.assets[0].size = 0 }
        'uploading' { $newer.assets[0].state = 'new' }
        'draft' { $newer.draft = $true }
        'unpublished' { $newer.published_at = $null }
        'prerelease' { $newer.prerelease = $true }
        'prerelease-tag' { $newer.tag_name = 'v1.2.0-rc.1' }
    }
    Assert-Detection @($newer, $current) '1.0.3'
}

foreach ($page in @($null, '{}', '{"message":"API rate limit exceeded"}', '[invalid json')) {
    $failed = $false
    try { Invoke-Command $script | Out-Null } catch { $failed = $true }
    if (!$failed) { throw 'Invalid release data must fail explicitly.' }
}
Write-Output 'PASS: Jcode selects only complete Windows stable releases and does not downgrade.'
