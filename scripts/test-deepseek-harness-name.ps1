$ErrorActionPreference = 'Stop'
if (Test-Path -LiteralPath (Join-Path $PSScriptRoot '../bucket/dshdesktop.json')) { throw 'Only deepseek-harness.json should be active, not the old dshdesktop package.' }
$manifest = Get-Content -LiteralPath (Join-Path $PSScriptRoot '../bucket/deepseek-harness.json') -Raw | ConvertFrom-Json
# Upstream Windows productName is DeepSeek Harness. Keep the package ID separate
# from the visible product name, and disclose the community origin in notes.
if ($manifest.shortcuts.Count -ne 1 -or $manifest.shortcuts[0][0] -cne 'DeepSeek Harness.exe' -or $manifest.shortcuts[0][1] -cne 'DeepSeek Harness') {
    throw 'DSH must use the official Windows product name DeepSeek Harness and its unchanged executable.'
}
if (($manifest.notes -join ' ') -notmatch 'Unofficial, unsigned community build, not an official DeepSeek distribution') {
    throw 'Matching the official product name must not remove the unofficial-build disclosure.'
}
if ($manifest.bin) { throw 'The desktop package must not replace the dsh CLI command.' }
Write-Output 'PASS: DSH shortcut matches the official DeepSeek Harness product name and retains unofficial-build disclosure.'
