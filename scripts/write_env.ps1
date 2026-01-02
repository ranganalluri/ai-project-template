# Define the .env file path
$envDir = "apps\api"
$envFilePath = Join-Path $envDir ".env"

# Ensure the directory exists
if (-not (Test-Path $envDir)) {
    New-Item -ItemType Directory -Path $envDir -Force | Out-Null
    Write-Host "Created directory: $envDir" -ForegroundColor Yellow
}

# Clear the contents of the .env file
Set-Content -Path $envFilePath -Value ""

# Get values from azd environment variables
$azureCosmosDbEndpoint = 'https://localhost:8081/'
$azureCosmosDbKey = 'C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+4QDU5DE2nQ9nDuVTqobD4b8mGGyPMbIZnqyMsEcaGQy67XIw/Jw=='
$azureCosmosDbDatabaseName = azd env get-value AZURE_COSMOSDB_DATABASE_NAME 2>$null
$aiFoundryEndpoint = azd env get-value AI_FOUNDRY_ENDPOINT 2>$null
$aiFoundryProjectName = azd env get-value AI_FOUNDRY_PROJECT_NAME 2>$null
$aiFoundryGpt4Deployment = azd env get-value AI_FOUNDRY_GPT4_DEPLOYMENT 2>$null
$foundryConnectionString = azd env get-value FOUNDRY_CONNECTION_STRING 2>$null
$managedIdentityClientId = azd env get-value MANAGED_IDENTITY_CLIENT_ID 2>$null
$azureStorageAccountName = 'devstoreaccount1'
$azureStorageAccountKey = 'Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw=='
$uiUrl = 'https://localhost:5173/'

# Format Foundry endpoint if both endpoint and project name are available
$foundryEndpoint = $null
if ($aiFoundryEndpoint -and $aiFoundryProjectName) {
    $foundryEndpoint = "${aiFoundryEndpoint}api/projects/${aiFoundryProjectName}"
}

# Append values to the .env file (only if they have values)
if ($azureCosmosDbEndpoint) {
    Add-Content -Path $envFilePath -Value "AZURE_COSMOSDB_ENDPOINT=$azureCosmosDbEndpoint"
}

if ($azureCosmosDbKey) {
    Add-Content -Path $envFilePath -Value "AZURE_COSMOSDB_KEY=$azureCosmosDbKey"
}

if ($azureCosmosDbDatabaseName) {
    Add-Content -Path $envFilePath -Value "DATABASE_NAME=$azureCosmosDbDatabaseName"
}

if ($foundryEndpoint) {
    Add-Content -Path $envFilePath -Value "FOUNDRY_ENDPOINT=$foundryEndpoint"
}

if ($foundryConnectionString) {
    Add-Content -Path $envFilePath -Value "FOUNDRY_PROJECT_CONNECTION_STRING=$foundryConnectionString"
}

if ($aiFoundryGpt4Deployment) {
    Add-Content -Path $envFilePath -Value "FOUNDRY_DEPLOYMENT_NAME=$aiFoundryGpt4Deployment"
}

if ($azureStorageAccountName) {
    Add-Content -Path $envFilePath -Value "AZURE_STORAGE_ACCOUNT_NAME=$azureStorageAccountName"
}

if ($azureStorageAccountKey) {
    Add-Content -Path $envFilePath -Value "AZURE_STORAGE_ACCOUNT_KEY=$azureStorageAccountKey"
}

if ($uiUrl) {
    Add-Content -Path $envFilePath -Value "UI_URL=$uiUrl"
}

Write-Host ".env file created at $envFilePath" -ForegroundColor Green

