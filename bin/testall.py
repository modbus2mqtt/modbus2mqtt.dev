#!/usr/bin/env python3
import argparse
import repositories
import os
import shutil
parser = argparse.ArgumentParser()
parser.add_argument("repositorys", help="repositories.json file ",  type=str)
parser.add_argument("login", help="user logged in ",  type=str)

args = parser.parse_args()
repositorysList = repositories.readrepositorys(args.repositorys, args.login)
try:
    repositories.doWithRepositorys(repositorysList, 'test')
    os.chdir("server")
    if os.path.isdir(os.path.join("cypress", "e2e")):
        print("::group::Cypress initialization")
        macngxinlib="/opt/homebrew/var/homebrew/linked/nginx"
 
        if not ( os.path.isdir("/var/lib/nginx") or os.path.isdir(macngxinlib))or shutil.which("mosquitto_sub")is None:
            repositories.executeSyncCommand([os.path.join("cypress", "servers","installPackages")])
        repositories.executeSyncCommand([os.path.join("cypress", "servers", "startRunningServers")])
        print( '::endgroup::' )
        print("::group::Cypress run tests")
        repositories.eprint(repositories.executeSyncCommand(["npx", "cypress", "run"]).decode("utf-8"))
        print( '::endgroup::' )
        print("::group::Cypress cleanup")
        repositories.executeSyncCommand([os.path.join("cypress", "servers", "killServers", "nginx")])
        print( '::endgroup::' )
    else:
        repositories.eprint("No Cypress tests ín" + os.getcwd())
except repositories.SyncException as err1:
    repositories.eprint(repositories.currentRepository + ": " + err1.args[0])
    for arg in err1.args:
        repositories.eprint( arg)
    exit(2)
except Exception as err:
    for arg in err.args:
        repositories.eprint(arg)
    exit(2)