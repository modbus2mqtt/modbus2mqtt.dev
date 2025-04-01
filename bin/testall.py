#!/usr/bin/env python3
import argparse
import repositories
import os
import shutil

def testall(repositorysList)->bool:
    repositories.doWithRepositorys(repositorysList, 'test')
            
    os.chdir("server")
            
            
    if os.path.isdir(os.path.join("cypress", "e2e")):

            print("::group::Cypress run tests")
            repositories.eprint(repositories.executeSyncCommand(["npx", "cypress", "run"]).decode("utf-8"))
            print( '::endgroup::' )
            print("::group::Cypress cleanup")
            repositories.executeSyncCommand([os.path.join("cypress", "servers", "killServers")], "nginx")
            print( '::endgroup::' )
    else:
            repositories.eprint("No Cypress tests ín" + os.getcwd())
