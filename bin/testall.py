#!/usr/bin/env python3
import argparse
import re
import socket
import stat
import subprocess
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
    if  not os.path.isdir(defaultMimeTypes):
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
        
def testall(repositorysList)->bool:
    repositories.doWithRepositorys(repositorysList, repositories.testRepository)
    os.chdir("server")
    if os.path.isdir(os.path.join("cypress", "e2e")):

            print("::group::Cypress run tests")
            repositories.eprint(repositories.executeSyncCommand(["npx", "cypress", "run"]).decode("utf-8"))
            print( '::endgroup::' )
            print("::group::Cypress cleanup")
            print( '::endgroup::' )
    else:
            repositories.eprint("No Cypress tests ín" + os.getcwd())
