#!/usr/bin/env python3
import argparse
import re
import socket
import stat
import subprocess
import sys
import time
import repositories
import os
import shutil

def isOpen(ip,port):
   s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
   try:
      s.connect((ip, int(port)))
      s.shutdown(2)
      return True
   except:
      return False

def isCallable(command:str):
    try:
        nginxPath = repositories.executeSyncCommand(["which", command]).decode("utf-8")
    except Exception as err:
        raise repositories.SyncException( command + " must be installed!")
 
 
defaultMimeTypes = "/etc/nginx/mime.types"
defaultLibDir = "/var/lib/nginx"
    
def nginxGetMimesTypes():
    if  not os.path.exists(defaultMimeTypes):
        return "/opt/homebrew/" + defaultMimeTypes
    return defaultMimeTypes

def nginxGetLibDir():
    if  not os.path.isdir(defaultLibDir):
         return "/opt/homebrew/var/homebrew/linked/nginx"
    return defaultLibDir
   
def checkRequiredApps():
    # nginx must be preinstalled
    isCallable("nginx")
    ngxinlib = nginxGetLibDir()
    if not os.path.isdir(ngxinlib) :
        raise repositories.SyncException( nginxGetLibDir() + " directory not found!") 
    if not os.access(ngxinlib,os.W_OK):
        raise repositories.SyncException( ngxinlib + " must be writable!")
             

def startRequiredApps():
    checkRequiredApps()
    with open( "server/cypress/servers/nginx.conf/nginx.conf","r") as f:
        nginxConf = f.read()
        nginxConf = re.sub(r"mime.types", nginxGetMimesTypes(),nginxConf)
        # default directory
    with open("nginx.conf", "w") as g:
        g.write( nginxConf)
    subprocess.Popen(["nohup", "nginx","-c","nginx.conf","-p","."])
    subprocess.Popen(["nohup", "node", "server/dist/runModbusTCPserver.js", "-y", "server/cypress/servers/modbustcp.conf/yaml-dir" , "--busid", "0"])
    for port in [3002,3006]:
        count=0
        while count < 12:            
            if not isOpen("localhost", port):
                time.sleep(1)
            else:
                break
            count += 1
        if count == 12:
            with open( "nohup.out") as f:
                repositories.eprint(f.read())
            repositories.eprint( repositories.executeSyncCommand(["pgrep", "-f", "nginx: master|runModbusTCP"]))
            raise repositories.SyncException("Port " + str(port) + " is not up")

def unlinkIfExist( file:str):
  if os.path.exists(file):
        os.unlink(file)
 
def killRequiredApps():
    print("::group::Cypress cleanup")
    try:
        repositories.executeSyncCommand(["pkill", "-f", "nginx: master|runModbusTCP"])
        unlinkIfExist("nginx.conf")
        unlinkIfExist("nohup.out" )
        unlinkIfExist("nginx.error.log" )
        unlinkIfExist("nginx.pid" )
    except:
        return 
    print( '::endgroup::' )

def testRepository(repository: repositories.Repository):
    
    args = ["npm", 'run', 'test' ]
    # If there are jest tests, append reporters

    if os.path.exists("__tests__"):
        args = args +[ "--", "--reporters", "default", "--reporters",  "github-actions"]
    if not repository.notest:
        print("::group::Unit tests for " + repository.name)
        repositories.executeCommandWithOutputs(args,sys.stderr, sys.stderr)
        print( '::endgroup::' )

def testpackagejson(repository: repositories.Repository):
    # read package.json
    f = open("package.json")
    
    if re.search('.*("@modbus2mqtt\\/[^"]*":\\s*"file:\\.\\.\\/)',f.read()):
        raise repositories.SyncException( "package.json contains local dependencies" )

def packagejson(repositorysList)->bool:
    repositories.doWithRepositorys(repositorysList, testpackagejson)


def testall(repositorysList)->bool:
    repositories.doWithRepositorys(repositorysList, testRepository)
    os.chdir("server")
    if os.path.isdir(os.path.join("cypress", "e2e")):

            print("::group::Cypress run tests")
            repositories.executeCommandWithOutputs(["npx", "cypress", "run"],sys.stderr, sys.stdout)
            print( '::endgroup::' )
    else:
            repositories.eprint("No Cypress tests ín" + os.getcwd())
