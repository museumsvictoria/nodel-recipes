import os

DEFAULT_WORKINGDIR = '/opt/bit/site/stablehost'
DEFAULT_PORT = 0
DEFAULT_NODELRELEASE = '/opt/nodel/nodelhost.jar'

param_working = Parameter({'title': 'Working directory', 'schema': {'type': 'string', 'hint': DEFAULT_WORKINGDIR}})
param_port = Parameter({'title': 'Port', 'desc': 'Use "0" for any port (recommended) or choose a fixed TCP port.', 'schema': {'type': 'integer', 'hint': DEFAULT_PORT}})
param_nodelRelease = Parameter({'title': 'Nodel release', 'desc': 'The full path to the Nodel release.', 
                                'schema': {'type': 'string', 'hint': DEFAULT_NODELRELEASE}})
param_interface = Parameter({'title': 'Interface', 'desc': 'The interface to bind to.', 'schema': {'type': 'string'}})

local_event_Disabled = LocalEvent({'schema': {'type': 'boolean'}})

process = None # (init. in main)

def main():
  console.info('Started!')
  
  if param_working == None or local_event_Disabled.getArg() == True:
    console.warn('Process launch disabled - disabled or working directory not set')
    return
  
  working = param_working if param_working != None and len(param_working)>0 else DEFAULT_WORKINGDIR
  if not os.path.exists(working):
    console.info('Creating working directory "%s"...' % working)
    os.makedirs(working)
  
  nodelRelease = param_nodelRelease if param_nodelRelease != None and len(param_nodelRelease)>0 else DEFAULT_NODELRELEASE
  nodelPort = param_port if param_port != None else DEFAULT_PORT
  
  params = ['java', '-jar', nodelRelease, '-p', str(nodelPort)]
  
  # use the interface setting if specified
  if param_interface != None:
    params.extend(['-i', param_interface])
    
  global process
  process = Process(params,
                    stderr=lambda line: console.warn('err: %s' % line),
                    stdout=lambda line: console.info('out: %s' % line),
                    working=working)
  
  console.info('Starting Nodel host... (params are %s)' % params)
  process.start()
    
def local_action_Disable(arg=None):
  """{"schema": {"type": "boolean"}}"""
  local_event_Disabled.emit(True)
  process.close()  
