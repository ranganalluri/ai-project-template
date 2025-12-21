# Multi-stage build for FastAPI application
FROM python:3.12-slim as builder

WORKDIR /build

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
COPY apps/ apps/
RUN mkdir -p /build/wheelhouse
RUN uv export --project ./apps/api --format requirements-txt --no-editable --no-hashes --no-emit-workspace >./requirements.txt
RUN uv run pip download -r ./requirements.txt -d /build/wheelhouse/ 
RUN uv build --project ./apps/api --wheel --out-dir /build/wheelhouse/ 
RUN uv build --project ./apps/common-py --wheel --out-dir /build/wheelhouse/ 

# Debug: List wheelhouse contents
RUN echo "Does wheelhouse exist?" && [ -d /build/wheelhouse ] && echo "Yes" || echo "No"

# Runtime stage
FROM python:3.12-slim

WORKDIR /app

RUN groupadd -r appuser && useradd -r -g appuser appuser

RUN mkdir -p /app/wheelhouse

COPY --from=builder /build/wheelhouse/ /app/wheelhouse/
COPY --from=builder /build/requirements.txt /app/requirements.txt
RUN ls -l /app/wheelhouse
# Install deps OFFLINE from wheelhouse only
# RUN pip install --no-index --find-links=/app/wheelhouse -r /app/requirements.txt
RUN pip install --no-index --find-links=/app/wheelhouse /app/wheelhouse/*.whl

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

USER appuser

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
