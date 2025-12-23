# Multi-stage build for FastAPI application
FROM python:3.12-slim as builder

WORKDIR /build

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
COPY apps/ apps/
RUN mkdir -p /build/wheelhouse
RUN uv export --project ./apps/functions --format requirements-txt --no-editable --no-hashes --no-emit-workspace >./requirements.txt
RUN uv run pip download -r ./requirements.txt -d /build/wheelhouse/ 
RUN uv build --project ./apps/common-py --wheel --out-dir /build/wheelhouse/ 
# RUN uv build --project ./apps/functions --wheel --out-dir /build/wheelhouse/

# Debug: List wheelhouse contents
RUN echo "Does wheelhouse exist?" && [ -d /build/wheelhouse ] && echo "Yes" || echo "No"

# Runtime stage

FROM mcr.microsoft.com/azure-functions/python:4-python3.12

ENV AzureWebJobsScriptRoot=/home/site/wwwroot \
    AzureFunctionsJobHost__Logging__Console__IsEnabled=true

USER root
RUN mkdir -p /app/wheelhouse
COPY --from=builder /build/wheelhouse/ /app/wheelhouse/
COPY --from=builder /build/requirements.txt /app/requirements.txt

# Install deps OFFLINE from wheelhouse only
# RUN pip install --no-index --find-links=/app/wheelhouse -r /app/requirements.txt
RUN pip install --no-index --find-links=/app/wheelhouse /app/wheelhouse/*.whl
USER 1000
COPY ./apps/functions /home/site/wwwroot
