'''
BirdDog Mini encoder/decoder

`rev 2.2405`

* use Sources parameter when decoder

_changelog_

 * _rev 2.240514 JP belatedly added to repo_
 * _rev 1.200214 JP first created_
 
'''

# <!-- parameters

param_disabled  = Parameter({'schema': {'type': 'boolean', 'desc': 'Disables this node'}})
param_ipAddress = Parameter({'schema': {'type': 'string'}})
param_sources   = Parameter({'schema': {'type': 'array', 'desc': '(use remote signal or this to override)', 'items': {'type': 'object', 'properties': {
                               'name': {'type': 'string', 'order': 1, 'hint': '(recommend using short consecutive letters or digits, e.g. "1", "2", or "A", "B")'},
                               'location': {'type': 'object', 'order': 2, 'properties': {
                                       'ip':   {'type': 'string', 'order': 1},
                                       'port': {'type': 'integer', 'order': 2},
                                       'name': {'type': 'string', 'order': 3} }}}}}})

# -->

local_event_Source = LocalEvent({'group': 'Switching', 'order': next_seq(), 'schema': {'type': 'string'}})
# ... individual source will attach emit handlers

local_event_SourceUnknown = LocalEvent({'title': 'Unknown', 'group': 'Sources', 'order': next_seq(), 'schema': {'type': 'boolean'}})

_srcLocations_byName = { }         # e.g. { '1':           { ip: '1.2.2.2', port: 23, .... } }
_srcNames_byNetworkLocation = { }  # e.g. { '1.2.2.2:23':  '1', ... }

def main():
  if param_disabled:
    console.warn('Disabled; nothing to do!')
    return
  
  if len(param_sources or local_event_Sources.getArg() or EMPTY) == 0:
    console.warn('No sources configured; nothing to do!')
    return
  
  initSources()
  
  console.info('Will monitor and control [%s]' % param_ipAddress)
  console.info('%s sources listed' % len(_srcLocations_byName))
  
local_event_Sources = LocalEvent({'group': 'Config', 'schema': {'type': 'array', 'items': {'type': 'object', 'properties': {
                                    'name': {'type': 'string', 'order': 1},
                                    'location': {'type': 'object', 'order': 2, 'properties': {
                                      'ip':   {'type': 'string', 'order': 1},
                                      'port': {'type': 'integer', 'order': 2},
                                      'name': {'type': 'string', 'order': 3} }}}}}})

def remote_event_Sources(arg):
  if len(param_sources or EMPTY) > 0:
    console.warn('Ignoring new remote source list; parameter in use instead')
    return
  
  console.warn('Received new source list! [%s]' % arg)
  local_event_Sources.emit(arg)
  
  console.warn('Node will self-restart!')
  _node.restart()

  
def initSources():
  sources = param_sources or local_event_Sources.getArg() or EMPTY
  
  if len(sources) == 0:
    console.warn('No sources specified')
    return
  
  for srcInfo in sources:
    initSource(srcInfo)
    
  # also handle unknown sources
  
  def handler(arg):
    local_event_SourceUnknown.emit(arg not in _srcLocations_byName)
    
  local_event_Source.addEmitHandler(handler)
  
  # emit sources for slave config
  local_event_Sources.emit(sources)
    
def initSource(srcInfo):
  name = srcInfo['name']
  location = srcInfo['location']
  
  if not name or not location:
    raise Warning("incomplete config - missing name or location")
  
  networkLocation = '%s:%s' % (location['ip'], location['port']) # will be used as a key later
  
  # the signal
  activeSrcSignal = Event('Source %s' % name, {'title': '"%s"' % name, 'group': 'Sources', 'order': next_seq(), 'schema': {'type': 'boolean'}})
  
  # emit boolean on source change
  def handler(arg):   
    activeSrcSignal.emit(arg == name)
    
  local_event_Source.addEmitHandler(handler)

  # the action
  def actionHandler(arg):
    SwitchTo.call(location)
  
  srcSwitch = Action('Source %s' % name, actionHandler, {'title': '"%s"' % name, 'group': 'Sources', 'order': next_seq()})
  
  _srcLocations_byName[name] = location
  _srcNames_byNetworkLocation[networkLocation] = name  # e.g. { '1.2.2.2:23':  '1', ... }

# -->

@local_action({'group': 'Switching', 'order': next_seq(), 'schema': {'type': 'object', 'properties': {
                                          'ip': {'type': 'string', 'order': 1},
                                          'port': {'type': 'integer', 'order': 2},
                                          'name': {'type': 'string', 'order': 3}}}})
def SwitchTo(arg):
  console.info('SwitchTo(%s) called' % arg)
  ip = arg['ip']
  port = arg['port']
  result = request('connectTo', {'connectToIp': ip, 'port': port, 'sourceName': arg['name']})
  log(2, 'SwitchTo result [%s]' % result)
  
  # todo check result
  
  # assume good
  
  networkLocation = '%s:%s' % (ip, port)
  name = _srcNames_byNetworkLocation.get(networkLocation)
  
  local_event_Source.emit(name if name else 'Unknown')
  
@local_action({'group': 'Switching', 'order': next_seq()})
def PollSource(ignore):
  log(2, 'PollSource')
  resp = request('connectTo')
  
  global _lastReceive
  _lastReceive = system_clock()
  
  ip = resp['connectToIp']
  port = resp['port']
  
  networkLocation = '%s:%s' % (ip, port)
  name = _srcNames_byNetworkLocation.get(networkLocation)
  
  local_event_Source.emit(name if name else 'Unknown')

  log(2, 'PollSource resp [%s]' % resp)
  
Timer(lambda: PollSource.call(), 15, 5) # every 15s, first after 5s
  
def request(endPoint, arg=None):
  # e.g. curl http://birddog-1be4d:8080/connectTo -H "Content-Type: application/json" -d "{\"connectToIp\":\"192.168.178.151\",\"port\":5962,\"sourceName\":\"MM-LL-LABPTZ (CAM)\"}" -v
  post = None if arg == None else json_encode(arg)
  
  url = 'http://%s:8080/%s' % (param_ipAddress, endPoint)
  
  log(3, 'url:%s%s' % (url, ' post:%s' % post if post else ''))
  
  result = get_url(url, headers={'Content-Type': 'application/json'}, post=post)
  
  return json_decode(result) if len(result or BLANK) > 0 else None 

# <!-- status

local_event_Status = LocalEvent({'title': 'Status', 'group': 'Status', 'order': 9990, "schema": { 'title': 'Status', 'type': 'object', 'properties': {
        'level': {'title': 'Level', 'order': 1, 'type': 'integer'},
        'message': {'title': 'Message', 'order': 2, 'type': 'string'}
    } } })

_lastReceive = 0 # last valid comms, system_clock() based

# roughly, the last contact  
local_event_LastContactDetect = LocalEvent({'group': 'Status', 'title': 'Last contact detect', 'schema': {'type': 'string'}})
  
def statusCheck():
  # lampUseHours = local_event_LampUseHours.getArg() or 0
  
  diff = (system_clock() - _lastReceive)/1000.0 # (in secs)
  now = date_now()
  
  if diff > status_check_interval+15:
    previousContactValue = local_event_LastContactDetect.getArg()
    
    if previousContactValue == None:
      message = 'Always been missing.'
      
    else:
      previousContact = date_parse(previousContactValue)
      message = 'Off the network %s' % formatPeriod(previousContact)
      
    local_event_Status.emit({'level': 2, 'message': message})
    return
    
  # TODO: warning if on UNKNOWN source
  
  local_event_Status.emit({'level': 0, 'message': 'OK'})
  
  local_event_LastContactDetect.emit(str(now))
  
status_check_interval = 75
status_timer = Timer(statusCheck, status_check_interval)

def formatPeriod(dateObj):
  if dateObj == None:      return 'for unknown period'
  
  now = date_now()
  diff = (now.getMillis() - dateObj.getMillis()) / 1000 / 60 # in mins
  
  if diff == 0:             return 'for <1 min'
  elif diff < 60:           return 'for <%s mins' % diff
  elif diff < 60*24:        return 'since %s' % dateObj.toString('h:mm:ss a')
  else:                     return 'since %s' % dateObj.toString('E d-MMM h:mm:ss a')
  
# status -->


# <!-- logging

local_event_LogLevel = LocalEvent({'group': 'Debug', 'order': 10000+next_seq(), 'desc': 'Use this to ramp up the logging (with indentation)',  
                                   'schema': {'type': 'integer'}})

def warn(level, msg):
  if local_event_LogLevel.getArg() >= level:
    console.warn(('  ' * level) + msg)

def log(level, msg):
  if local_event_LogLevel.getArg() >= level:
    console.log(('  ' * level) + msg)

# --!>
