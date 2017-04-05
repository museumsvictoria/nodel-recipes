import random

# show debugging information
showDebug = Event('Show Debug', {'title': 'Show Debug', 'group': 'Debug', 'order': next_seq(), 'schema': {'type': 'boolean'}})

UDP_PORT = 161

param_disabled = Parameter({'title': 'Disabled', 'schema': {'type': 'boolean'}})

param_ipAddress = Parameter({'title': 'IP address', 'schema': {'type': 'string'}})

param_outlets = Parameter({'title': 'Outlets', 'schema': {'type': 'array', 'items': {
        'type': 'object', 'title': 'Outlet', 'properties': {
          'num': {'type': 'integer', 'title': 'Outlet number', 'desc': 'Greater than 0', 'order': next_seq()},
          'label': {'type': 'string', 'title': 'Label', 'order': next_seq()}
        } } }})

# general device status
local_event_Status = LocalEvent({'order': -100, 'schema': {'type': 'object', 'title': 'Status', 'properties': {
        'level': {'type': 'integer', 'title': 'Level'},
        'message': {'type': 'string', 'title': 'Message'}
      }}})

# the minimum gap between requests (sets or gets) (milliseconds)
MIN_GAP_MS = 800

# the gap between ensuring a state (seconds)
ENSURE_GAP = 20

# every 5 mins
SLOW_GET_INTERVAL = 5*60

# the last time *anything* was sent to the unit
lastSend = [0]
lastReceive = [0]

def main():
  for info in param_outlets or []:
    bindOutlet(info)
    
  if param_disabled == True:
    console.warn('"Disabled" is true; not starting.')
  
  udp.setDest('%s:%s' % (param_ipAddress, UDP_PORT))
  
  console.info('Node started!')


def bindOutlet(info):
  print 'Binding %s' % info
  
  num = info['num']
  label = info['label']
  
  name = 'Outlet %s' % num
  
  if len(label or '') > 0:
    group = 'Outlet %s ("%s")' % (num, label)
    label = '"%s"' % label
  else:
    label = 'Outlet %s' % num
    group = label
  
  desiredState = Event('%s Desired State' % name, {'title': 'Desired State', 'group': group, 'order': next_seq(), 'schema': {'type': 'string', 'enum': ['On', 'Off', 'Unchanged']}})
  
  state = Event('%s State' % name, {'title': 'State', 'group': group, 'order': next_seq(), 'schema': {'type': 'string', 'enum': ['On', 'Off', 'Unchanged']}})
  
  # triggers a state request 
  def getter():
    debug(num, 'Getting state...')
    get_state(num)  
  
  getterTimer = Timer(getter, SLOW_GET_INTERVAL, 10 + random.random()*10)
  getterTimer.start()
  
  def ensurer(ttl):
    d, s = desiredState.getArg(), state.getArg()
    if d == None or d == s:
      debug(num, 'desired state has been matched or is empty')
      getterTimer.setInterval(SLOW_GET_INTERVAL)
      return
    
    # 'd' is different to 's'
    
    # check time since last send
    diff = system_clock() - lastSend[0]
    
    if diff < MIN_GAP_MS:
      # try again when the min gap
      debug(num, 'min gap is not enough (diff:%s)' % diff)
      call_safe(lambda: ensurer(ttl), (MIN_GAP_MS-diff)/1000.0)
      return
    
    if d == 'On':
      code = ON
    elif d == 'Off':
      code = OFF
    else:
      return
    
    set_state(num, code)
    
    # check next 2 seconds and then every 10
    getterTimer.setDelayAndInterval(2, 10)
    
    # give it a while before checking again
    newTTL = ttl - 1
    if newTTL >= 0:
      call_safe(lambda: ensurer(newTTL-1), ENSURE_GAP)
    else:
      console.warn('Gave up ensuring state (%s) of outlet %s' % (d, num))
  
  def setter(state):
    desiredState.emit(state)
    
    call_safe(lambda: ensurer(4)) # give it 4 opportunities
  
  control = Action('%s State' % name, setter, {'title': 'State', 'group': group, 'order': next_seq(), 'Caution': 'This affects power - please ensure equipment can be safely turned on or off right now.', 'schema': {'type': 'string', 'enum': ['On', 'Off']}})


def udp_received(src, data):
  debug('UDP_RECV', '[%s]' % data.encode('hex'))
  
  lastReceive[0] = system_clock()
  
  oidPos = data.find(OID_RAW)
  
  if oidPos < 0:
    debug('UDP_RECV', 'no OID found in response')
    return
  
  if VAR_INT_RAW != data[-3:-1]:
    debug('UDP_RECV', 'VAR_INT token not in response')
    return
  
  outletNumChar = data[-4:-3]
  
  codeChar = data[-1:]
  
  if codeChar == '' or outletNumChar == '':
    debug('UDP_RECV', 'Could not determine code or outlet number')
    return
  
  outletNum = ord(outletNumChar)
  code = ord(codeChar)
  
  if code == ON:
    state = 'On'
  elif code == OFF:
    state = 'Off'
  else:
    state = 'Unknown'
    
  e = lookup_local_event('Outlet %s State' % outletNum)
  if e == None:
    console.warn('Got a response from an unexpected outlet - #%s' % outletNum)
    return
  
  e.emit(state)
                 
  
def udp_sent(data):
  debug('UDP_SENT', '[%s]' % data.encode('hex'))

udp = UDP(received=udp_received, sent=udp_sent)

def get_state(outlet):
  packet = GET_PACKET_HEAD + '%02x' % outlet + GET_TAIL
  udp.send(packet.decode('hex'))
  
def set_state(outlet, state):
  packet = SET_PACKET_HEAD + '%02x' % outlet + VAR_INT + '%02x' % state
  udp.send(packet.decode('hex'))

# roughly, the last contact  
local_event_LastContactDetect = LocalEvent({'group': 'Status', 'title': 'Last contact detect', 'schema': {'type': 'string'}})
  
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
      message = 'Missing for approx. %s minutes' % roughDiff
      
    local_event_Status.emit({'level': 2, 'message': message})
    
  else:
    local_event_LastContactDetect.emit(str(now))
    local_event_Status.emit({'level': 0, 'message': 'OK'})
    
status_check_interval = SLOW_GET_INTERVAL+15
status_timer = Timer(statusCheck, status_check_interval)
    
# constants ----
  
ON = 1
OFF = 2
OID = "2b06010401823e01010404020103"
OID_RAW = OID.decode('hex')
SET_PACKET_HEAD = "3030020100040770726976617465a3220202000102010002010030163014060f" + OID
GET_PACKET_HEAD = "302f020100040770726976617465a0210202000102010002010030153013060f" + OID
GET_TAIL = "0500"
VAR_INT = "0201"
VAR_INT_RAW = VAR_INT.decode('hex')

# convenience functions
def debug(context, msg):
  if showDebug.getArg() == True:
    console.log('%s: %s' % (context, msg))
 