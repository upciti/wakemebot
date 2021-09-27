FROM ubuntu:18.04

ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y wget apt-utils gnupg2 gpgv2 bash \
    && rm -rf /var/lib/apt/lists/*

RUN echo "deb http://repo.aptly.info/ squeeze main" >> /etc/apt/sources.list \
    && wget -qO - https://www.aptly.info/pubkey.txt | apt-key add - \
    && apt-get update \
    && apt-get install -y aptly \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 1000 albert
USER 1000
