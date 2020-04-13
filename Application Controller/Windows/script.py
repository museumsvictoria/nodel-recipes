'''Long-running application with interruption detection. Warnings will self-clear after 4 stable days'''

# <parameters ---

DEFAULT_APP_PATH = 'notepad.exe'

param_AppPath = Parameter({'title': 'Single-app mode: App. Path', 'schema': {'type': 'string', 'hint': DEFAULT_APP_PATH},
                           'desc': 'The full path to the application executable'})

param_AppArgs = Parameter({'title': 'Single-app mode: App. Args', 'schema': {'type': 'string', 'hint': 'e.g. --color BLUE --title What\'s\\ Your\\ Story? --subtitle \"Autumn Surprise!\"'},
                           'desc': 'Application arguments, space delimeted, backslash-escaped'})

param_AppWorkingDir = Parameter({'title': 'Single-app mode: App. Working Dir.', 'schema': {'type': 'string', 'hint': 'e.g. c:\\temp'},
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

@after_main
def persistSignals():
  for s in [ local_event_Running, local_event_DesiredPower, local_event_Power, 
             local_event_LastStarted, local_event_FirstInterrupted, local_event_LastInterrupted ]:
    persistSignal(s)
  
def persistSignal(s):
  s.addEmitHandler(lambda arg: s.persistNow())

# --- signals>


appArgsList = list() # will hold the 'decoded' argument list (as opposed to single string)


# <main ---

import os
import sys

def main():
  # some checks and warnings
  if not is_blank(param_AppPath) and not os.path.isfile(param_AppPath):
    console.error('The application path could not be found - [%s]' % (param_AppPath or 'blank given'))
    return
  
  if not is_blank(param_AppWorkingDir) and not os.path.isdir(param_AppWorkingDir):
    console.error('The application working directory was specified but could not be found - [%s]' % param_AppWorkingDir)
    return
  
  # if on Windows, recommend that the process sandbox is used
  if os.environ.get('windir') and not (os.path.isfile('ProcessSandbox.exe') or os.path.exists('%s\ProcessSandbox.exe' % sys.exec_prefix)):
    console.warn('-- ProcessSandbox.exe NOT FOUND BUT RECOMMENDED --')
    console.warn('-- It is recommended the Nodel Process Sandbox launcher is used on Windows (see nodel releases) --')
    console.warn('-- The launcher safely manages multiple process applications, preventing rougue behaviour --')
    
  # ready to start
    
  console.info('This node will issue a warning status if it detects application interruptions i.e. crashing or external party closing it (not by Node)')
  
  # turn the arguments string into an array of args
  if not is_blank(param_AppArgs):
    appArgsList.extend(decodeArgList(param_AppArgs))
    console.info('(arg list %s)' % appArgsList)
                  
  if param_PowerStateOnStart == 'On':
    lookup_local_action('Power').call('On')
  
  elif param_PowerStateOnStart == 'Off':
    lookup_local_action('Power').call('Off')

  else:
    if local_event_DesiredPower.getArg() != 'On':
      console.info('(desired power was previously off so not starting)')
      process.stop()

    # otherwise process will start itself

# --- main>


# <power ---


@local_action({'group': 'Power', 'order': next_seq(), 'schema': {'type': 'string', 'enum': ['On', 'Off']},
               'desc': 'Also use to clear First Interrupted warnings'})
def Power(arg):
  # clear the first interrupted
  local_event_FirstInterrupted.emit('')
  
  if arg == 'On':
    local_event_DesiredPower.emit('On')
    process.start()
    
  elif arg == 'Off':
    local_event_DesiredPower.emit('Off')
    process.stop()
    
@before_main
def sync_RunningEvent():
  local_event_Running.emit('Off')
    
def determinePower(arg):
  desired = local_event_DesiredPower.getArg()
  running = local_event_Running.getArg()
  
  if desired == None:
    local_event_Power.emit(running)
  
  elif desired == running:
    local_event_Power.emit(running)
    
  else:
    local_event_Power.emit('Partially %s' % desired)
    
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
    

process = Process(None,
                  started=process_started,
                  stdout=process_feedback,
                  stdin=None,
                  stderr=process_feedback,
                  stopped=process_stopped)

@before_main
def updateProcessArgs():
  # called after full script parse
  fullCmdList = [param_AppPath or DEFAULT_APP_PATH]
  
  if appArgsList:
    fullCmdList.extend(appArgsList)
  
  process.setCommand(fullCmdList)
                  
  # use working directory is specified
  if not is_blank(param_AppWorkingDir):
    process.setWorking(param_AppWorkingDir)

# --->

# < cpu checking --- 

local_event_CPUUsage = LocalEvent({'group': 'Monitoring', 'schema': {'type': 'number'}})

def cpuChecker_feedback(data):
  activity = json_decode(data)
  
  signalName = activity.get('event')
  if is_blank(signalName):
    return
  
  local_event_CPUUsage.emit(activity.get('arg'))
  
cpuChecker = Process([r'%s\CPUChecker.exe' % _node.getRoot().getAbsolutePath()], stdout=cpuChecker_feedback)
cpuChecker.stop()

def compileComplete(arg):
  if arg.code != 0:
    console.error('BAD COMPILATION RESULT (code was %s)' % arg.code)
    console.error(arg.stdout)
    return
  
  # otherwise run the program
  cpuChecker.start()

# compile to code on first run
quick_process([r'C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe', 'CPUChecker.cs'], finished=compileComplete)

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