FROM wakemeops/minideb:bullseye

RUN install_packages wget apt-utils gnupg2 gpgv2 bash aptly

RUN useradd --create-home --uid 1000 albert

USER 1000

HEALTHCHECK --interval=1m --timeout=30s --retries=3 CMD gpg --list-secret-keys || kill 1

CMD ["aptly","api", "serve", "-listen=:8080", "-no-lock"]
