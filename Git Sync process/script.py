working = None

DEFAULT_WORKINGDIR = '/opt/bit/site/stablehost'

param_working = Parameter({'title': 'Working directory', 'schema': {'type': 'string', 'hint': DEFAULT_WORKINGDIR}})

def main():
  if param_working == None or local_event_Disabled.getArg() == True:
    console.warn('Process launch disabled - disabled or working directory not set')
    return
  
  global working
  
  working = param_working if param_working != None and len(param_working)>0 else DEFAULT_WORKINGDIR
  if not os.path.exists(working):
    console.info('Creating working directory "%s"...' % working)
    os.makedirs(working)

def noFunc():
  pass

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


def local_action_GitPush(arg=None):
  '''{"order": 5, "group": "git"}'''
  gitPush(noFunc)
    
def gitPush(complete):
  console.info('git push')
  quick_process(['git', 'push', '-f'], working=working, finished=lambda arg: 
                             [console.info('exit:%s, out:%s err:%s' % (arg.code, arg.stdout, arg.stderr)), complete()])

  
def local_action_Sync(arg=None):
  gitAdd(lambda: gitCommit(lambda: gitPull(lambda: gitPush(lambda: gitCommit(noFunc)))))  
  
  