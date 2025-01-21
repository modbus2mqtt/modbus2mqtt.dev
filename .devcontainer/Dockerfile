FROM mcr.microsoft.com/devcontainers/javascript-node:20
ARG REMOTE_UID=1000
COPY ./.env /tmp/.env
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y install  git mosquitto nginx mosquitto mosquitto-clients \
    ca-certificates curl \
    && install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc \
    && chmod a+r /etc/apt/keyrings/docker.asc \
    && echo \
        "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian \
        $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
    tee /etc/apt/sources.list.d/docker.list > /dev/null \
    && apt-get update \
    && . /tmp/.env ; groupadd -g $DOCKER_GID docker \
    && apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin \
    && chown 1000 /var/lib/nginx 
RUN if ! id -nu $REMOTE_UID;\
    then \
      useradd -u ${REMOTE_UID} remoteuser; \
      usermod -a -G docker remoteuser; \
    else \
      usermod -a -G docker $(id -nu $REMOTE_UID); \
    fi
