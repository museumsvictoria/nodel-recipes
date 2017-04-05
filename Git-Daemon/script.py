# git daemon --verbose --base-path=c:\nodel-repos --reuseaddr --enable=receive-pack c:\nodel-repos

import os

# git daemon --verbose --base-path=d:\git --reuseaddr --enable=receive-pack d:\git

DEFAULT_ROOTDIR = '/opt/git/daemon/repos/'

param_root = Parameter({'title': 'Root directory', 'schema': {'type': 'string', 'hint': DEFAULT_ROOTDIR}})
param_port = Parameter({'title': 'Daemon port', 'schema': {'type': 'string', 'hint': '9418'}})
param_repo = Parameter({'title': 'Repo directory', 'schema': {'type': 'string', 'hint': 'c:\\nodel-repos\\nodel-cgpres.git'}})


local_event_Disabled = LocalEvent({'schema': {'type': 'boolean'}})

process = None # (init. in main)

def main():
  console.info('Started!')

  if param_root == None or local_event_Disabled.getArg() == True:
    console.warn('Launch disabled - disabled or working directory not set')
    return

  root = param_root if param_root != None and len(param_root)>0 else DEFAULT_ROOTDIR
  if not os.path.exists(root):
    console.info('Creating root directory "%s"...' % root)
    os.makedirs(root)

  params = ("git daemon --verbose --base-path=%s --reuseaddr --export-all --enable=receive-pack %s" % (root, root)).split(' ')

  global process
  process = Process(params,
                    stderr=lambda line: console.warn('err: %s' % line),
                    stdout=lambda line: console.info('out: %s' % line),
                    working=root)

  console.info('Starting Dit daemon... (params are %s)' % params)
  process.start()
  
  global working
  
  working = param_repo
  print working

def local_action_Disable(arg=None):
  """{"schema": {"type": "boolean"}}"""
  local_event_Disabled.emit(True)
  process.close() 
  
### Sync Component

# Note: for Windows system SSH location: C:\Windows\system32\config\systemprofile

  
def noFunc():
  pass

working = None

def local_action_GitStatus(arg=None):
  '''{"order": 1, "group": "git"}'''
  gitStatus(noFunc)
  
def gitStatus(complete):
  console.info('git status')
  quick_process(['git', 'status'], working=working, finished=lambda arg: 
                             [console.info('exit:%s, out:%s err:%s' % (arg.code, arg.stdout, arg.stderr)), complete()])

def local_action_GitCommitAll(arg=None):
  '''{"order": 2, "group": "git"}'''
  gitCommit(noFunc)

def gitCommit(complete):  
  console.info('git commit')
  quick_process(['git', 'commit', '-a', '-m', '(background)'], working=working, finished=lambda arg: 
                             [console.info('exit:%s, out:%s err:%s' % (arg.code, arg.stdout, arg.stderr)), complete()])

  
def local_action_GitAdd(arg=None):
  '''{"order": 3, "group": "git"}'''
  gitAdd(noFunc)
  
def gitAdd(complete):
  console.info('git add')
  quick_process(['git', 'add', '-A'], working=working, finished=lambda arg: 
                             [console.info('exit:%s, out:%s err:%s' % (arg.code, arg.stdout, arg.stderr)), complete()])

  
  
def local_action_GitPull(arg=None):
  '''{"order": 4, "group": "git"}'''
  gitPull(noFunc)
  
def gitPull(complete):
  console.info('git pull')
  quick_process(['git', 'pull', '-f'], working=working, finished=lambda arg: 
                             [console.info('exit:%s, out:%s err:%s' % (arg.code, arg.stdout, arg.stderr)), complete()])

def local_action_GitFetch(arg=None):
  '''{"order": 4, "group": "git"}'''
  gitFetch(noFunc)
  
def gitFetch(complete):
  console.info('git fetch')
  quick_process(['git', 'fetch'], working=working, finished=lambda arg: 
                             [console.info('exit:%s, out:%s err:%s' % (arg.code, arg.stdout, arg.stderr)), complete()])

def local_action_GitMerge(arg=None):
  gitMerge(noFunc)
  
def gitMerge(complete):
  console.info('git merge')
  quick_process(['git', 'merge'], working=working, finished=lambda arg: 
                             [console.info('exit:%s, out:%s err:%s' % (arg.code, arg.stdout, arg.stderr)), complete()])  
  
def local_action_GitPush(arg=None):
  '''{"order": 5, "group": "git"}'''
  gitPush(noFunc)
    
def gitPush(complete):
  console.info('git push')
  quick_process(['git', 'push', '-f'], working=working, finished=lambda arg: 
                             [console.info('exit:%s, out:%s err:%s' % (arg.code, arg.stdout, arg.stderr)), complete()])

  
def local_action_Sync(arg=None):
  gitFetch(lambda: gitPush(noFunc))  
