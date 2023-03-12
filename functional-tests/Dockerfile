# syntax=docker/dockerfile:1.3-labs

FROM wakemeops/minideb:bullseye

RUN install_packages wget apt-utils gnupg2 gpgv2 bash aptly

RUN useradd --create-home --uid 1000 albert

USER 1000

RUN aptly repo create -component="devops" wakemeops-devops \
  && aptly repo create -component="terminal" wakemeops-terminal \
  && aptly publish repo -skip-signing -architectures="amd64,armhf,i386", -distribution="stable" -component="devops,terminal" wakemeops-devops wakemeops-terminal

HEALTHCHECK --interval=1m --timeout=30s --retries=3 CMD gpg --list-secret-keys || kill 1

CMD ["aptly","api", "serve", "-listen=:8080", "-no-lock"]
