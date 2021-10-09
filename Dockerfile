ARG PYTHON_VERSION="3.9"
ARG POETRY_VERSION="1.1.8"

#### Python base
FROM python:${PYTHON_VERSION}-slim as python_base

ENV PIP_NO_CACHE_DIR=off \
    POETRY_PATH=/opt/poetry \
    PIP_DEFAULT_TIMEOUT=100 \
    VENV_PATH=/opt/venv \
    POETRY_VERSION=${POETRY_VERSION}

ENV PATH="$POETRY_PATH/bin:$VENV_PATH/bin:$PATH"
WORKDIR /wakemebot
RUN apt-get update -qq && \
    apt install -qq -yy \
      dpkg-dev \
      jq \
      curl \
      git \
      openssh-client \
      expect \
      unzip \
      debhelper \
      gnupg && \
    rm -rf /var/lib/apt/lists/* && \
    ln -s $(which unzip) /bin/unzip # for ops2deb

#### Builder
FROM python_base as builder

RUN curl -ssL https://raw.githubusercontent.com/sdispater/poetry/master/get-poetry.py | python && \
    python -m venv $VENV_PATH && \
    mv /root/.poetry $POETRY_PATH && \
    poetry config virtualenvs.create false

COPY poetry.lock pyproject.toml README.md .
COPY src src
RUN poetry install --no-dev --no-interaction --no-ansi -vvv

#### CI Executor
FROM python_base as executor

COPY --chown=1000:1000 --from=builder /wakemebot /wakemebot
COPY --from=builder $VENV_PATH $VENV_PATH

RUN groupadd --gid 1000 wakemebot \
    && useradd --uid 1000 --gid wakemebot --shell /bin/bash --create-home wakemebot

USER 1000
WORKDIR /
