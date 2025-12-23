#!/usr/bin/env pwsh

# Post-deploy hook to verify or customize after deployment

param(
    [string]$ServiceName
)

Write-Host "Running post-deploy hook for service: $ServiceName" -ForegroundColor Cyan

$RESOURCE_GROUP = azd env get-value AZURE_RESOURCE_GROUP


Write-Host "Fetching deployed service details..." -ForegroundColor Green
# Start-Sleep -Seconds 50
pwsh -NoProfile -ExecutionPolicy Bypass -File "$PSScriptRoot/ui-postdeploy.ps1"

if ($ServiceName) {
    Write-Host "Service $ServiceName deployed successfully" -ForegroundColor Green
    
    # Add custom post-deployment logic here
    # Example: Update configurations, restart services, run health checks, etc.
}

Write-Host "Post-deploy hook completed" -ForegroundColor Green
