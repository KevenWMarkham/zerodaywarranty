# Multi-stage image for the three Zero Day Warranty Container Apps.
# deploy.yml builds one target per service:
#   docker build --target orchestrator  -t .../zdw/orchestrator:<tag> .
#   docker build --target mcp-warranty   -t .../zdw/mcp-warranty:<tag> .
#   docker build --target mcp-ledger     -t .../zdw/mcp-ledger:<tag> .

FROM python:3.11-slim AS base
WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8080
# Install the package (runtime deps: pydantic + pyyaml).
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .
EXPOSE 8080
# Non-root runtime.
RUN useradd --create-home --uid 10001 appuser
USER appuser
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD ["python", "-c", "import os,urllib.request;urllib.request.urlopen(f\"http://localhost:{os.getenv('PORT','8080')}/health\").read()"]
CMD ["python", "-m", "zero_day_warranty.server"]

FROM base AS orchestrator
ENV ZDW_ROLE=orchestrator

FROM base AS mcp-warranty
ENV ZDW_ROLE=mcp-warranty

FROM base AS mcp-ledger
ENV ZDW_ROLE=mcp-ledger
