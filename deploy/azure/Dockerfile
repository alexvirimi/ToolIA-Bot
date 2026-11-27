FROM python:3.14-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/opt/playwright

WORKDIR /app

COPY deploy/azure/requirements.txt /tmp/toolia-requirements.txt
RUN apt-get update && apt-get install -y --no-install-recommends libatomic1 \
    && python -m pip install --no-cache-dir -r /tmp/toolia-requirements.txt \
    && python -m playwright install --with-deps --only-shell chromium \
    && rm -rf /var/lib/apt/lists/* /tmp/toolia-requirements.txt \
    && groupadd --gid 10001 toolia \
    && useradd --uid 10001 --gid toolia --create-home toolia

COPY scripts/download_data_azure.py scripts/
COPY data/sources.txt data/

USER toolia
CMD ["python", "scripts/download_data_azure.py"]
