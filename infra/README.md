# Azure Infrastructure Setup Guide

## Overview

This infrastructure deploys a multi-container application using Azure Container Apps with three services:
- **UI**: React frontend (port 80)
- **API**: FastAPI backend (port 8080)
- **Functions**: Azure Functions as container (port 7071)

All services have **static, auto-assigned FQDNs** and are deployed in a shared Container Apps Environment.

## Key Features

### 1. **Static URLs**
- Each container app gets a unique, deterministic FQDN
- Format: `<app-name>.<region>.azurecontainerapps.io`

### 2. **Managed Identity**
- All containers authenticate to ACR using Managed Identity
- Secure by default, no credentials in env vars

### 3. **Service Communication**
- UI receives API URL via `VITE_API_URL` environment variable
- Functions receive API URL via `API_URL` environment variable

### 4. **Health Probes & Auto-scaling**
- Liveness and readiness probes configured per service
- Auto-scales from 1-3 replicas based on load

### 5. **Monitoring**
- Log Analytics workspace captures all logs
- Container App metrics available in Azure Portal

## Deployment with AZD

### Step 1: Prerequisites

```bash
# Install Azure Developer CLI
# https://learn.microsoft.com/azure/developer/azure-developer-cli/

azd auth login
```

### Step 2: Deploy Infrastructure

```bash
cd ai_project_template
azd provision
```

This creates:
- Resource group
- Container Apps Environment
- Log Analytics workspace
- Managed Identity
- Container Registry reference

### Step 3: Deploy Applications

```bash
azd deploy
```

This:
- Builds Docker images
- Pushes to ACR
- Deploys container apps with static FQDNs
- Outputs all service URLs

## File Structure

- **main.bicep** - Orchestrates CAE, container apps, and monitoring
- **modules/container-app.bicep** - Reusable container app module
- **modules/container-registry.bicep** - ACR setup
- **parameters/dev.parameters.json** - Environment-specific config

## Configuration

### Environment Variables

Edit `main.bicep` to add environment variables to services:

```bicep
envVars: [
  { name: 'LOG_LEVEL', value: 'debug' }
]
```

### Scaling

Modify `container-app.bicep` scale section:

```bicep
scale: {
  minReplicas: 1
  maxReplicas: 3
}
```

### Image Tags

In `parameters/dev.parameters.json`, update image values:

```json
"apiImage": { "value": "${REGISTRY_LOGIN_SERVER}/api:v1.2.3" }
```

## Troubleshooting

```bash
# View container logs
az containerapp logs show -n contoso-api-dev01 -g <rg>

# List all container apps
az containerapp list -g <rg>

# Check ingress config
az containerapp ingress show -n contoso-api-dev01 -g <rg>
```

## Costs & Optimization

- Default: 1 minimum replica per app (~$36/month each)
- Development: Set minReplicas to 0 for cost savings
- Production: Increase maxReplicas to 5-10 for high availability
