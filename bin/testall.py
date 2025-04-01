#!/usr/bin/env python3
import argparse
import repositories
import os.path
import shutil
parser = argparse.ArgumentParser()
parser.add_argument("repositorys", help="repositories.json file ",  type=str)
parser.add_argument("login", help="user logged in ",  type=str)

args = parser.parse_args()
repositorysList = repositories.readrepositorys(args.repositorys, args.login)
try:
    repositories.doWithRepositorys(repositorysList, 'test')
      
    if os.path.isdir(os.path.join("cypress", "e2e")):
        print("::group::Cypress E2E tests")
        if not os.path.isdir("/var/lib/nginx" or shutil.which("mosquitto_sub")is not None):
            repositories.executeSyncCommand([os.path.join("cypress", "servers","installPackages")])
        repositories.executeSyncCommand([os.path.join("cypress", "servers","startRunningServers")])
        repositories.executeSyncCommand(["npx", "cypress", "run", "--reporter", "json" ,"--reporter-options" "output=cypress-mocha.json"])
        repositories.executeSyncCommand([os.path.join("cypress", "servers","killServers")])
        print( '::endgroup::' )
    else:
        repositories.eprint("No Cypress tests")
except repositories.SyncException as err1:
    repositories.eprint(repositories.currentRepository + ": " + err1.args[0])
    for arg in err1.args:
        repositories.eprint( arg)
    exit(2)
except Exception as err:
    for arg in err.args:
        repositories.eprint(arg)
    exit(2)