# Creates a RT-RAMSIS core production image
#
# To run the ramsis GUI, make sure there is a display available to the
# when the app is launched. Since this is platform specific, it's best to
# inject the DISPLAY env var from the command line when starting the container
# (and mount the X11 server socket when on a linux host).
#
# Also, since the docker container doesn't have access to the users ssh agent,
# we need to incect gitlab credentials via GITLAB_USER and GITLAB_PASSWORD
# ARGs so that we can access private repositories. We use a multi-stage build
# so that access credentials aren't carried over to the final image.
#
# Copyright (C) 2018, ETH Zürich, Swiss Seismological Service

ARG PYTHON_VERSION=3.6-slim


# 1. CREATE BUILD IMAGE
# Contains all dependencies as wheels

FROM python:${PYTHON_VERSION} as builder

RUN apt-get update && apt-get install -y \
    build-essential \
    libxml2-dev libxslt1-dev zlib1g-dev \
    git

WORKDIR /wheels

COPY requirements.txt ./requirements.txt

# Inject gitlab username and password into requirements.txt where private
# repositories are cloned from our gitlab server. Also, remove any -e installs.
ARG GITLAB_USER
ARG GITLAB_PW
RUN SEARCH='//\(gitlab\.seismo\.ethz\.ch\)' \
    && sed -i "s|$SEARCH|//$GITLAB_USER:$GITLAB_PW@\1|g" ./requirements.txt \
    && sed -i 's|^-e ||g' ./requirements.txt

RUN pip install -U pip \
    && pip wheel -r ./requirements.txt


# 2. CREATE BASE IMAGE
# Installs the dependencies but not the app itself. Having this intermediate
# stage can be useful as a development image

FROM python:${PYTHON_VERSION} as base
ENV PYTHONUNBUFFERED=1

COPY --from=builder /wheels /wheels

# Add missing runtime dependencies that don't come packed with their
# respective packages for some reason.
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libgl1-mesa-glx \
    libxml2-dev libxslt1-dev zlib1g-dev \
    libfontconfig libxrender1 libxkbcommon-x11-0 libdbus-1-3

# We don't have a gpu in the container so we software-render openGL
ENV LIBGL_ALWAYS_SOFTWARE=1

# Since all packages are now available as wheels we need to turn vcs specifiers
# into requirements specifiers. Otherwise pip will try to download them again.
RUN sed -i 's/.*#egg=\([\w\.]*\)/\1/g' /wheels/requirements.txt \
    && pip install -U pip \
    && pip install -r /wheels/requirements.txt -f /wheels \
    && rm -rf /wheels \
    && rm -rf /root/.cache/pip/*


# 3. CREATE PRODUCTION IMAGE
# Final image with the application installed

FROM base

COPY . /build

RUN pip install --no-index /build \
    && rm -rf /build

RUN apt-get install -y x11-apps

