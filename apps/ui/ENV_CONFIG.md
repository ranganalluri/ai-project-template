# UI Environment Variables

This UI app uses runtime environment variable injection to allow configuration without rebuilding the Docker image.

## How it works

1. **Build time**: The app is built with placeholder values from `.env` or `.env.example`
2. **Runtime**: When the container starts, `generate-env-config.sh` creates `/dist/env-config.js` with actual environment variables
3. **App loads**: `index.html` loads `env-config.js` before React starts, making variables available via `window.ENV`

## Configuration

### Local Development

Create a `.env` file:

```bash
VITE_API_URL=http://localhost:8000
VITE_ENVIRONMENT=development
```

Run the dev server:

```bash
pnpm dev
```

### Container/Production

Environment variables are injected at container startup. Set them in:

- **Docker**: `docker run -e VITE_API_URL=https://api.example.com`
- **Azure Container Apps**: Set in Bicep `envVars` parameter (already configured)
- **Kubernetes**: ConfigMap or environment variables

### Adding New Variables

1. Add to `.env.example`:
   ```bash
   VITE_NEW_VAR=default_value
   ```

2. Update `generate-env-config.sh`:
   ```bash
   VITE_NEW_VAR: "${VITE_NEW_VAR:-default_value}"
   ```

3. Update `public/env-config.js` placeholder:
   ```javascript
   window.ENV = {
     VITE_NEW_VAR: 'default_value'
   }
   ```

4. Use in your app:
   ```typescript
   const newVar = window.ENV?.VITE_NEW_VAR || import.meta.env.VITE_NEW_VAR
   ```

## Available Variables

- `VITE_API_URL`: Backend API URL
- `VITE_ENVIRONMENT`: Environment name (development, staging, production)
