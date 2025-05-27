FROM python:3.12-slim-bookworm AS builder

LABEL maintainer="Nicolas Schmid <nicolas.schmid@sed.ethz.ch>"

WORKDIR /web

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl libpq-dev git\
    && rm -rf /var/lib/apt/lists/* /usr/share/doc /usr/share/man \
    && apt-get clean

COPY . .

RUN pip wheel --no-cache-dir --no-deps --wheel-dir /web/wheels -r requirements-web.txt

FROM python:3.12-slim-bookworm

WORKDIR /web


RUN useradd --create-home python \
    && chown python:python -R /web

USER python

COPY --from=builder --chown=python:python /web/wheels /wheels

RUN pip install --no-cache --user /wheels/*

ENV PYTHONUNBUFFERED="true" \
    PYTHONPATH="." \
    PATH="${PATH}:/home/python/.local/bin" \
    USER="python"

COPY --chown=python:python /web /web

EXPOSE 8000

CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "-c", "python:hermes.config.gunicorn", "web.main:app"]