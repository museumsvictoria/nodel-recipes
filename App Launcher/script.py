'''For long-running applications, rapidly controls the active state of the application. Includes child-process cleanup and interruption detection. Warnings will self-clear after 4 stable days'''

# <parameters ---

param_AppPath = Parameter({'title': 'App. Path (required, executable name with or without path)', 'required': True, 'schema': {'type': 'string', 'hint': '(e.g. "C:\\MyApps\\myapp.exe" or "somethingOnThePath.exe")'},
                           'desc': 'The full path to the application executable'})

param_AppArgs = Parameter({'title': 'App. Args', 'schema': {'type': 'string', 'hint': 'e.g. --color BLUE --title What\'s\\ Your\\ Story? --subtitle \"Autumn Surprise!\"'},
                           'desc': 'Application arguments, space delimeted, backslash-escaped'})

param_AppWorkingDir = Parameter({'title': 'App. Working Dir.', 'schema': {'type': 'string', 'hint': 'e.g. c:\\temp'},
                                 'desc': 'Full path to the working directory'})

param_PowerStateOnStart = Parameter({'title': 'Running state on Node Start', 'schema': {'type': 'string', 'enum': ['On', 'Off', '(previous)']},
                                     'desc': 'What "power" state to start up in when the node itself starts, typically on boot'})

param_FeedbackFilters = Parameter({'title': 'Console Feedback filters', 'schema': {'type': 'array', 'items': {'type': 'object', 'properties': {
                                     'type': {'type': 'string', 'enum': ['Include', 'Exclude'], 'order': 1},
                                     'filter': {'type': 'string', 'order': 2}}}}})

# --->


# <signals ---

local_event_Running = LocalEvent({'group': 'Monitoring', 'schema': {'type': 'string', 'enum': ['On', 'Off']},
                                  'desc': 'Locks to the actual running state of the application process'})

local_event_DesiredPower = LocalEvent({'group': 'Power', 'schema': {'type': 'string', 'enum': ['On', 'Off']},
                                       'desc': 'The desired "power" (or running state), set using the action'})

local_event_Power = LocalEvent({'group': 'Power', 'schema': {'type': 'string', 'enum': ['On', 'Partially On', 'Off', 'Partially Off']},
                                'desc': 'The "effective" power state using Nodel power conventions taking into account actual and desired'})

local_event_LastStarted = LocalEvent({'group': 'Monitoring', 'schema': {'type': 'string'}, # holds dates
                                      'desc': 'The last time the application started'}) 

local_event_FirstInterrupted = LocalEvent({'group': 'Monitoring', 'schema': {'type': 'string'}, # holds dates
                                           'desc': 'The first time the process was "interrupted" (meaning it died prematurely)'})

local_event_LastInterrupted = LocalEvent({'group': 'Monitoring', 'schema': {'type': 'string'}, # holds dates
                                           'desc': 'The last time the process was "interrupted" (meaning it died/stopped prematurely)'})

# ensure these signals aggressively persist their values 
# (by default Nodel is very relaxed which is not ideal for clients that may deal with more interruptions)

@after_main
def ensurePersistSignals():
  def ensure(s): # variable capture requires separate function
    s.addEmitHandler(lambda arg: s.persistNow())
  
  for s in [ local_event_Running, local_event_DesiredPower, local_event_Power, 
             local_event_LastStarted, local_event_FirstInterrupted, local_event_LastInterrupted ]:
    ensure(s)

# --- signals>


# <main ---

import os    # path functions
import sys   # launch environment info

_resolvedAppPath = None # includes entire path

def main():
  # App Path MUST be specified
  if is_blank(param_AppPath):
    console.error('No App. Path has been specified, nothing to do!')
    _process.stop()
    return

  # check if a full path has been provided i.e. does it contain a backslash "\" 
  if os.path.sep in param_AppPath: # e.g. 
    global _resolvedAppPath
    _resolvedAppPath = param_AppPath # use full path
    finishMain()
  
  else:
    # otherwise test the path using 'where.exe' (Windows) or 'which' (Linux)
    
    # e.g. > where notepad
    #      < C:\Windows\System32\notepad.exe
    #      < C:\Windows\notepad.exe

    def processFinished(arg):
      global _resolvedAppPath

      if arg.code == 0: # 'where.exe' succeeded
        paths = arg.stdout.splitlines()
        if len(paths or EMPTY) > 0:
          _resolvedAppPath  = paths[0]
        
      if is_blank(_resolvedAppPath):
        _resolvedAppPath = param_AppPath

      finishMain()

    # path not fully provided so use 'where' to scan PATH environment, (has to be done async)
    whereCmd = 'where' if os.environ.get('windir') else 'which'
    quick_process([ whereCmd, param_AppPath], finished=processFinished)

def finishMain():
  if not os.path.isfile(_resolvedAppPath):
    console.error('The App. Path could not be found - [%s]' % _resolvedAppPath)
    return
  
  # App Working Directory is optional
  if not is_blank(param_AppWorkingDir) and not os.path.isdir(param_AppWorkingDir):
    console.error('The App. working directory was specified but could not be found - [%s]' % param_AppWorkingDir)
    return

  # recommend that the process sandbox is used if one can't be found

  # later versions of Nodel have the sandbox embedded (dynamically compiled)
  usingEmbeddedSandbox = False
  try:
    from org.nodel.toolkit.windows import ProcessSandboxExecutable
    usingEmbeddedSandbox = True
  except:
    usingEmbeddedSandbox = False

  if not usingEmbeddedSandbox and os.environ.get('windir') and not (os.path.isfile('ProcessSandbox.exe') or os.path.exists('%s\\ProcessSandbox.exe' % sys.exec_prefix)):
    console.warn('-- ProcessSandbox.exe NOT FOUND BUT RECOMMENDED --')
    console.warn('-- It is recommended the Nodel Process Sandbox launcher is used on Windows --')
    console.warn('-- The launcher safely manages applications process chains, preventing rogue or orphan behaviour --')
    console.warn('--')
    console.warn('-- Use Nodel jar v2.2.1.404 or later OR download ProcessSandbox.exe asset manually from https://github.com/museumsvictoria/nodel/releases/tag/v2.1.1-release391 --')
    
  # ready to start, dump info
    
  console.info('This node will issue a warning status if it detects application interruptions i.e. crashing or external party closing it (not by Node)')
  if usingEmbeddedSandbox:
    console.info('(embedded Process Sandbox detected and will be used)')

  # start the list with the application path
  cmdLine = [ _resolvedAppPath ]
  
  # turn the arguments string into an array of args
  if not is_blank(param_AppArgs):
    cmdLine.extend(decodeArgList(param_AppArgs))

  # use working directory is specified
  if not is_blank(param_AppWorkingDir):
    _process.setWorking(param_AppWorkingDir)    

  _process.setCommand(cmdLine)
    
  console.info('Full command-line: [%s]' % ' '.join(cmdLine))
                  
  if param_PowerStateOnStart == 'On':
    lookup_local_action('Power').call('On')
  
  elif param_PowerStateOnStart == 'Off':
    lookup_local_action('Power').call('Off')

  else:
    if local_event_DesiredPower.getArg() != 'On':
      console.info('(desired power was previously off so not starting)')
      _process.stop()

    # otherwise process will start itself

# --- main>


# <power ---

local_event_PowerOn = LocalEvent({ 'group': 'Power', 'title': 'On', 'order': next_seq(), 'schema': { 'type': 'boolean' }})

local_event_PowerOff = LocalEvent({ 'group': 'Power', 'title': 'Off', 'order': next_seq(), 'schema': { 'type': 'boolean' }})

@local_action({'group': 'Power', 'order': next_seq(), 'schema': {'type': 'string', 'enum': ['On', 'Off']},
               'desc': 'Also used to clear First Interrupted warnings'})
def Power(arg):
  # clear the first interrupted
  local_event_FirstInterrupted.emit('')
  
  if arg == 'On':
    local_event_DesiredPower.emit('On')
    _process.start()
    
  elif arg == 'Off':
    local_event_DesiredPower.emit('Off')
    _process.stop()
    
@local_action({'group': 'Power', 'title': 'On', 'order': next_seq()})
def PowerOn():
  Power.call('On')
  
@local_action({'group': 'Power', 'title': 'Off', 'order': next_seq()})
def PowerOff():
  Power.call('Off')  
  

@before_main
def sync_RunningEvent():
  local_event_Running.emit('Off')
    
def determinePower(arg):
  desired = local_event_DesiredPower.getArg()
  running = local_event_Running.getArg()
  
  if desired == None:      state = running
  elif desired == running: state = running
  else:                    state = 'Partially %s' % desired
    
  local_event_Power.emit(running)
  local_event_PowerOn.emit(running == 'On')
  local_event_PowerOff.emit(running == 'Off')
    
@after_main
def bindPower():
  local_event_Running.addEmitHandler(determinePower)
  local_event_DesiredPower.addEmitHandler(determinePower)
  
# --- power>


# <process ---

def process_started():
  console.info('application started!')
  local_event_Running.emit('On')
  local_event_LastStarted.emit(str(date_now()))
  
def process_stopped(exitCode):
  console.info('application stopped! exitCode:%s' % exitCode)
  
  nowStr = str(date_now()) # so exact timestamps are used
  
  if local_event_DesiredPower.getArg() == 'On':
    local_event_LastInterrupted.emit(nowStr)

    # timestamp 'first interrupted' ONCE
    if len(local_event_FirstInterrupted.getArg() or '') == 0:
      local_event_FirstInterrupted.emit(nowStr)
  
  local_event_Running.emit('Off')

# print out feedback from the console  
def process_feedback(line):
  inclusionFiltering = False
  
  keep = None
    
  for filterInfo in param_FeedbackFilters or []:
    filterType = filterInfo.get('type')
    ffilter = filterInfo.get('filter')
    matches = ffilter in line
      
    if filterType == 'Include':
      inclusionFiltering = True
      if matches:
        keep = True
          
    elif filterType == 'Exclude':
      if matches:
        keep = False

        
  if keep == None: # (not True or False)
    if not inclusionFiltering:
      # there are no Include filters in use so 'keep' defaults to True
      keep = True
      
    else:
      keep = False
  
  if keep:
    console.info('feedback> [%s]' % line)
    

_process = Process(None,
                  started=process_started,
                  stdout=process_feedback,
                  stdin=None,
                  stderr=process_feedback,
                  stopped=process_stopped)

# --->


# <status ---

local_event_Status = LocalEvent({'order': -100, 'group': 'Status', 'schema': {'type': 'object', 'properties': {
                                   'level': {'type': 'integer'},
                                   'message': {'type': 'string'}}}})

def statusCheck():
  # recently interrupted
  now = date_now()
  nowMillis = now.getMillis()
  
  # check for recent interruption within the last 4 days (to incl. long weekends)
  firstInterrupted = date_parse(local_event_FirstInterrupted.getArg() or '1960')
  firstInterruptedDiff = nowMillis - firstInterrupted.getMillis()

  lastInterrupted = date_parse(local_event_LastInterrupted.getArg() or '1960')
  
  if firstInterruptedDiff < 4*24*3600*1000L: # (4 days)
    if firstInterrupted == lastInterrupted:
      timeMsgs = 'last time %s' % toBriefTime(lastInterrupted)
    else:
      timeMsgs = 'last time %s, first time %s' % (toBriefTime(lastInterrupted), toBriefTime(firstInterrupted))
      
    local_event_Status.emit({'level': 1, 'message': 'Application interruptions may be taking place (%s)' % timeMsgs})
    
  # fallback to a general process check if it's supposed to be running
  elif local_event_DesiredPower.getArg == 'On' and local_event_Power.getArg() != 'On':
    local_event_Status.emit({'level': 2, 'message': 'Application is not running'})
    return
    
  else:
    local_event_Status.emit({'level': 0, 'message': 'OK'})
  
statusCheck_timer = Timer(statusCheck, 30)

# --->


# <--- convenience functions

# Converts into a brief time relative to now
def toBriefTime(dateTime):
  now = date_now()
  nowMillis = now.getMillis()

  diff = (nowMillis - dateTime.getMillis()) / 60000 # in minutes
  
  if diff == 0:
    return '<1 min ago'
  
  elif diff < 60:
    return '%s mins ago' % diff

  elif diff < 24*60:
    return dateTime.toString('h:mm:ss a')

  elif diff < 365 * 24*60:
    return dateTime.toString('h:mm:ss a, E d-MMM')

  elif diff > 10 * 365*24*60:
    return 'never'
    
  else:
    return '>1 year'


# Decodes a typical process arg list string into an array of strings allowing for
# limited escaping or quoting or both.
#
# For example, turns:
#    --name "Peter Parker" --character Spider\ Man

# into:
#    ['--name', '"Peter Parker"', '--character', 'Spider Man']   (Python list)
#
def decodeArgList(argsString):
  argsList = list()
  
  escaping = False
  quoting = False
  
  currentArg = list()
  
  for c in argsString:
    if escaping:
      escaping = False

      if c == ' ' or c == '"': # put these away immediately (space-delimiter or quote)
        currentArg.append(c)
        continue      
      
    if c == '\\':
      escaping = True
      continue
      
    # not escaping or dealt with special characters, can deal with any char now
    
    if c == ' ': # delimeter?
      if not quoting: 
        # hit the space delimeter (outside of quotes)
        if len(currentArg) > 0:
          argsList.append(''.join(currentArg))
          del currentArg[:]
          continue

    if c == ' ' and len(currentArg) == 0: # don't fill up with spaces
      pass
    else:
      currentArg.append(c)
    
    if c == '"': # quoting?
      if quoting: # close quote
        quoting = False
        argsList.append(''.join(currentArg))
        del currentArg[:]
        continue
        
      else:
        quoting = True # open quote
  
  if len(currentArg) > 0:
      argsList.append(''.join(currentArg))

  return argsList


# convenience --->
