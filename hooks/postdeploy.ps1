#!/usr/bin/env pwsh

# Post-deploy hook to verify or customize after deployment

param(
    [string]$ServiceName
)

Write-Host "Running post-deploy hook for service: $ServiceName" -ForegroundColor Cyan

$RESOURCE_GROUP = azd env get-value AZURE_RESOURCE_GROUP

# Get the directory where this script is located
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "Fetching deployed service details..." -ForegroundColor Green
Start-Sleep -Seconds 50

# Execute the UI post-deploy script
$uiPostdeployPath = Join-Path $scriptDir "ui-postdeploy.ps1"
if (Test-Path $uiPostdeployPath) {
    Write-Host "Running UI post-deploy: $uiPostdeployPath" -ForegroundColor Yellow
    & $uiPostdeployPath
} else {
    Write-Host "Warning: UI post-deploy script not found at $uiPostdeployPath" -ForegroundColor Yellow
}

if ($ServiceName) {
    Write-Host "Service $ServiceName deployed successfully" -ForegroundColor Green
    
    # Add custom post-deployment logic here
    # Example: Update configurations, restart services, run health checks, etc.
}

Write-Host "Post-deploy hook completed" -ForegroundColor Green
