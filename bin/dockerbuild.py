#!/usr/bin/env python3

import repositories
import sys
import os

home_dir = os.path.expanduser("~")


repositories.executeCommandWithOutputs(["docker", "run", "--rm", "--privileged", 
                                  "-v" , "/var/run/docker.sock:/var/run/docker.sock:ro",
                                  "-v", home_dir + "/modbus2mqtt.dev/hassio-addon-repository/modbus2mqtt.latest:/data",
                                  "ghcr.io/home-assistant/amd64-builder:latest",
                                  "--amd64", "-t", "/data" , "--test"], sys.stdout, sys.stderr)
