FROM python:3.10-slim-bullseye AS app

LABEL maintainer="Nicolas Schmid <nicolas.schmid@sed.ethz.ch>"

WORKDIR /web

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl libpq-dev git\
    && rm -rf /var/lib/apt/lists/* /usr/share/doc /usr/share/man \
    && apt-get clean \
    && useradd --create-home python \
    && chown python:python -R /web

USER python

COPY --chown=python:python . .

COPY --chown=python:python requirements-web.txt ./
RUN pip3 install --no-cache-dir --user -r requirements-web.txt

ENV PYTHONUNBUFFERED="true" \
    PYTHONPATH="." \
    PATH="${PATH}:/home/python/.local/bin" \
    USER="python"

EXPOSE 8000

CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "-c", "python:hermes.config.gunicorn", "web.main:app"]
