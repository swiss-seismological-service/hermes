# Creates a RT-RAMSIS core production image
#
# To run the ramsis GUI, make sure there is a display available to the
# when the app is launched. Since this is platform specific, it's best to
# inject the DISPLAY env var from the command line when starting the container
# (and mount the X11 server socket when on a linux host).
#
# Copyright (C) 2018, ETH Zürich, Swiss Seismological Service
#
ARG PYTHON_VERSION=3.6-slim


# Build image
FROM python:${PYTHON_VERSION} as builder

RUN apt-get update && apt-get install -y \
    build-essential \
    libxml2-dev libxslt1-dev zlib1g-dev \
    git

WORKDIR /wheels

COPY requirements-ci.txt ./requirements.txt
RUN pip install -U pip \
    && pip wheel -r ./requirements.txt



# Runtime image
FROM python:${PYTHON_VERSION}
ENV PYTHONUNBUFFERED=1

COPY --from=builder /wheels /wheels
# Since all packages are now available as wheels we need to turn vcs specifiers
# into requirements specifiers. Otherwise pip will try to download them again.
RUN sed -i 's/.*#egg=\([\w\.]*\)/\1/g' /wheels/requirements.txt \
    && pip install -U pip \
    && pip install -r /wheels/requirements.txt -f /wheels \
    && rm -rf /wheels \
    && rm -rf /root/.cache/pip/*
