# Infrastructure Constitution

**Reference**: See `constitution.md` for core principles  
**Last Updated**: 2026-01-13  
**Version**: 1.0.0  
**Scope**: Infrastructure as Code for AI Project Template (`infra/` Bicep files + `infra/modules/*`)

## Service Definition

This infrastructure provisions Azure resources for the three containerized services (UI, API, Functions) plus shared data and security services.

- **Compute**: Azure Container Apps (UI, API, Functions)
- **Networking**: Container Apps Environment with ingress per app (static FQDNs)
- **Registry**: Azure Container Registry (ACR)
- **Database**: Azure Cosmos DB (NoSQL)
- **Storage**: Azure Storage Account (Blob)
- **Secrets**: Azure Key Vault
- **Observability**: Log Analytics Workspace + Container Apps logs/metrics
- **Identity**: Managed Identity for each container app (for ACR/KV access)

## Directory Structure

```
infra/
├── main.bicep                 # Orchestrates environment + apps + observability
├── main.parameters.json       # Environment parameters
├── api.bicep                  # API container app composition
├── ui.bicep                   # UI container app composition
├── functions.bicep            # Functions container app composition
├── cosmos.parameters.json     # Cosmos DB parameters
├── modules/
│   ├── container-app.bicep    # Reusable container app module
│   ├── container-registry.bicep
│   ├── cosmos-db.bicep
│   ├── storage-account.bicep
│   ├── key-vault.bicep
│   └── ai-services.bicep      # (if used) AI services wiring
└── README.md                  # Infra deployment guide
```

## Core Principles (Non-Negotiable)

1) **Single Orchestrator**: `main.bicep` owns the environment. Service-specific files (`api.bicep`, `ui.bicep`, `functions.bicep`) are composed from `main.bicep` (no drift).
2) **Managed Identity Everywhere**: All container apps pull images from ACR and access Key Vault via system-assigned managed identity—no secrets in parameters.
3) **Static, Predictable Endpoints**: Each container app uses ingress with deterministic FQDNs (`<app>.<region>.azurecontainerapps.io`). Output these URLs.
4) **Parameterization**: All environment-specific values live in `*.parameters.json` (no hardcoded env settings in bicep).
5) **Health & Scaling**: Every app sets liveness/readiness probes and min/max replicas (default 1–3). Dev may set `minReplicas=0` for cost savings.
6) **Observability First**: Log Analytics workspace is mandatory; Container Apps send logs/metrics. Include request IDs in app logs (app responsibility).
7) **Network & Ingress**: Use Container Apps Environment shared ingress; per-app ingress rules defined in each app bicep. Enforce HTTPS.
8) **Secrets Management**: All sensitive values sourced from Key Vault references; never inline secrets. Connection strings are provided via Key Vault + environment variables.
9) **Data Layer Guardrails**: Cosmos DB uses specific containers and partition keys (as defined by app). Storage account is for blobs; access via managed identity.
10) **Consistency & Idempotency**: Modules are reusable; naming is deterministic. `azd up/provision/deploy` must be idempotent.

## Module Usage

- **container-app.bicep**: Reusable definition for a Container App with ingress, identity, probes, env vars, scale.
- **container-registry.bicep**: Creates ACR and outputs login server; apps authenticate via managed identity.
- **cosmos-db.bicep**: Creates DB/account; containers and partition keys defined per parameters file.
- **storage-account.bicep**: Creates storage with blob service; used for uploads/artifacts.
- **key-vault.bicep**: Central secrets store; apps consume secrets via Key Vault references.
- **ai-services.bicep**: (Optional) wiring for AI-related Azure services if needed.

## Container App Standards

- **Ingress**: HTTPS, static FQDN, per-app target port (UI 80, API 8080, Functions 7071 unless overridden).
- **Identity**: `identity.type = 'SystemAssigned'` and ACR pull via `imagePullSecret` or managed identity binding.
- **Probes**: Liveness + readiness required; target app health endpoints (`/health` for API/UI, `/api/health` or configured for Functions).
- **Scaling**: Default `minReplicas=1`, `maxReplicas=3`; optionally `minReplicas=0` for dev.
- **Env Vars**: Use parameters and/or Key Vault references. No secrets in plain text.

## Parameters & Configuration

- Keep environment-specific settings in `*.parameters.json` (e.g., `api.parameters.json`, `ui.parameters.json`, `functions.parameters.json`, `main.parameters.json`).
- Image values follow `${REGISTRY_LOGIN_SERVER}/app:tag` pattern. Tags provided at deploy time by pipeline.
- Probe paths and ports configurable per app parameters.
- Cosmos DB settings (account, database, containers) defined in cosmos parameters; include partition keys.

## Deployment Workflow (AZD)

```bash
azd auth login
azd provision   # creates RG, CAE, Log Analytics, ACR, Key Vault, Cosmos, Storage
azd deploy      # builds images, pushes to ACR, deploys container apps
```

Outputs to capture after deploy:
- UI FQDN, API FQDN, Functions FQDN
- ACR login server
- Cosmos DB endpoint
- Key Vault name
- Storage account name

## Quality & Compliance Checklist

- [ ] No secrets in bicep or parameters; all secrets in Key Vault.
- [ ] Managed identity enabled on every container app; ACR pull via MI.
- [ ] Liveness/readiness probes defined for UI, API, Functions.
- [ ] Ingress HTTPS enabled; FQDN outputs provided.
- [ ] Min/max replicas set per app; dev may use min=0.
- [ ] Log Analytics workspace configured and linked.
- [ ] Parameters files contain all env-specific values (no hardcoding in bicep).
- [ ] Cosmos containers use correct partition keys.
- [ ] Storage account present for uploads/artifacts.
- [ ] Idempotent: `azd provision` and `azd deploy` can be rerun safely.

## Resources

- Infra guide: [infra/README.md](../../infra/README.md)
- Main orchestration: [infra/main.bicep](../../infra/main.bicep)
- Container app module: [infra/modules/container-app.bicep](../../infra/modules/container-app.bicep)
- API app template: [infra/api.bicep](../../infra/api.bicep)
- UI app template: [infra/ui.bicep](../../infra/ui.bicep)
- Functions app template: [infra/functions.bicep](../../infra/functions.bicep)
- Cosmos config: [infra/cosmos.parameters.json](../../infra/cosmos.parameters.json)
- Key Vault module: [infra/modules/key-vault.bicep](../../infra/modules/key-vault.bicep)
- Storage module: [infra/modules/storage-account.bicep](../../infra/modules/storage-account.bicep)
- ACR module: [infra/modules/container-registry.bicep](../../infra/modules/container-registry.bicep)

---

**Version**: 1.0.0  
**Created**: 2026-01-13  
**Parent**: [constitution.md](constitution.md)
