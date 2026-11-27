FROM python:3.14-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY deploy/bot/requirements.txt /tmp/toolia-requirements.txt
RUN python -m pip install --no-cache-dir -r /tmp/toolia-requirements.txt \
    && rm /tmp/toolia-requirements.txt \
    && useradd --create-home --user-group --uid 10001 toolia \
    && install -d -o toolia -g toolia /var/lib/toolia

COPY src/ src/

USER toolia
CMD ["python", "src/rag/rag.py"]
