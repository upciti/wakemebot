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
    rsync \
    curl \
    ca-certificates \
    python3 \
    make \
    git

ENV PATH="/wakemebot/.venv/bin:$PATH"

COPY --from=builder /wakemebot /wakemebot

USER 1001
