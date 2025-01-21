FROM cypress/included:13.15.1 
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y install  git mosquitto nginx mosquitto mosquitto-clients \
    && chown 1000 /var/lib/nginx 