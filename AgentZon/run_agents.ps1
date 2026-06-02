param(
    [string]$HostAddress = "127.0.0.1",
    [switch]$OpenBrowser
)

$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $RootDir
$PythonCandidates = @(
    (Join-Path $RootDir ".venv\Scripts\python.exe"),
    (Join-Path $RepoRoot ".venv\Scripts\python.exe")
)

$PythonExe = $null
foreach ($candidate in $PythonCandidates) {
    if (Test-Path $candidate) {
        $PythonExe = $candidate
        break
    }
}

if (-not $PythonExe) {
    Write-Host "ERROR: No s'ha trobat cap entorn virtual (.venv)." -ForegroundColor Red
    Write-Host "Crea'l i instal·la dependències abans d'executar aquest script."
    exit 1
}

function Start-AgentWindow {
    param(
        [Parameter(Mandatory = $true)][string]$Title,
        [Parameter(Mandatory = $true)][string]$Module,
        [Parameter(Mandatory = $true)][string[]]$Arguments
    )

    $escapedArgs = ($Arguments | ForEach-Object { '"{0}"' -f ($_ -replace '"', '""') }) -join " "
    $command = "`$Host.UI.RawUI.WindowTitle = '$Title'; Set-Location '$RootDir'; & '$PythonExe' -m $Module $escapedArgs"

    Start-Process -FilePath "powershell.exe" -WorkingDirectory $RootDir -ArgumentList @(
        "-NoExit",
        "-ExecutionPolicy", "Bypass",
        "-Command", $command
    ) | Out-Null
}

$agents = @(
    @{ Title = "Agent Directory"; Module = "agents.agent_directory"; Args = @("--host", $HostAddress, "--port", "9000") },
    @{ Title = "Agent Proveidor de Pagament"; Module = "agents.agent_proveidor_de_pagament"; Args = @("--host", $HostAddress, "--port", "9006", "--directory-host", $HostAddress, "--directory-port", "9000") },
    @{ Title = "Agent Cobrador"; Module = "agents.agent_cobrador"; Args = @("--host", $HostAddress, "--port", "9005", "--directory-host", $HostAddress, "--directory-port", "9000", "--data-dir", "data") },
    @{ Title = "Agent Opinador"; Module = "agents.agent_opinador"; Args = @("--host", $HostAddress, "--port", "9004", "--directory-host", $HostAddress, "--directory-port", "9000", "--data-dir", "data") },
    @{ Title = "Transportista Fast"; Module = "agents.agent_transportista"; Args = @("--host", $HostAddress, "--port", "9010", "--transport-id", "fast", "--price-per-kg", "8.0", "--delivery-days", "1") },
    @{ Title = "Transportista Economy"; Module = "agents.agent_transportista"; Args = @("--host", $HostAddress, "--port", "9011", "--transport-id", "economy", "--price-per-kg", "4.0", "--delivery-days", "3") },
    @{ Title = "Centre Logistic BCN"; Module = "agents.agent_centre_logistic"; Args = @("--host", $HostAddress, "--port", "9003", "--centre-id", "CL-BCN", "--centre-city", "Barcelona", "--directory-host", $HostAddress, "--directory-port", "9000", "--transport-fast-host", $HostAddress, "--transport-fast-port", "9010", "--transport-economy-host", $HostAddress, "--transport-economy-port", "9011", "--data-dir", "data") },
    @{ Title = "Centre Logistic GI"; Module = "agents.agent_centre_logistic"; Args = @("--host", $HostAddress, "--port", "9007", "--centre-id", "CL-GI", "--centre-city", "Girona", "--directory-host", $HostAddress, "--directory-port", "9000", "--transport-fast-host", $HostAddress, "--transport-fast-port", "9010", "--transport-economy-host", $HostAddress, "--transport-economy-port", "9011", "--data-dir", "data") },
    @{ Title = "Centre Logistic TGN"; Module = "agents.agent_centre_logistic"; Args = @("--host", $HostAddress, "--port", "9008", "--centre-id", "CL-TGN", "--centre-city", "Tarragona", "--directory-host", $HostAddress, "--directory-port", "9000", "--transport-fast-host", $HostAddress, "--transport-fast-port", "9010", "--transport-economy-host", $HostAddress, "--transport-economy-port", "9011", "--data-dir", "data") },
    @{ Title = "Agent Compra"; Module = "agents.agent_compra"; Args = @("--host", $HostAddress, "--port", "9002", "--directory-host", $HostAddress, "--directory-port", "9000", "--data-dir", "data") },
    @{ Title = "Agent Cercador"; Module = "agents.agent_cercador"; Args = @("--host", $HostAddress, "--port", "9001", "--directory-host", $HostAddress, "--directory-port", "9000", "--data-dir", "data") }
)

Write-Host "Iniciant tots els agents AgentZon en finestres separades..."
Write-Host "Directori de treball: $RootDir"
Write-Host "Python: $PythonExe"

foreach ($agent in $agents) {
    Start-AgentWindow -Title $agent.Title -Module $agent.Module -Arguments $agent.Args
    Start-Sleep -Milliseconds 450
}

$uiUrl = "http://$HostAddress:9001/iface"
Write-Host "Agents iniciats. Interfície: $uiUrl"

if ($OpenBrowser.IsPresent) {
    Start-Process $uiUrl | Out-Null
}
