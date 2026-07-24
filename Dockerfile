# syntax=docker/dockerfile:1

FROM python:3.11-slim-bookworm

ARG APP_UID=10001
ARG APP_GID=10001

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/home/rag/.cache/huggingface

RUN apt-get update \
    && apt-get install --no-install-recommends --yes libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid "${APP_GID}" rag \
    && useradd --uid "${APP_UID}" --gid rag --create-home --shell /usr/sbin/nologin rag

WORKDIR /app

COPY requirements.txt ./
RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements.txt

COPY --chown=rag:rag app ./app
COPY --chown=rag:rag ui ./ui
COPY --chown=rag:rag .streamlit ./.streamlit
COPY --chown=rag:rag pyproject.toml README.md ./

RUN mkdir -p data/uploads data/chroma data/repositories "${HF_HOME}" \
    && chown -R rag:rag data /home/rag/.cache

USER rag

EXPOSE 8000 8501

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]
