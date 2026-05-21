FROM registry.access.redhat.com/ubi9/python-312:latest

USER root

RUN dnf install -y \
    gcc \
    python3-devel \
    podman \
    && dnf clean all

USER default

RUN pip install --no-cache-dir \
    ansible-dev-tools \
    mkdocs-material \
    mkdocs-static-i18n

ENV PATH="/opt/app-root/bin:${PATH}"
