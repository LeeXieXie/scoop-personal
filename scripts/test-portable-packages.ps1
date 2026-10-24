param([ValidateSet('smartsearch', 'jcode', 'jcode-desktop', 'deepseek-harness')][string[]]$App = @('smartsearch', 'jcode', 'jcode-desktop', 'deepseek-harness'))

$ErrorActionPreference = 'Stop'
if (!$env:SCOOP_HOME) { $env:SCOOP_HOME = Convert-Path (scoop prefix scoop) }
. "$env:SCOOP_HOME\lib\core.ps1"
. "$env:SCOOP_HOME\lib\decompress.ps1"

$sevenZip = Get-Command '7z.exe' -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
if (!$sevenZip -and (Test-Path -LiteralPath "$env:ProgramFiles\7-Zip\7z.exe")) {
    $env:PATH = "$env:ProgramFiles\7-Zip;$env:PATH"
    $sevenZip = Get-Command '7z.exe' -CommandType Application -ErrorAction Stop | Select-Object -First 1
}
if (!$sevenZip) { throw 'Package smoke tests require an external 7z.exe.' }
# The runner checks out Scoop but does not install its helper packages. Set only
# this script's in-memory config; never modify the user's persisted Scoop config.
$scoopConfig = [pscustomobject]@{ use_external_7zip = $true }

$sandbox = Join-Path ([IO.Path]::GetTempPath()) ('scoop-package-smoke-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $sandbox | Out-Null

function Get-PeMachine([string]$Path) {
    $stream = [IO.File]::OpenRead($Path)
    $reader = New-Object IO.BinaryReader($stream)
    try {
        if ($reader.ReadUInt16() -ne 0x5A4D) { throw "Not a Windows executable: $Path" }
        $stream.Position = 0x3C
        $offset = $reader.ReadUInt32()
        $stream.Position = $offset
        if ($reader.ReadUInt32() -ne 0x4550) { throw "Invalid PE header: $Path" }
        return $reader.ReadUInt16()
    } finally { $reader.Dispose(); $stream.Dispose() }
}

foreach ($name in $App) {
    $manifest = Get-Content -LiteralPath (Join-Path $PSScriptRoot "../bucket/$name.json") -Raw | ConvertFrom-Json
    foreach ($arch in @($manifest.architecture.PSObject.Properties.Name)) {
        $platform = $manifest.architecture.$arch
        $directory = Join-Path $sandbox "$name-$arch"
        New-Item -ItemType Directory -Path $directory | Out-Null
        $archive = Join-Path $sandbox ([Uri]$platform.url).Segments[-1]
        Invoke-WebRequest -Uri $platform.url -OutFile $archive -UseBasicParsing
        if ((Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLower() -ne $platform.hash) {
            throw "Downloaded $name/$arch hash does not match the manifest."
        }
        $hashConfig = $manifest.autoupdate.hash
        if ($manifest.autoupdate.architecture.$arch.hash) { $hashConfig = $manifest.autoupdate.architecture.$arch.hash }
        $checksumsUrl = $hashConfig.url.Replace('$baseurl', $platform.url.Substring(0, $platform.url.LastIndexOf('/')))
        $checksums = (Invoke-WebRequest -Uri $checksumsUrl -UseBasicParsing).Content
        if ($checksums -is [byte[]]) { $checksums = [Text.Encoding]::UTF8.GetString($checksums) }
        $filename = [Uri]::UnescapeDataString(([Uri]$platform.url).Segments[-1])
        $checksumLine = '(?m)^' + [regex]::Escape($platform.hash) + '\s+\*?' + [regex]::Escape($filename) + '\s*$'
        if ($checksums -notmatch $checksumLine) { throw "Published checksum missing or mismatched for $filename" }

        $options = @{ Path = $archive; DestinationPath = $directory }
        $extractDir = $manifest.extract_dir
        if ($platform.extract_dir) { $extractDir = $platform.extract_dir }
        if ($extractDir) { $options.ExtractDir = $extractDir }
        Expand-7zipArchive @options
        $exe = switch ($name) {
            'smartsearch' { 'SmartSearch.Desktop.exe' }
            'deepseek-harness' { 'DeepSeek Harness.exe' }
            'jcode-desktop' { 'jcode-desktop.exe' }
            default { $platform.bin[0][0] }
        }
        $executable = Join-Path $directory $exe
        if (!(Test-Path -LiteralPath $executable -PathType Leaf)) { throw "Missing executable after Scoop extraction: $executable" }
        $expectedMachine = if ($arch -eq '64bit') { 0x8664 } else { 0xAA64 }
        if ((Get-PeMachine $executable) -ne $expectedMachine) { throw "Wrong executable architecture: $name/$arch" }

        if ($name -eq 'smartsearch') {
            foreach ($file in @('Assets\smart-search.ico', 'coreclr.dll', 'SmartSearch.Desktop.dll', 'SmartSearch.Desktop.runtimeconfig.json')) {
                if (!(Test-Path -LiteralPath (Join-Path $directory $file) -PathType Leaf)) { throw "Incomplete desktop runtime: $file" }
            }
        } elseif ($name -eq 'jcode-desktop') {
            foreach ($file in @('jcode.exe', 'jcode-harness-api-bridge.exe', 'Jcode.png', 'jcode-desktop.exe.manifest')) {
                if (!(Test-Path -LiteralPath (Join-Path $directory $file) -PathType Leaf)) { throw "Incomplete desktop bundle: $file" }
            }
            foreach ($file in @('jcode.exe', 'jcode-harness-api-bridge.exe')) {
                if ((Get-PeMachine (Join-Path $directory $file)) -ne $expectedMachine) { throw "Wrong backend architecture: $file" }
            }
            $dir = $directory
            & ([scriptblock]::Create(($manifest.pre_install -join "`n")))
            $icon = New-Object Drawing.Icon (Join-Path $directory 'Jcode.ico')
            try { if ($icon.Width -ne 256 -or $icon.Height -ne 256) { throw 'Invalid desktop shortcut icon dimensions.' } }
            finally { $icon.Dispose() }
        } elseif ($name -eq 'deepseek-harness') {
            foreach ($file in @('resources/app.asar', 'resources/runtime/versions.json', 'resources/runtime/primary-runtime/runtime.json', 'resources/runtime/primary-runtime/dependencies/node/bin/node.exe', 'resources/runtime/primary-runtime/dependencies/python/python.exe', 'resources/runtime/primary-runtime/dependencies/pnpm/bin/pnpm.cjs', 'resources/runtime/cli/command-manager.js', 'build-source.json', 'LICENSE', 'THIRD_PARTY_NOTICES')) {
                if (!(Test-Path -LiteralPath (Join-Path $directory $file) -PathType Leaf)) { throw "Incomplete DSH Desktop bundle: $file" }
            }
            $record = Get-Content -LiteralPath (Join-Path $directory 'build-source.json') -Raw | ConvertFrom-Json
            if ($record.version -ne $manifest.version -or $record.platform -ne 'windows' -or $record.architecture -ne 'x64' -or $record.unsigned -cne $true -or $record.automaticUpdates -cne $false -or $record.mandatoryUpdatePolicy -cne $false) { throw 'Unexpected DSH build source/update metadata.' }
            if (Test-Path -LiteralPath (Join-Path $directory 'resources/app-update.yml')) { throw 'Community package must not use an official updater feed.' }
            foreach ($file in @('resources/runtime/primary-runtime/dependencies/node/bin/node.exe', 'resources/runtime/primary-runtime/dependencies/python/python.exe')) {
                if ((Get-PeMachine (Join-Path $directory $file)) -ne $expectedMachine) { throw "Wrong DSH bundled runtime architecture: $file" }
            }
            $runtime = Get-Content -LiteralPath (Join-Path $directory 'resources/runtime/primary-runtime/runtime.json') -Raw | ConvertFrom-Json
            if ($runtime.desktopVersion -ne $record.productVersion -or $runtime.platform -ne 'win32' -or $runtime.arch -ne 'x64') { throw 'Unexpected DSH bundled runtime metadata.' }
        } elseif ($arch -eq '64bit') {
            $oldHome = $env:JCODE_HOME
            $oldUpdate = $env:JCODE_NO_AUTO_UPDATE
            try {
                $env:JCODE_HOME = Join-Path $sandbox 'jcode-home'
                $env:JCODE_NO_AUTO_UPDATE = '1'
                $versionOutput = (& $executable --version | Out-String).Trim()
                if ($LASTEXITCODE -ne 0 -or $versionOutput -notmatch [regex]::Escape($manifest.version)) {
                    throw "jcode --version failed: $versionOutput"
                }
                Write-Output $versionOutput
            } finally { $env:JCODE_HOME = $oldHome; $env:JCODE_NO_AUTO_UPDATE = $oldUpdate }
        }
        Write-Output "PASS: $name/$arch download, published checksum, Scoop extraction, executable architecture, and required files."
    }
}
