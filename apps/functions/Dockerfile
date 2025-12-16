# Multi-stage build for Azure Functions
FROM python:3.12-slim as builder

WORKDIR /build

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
COPY apps/functions apps/functions
COPY apps/common apps/common

RUN uv sync --frozen --no-install-project

# Runtime stage
FROM mcr.microsoft.com/azure-functions/python:4-python3.12

ENV AzureWebJobsScriptRoot=/home/site/wwwroot \
    AzureFunctionsVersion=4 \
    PYTHONPATH=/home/site/wwwroot

WORKDIR /home/site/wwwroot

COPY --from=builder /build/.venv /home/site/wwwroot/.venv
COPY apps/functions /home/site/wwwroot

ENV PATH="/home/site/wwwroot/.venv/bin:$PATH"

USER appuser

CMD ["func", "start"]
