#### Builder
ARG PYTHON_VERSION="3.9"
FROM python:${PYTHON_VERSION}-slim as builder

ENV PIP_DEFAULT_TIMEOUT=100 \
    POETRY_HOME=/opt/poetry \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_VERSION=1.1.8

ENV PATH="$POETRY_HOME/bin:$PATH"

WORKDIR /wakemebot

RUN apt-get update -qq && \
    apt install -qq -yy curl && \
    rm -rf /var/lib/apt/lists/*

RUN curl -ssL https://raw.githubusercontent.com/sdispater/poetry/master/get-poetry.py | python

COPY poetry.lock pyproject.toml README.md ./
RUN poetry install --no-dev --no-interaction --no-ansi --no-root

COPY src src
RUN poetry install --no-dev --no-interaction --no-ansi

#### CI Executor
FROM python:${PYTHON_VERSION}-slim as executor

ENV PATH="/wakemebot/.venv/bin:$PATH"

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
    rm -rf /var/lib/apt/lists/*

COPY --from=builder /wakemebot /wakemebot

RUN groupadd --gid 1003 wakemebot && \
    useradd --uid 1003 --gid wakemebot --create-home wakemebot

USER 1003
