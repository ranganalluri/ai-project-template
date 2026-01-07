# Define the directories where .env files should be created
$envDirs = @("apps\api", "apps\common-py")

# Get values from azd environment variables
$azureCosmosDbEndpoint = 'https://localhost:8081/'
$azureCosmosDbKey = 'C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+4QDU5DE2nQ9nDuVTqobD4b8mGGyPMbIZnqyMsEcaGQy67XIw/Jw=='
$azureCosmosDbDatabaseName = azd env get-value AZURE_COSMOSDB_DATABASE_NAME 2>$null
$aiFoundryEndpoint = azd env get-value AI_FOUNDRY_ENDPOINT 2>$null
$aiFoundryProjectName = azd env get-value AI_FOUNDRY_PROJECT_NAME 2>$null
$aiFoundryGpt4Deployment = azd env get-value AI_FOUNDRY_GPT4_DEPLOYMENT 2>$null
$foundryConnectionString = azd env get-value FOUNDRY_CONNECTION_STRING 2>$null
$managedIdentityClientId = azd env get-value MANAGED_IDENTITY_CLIENT_ID 2>$null
$cuEndpoint = azd env get-value CU_ENDPOINT 2>$null

# CU_KEY is marked as @secure() in Bicep, so azd may not expose it via env get-value
# Try to get it from azd first, then fall back to Key Vault if available
$ErrorActionPreference = 'SilentlyContinue'
$cuKeyOutput = azd env get-value CU_KEY 2>&1
$ErrorActionPreference = 'Continue'

# Check if the output is an error message or actual value
$cuKey = $null
if ($cuKeyOutput -and -not ($cuKeyOutput -match "ERROR|not found")) {
    $cuKey = $cuKeyOutput.Trim()
}

Write-Host "CU_KEY from azd: $(if ($cuKey) { 'Found' } else { 'Not found or secure' })" -ForegroundColor $(if ($cuKey) { 'Green' } else { 'Yellow' })

if ([string]::IsNullOrWhiteSpace($cuKey)) {
    # Try to get from Key Vault as fallback (for local development)
    $keyVaultName = azd env get-value KEY_VAULT_NAME 2>$null
    if ($keyVaultName -and -not [string]::IsNullOrWhiteSpace($keyVaultName)) {
        Write-Host "Attempting to retrieve CU_KEY from Key Vault: $keyVaultName" -ForegroundColor Cyan
        try {
            $cuKey = az keyvault secret show --vault-name $keyVaultName --name CuKey --query value -o tsv 2>$null
            if ($LASTEXITCODE -eq 0 -and -not [string]::IsNullOrWhiteSpace($cuKey)) {
                Write-Host "Successfully retrieved CU_KEY from Key Vault" -ForegroundColor Green
            } else {
                Write-Host "CU_KEY not found in Key Vault (secret name: CuKey)" -ForegroundColor Yellow
                $cuKey = $null
            }
        } catch {
            Write-Host "Failed to retrieve CU_KEY from Key Vault: $_" -ForegroundColor Yellow
            $cuKey = $null
        }
    } else {
        Write-Host "KEY_VAULT_NAME not found, skipping Key Vault lookup for CU_KEY" -ForegroundColor Yellow
    }
} else {
    Write-Host "CU_KEY retrieved from azd environment" -ForegroundColor Green
}
$azureStorageAccountName = 'devstoreaccount1'
$azureStorageAccountKey = 'Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw=='
$uiUrl = 'https://localhost:5173/'

# Format Foundry endpoint if both endpoint and project name are available
$foundryEndpoint = $null
if ($aiFoundryEndpoint -and $aiFoundryProjectName) {
    $foundryEndpoint = "${aiFoundryEndpoint}api/projects/${aiFoundryProjectName}"
}

# Build the .env file content
$envContent = @()

if ($azureCosmosDbEndpoint) {
    $envContent += "AZURE_COSMOSDB_ENDPOINT=$azureCosmosDbEndpoint"
}

if ($azureCosmosDbKey) {
    $envContent += "AZURE_COSMOSDB_KEY=$azureCosmosDbKey"
}

if ($azureCosmosDbDatabaseName) {
    $envContent += "DATABASE_NAME=$azureCosmosDbDatabaseName"
}

if ($foundryEndpoint) {
    $envContent += "FOUNDRY_ENDPOINT=$foundryEndpoint"
}

if ($foundryConnectionString) {
    $envContent += "FOUNDRY_PROJECT_CONNECTION_STRING=$foundryConnectionString"
}

if ($aiFoundryGpt4Deployment) {
    $envContent += "FOUNDRY_DEPLOYMENT_NAME=$aiFoundryGpt4Deployment"
}

if ($azureStorageAccountName) {
    $envContent += "AZURE_STORAGE_ACCOUNT_NAME=$azureStorageAccountName"
}

if ($azureStorageAccountKey) {
    $envContent += "AZURE_STORAGE_ACCOUNT_KEY=$azureStorageAccountKey"
}

if ($uiUrl) {
    $envContent += "UI_URL=$uiUrl"
}

if ($cuEndpoint) {
    $envContent += "CU_ENDPOINT=$cuEndpoint"
}

if ($cuKey) {
    $envContent += "CU_KEY=$cuKey"
}

# Write .env file to each directory
foreach ($envDir in $envDirs) {
    # Ensure the directory exists
    if (-not (Test-Path $envDir)) {
        New-Item -ItemType Directory -Path $envDir -Force | Out-Null
        Write-Host "Created directory: $envDir" -ForegroundColor Yellow
    }

    $envFilePath = Join-Path $envDir ".env"
    
    # Write the content to the .env file
    Set-Content -Path $envFilePath -Value $envContent
    
    Write-Host ".env file created at $envFilePath" -ForegroundColor Green
}

