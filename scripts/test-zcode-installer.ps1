$ErrorActionPreference = 'Stop'
$manifest = Get-Content -LiteralPath (Join-Path $PSScriptRoot '../bucket/zcode.json') -Raw | ConvertFrom-Json
$root = Join-Path ([IO.Path]::GetTempPath()) ('zcode-hook-regression-' + [guid]::NewGuid().ToString('N'))
$payloadDirectory = Join-Path $root '$PLUGINSDIR'
New-Item -ItemType Directory -Path $payloadDirectory -Force | Out-Null
New-Item -ItemType File -Path (Join-Path $payloadDirectory 'app-64.7z') | Out-Null
$script:archivePath = $null
function Expand-7zipArchive {
    param([Parameter(ValueFromPipeline = $true)][string]$Path, [string]$DestinationPath, [switch]$Removal)
    $script:archivePath = $Path
    if (![IO.Path]::IsPathRooted($Path)) { throw "Expected absolute archive path, received: $Path" }; Set-Location $DestinationPath; New-Item -ItemType File -Path (Join-Path $DestinationPath 'ZCode.exe') -Force | Out-Null
}
$dir = $root
Push-Location $payloadDirectory
try {
    & ([scriptblock]::Create(($manifest.installer.script -join "`n")))
} finally {
    Pop-Location
}
$expected = Join-Path $payloadDirectory 'app-64.7z'
if ($script:archivePath -ne $expected) { throw "Expected absolute archive path '$expected', received '$script:archivePath'." }
if (Test-Path -LiteralPath $payloadDirectory) { throw 'Installer remnants were not removed.' }
Write-Output 'ZCode installer passes an absolute payload path even when the current directory is the payload directory.'
