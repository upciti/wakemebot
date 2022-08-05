FROM bitnami/minideb:bullseye AS slim

ENV LC_ALL=C.UTF-8 \
    LANG=C.UTF-8

ARG WAKEMEBOT_PATH="dist/wakemebot"
COPY ${WAKEMEBOT_PATH} /usr/local/bin/wakemebot

USER 1001


