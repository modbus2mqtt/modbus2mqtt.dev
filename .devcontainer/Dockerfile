FROM mcr.microsoft.com/devcontainers/javascript-node:20
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y install  systemd git mosquitto nginx mosquitto mosquitto-clients\
    && systemctl stop nginx
