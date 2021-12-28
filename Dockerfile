#### Builder
FROM wakemeops/debian:bullseye-slim as builder

ENV PIP_DEFAULT_TIMEOUT=100 \
    POETRY_VIRTUALENVS_IN_PROJECT=true

WORKDIR /wakemebot

RUN install_packages poetry=1.*

COPY poetry.lock pyproject.toml README.md ./
RUN poetry install --no-dev --no-interaction --no-ansi --no-root

COPY src src
RUN poetry install --no-dev --no-interaction --no-ansi


#### CI Executor
FROM wakemeops/debian:bullseye-slim as executor

RUN install_packages \
    github-cli \
    python3 \
    dpkg-dev \
    jq \
    curl \
    git \
    openssh-client \
    expect \
    unzip \
    debhelper \
    gnupg

ENV PATH="/wakemebot/.venv/bin:$PATH"

COPY --from=builder /wakemebot /wakemebot

RUN groupadd --gid 1003 wakemebot && \
    useradd --uid 1003 --gid wakemebot --create-home wakemebot

USER 1003
