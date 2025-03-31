#!/usr/bin/env python3
import argparse
import repositories

parser = argparse.ArgumentParser()
parser.add_argument("repositorys", help="repositories.json file ",  type=str)

args = parser.parse_args()
repositorysList = repositories.readrepositorys(args.repositorys)
try:
    repositories.doWithRepositorys(repositorysList, 'test')
except repositories.SyncException as err1:
    repositories.eprint(repositories.currentRepository + ": " + err1.args[0])
    for arg in err1.args:
        repositories.eprint( arg)
    exit(2)
except Exception as err:
    for arg in err.args:
        repositories.eprint(arg)
    exit(2)