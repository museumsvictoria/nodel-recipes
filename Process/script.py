# Date:         2017.01.13
# Version:      0.4

'''Process Node'''

### Libraries required by this Node



### Parameters used by this Node
win32_sandbox = ['-u', 'complex_vlc_player.py']

EXAMPLE_PROCESS = 'C:\\Windows\\System32\\notepad.exe'

param_args = Parameter({ 'title': 'Arguments',
                'desc': 'The list of command line arguments as JSON',
                'order': next_seq(),
                'schema': { 'type': 'array', 'items': {
                'type': 'object',
                  'properties': { 'arg': {'type': 'string'} } } } })

param_app = Parameter({ 'title': 'Target process',
                'desc': 'Location of process to run.',
                'order': next_seq(),
                'schema': { 'type': 'string', 'hint': EXAMPLE_PROCESS } } )

param_filterStyle = Parameter({ 'title': 'Filter behaviour',
                'desc': 'Filter behaviour.',
                'order': next_seq(),
                'schema': { 'type': 'string', 'enum': ['Include', 'Exclude'] } } )

param_filter = Parameter({ 'title': 'Filter',
                'desc': 'The list of console messages to filter',
                'order': next_seq(),
                'schema': { 'type': 'array', 'items': {
                'type': 'object',
                  'properties': { 'arg': {'type': 'string'} } } } })

param_behaviour = Parameter({ 'title': 'Disable process heartbeat',
                'desc': 'Do not attempt to revive ended process.',
                'order': next_seq(),
                'schema': { 'type': 'boolean' } } )



### Functions used by this Node
def manage_started():
  console.info('Process started.')
  local_event_State.emit(True)

def manage_stopped(exitCode):
  console.info('Process stopped (exit code %s)' % exitCode)
  local_event_State.emit(False)

def manage_stdout(line):
  if param_filter:
    filter(line)
  else:
    console.info(line)

def filter(line):
  count = 0
  for word in param_filter:
    if word['arg'] in line:
      count += 1

  if count > 0:
    if param_filterStyle == 'Include':
      console.info(line)
  else:
    if param_filterStyle == 'Exclude':
      console.info(line)



# Local actions this Node provides
def local_action_Start(arg = None):
  '''{"title":"Start","desc":"Start specified process.","group":"Control",}'''
  print 'Action Start requested'
  if local_event_State.arg:
    console.warn('Process already running.')
  else:
    process.start()

def local_action_Stop(arg = None):
  '''{"title":"Stop","desc":"Stop specified process.","group":"Control",}'''
  print 'Action Stop requested'
  process.stop()

### Process managed by this Node
process = Process([],
                  started=manage_started,
                  stdout=manage_stdout,
                  stdin=None,
                  stderr=lambda data: console.info('got stderr "%s"' % data), # stderr handler
                  stopped=lambda exitCode: manage_stopped(exitCode), # when the process is stops / stopped
                  timeout=lambda: console.warn('Request timeout'))  


### Events provided by this Node
local_event_State = LocalEvent('{"title":"Active","desc":"State of process.","group":"Status","schema": { "type": "boolean"} }')



def main(arg = None):
  # Start your script here.
  print 'Nodel process node script started.'

  #process.stop()

  process_args = []
  if (param_app and param_args):
    process_args = [x['arg'] for x in param_args]
    process_args.insert(0, param_app)
    process.setCommand(process_args)
    console.info('Process: %s' % process_args)
  elif param_app:
    process_args.append(param_app)
    process.setCommand(process_args)
    console.info('Process: %s' % process_args)
  else:
    console.warn('Application not specified.')
    process.close()