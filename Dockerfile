FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DEFAULT_TIMEOUT=180 \
    PIP_RETRIES=15 \
    PIP_PROGRESS_BAR=off \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# Arabic-capable fonts so the PDF can render and shape Arabic text.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        fonts-hosny-amiri \
        fonts-noto-core \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
# The pip cache mount lets a retried build resume downloads on slow connections.
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

COPY app.py ./
COPY w2pdf ./w2pdf
COPY .streamlit ./.streamlit
COPY sample_data ./sample_data
COPY static ./static

RUN mkdir -p /app/output /app/files \
    && useradd --create-home --uid 10001 app \
    && chown -R app:app /app
USER app

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=4).status == 200 else 1)"

# Keep the label last so a version bump only rebuilds this metadata layer.
ARG APP_VERSION=1.11.0
LABEL org.opencontainers.image.title="W2PDF" \
      org.opencontainers.image.description="WhatsApp images and texts to PDF with Arabic to French translation" \
      org.opencontainers.image.version="${APP_VERSION}" \
      org.opencontainers.image.source="https://github.com/kouljihate/w2pdf"

CMD ["streamlit", "run", "app.py", \
     "--server.address=0.0.0.0", \
     "--server.port=8501", \
     "--server.fileWatcherType=none"]
