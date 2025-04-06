#!/usr/bin/env python3
from dataclasses import dataclass
from enum import Enum
import functools
import io
import json
import argparse
import os
import subprocess
import sys
import re
import time
from typing import Any, Dict
import typing
import time
from threading import Thread
import testall

@dataclass
class PullTexts:
    type: str= ""
    topic: str= ""
    text: str = ""
    draft: bool = True

currentRepository = "unknown"    

class TestStatus(Enum):
    running = 1
    failed = 2
    success = 3
    allfailed = 4
    notstarted = 0
class PullRequest:
        
    def __init__(self, name:str,number:int):
        self.name = name
        self.number = number
    def _is_valid_operand(self, other):
        return (hasattr(other, "name") and
                hasattr(other, "number"))

    def __eq__(self, other):
        if not self._is_valid_operand(other):
            return NotImplemented
        return self.name.lower() == other.name.lower()

    def __lt__(self, other):
        if not self._is_valid_operand(other):
            return NotImplemented
        return self.name.lower() < other.name.lower()
    name: str
    number: int

@functools.total_ordering
class Repository:      
    def __init__(self, name:str):
        self.name = name
        self.branch = None
        self.pulltexts =[]
        self.remoteBranch = None
    def _is_valid_operand(self, other):
        return (hasattr(other, "name") and
                hasattr(other, "owner"))

    def __eq__(self, other):
        if not self._is_valid_operand(other):
            return NotImplemented
        return self.name.lower() == other.name.lower()

    def __lt__(self, other):
        if not self._is_valid_operand(other):
            return NotImplemented
        return self.name.lower() < other.name.lower()
    name: str
    branch: str
    isForked: bool = False
    remoteBranch: str = None
    localChanges: int
    gitChanges: int
    pulltexts: list[PullTexts] = []
    pullrequestid: int = None
    testStatus: TestStatus = TestStatus.notstarted

class Repositorys: 
    def __init__(self, para:Dict):
        self.owner = para['owner']
        self.repositorys = para['repositories']
    owner: str
    login:str
    repositorys: Any
    pulltext: PullTexts = None

def getGitPrefix( repositorys:Repositorys):
    eprint( repositorys.login )
    if repositorys.owner == repositorys.login:
        return "https://github.com/"
    else:
        return "git@github.com:"
    
class SyncException(Exception):
    pass

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

def executeCommand(cmdArgs: list[str], *args, **kwargs)-> str:
    ignoreErrors = kwargs.get('ignoreErrors', None)
    result = subprocess.Popen(cmdArgs,
	cwd=os.getcwd(),
 	stdout=subprocess.PIPE,
 	stderr=subprocess.PIPE) 
    out, err = result.communicate()
    err = err.decode("utf-8")
    return_code = result.returncode
    if err != b'' and err != '' and not ignoreErrors:
        eprint(err)
    if return_code != 0:
        if out != b'':
            eprint(out.decode("utf-8"))
        return "".encode('utf-8')
    else:
        if out.decode("utf-8") == '':
            return '{"status": "OK"}'.encode('utf-8')
    return out

class StreamThread ( Thread ):
    def __init__(self, buffer):
        Thread.__init__(self)
        self.buffer = buffer
    def run ( self ):
        while 1:
            line = self.buffer.readline()
            eprint(line,end="")
            sys.stderr.flush()
            if line == '':
                break

def executeSyncCommandWithCwd(cmdArgs: list[str], cwdP:str, *args, **kwargs)-> str:
            
    if cwdP == None:
        cwdP = os.getcwd()
    proc = subprocess.Popen(cmdArgs,
    cwd=cwdP,
    stdout=subprocess.PIPE,
 	stderr=subprocess.PIPE) 
    out, err = proc.communicate()
    proc.returncode
    if proc.returncode != 0:
        raise SyncException( cwdP +':'+ err.decode("utf-8"), ' '.join(cmdArgs), out.decode("utf-8"))
    if len(err)>0:    
        eprint(err.decode("utf-8"))
    return out

def executeSyncCommand(cmdArgs: list[str], *args, **kwargs)-> str:
    return executeSyncCommandWithCwd(cmdArgs, os.getcwd(), *args, **kwargs)
   
def ghapi(method:str, url:str, *args)->str:

    return executeSyncCommand(['gh','api','-H', "Accept: application/vnd.github+json",
                           '-H',"X-GitHub-Api-Version: 2022-11-28",
                           '-X', method,
                           url ]+ list(*args))
def ghcompare( repo:str, owner:str, base:str, head:str, *args, **kwargs)->str:
    sha = kwargs.get('sha', None)
    delimiter = '...'
    if sha != None:
        delimiter = '..'
    url = '/repos/' + owner + '/' + repo + '/compare/' + base  + delimiter + head
    return ghapi( 'GET', url )
def json2Repositorys(dct:Any ):
    if 'name' in dct:
        p =   Repository( dct['name'])
        return p
    return dct

def isRepositoryForked( repositoryName )->bool:
    forked = json.loads(executeCommand(['gh', 'repo' , 'list', '--fork', '--json', 'name'] ))
    for repository in forked:
        if repository['name'] == repositoryName :
            return True
    return False
def forkRepository( repositoryName, owner ):
   
    if '' != executeSyncCommand(['gh', 'repo' , 'fork',  owner + '/' + repositoryName]):
            time.sleep(3)
def branchExists( branch):
    try:
        executeSyncCommand( ['git', 'branch', branch])
        return False
    except SyncException as err:
        return True
def readrepositorys(repositorysFile:str, owner:str)->Repositorys:
    try:
        input_file = open (repositorysFile)
        jsonDict:Dict[str,Any] =  json.load(input_file, object_hook=json2Repositorys)
        p =  Repositorys(jsonDict)
        if owner == None:
            js = json.loads(ghapi('GET', '/user'))
            p.login = js['login']
        else:
            p.login = owner
        return p
    except Exception as e:
        print("something went wrong " , e)
def getLocalChanges()->int:
    return int(subprocess.getoutput('git status --porcelain| wc -l')) 

def getTestResultStatus(repositorys:Repositorys):
    failedCount = 0
    for p in repositorys.repositorys:
        if p.testStatus == TestStatus.failed:
            failedCount +=1
    if failedCount > 0:
        if failedCount == len(repositorys.repositorys):
            return TestStatus.allfailed
        else:
            return TestStatus.failed
    else:
        return TestStatus.success
def hasLoginFeatureBranch(repository:Repository, repositorys:Repositorys):
    try:
        out = ghapi('GET', 'repos/' +repositorys.login + '/'+ repository.name +'/branches/' + repository.branch)
        return True
    except SyncException as err:
        return False        
def checkRemote( remote:str):
        out = executeSyncCommand(['git', 'remote','-v',]).decode("utf-8")
        return len(re.findall(r'((\n|^)' + remote + ')', out, re.MULTILINE)) >0

def addRemote(repositories:Repositorys, repository:Repository, origin:str):
     cmd = ['git', 'remote', 'add', origin, getGitPrefix(repositories)  + origin + '/' + repository.name + '.git' ]
     executeSyncCommand(cmd)
def setUrl(repository:Repository, repositorys:Repositorys):
    eprint("setUrl")
    origins = [repositorys.owner]
    if isRepositoryForked( repository.name):
        if hasLoginFeatureBranch(repository, repositorys):
            origins.append(repositorys.login)

    for origin in origins:
        if not checkRemote(origin):
            addRemote(repositorys,repository, origin)
    if hasLoginFeatureBranch(repository, repositorys):
        executeCommand([ 'git','fetch' , origin, repository.branch ])
        executeSyncCommand([ 'git','branch','--set-upstream-to='+ repositorys.login + '/' + repository.branch] )
    else:
        executeSyncCommand([ 'git','fetch', repositorys.owner , 'main'] )
        executeSyncCommand([ 'git','branch','--set-upstream-to='+ repositorys.owner + '/main'] )

   
def sendTestStatus( repositorys:Repositorys, status:TestStatus, update:bool=True):
    try:
        if repositorys.owner != repositorys.login:
            eprint( "Only the owner of the repos is allowed to update pull requests. No updates sent, but tests will be executed")
        statusStr = "No tests"
        match( status):
            case TestStatus.running: 
                statusStr = '# Tests are running ...'
            case TestStatus.success: 
                statusStr = '# Tests successful'
            case TestStatus.failed: 
                statusStr = '# Some Tests failed'
            case TestStatus.allfailed: 
                statusStr = '# All Tests failed'

        for p in repositorys.repositorys:
            if p.pullrequestid != None:
                if update:
                    executeSyncCommand(['gh', repositorys.owner + '/' + p.name , 'pr', 'comment', '--edit-last', '-b', statusStr ])
                else:
                    executeSyncCommand(['gh', repositorys.owner + '/' + p.name, 'pr', 'comment', '-b', statusStr ])
    except:
        eprint("Unable to send status to Pull Requests")
        #This will be ignored. The test results will also be 

@dataclass
class Checkrun:
    completed: bool
    success: bool

def getLastCheckRun(repositories:Repositorys,repository:Repository, branch:str)->Checkrun:
    js = json.loads(ghapi('GET', '/repos/' + repositories.owner +'/' + repository.name + '/commits/' + branch + '/check-runs?filter=latest').decode('utf-8'))
    if js['total_count'] != 1:
        raise SyncException( "Invalid number of check runs for " + '/'.join([repositories.owner , repository.name, branch]) + ': ' + js['total_count'])
    checkrunjs = js["checkruns"][0]
    return Checkrun(checkrunjs['status'] ==  "completed", checkrunjs["conclusion"] == "success")
              
def waitForMainTestPullRequest(repositories:Repositorys, mainTestPullRequest:PullRequest):
    eprint( "waiting for " + mainTestPullRequest.name + ":" + str(mainTestPullRequest.number))
    for mr in repositories.repositorys:
        if mr.name != mainTestPullRequest.name:
            while  True:
                # set the pull request number to identify the pull request
                mainTest = Repository(mainTestPullRequest.name)
                mainTest.pullrequestid = mainTestPullRequest.number
                js = searchPullRequest(mainTest,repositories,['state','headRefName', 'number'])
                for entry in js:
                    if entry['number'] == mainTestPullRequest.number:
                        js = entry
  
                if js == None:
                    raise SyncException("Unable to get pull request id for " + mr.name)
                match ( js['state'] ):
                    case 'OPEN'| 'APPROVED':  
                        eprint( "state " + js['state'])
                        checkrun = getLastCheckRun(repositories, mainTest, js['headRefName'] )
                        if checkrun.completed:
                            if checkrun.success:
                                eprint( mainTestPullRequest.name + ":" + mainTestPullRequest.number + " finished with success")
                                print("status=success" )
                                return
                            else:
                                eprint( mainTestPullRequest.name + ":" + mainTestPullRequest.number + " finished with failure")
                                print("status=failure" )
                                return
                    case _:
                        # try again later
                        time.sleep(30)
    # check run not found or other issues. It should stop with exit() when checkrun is finished
    SyncException( "Unable validate check run for pull Request " + mainTestPullRequest.name + ":" +  str(mainTestPullRequest.number ))

def testRepository(repository: Repository):

    args = ["npm", 'run', 'test' ]
    # If there are jest tests, append reporters

    if os.path.exists("__tests__"):
        args = args +[ "--", "--reporters", "default", "--reporters",  "github-actions"]

    print("::group::Unit tests for " + repository.name)
    eprint( executeSyncCommand(args).decode("utf-8"))
    print( '::endgroup::' )

# syncs main from original github source to local git branch (E.g. 'feature')
def syncRepository(repository: Repository, repositorys:Repositorys):
    repository.isForked = isRepositoryForked(repository.name)
    repository.branch =  subprocess.getoutput('git rev-parse --abbrev-ref HEAD')
    setUrl(repository,repositorys)  
    out = executeCommand(['git','remote','show',repositorys.login])
    match = re.search(r'.*Push *URL:[^:]*:([^\/]*)', out.decode("utf-8"))
    match = re.search(r'.*Remote[^:]*:[\r\n]+ *([^ ]*)', out.decode("utf-8"))
    repository.remoteBranch = match.group(1)
    # Sync owners github repository main branch from modbus2mqtt main branch
    # Only the main branch needs to be synced from github
    executeSyncCommand(['git','switch', 'main' ]).decode("utf-8")
    # ghapi('GET', ownerrepo+ '/merge-upstream', '-f', 'branch=main'
    # Is is not neccessary to update the main branch in forked repository, because the main branch's origin points to owner
    if repository.isForked:
        executeSyncCommand( ['gh','repo','sync', repositorys.login + '/' + repository.name ,  '-b' , 'main' ]  ).decode("utf-8")
        # download all branches from owners github to local git main branch
        try:
            ghapi('GET', '/repos/' + repositorys.login + '/' + repository.name + '/branches/' + repository.branch)
            executeSyncCommand(['git','switch', repository.branch]).decode("utf-8")
            executeSyncCommand(['git','branch','--set-upstream-to='+ repositorys.login +'/' + repository.branch, repository.branch ])
            executeSyncCommand(['git','pull','--rebase']).decode("utf-8")
        except SyncException as err:
            
            if  err.args[0] != "":
                if  "fatal: the requested upstream branch" in  err.args[0]:
                    executeSyncCommand(['git','fetch', 'modbus2mqtt']).decode("utf-8")
                    executeSyncCommand(['git','branch','--set-upstream-to='+ repositorys.owner +'/main' ])
                else:
                    js = json.loads(err.args[2])
                    if not js['message'].startswith("Branch not found"):
                        raise err
                    else:
                        executeSyncCommand(['git','branch','--set-upstream-to='+ repositorys.login +'/main', repository.branch ])
    else:
        executeSyncCommand(['git','switch', repository.branch]).decode("utf-8")
        executeSyncCommand(['git','pull', '--rebase']).decode("utf-8")
   
    repository.localChanges = getLocalChanges()
    executeSyncCommand( ['git','merge',  repositorys.owner +'/main'] ).decode("utf-8")
    out = executeSyncCommand(['git','diff', '--name-only','main' ]).decode("utf-8")
    repository.gitChanges = out.count('\n')

# syncs main from original github source to local git branch (E.g. 'feature')
def syncpullRepository(repository: Repository, repositorys:Repositorys, prs:list[PullRequest], branch:str):
    executeSyncCommand(['git','switch', 'main'])
    for pr in prs:
        found = False
        if not found and repository.name == pr.name:
            found = True
            checkRemote(repositorys.owner)
            branch = 'pull'+ str(pr.number)
            executeSyncCommand(['git', 'fetch', repositorys.owner, 'pull/' + str(pr.number)+ '/head:'+ branch ])
            executeSyncCommand(['git','switch', branch])
    if not found:
        #sync to main branch
        executeSyncCommand(['git', 'fetch', repositorys.owner, 'main'])
        executeSyncCommand(['git', 'checkout', 'main'])

def pushRepository(repository:Repository, repositorys:Repositorys):
    # Check if login/repository repository exists in github
    if repository.gitChanges == 0:
        return
    
    if not isRepositoryForked( repository.name):
        forkRepository(repository.name, repositorys.owner)
        executeSyncCommand(['git', 'remote', 'set-url', repositorys.login, getGitPrefix(repositorys)  + repositorys.login + '/'+ repository.name + '.git' ])
    executeSyncCommand(['git','switch', repository.branch])
    # push local git branch to remote servers feature branch
    executeSyncCommand(['git','push', repositorys.owner, repository.branch]).decode("utf-8")

def compareRepository( repository:Repository, repositorys:Repositorys):
    # compares git current content with remote branch 
    repository.branch =  subprocess.getoutput('git rev-parse --abbrev-ref HEAD')
    showOrigin = executeCommand( [ 'git', '-v', 'show', repositorys.login ])
    repository.hasChanges = False
    repository.localChanges = int(subprocess.getoutput('git status --porcelain| wc -l'))

    # No remote branch compare main and feature branch with git
    out = executeSyncCommand(['git','diff', 'main']).decode("utf-8")
    repository.hasChanges = out.count('\n') > 0

def createpullRepository( repository: Repository, repositorysList:Repositorys, pullRepositorys, pullText:PullTexts, issuenumber:int):
    if repository.gitChanges == 0:
        return
    args = []
    if pullText != None:
        args.append("-f"); args.append( "title=" + pullText.topic)
        args.append("-f"); args.append( "body=" + pullText.text)
        if pullText.draft == False:
            args.append("-f"); args.append( 'draft=false')
        else:
            args.append("-f"); args.append( 'draft=true' )    
    else:
        args.append("-f"); args.append( "issue=" + str( issuenumber))
        args.append("-f"); args.append( 'draft=false')
    args.append("-f"); args.append( "head=" + repositorysList.login + ":" + repository.branch)
    #args.append("-f"); args.append( "head=" + repository.branch)
    args.append("-f"); args.append( "base=main")  
    try:      
        js = json.loads(ghapi('POST','/repos/'+ repositorysList.owner +'/' + repository.name + '/pulls',args))
        # Append "requires:" text
        repository.pullrequestid = js['number']
    except SyncException as err:
        if len(args) and err.args[0] != "":
            js = json.loads(err.args[1])
            if js['errors'][0]['message'].startswith("A pull request already exists for"):
                eprint( js['errors'][0]['message']  + ". Continue...")
                repository.pullrequestid = getPullrequestId(repository,repositorysList)
                return


   
def newBranchRepository(repository:Repository, branch:str):
    try:
        executeSyncCommand(['git','show-ref','--quiet','refs/heads/' + branch])
    except:
        executeSyncCommand(['git','checkout','-b', branch ])
    executeSyncCommand(['git','switch', branch])
    executeSyncCommand(['git','fetch'])
# not used?    
def getPullRequests(repository:Repository, repositorys:Repositorys):
    return getRequiredPullrequests(repository, repositorys)

def checkFileExistanceInGithubBranch(owner, repo, branch, file):
    result = json.loads(ghapi('GET','/repos/'+ owner +'/' + repo + '/git/trees/'+ branch +'?recursive=true'))
    tree = result['tree']
    for o in tree:
        if o['path'] == file:
            return True
    return False

def checkFileExistanceInGithubPullRequest(owner, repo, pullnumber, file):                           
    result = json.loads(ghapi('GET','/repos/'+ owner +'/' + repo + '/pulls/'+ pullnumber +'/files'))
    for o in result:
        if o['filename'] == file:
            return True
    return False

def readpulltextRepository(repository:Repository):
    out = executeSyncCommand(['git','log','main...' + repository.branch , '--pretty=BEGIN%s%n%b%nEND']).decode("utf-8")
    repository.pulltexts = []
    while True:
        posBegin = out.find("BEGIN")
        posEnd = out.find("\nEND")
        commit = out[posBegin+5:posEnd]
        out = out[posEnd+4:]
        if posBegin != -1 and posEnd != -1:
            match = re.search(r'\[(bug|feature)\]([^\n]+)\n([\s\S]*)', commit)
            if match:
                pt = PullTexts(match.groups()[0],  match.groups()[1])
                if 3 == len(match.groups()):
                    pt.text = match.groups()[2]
                repository.pulltexts.append(pt)
            
        if re.search(r'\s*$', out):
            break;
def searchPullRequest( repository:Repository, repositorys:Repositorys):
    prtext = ""
    if repository.pullrequestid != None:
        prtext= "/" + str(repository.pullrequestid)
    rc = json.loads(ghapi('GET', "repos/" + repositorys.owner + "/" + repository.name + "/pulls" + prtext))
    if type(rc) is list:
        return rc;
    else:
        return [rc]

def getPullrequestId(repository:Repository, repositorys:Repositorys):
    js = searchPullRequest(repository, repositorys)
    if len(js) > 0:
        for entry in js:
            if repository.branch != None:
                if entry['head']['label'] == repositorys.login + ':' + repository.branch:                
                    return entry["number"]

    return None
def getpulltextFromGithub( pullrequest:PullRequest, baseowner:str)->str:

    js = json.loads(executeSyncCommand([ "gh", "pr", "view" , str( pullrequest.number), 
        "-R", baseowner + "/" + pullrequest.name,
        "--json", "body"  ]))
    return  js['body']

requiredRepositorysRe = r"\/([^\/]*)\/pulls\/(\d+)"

def getPullrequestFromString(prname:str )->PullRequest:
    pr = prname.split(':')
    if len(pr) != 2:
        raise SyncException("Invalid format for pull request (expected: <repository>:<pull request number>)")
    return PullRequest(pr[0],int(pr[1]))

def getRequiredReposFromPRDescription(prDescription:str,pullrequest:PullRequest)->list[PullRequest]:
    rc:list[PullRequest] = []      
    if( prDescription != None):
        matches = re.findall( requiredRepositorysRe, prDescription, re.MULTILINE )
        for m in matches:
           rc.append(PullRequest(m[0],int(m[1])))
    if len(rc)==0:
        if pullrequest != None:
            rc.append(pullrequest)
        else:
            raise SyncException("Unable to determine pull requests no pull request available and the pull description contains no dependencies ") 
    return rc

def getRequiredPullrequests( pullrequest:PullRequest= None, pulltext:str = None, owner:str=None )->list[PullRequest]:
    if pulltext == None or pulltext == '':
        pulltext = getpulltextFromGithub( pullrequest, owner )
    return getRequiredReposFromPRDescription(pulltext,pullrequest)

  
def updatepulltextRepository(repository:Repository, repositorysList: Repositorys, pullRepositorys):
    requiredText = "### Dependant Pullrequests\n" + \
                    "|Repository|Pull Request|\n" + \
                    "|----|----|\n"
    for p in pullRepositorys:
        prnumber = str(p.pullrequestid)
        requiredText +=  "|["+ p.name +"](https://github.com/"+repositorysList.owner +"/"+ p.name +"/pulls/"+ prnumber+")|"+ prnumber+"|\n"
    if requiredText.endswith(", "):
        requiredText = requiredText[:-2]
    if repository.pullrequestid != None:
        txt = getpulltextFromGithub(PullRequest(repository.name,repository.pullrequestid), repositorysList.owner)
        pulltext = re.sub(
           requiredRepositorysRe, 
           "", 
           txt)
        eprint( pulltext)
        args = [ "gh", "pr", "edit", str( repository.pullrequestid), 
            "-R", repositorysList.owner + "/" + repository.name,
            "--body", pulltext + "\n" + requiredText ]
        executeSyncCommand(args)
def readPackageJson( dir:str)->Dict[str,any]:
    try:
        with open(dir) as json_data:
            return  json.load( json_data)
    except Exception as err:
        eprint("Exception read " )
        msg = str(err.args)
        raise SyncException("Try to open package.json in " + os.getcwd() + '\n' +  msg)
def updatePackageJsonReferences(repository:Repository,  repositorysList: Repositorys,dependencytype: str, pullRequests:list[PullRequest]):
    if dependencytype != 'pull':
        pullRequests = []
        for pr in repositorysList.repositorys:
            pullRequests.append(PullRequest(pr.name, pr.pullrequestid))         
    npminstallargs = []
    npmuninstallargs = []
    pkgjson = readPackageJson('package.json')
    
    for pr in pullRequests:
         # restrict to open PR's
            
        package = '@' + repositorysList.owner+ '/' +  pr.name
        
        if 'dependencies' in pkgjson and package in pkgjson['dependencies'].keys():
            pRepository = Repository(pr.name)
            pRepository.branch = repository.branch
            pRepository.pullrequestid = pr.number
            js = searchPullRequest( pRepository,repositorysList)
            # If PR is no more open, use main branch instead of PR
            if js != None and dependencytype == 'pull' and js[0]['state'].lower() not in ['open', 'approved']:      
                dependencytype ='remote'
                   
            match dependencytype:
                case "local":
                    npminstallargs.append( os.path.join('..',pr.name))
                    npmuninstallargs.append( package )
                case "remote":
                    # for testing: Use login instead of owner
                    # In production owner == login
                    githubName = 'github:'+ repositorysList.owner +'/' + pr.name
                    if checkFileExistanceInGithubBranch('modbus2mqtt', pr.name,'main', 'package.json'):
                        npminstallargs.append(  githubName)
                        npmuninstallargs.append( package )
                    else:
                        eprint("package.json is missing in modbus2mqtt/" + pr.name +"#main"
                        + ".\nUnable to set remote reference in modbus2mqtt/" + repository.name 
                        + "\nContinuing with invalid reference")
                case "release":
                    # read package.json's version number build version tag
                    versionTag = "v" + readPackageJson(os.path.join('..', pr.name ,'package.json'))['version']
                    releaseName = 'github:'+ repositorysList.login +'/' + pr.name+ '#' +versionTag
                    npminstallargs.append(  releaseName)
                    npmuninstallargs.append( package )                    
                case "pull":
                    githubName = getGitPrefix(repositorysList) + repositorysList.owner +'/' + pr.name
                    newgithubName = githubName + '#pull/' + str(pr.number) + '/head'
                    if checkFileExistanceInGithubBranch(repositorysList.owner, pr.name,'main', 'packdage.json'
                        ) or checkFileExistanceInGithubPullRequest(repositorysList.owner, pr.name,str(pr.number), 'package.json'):
                        npminstallargs.append(  newgithubName )  
                        npmuninstallargs.append( package )
                    else:
                        eprint("package.json is missing in " + newgithubName
                        + ".\nUnable to set remote reference                                                                                                                                                                                                                                in modbus2mqtt/" + pr.name + '/package.json'
                        + "\nContinuing with invalid reference")
#    if len(npmuninstallargs ) > 0:
#        executeSyncCommand(["npm", "uninstall"] + npmuninstallargs)
    try:        
        executeSyncCommand(["npm", "install"]  + npminstallargs)
        return len(npminstallargs ) > 0
    except Exception as err:
        eprint("npm cache exceptions can happen if the github url in dependencies is wrong!")
        raise err
    
def tagExists(tagname:str)->bool:
    try:
        return executeSyncCommand(["git","tag", "-l", tagname]).decode("utf-8").count('\n') > 0
    except Exception as err:
        eprint( "tag doesn't exists", err.args[0])
        return False

def ensureNewPkgJsonVersion():
    versionTag = "v" + readPackageJson('package.json')['version']        
    if tagExists(versionTag):
        executeSyncCommand(["npm", "--no-git-tag-version", "version", "patch"])
        return "v" + readPackageJson('package.json')['version']        
    return versionTag

def dependenciesRepository(repository:Repository,  repositorysList: Repositorys,dependencytype: str, pullRequests:list[PullRequest]):

    if dependencytype == 'release':
        # find unreleased commits
        changedInMain = 0
        executeSyncCommand( ['git','switch', 'main'] )
        executeSyncCommand( ['git','pull','--rebase'] )
        try:
            sha = executeSyncCommand( ['git','merge-base','--fork-point', 'release' ] ).decode("utf-8")
            sha = sha.replace('\n','')
            out:str = executeSyncCommand(['git','diff', '--name-status', sha ]).decode("utf-8")
            changedInMain = out.count('\n')
            js = ghcompare( repository.name,repositorysList.owner,"main", repositorysList.owner + ":" + repository.branch)
            cmpResult = json.loads(js)
            changedInMain +=  int(cmpResult['behind_by'])

        except SyncException as err:
            if err.args[0] != '': # Wrong return code from git merge-base but no changes
                raise err
                
        versionTag = ""
        needsNewRelease = False
        if changedInMain >0:
            # Check in version number to main branch
            versionTag = ensureNewPkgJsonVersion()
            if  getLocalChanges() > 0:
                executeSyncCommand( ["git", "add", "."])
                executeSyncCommand( ["git", "commit", "-m" , "Update npm version number " + versionTag] )
                executeSyncCommand( ["git", "pull", "-X", "theirs"] )
                executeSyncCommand( ["git", "push" , "-f", repositorysList.owner, "HEAD"])
                needsNewRelease = True

        executeSyncCommand( ['git','switch', 'release'] )
        executeSyncCommand( ["git", "pull", "-X", "theirs"] )
        executeSyncCommand( ['git','merge', '-X','theirs', 'main'] )
        updatePackageJsonReferences(repository, repositorysList, dependencytype, pullRequests)    
        if  getLocalChanges() > 0:
            # makes sure, the version number in local pgkJson is new
            # local changes are from updated dependencies            
            versionTag = ensureNewPkgJsonVersion()
            executeSyncCommand(["git", "add", "."])
            executeSyncCommand(["git", "commit", "-m" , "Release " + versionTag] )
            needsNewRelease = True
        # May be the version number is up to date, but the tag doesn't exist
        versionTag = "v" + readPackageJson('package.json')['version']
        if  not tagExists(versionTag):
                executeSyncCommand(["git", "tag", versionTag] )
                if needsNewRelease:
                    executeSyncCommand(["git", "push", "--atomic", "-f", repositorysList.owner , "release", versionTag])
                else:
                    executeSyncCommand(["git", "push", repositorysList.owner, "tag", versionTag])
                eprint( "Released " + repository.name + ":" + versionTag)
        else:
            if needsNewRelease:
                raise SyncException( "Release failed: Tag '" + versionTag + "' exists in " + repository.name )
    else:
        updatePackageJsonReferences(repository, repositorysList, dependencytype, pullRequests)
        
def prepareGitForReleaseRepository(repository:Repository,  repositorysList: Repositorys):
    if repositorysList.login != repositorysList.owner:
       raise SyncException("Release is allowed for " + repositorysList.owner + " only")
    js = executeSyncCommand(['git', 'remote', '-v']).decode("utf-8")
    match = re.search(r'' + repositorysList.owner + '/', js)
    if not match:
       raise SyncException("Git origin is not " + repositorysList.owner + '/' + repository.name )
    executeSyncCommand(['git', 'switch', 'release']).decode("utf-8")
    repository.branch = "release"
def npminstallRepository(repository:Repository, ci:bool):
    if ci:
        executeSyncCommand(['npm','ci'])
    else:
        executeSyncCommand(['npm','install'])

def buildRepository(repository:Repository):
    eprint(executeSyncCommand(['npm','run', 'build']).decode("utf-8"))
 
repositoryFunctions = {
    'compare' : compareRepository,
    'sync' : syncRepository,
    'npminstall':npminstallRepository,
    'build':buildRepository,
    'test':testRepository,
    'syncpull': syncpullRepository,
    'push' : pushRepository,
    'createpull' : createpullRepository,
    'newbranch': newBranchRepository,
    'readpulltext': readpulltextRepository,
    'dependencies': dependenciesRepository,
    'updatepulltext': updatepulltextRepository,
    'prepareGitForRelease': prepareGitForReleaseRepository,
}


def doWithRepositorys( repositorys:Repositorys, repoFunction:Any, *args:Any ): 
    eprint("step: " + repoFunction.__name__, sep=' ', end='', flush=True )
    pwd = os.getcwd()
    for repository in repositorys.repositorys:
        global currentRepository 
        eprint( repository.name)
        currentRepository = repository.name
        eprint(" " + currentRepository, sep=' ', end='', flush=True )
        os.chdir(repository.name)
        eprint(os.getcwd())
        try:
            repoFunction( repository, *args)
        finally:
            os.chdir(pwd)
    eprint("")

