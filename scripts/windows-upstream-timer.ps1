[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [switch]$Install,
    [switch]$Uninstall,
    [string]$GhPath,
    [string]$StateDirectory = (Join-Path $env:LOCALAPPDATA 'ScoopPersonalUpstreamWatch')
)

$ErrorActionPreference = 'Stop'
$taskName = 'ScoopPersonalUpstreamWatch'
$repository = 'LeeXieXie/scoop-personal'
if ($Install -and $Uninstall) { throw 'Choose only one of Install and Uninstall.' }
if ($Uninstall) {
    $existing = Get-ScheduledTask -TaskName $taskName -ErrorAction Stop
    if ($existing.Description -ne 'Scoop Personal independent upstream trigger (current user, every 30 minutes).') {
        throw 'Refusing to unregister a task not owned by this installer.'
    }
    if ($PSCmdlet.ShouldProcess($taskName, 'Unregister scheduled task')) {
        Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    }
    return
}
if (!$GhPath) { $GhPath = (Get-Command gh -CommandType Application -ErrorAction Stop).Source }
if (!(Test-Path -LiteralPath $GhPath -PathType Leaf)) { throw 'GitHub CLI executable not found.' }
$GhPath = (Resolve-Path -LiteralPath $GhPath).Path
if ($Install) {
    $existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    $scriptPath = $PSCommandPath
    if ($existing -and $existing.Description -ne 'Scoop Personal independent upstream trigger (current user, every 30 minutes).') {
        throw 'Refusing to replace a task not owned by this installer.'
    }
    $powershell = Join-Path $PSHOME 'powershell.exe'
    $arguments = '-NoProfile -NonInteractive -WindowStyle Hidden -File "{0}" -GhPath "{1}" -StateDirectory "{2}"' -f $scriptPath, $GhPath, $StateDirectory
    $action = New-ScheduledTaskAction -Execute $powershell -Argument $arguments
    $trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 30)
    $principal = New-ScheduledTaskPrincipal -UserId ([Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive -RunLevel Limited
    $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RunOnlyIfNetworkAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 5)
    if ($PSCmdlet.ShouldProcess($taskName, 'Register current-user task, every 30 minutes while logged in')) {
        Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description 'Scoop Personal independent upstream trigger (current user, every 30 minutes).' -Force | Out-Null
        Get-ScheduledTaskInfo -TaskName $taskName | Select-Object TaskName, NextRunTime, LastRunTime, LastTaskResult
    }
    return
}

# Reuse this user's gh keyring login, not an unrelated inherited process token.
$previousGhToken = $env:GH_TOKEN
$previousGithubToken = $env:GITHUB_TOKEN
$previousGhRepo = $env:GH_REPO
try {
    $env:GH_TOKEN = $null
    $env:GITHUB_TOKEN = $null
    $env:GH_REPO = $null
    New-Item -ItemType Directory -Path $StateDirectory -Force | Out-Null
    $logPath = Join-Path $StateDirectory 'trigger.log'
    if ((Test-Path -LiteralPath $logPath) -and (Get-Item -LiteralPath $logPath).Length -gt 1048576) {
        Move-Item -LiteralPath $logPath -Destination (Join-Path $StateDirectory 'trigger.previous.log') -Force
    }
    function Write-TriggerLog([string]$Message) {
        $line = '{0} {1}' -f [DateTime]::UtcNow.ToString('o'), $Message
        Add-Content -LiteralPath $logPath -Value $line -Encoding UTF8
        Write-Output $line
    }
    $runsJson = & $GhPath run list --repo $repository --workflow upstream-watch.yml --branch master --limit 100 --json status 2>$null
    if ($LASTEXITCODE -ne 0) { throw 'Cannot list upstream watcher runs. Check network and gh keyring login.' }
    $runs = @($runsJson -join "`n" | ConvertFrom-Json)
    if (@($runs | Where-Object { $_.status -ne 'completed' }).Count -gt 0) {
        Write-TriggerLog 'SKIP: an upstream watcher run is already unfinished.'
        return
    }
    if ($PSCmdlet.ShouldProcess("$repository upstream-watch.yml master", 'Dispatch full-bucket upstream check')) {
        $null = & $GhPath workflow run upstream-watch.yml --repo $repository --ref master 2>$null
        if ($LASTEXITCODE -ne 0) { throw 'Workflow dispatch failed. Check network, repository access and gh keyring login.' }
        Write-TriggerLog 'SUCCESS: dispatched full-bucket upstream check on master.'
    }
} catch {
    if (Get-Command Write-TriggerLog -ErrorAction SilentlyContinue) { Write-TriggerLog ('ERROR: ' + $_.Exception.Message) }
    throw
} finally {
    $env:GH_TOKEN = $previousGhToken
    $env:GITHUB_TOKEN = $previousGithubToken
    $env:GH_REPO = $previousGhRepo
}
