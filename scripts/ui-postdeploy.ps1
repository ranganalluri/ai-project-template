#!/usr/bin/env pwsh

# Post-provision hook to update API with UI URL (resolves circular dependency)

param(
    [string]$ServiceName
)


Write-Host "Running post-provision hook to update API with UI URL..." -ForegroundColor Cyan


$UI_URL = azd env get-value UI_URL
$API_NAME = azd env get-value API_NAME
$RESOURCE_GROUP = azd env get-value AZURE_RESOURCE_GROUP

if ([string]::IsNullOrEmpty($UI_URL)) {
    Write-Host "UI_URL not found, skipping API update" -ForegroundColor Yellow
    exit 0
}

Write-Host "Updating API with UI_URL: $UI_URL" -ForegroundColor Green

az containerapp update `
    --name $API_NAME `
    --resource-group $RESOURCE_GROUP `
    --set-env-vars "UI_URL=$UI_URL" `
    --output none

Write-Host "API updated successfully!" -ForegroundColor Green

