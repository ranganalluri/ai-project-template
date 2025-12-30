#!/usr/bin/env pwsh

# Pre-deploy hook to override deployment behavior

param(
    [string]$ServiceName
)

Write-Host "Running pre-deploy hook for service: $ServiceName" -ForegroundColor Cyan

# Add custom deployment logic here
# This runs before azd deploys each service

# Example: Skip deployment for specific services
# if ($ServiceName -eq "api") {
#     Write-Host "Skipping API deployment" -ForegroundColor Yellow
#     exit 0
# }

Write-Host "Pre-deploy hook completed" -ForegroundColor Green

