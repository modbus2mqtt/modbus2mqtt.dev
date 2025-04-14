#!/usr/bin/env python3
import argparse
import os
import re
import json
import shutil
import sys
import tarfile
import subprocess

import repositories
from typing import NamedTuple

server ='server'
hassioAddonRepository= 'hassio-addon-repository'

modbus2mqtt ='modbus2mqtt'
modbus2mqttLatest ='modbus2mqtt.latest'
configYaml='config.yaml'
dockerDir ='docker'
dockerFile = 'docker/Dockerfile'

class StringReplacement(NamedTuple):
    pattern: str
    newValue:str

def getLatestClosedPullRequest( ):
    return json.loads(repositories.executeSyncCommand(['gh', '-R' , 'modbus2mqtt/server', 'pr', 'list', 
	    '-s' , 'closed' , '-L', '1', '--json', 'number']))[0]['number']


def removeTag(basedir, component, tagname ):
    try:
        repositories.executeSyncCommandWithCwd(['git', 'push', '--delete', 
	    'origin' , tagname], os.path.join(basedir, component))
    except repositories.SyncException as err:
        repositories.eprint( err.args)
    try:
        repositories.executeSyncCommandWithCwd(['git', 'tag', '-d', tagname], os.path.join(basedir, component))
    except repositories.SyncException as err:
        repositories.eprint( err.args)


def getVersionForDevelopment(pkgjson:str):
    js = repositories.readPackageJson(os.path.join(pkgjson,'package.json'))
    version =js['version']
    prnumber = getLatestClosedPullRequest()
    return version + "-srv" + str(prnumber)

def replaceStringInFile(inFile, outFile, replacements):
    for repl in replacements:
        repositories.eprint( "replacements: " , repl.pattern, repl.newValue)
    with open(inFile, 'r') as file:
        data = file.read()
        for repl in replacements:
            data = re.sub(rf"{repl.pattern}", repl.newValue,data)
        with open(outFile, 'w') as w:        
            w.write( data)

# runs in (@modbus2mqtt)/server
# updates config.yaml in (@modbus2mqtt)/hassio-addon-repository
def updateConfigAndDockerfile(basedir,version, replacements,replacementsDocker=None):
    sys.stderr.write("createAddonDirectory release " + basedir  + " " +  version + "\n")
    config = os.path.join(basedir,  configYaml)
    docker = os.path.join(basedir,  dockerFile)
    replaceStringInFile(config,config, replacements)
    if replacementsDocker != None:
        replaceStringInFile(docker, docker, replacementsDocker )
 

# publishes docker image from (@modbus2mqtt)/hassio-addon-repository
# docker login needs to be executed in advance 
def pusblishDocker(basedir, version):
    sys.stderr.write("publishDocker "  + basedir + " " + version)

parser = argparse.ArgumentParser()
parser.add_argument("-b", "--basedir", help="base directory of all repositories", default='.')
parser.add_argument("-R", "--ref", help="ref branch or tag ", default='refs/heads/main')
parser.add_argument("-r", "--release", help="builds sets version number in config.yaml", action='store_true')
parser.add_argument("-p", "--pkgjson", help="directory of package.json file for version number in config.yaml",  type= str,   nargs='?',  default=None)

args = parser.parse_args()
if not args.release and not args.ref.endswith("release"):
    version = None
    if args.pkgjson == None:
        version = getVersionForDevelopment(os.path.join(args.basedir, 'server')) 
    else:
        version = getVersionForDevelopment(args.pkgjson)
    replacements = [
        StringReplacement(pattern='version: [0-9.][^\n]*', newValue='version: ' +version ),
        ]
    updateConfigAndDockerfile(os.path.join(args.basedir, hassioAddonRepository,modbus2mqttLatest), version, replacements,replacements)
    print("TAG_NAME=" + version)
else:
    repositories.executeSyncCommand(['rsync', '-avh', os.path.join(args.basedir,hassioAddonRepository,modbus2mqttLatest) + '/', os.path.join(args.basedir,hassioAddonRepository,modbus2mqtt) +'/'])

    if args.pkgjson == None:
        version = repositories.readPackageJson(os.path.join( args.basedir, 'server', 'package.json'))['version']
    else:
        version = repositories.readPackageJson(os.path.join(args.pkgjson, 'package.json'))
    removeTag(args.basedir,hassioAddonRepository, 'v' +version)
    githuburl = 'github:modbus2mqtt/server'
    replacements = [
        StringReplacement(pattern='version: [0-9.][^\n]*', 
                          newValue='version: ' +  version ),
        StringReplacement(pattern='Modbus <=> MQTT latest', 
                          newValue='Modbus <=> MQTT' ),
        StringReplacement(pattern='image: ghcr.io/modbus2mqtt/modbus2mqtt.latest', newValue= 'image: ghcr.io/modbus2mqtt/modbus2mqtt'),
        StringReplacement(pattern='slug:.*', newValue='slug: modbus2mqtt'),
        ]
    replacementsDocker = [
        StringReplacement(pattern=githuburl+ '[^\n]*', newValue=githuburl + '#v' + version  )
        ]        
    updateConfigAndDockerfile(os.path.join(args.basedir, hassioAddonRepository,modbus2mqtt), version, replacements,replacementsDocker)
    print("TAG_NAME=" + version)

