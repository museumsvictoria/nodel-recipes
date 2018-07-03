'''Yamama AV Receiver using the YNCA protocol'''

# see http://www.sdu.se/pub/yamaha/yamaha-ynca-receivers-protocol.pdf'''

YNCA_TCPPORT = 50000

param_Disabled = Parameter({'schema': {'type': 'boolean'}})
param_IPAddress = Parameter({'title': 'IP address (or blank for discovery via UPnP node)', 'schema': {'type': 'string'}})

# <main ---
  
def main():
  if param_Disabled:
    console.warn('Disabled! nothing to do')
    return
  
  ipAddress = param_IPAddress
  
  if is_blank(ipAddress):
    if lookup_remote_event('UPnPBeacon').getNode():
      # discovery is in use
      ipAddress = local_event_DiscoveredIPAddress.getArg()
      
      # has it been discovered at least once
      if is_blank(ipAddress):
        console.info('Using discovery via UPnP...')
        return
      
      console.info('Using discovery based on last IP address...')
      
    else:
      console.warn('No IP address set; nothing to do')
      return
  
  dest = '%s:%s' % (ipAddress, YNCA_TCPPORT)
  
  console.info('Will connect to [%s]' % dest)
  tcp.setDest(dest)

# --- main>

# <operations ---

@after_main
def bind_sys_information():
  bind_oneway_unitfunc('Version', 'System Info', '@SYS:VERSION', {'type': 'string'})
  
INPUTS_CODES = [ 'TUNER', 'PHONE', 'HDMI1', 'HDMI2', 'HDMI3', 
                 'HDMI4', 'HDMI5', 'AV1', 'AV2', 'VAUX', 
                 'AUDIO1', 'AUDIO2', 'AUDIO3', 'AUDIO4', 'AUDIO5', 
                 'CLINK', 'SERVER', 'NETRADIO', 'BT', 'USB' ]

# zonePrefix: e.g. "Power"
# zoneCode: e.g. "MAIN"
@after_main
def bind_zones():
  bind_zone_unit_funcs('Main', 'MAIN')
  bind_zone_unit_funcs('Zone 2', 'ZONE2')  

def bind_zone_unit_funcs(zonePrefix, zoneCode):
  bind_twoway_unitfunc('%s Power' % zonePrefix, '%s Power' % zonePrefix, '@%s:PWR' % zoneCode, 
                       {'type': 'string', 'enum': ['On', 'Off']}, 
                       title='Power',
                       setterFilter=lambda arg: 'Standby' if arg == 'Off' else arg,
                       getterFilter=lambda arg: 'Off' if arg == 'Standby' else arg,
                       pollingPeriod=20) # the amp has a TCP idle time of about ~40s so needs to be more frequent
  
  bind_twoway_unitfunc('%s Volume' % zonePrefix, '%s Volume' % zonePrefix, '@%s:VOL' % zoneCode, {'type': 'number'},
                       title='Volume',
                       # make sure it's on 0.5 boundaries
                       setterFilter=lambda arg: '%1.1f' % (int((arg * 10) / 5) * 5 / 10.0),
                       getterFilter=lambda arg: float(arg))
  
  mutingAction, mutingSignal = bind_twoway_unitfunc('%s Muting' % zonePrefix, '%s Volume' % zonePrefix, '@%s:MUTE' % zoneCode, {'type': 'string', 'enum': ['On', 'Off']}, title='Muting')
  
  # muting toggle
  Action('%s Muting Toggle' % zonePrefix, lambda ignore: mutingAction.call('On' if mutingSignal.getArg() == 'Off' else 'Off'),
                      {'group': '%s Volume' % zonePrefix, 'title': 'Muting Toggle', 'order': next_seq()})
  
  inputAction, inputSignal = bind_twoway_unitfunc('%s Input' % zonePrefix, '%s Inputs' % zonePrefix, '@%s:INP' % zoneCode, {'type': 'string', 'enum': INPUTS_CODES}, title='Input')
  
  def bindInput(name):
    action = Action('%s Input %s' % (zonePrefix, name), lambda arg: inputAction.call(name), {'group': '%s Inputs' % zonePrefix, 'title': name, 'order': next_seq()})
    signal = Event('%s Input %s' % (zonePrefix, name), {'group': '%s Inputs' % zonePrefix, 'title': name, 'order': next_seq(), 'schema': {'type': 'boolean'}})
    inputSignal.addEmitHandler(lambda arg: signal.emit(arg == name))
  
  # turn into interlocked
  for inputCode in INPUTS_CODES:
    bindInput(inputCode)

# --- operations>

# <protocol ---

resultCallbacks = {} # e.g. {"@MAIN:PWR=", func}

def handle_resp(resp):
  # e.g. @MAIN:PWR=Standby
  
  # look up for callback
  indexOfEquals = resp.find('=')
  if indexOfEquals <= 0:
    # ignore
    log(2, 'handle_resp ignoring [%s]' % resp)
    return
  
  leftSide = resp[:indexOfEquals]
  rightSide = resp[indexOfEquals+1:]
  
  log(2, 'handle_resp got leftSide:[%s] rightSide:[%s]' % (leftSide, rightSide))
  
  callback = resultCallbacks.get(leftSide)
  if callback == None:
    return
  
  callback(rightSide)
  
# examples:
#    tcp_sent [@ZONE2:INP=?]
#    tcp_recv [@ZONE2:INP=AUDIO2]      ---> got leftSide:[@ZONE2:INP] rightSide:[AUDIO2]
#    tcp_sent [@MAIN:VOL=?]
#    tcp_recv [@MAIN:VOL=-20.5]
  
def bind_oneway_unitfunc(name, group, unitFunction, schema, title=None, pollingPeriod=120):
  if title == None:
    title = name
  
  signal = Event(name, {'title': title, 'group': group, 'order': next_seq(), 'schema': schema})
  getter = Action('Get %s' % name, lambda arg: tcp.send(unitFunction + '=?'), {'group': group, 'order': next_seq()})
  resultCallbacks[unitFunction] = lambda result: signal.emit(result)

  Timer(lambda: getter.call(), random(pollingPeriod-15, pollingPeriod+15), random(10,15))
  
def bind_twoway_unitfunc(name, group, unitFunction, schema, title=None, pollingPeriod=120, setterFilter=None, getterFilter=None):
  if title == None:
    title = name
  
  signal = Event(name, {'title': title, 'group': group, 'order': next_seq(), 'schema': schema})
  getter = Action('Get ' + name, lambda arg: tcp.send(unitFunction+'=?'), {'title': 'Get %s' % title, 'group': group, 'order': next_seq()})
    
  setter = Action(name, lambda arg: tcp.send(unitFunction+'=%s' % (arg if not setterFilter else setterFilter(arg))), 
                  {'title': title, 'group': group, 'order': next_seq(), 'schema': schema})
  
  resultCallbacks[unitFunction] = lambda result: signal.emit(result if not getterFilter else getterFilter(result))
  
  Timer(lambda: getter.call(), random(pollingPeriod-15, pollingPeriod+15), random(10,15))
  
  return setter, signal

# --- protocol>

 
# <tcp ---
  
def tcp_connected():
  console.info('tcp_connected')
  tcp.clearQueue()
  
def tcp_received(data):
  log(3, 'tcp_recv [%s]' % data)
  
  # indicate a parsed packet (for status checking)
  lastReceive[0] = system_clock()
  
  handle_resp(data)
  
def tcp_sent(data):
  log(3, 'tcp_sent [%s]' % data)
  
def tcp_disconnected():
  console.warn('tcp_disconnected')
  
def tcp_timeout():
  console.warn('tcp_timeout')

tcp = TCP(connected=tcp_connected, 
          received=tcp_received, 
          sent=tcp_sent, 
          disconnected=tcp_disconnected, 
          sendDelimiters='\r\n',
          timeout=tcp_timeout)

# --- tcp>


# <logging ---

local_event_LogLevel = LocalEvent({'group': 'Debug', 'order': 10000+next_seq(), 'schema': {'type': 'integer'}})

def warn(level, msg):
  if local_event_LogLevel.getArg() >= level:
    console.warn(('  ' * level) + msg)

def log(level, msg):
  if local_event_LogLevel.getArg() >= level:
    console.log(('  ' * level) + msg)    

# --->


# <status and error reporting ---

local_event_LastCommsErrorTimestamp = LocalEvent({'title': 'Last Comms Error Timestamp', 'group': 'Status', 'order': 99999+next_seq(), 'schema': {'type': 'string'}})

# for comms drop-out
lastReceive = [0]

# roughly, the last contact  
local_event_LastContactDetect = LocalEvent({'group': 'Status', 'order': 99999+next_seq(), 'title': 'Last contact detect', 'schema': {'type': 'string'}})

# node status
local_event_Status = LocalEvent({'group': 'Status', 'order': 99999+next_seq(), 'schema': {'type': 'object', 'properties': {
        'level': {'type': 'integer', 'order': 1},
        'message': {'type': 'string', 'order': 2}}}})
  
def statusCheck():
  diff = (system_clock() - lastReceive[0])/1000.0 # (in secs)
  now = date_now()
  
  if diff > status_check_interval+15:
    previousContactValue = local_event_LastContactDetect.getArg()
    
    if previousContactValue == None:
      message = 'Always been missing.'
      
    else:
      previousContact = date_parse(previousContactValue)
      roughDiff = (now.getMillis() - previousContact.getMillis())/1000/60
      if roughDiff < 60:
        message = 'Missing for approx. %s mins' % roughDiff
      elif roughDiff < (60*24):
        message = 'Missing since %s' % previousContact.toString('h:mm:ss a')
      else:
        message = 'Missing since %s' % previousContact.toString('h:mm:ss a, E d-MMM')
      
    local_event_Status.emit({'level': 2, 'message': message})
    
  else:
    # update contact info
    local_event_LastContactDetect.emit(str(now))
    
    # TODO: check internal device status if possible

    local_event_LastContactDetect.emit(str(now))
    local_event_Status.emit({'level': 0, 'message': 'OK'})
    
status_check_interval = 75
status_timer = Timer(statusCheck, status_check_interval)

# --->

# <! UPnP discovery ----

local_event_DiscoveredIPAddress = LocalEvent({'group': 'Discovery', 'schema': {'type': 'string'}})

from urlparse import urlparse

def remote_event_UPnPBeacon(arg):
  # look for IP address
  presURL = arg.get('presentationurl') # e.g. "http://192.168.178.65/"
  if presURL == None:
    return
  
  result = urlparse(presURL)

  # safe to keep setting the address (column 1)
  ipAddress = result[1]
  
  local_event_DiscoveredIPAddress.emit(ipAddress)
  
  tcp.setDest('%s:%s' % (ipAddress, YNCA_TCPPORT))

# ! UPnP ----!>


# <convenience methods ---

def getOrDefault(value, default):
  return default if value == None or is_blank(value) else value

from java.util import Random
_rand = Random()

# returns a random number between an interval
def random(fromm, to):
  return fromm + _rand.nextDouble()*(to - fromm)

# --->
