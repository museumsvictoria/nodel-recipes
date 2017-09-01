import os
from java.io import File

DEFAULT_WORKINGDIR = '/opt/bit/site/stablehost'
DEFAULT_PORT = 0
DEFAULT_WSPORT = 0
DEFAULT_NODELRELEASE = '/opt/nodel/nodelhost.jar'

param_working = Parameter({'title': 'Working directory', 'schema': {'type': 'string', 'hint': DEFAULT_WORKINGDIR}})
param_port = Parameter({'title': 'Port', 'desc': 'Use "0" for any port (recommended) or choose a fixed TCP port.', 'schema': {'type': 'integer', 'hint': DEFAULT_PORT}})
param_wsPort = Parameter({'title': 'Websocket port', 'desc': 'Use "0" for any port (recommended) or choose a fixed TCP port.', 'schema': {'type': 'integer', 'hint': DEFAULT_WSPORT}})
param_nodelRelease = Parameter({'title': 'Nodel release', 'desc': 'The full path to the Nodel release.', 
                                'schema': {'type': 'string', 'hint': DEFAULT_NODELRELEASE}})
param_interface = Parameter({'title': 'Interface', 'desc': 'The interface to bind to.', 'schema': {'type': 'string'}})
param_nodesRoot = Parameter({'title': 'Nodes root', 'schema': {'type': 'string'}})
param_watch = Parameter({'title': 'Watch for updates?', 'desc': 'Will watch for updates and recycle the process if detected.', 'schema': {'type': 'boolean'}})
param_logToFile = Parameter({'title': 'Logging to file? (advanced)', 'schema': {'type': 'boolean'}})

param_nodeFilters = Parameter({'title': 'Node filtering', 'schema': { 'type': 'array', 'items': {
        'type': 'object', 'properties': {
          'type':   {'title': 'Type', 'type': 'string', 'enum': ['Include', 'Exclude'], 'order': 1},
          'filter': {'title': 'Filter', 'type': 'string', 'order': 2}}}}})

local_event_Disabled = LocalEvent({'schema': {'type': 'boolean'}})

process = None # (init. in main)

# holds the resolved Nodel release
nodelRelease = None

def main():
  console.info('Started!')
  
  if param_working == None or local_event_Disabled.getArg() == True:
    console.warn('Process launch disabled - disabled or working directory not set')
    return
  
  working = param_working if param_working != None and len(param_working)>0 else DEFAULT_WORKINGDIR
  if not os.path.exists(working):
    console.info('Creating working directory "%s"...' % working)
    os.makedirs(working)
  
  global nodelRelease
  nodelRelease = param_nodelRelease if param_nodelRelease != None and len(param_nodelRelease)>0 else DEFAULT_NODELRELEASE
  nodelPort = param_port if param_port != None else DEFAULT_PORT
  
  params = ['java', '-jar', nodelRelease, '-p', str(nodelPort)]
  
  # use the interface setting if specified
  if param_interface != None:
    params.extend(['-i', param_interface])
    
  if param_nodesRoot != None:
    params.extend(['-r', param_nodesRoot])
    
  if param_wsPort != None:
    param.extend(['--wsPort', param_wsPort])
    
  inclList = list()
  exclList = list()
  
  if param_nodeFilters != None:
    for nodeFilter in param_nodeFilters:
      typee = nodeFilter['type']
      filterr = nodeFilter['filter']
      
      if typee == 'Include':
        inclList.append(filterr)
      
      elif typee == 'Exclude':
        exclList.append(filterr)
        
    for incl in inclList:
      params.extend(['-I', incl])
      
    for excl in exclList:
      params.extend(['-X', excl])
      
  if param_logToFile:
    params.append('-l')
    
  global process
  process = Process(params,
                    stderr=lambda line: console.warn('err: %s' % line),
                    stdout=lambda line: console.info('out: %s' % line),
                    working=working)
  
  console.info('Starting Nodel host... (params are %s)' % params)
  process.start()
  
  if param_watch:
    console.info('Will check for updates every 2 mins.')
    Timer(lambda: lookup_local_action('CheckForUpdate').call(), 120, 10)
    
def local_action_Disable(arg=None):
  """{"schema": {"type": "boolean"}}"""
  local_event_Disabled.emit(True)
  process.close()
  
local_event_NodelReleaseModified = LocalEvent({'title': 'Nodel release modified', 'schema': {'type': 'string'}})
  
def local_action_CheckForUpdate(arg=None):
  '''{"desc": "Checks for an update", "caution": "If a new update is detected, the process will be recycled."}'''
  # get the actual modified value
  actualLastModifiedStr = str(date_instant(File(nodelRelease).lastModified()))
  
  # and the previous one
  lastModifiedStr = local_event_NodelReleaseModified.getArg()
  
  if lastModifiedStr == None:
    local_event_NodelReleaseModified.emit(actualLastModifiedStr)
    return
  
  if actualLastModifiedStr != lastModifiedStr:
    console.info('File update detected (new modified:%s, old modified:%s); process will be recycled.' % (actualLastModifiedStr, lastModifiedStr))
    
    # update before recycling process (drop)
    local_event_NodelReleaseModified.emit(actualLastModifiedStr)
    
    process.drop()
