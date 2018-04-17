'No direct network port available. Link to manual (see page 71) - http://www.lg.com/us/commercial/documents/MAN_SE3B_SE3KB_SL5B.pdf'

DEFAULT_ADMINPORT = 9761
DEFAULT_BROADCASTIP = '192.168.1.255'

# general device status
local_event_Status = LocalEvent({'order': -100, 'group': 'Status', 'schema': {'type': 'object', 'title': 'Status', 'properties': {
        'level': {'type': 'integer', 'title': 'Value'},
        'message': {'type': 'string', 'title': 'String'}
      }}})

DEFAULT_SET_ID = '001' # sometime this is 01

param_ipAddress = Parameter({'title': 'IP address', 'schema': {'type': 'string'}})
param_setID = Parameter({'title': 'Set ID', 'schema': {'type': 'string', 'hint': DEFAULT_SET_ID}})
param_broadcastIPAddress = Parameter({'title': 'Broadcast IP address', 'schema': {'type': 'string', 'hint': DEFAULT_BROADCASTIP}})
param_adminPort = Parameter({'title': 'Admin port', 'schema': {'type': 'integer', 'hint': DEFAULT_ADMINPORT}})
param_macAddress = Parameter({'title': 'MAC address', 'schema': {'type': 'string'}})

wol = UDP( # dest='10.65.255.255:9999' % , # set after main
          sent=lambda arg: console.info('wol: sent [%s]' % arg),
          ready=lambda: console.info('wol: ready'), received=lambda arg: console.info('wol: received [%s]'))

local_event_DebugShowLogging = LocalEvent({'group': 'Debug', 'order': 9999, 'schema': {'type': 'boolean'}})

POWER_STATES = ['On', 'Input Waiting', 'Unknown', 'Turning On', 'Turning Off', 'Off']
local_event_Power = LocalEvent({'title': 'Power', 'group': 'Power', 'order': next_seq(), 'schema': {'type': 'string', 'enum': POWER_STATES + ['Partially On', 'Partially Off']}})
local_event_RawPower = LocalEvent({'title': 'Raw', 'group': 'Power', 'order': next_seq(), 'schema': {'type': 'string', 'enum': POWER_STATES}})
local_event_DesiredPower = LocalEvent({'title': 'Desired', 'group': 'Power', 'order': next_seq(), 'schema': {'type': 'string', 'enum': ['On', 'Off']}}) 
local_event_LastPowerRequest = LocalEvent({'title': 'Last request', 'group': 'Power', 'order': next_seq(), 'schema': {'type': 'string'}}) 

INPUTS_TABLE = [ ('RGB', '60'),
                 ('DVI-D (PC)', '70'),
                 ('DVI-D (DTV)', '80'),
                 ('HDMI (HDMI1) (DTV)', '90'),
                 ('HDMI (HDMI1) (PC)', 'A0') ]
INPUTS_STR = [row[0] for row in INPUTS_TABLE]
INPUTS_STR.append('Unknown')

INPUTNAMES_byCode = {}
for row in INPUTS_TABLE:
  INPUTNAMES_byCode[row[1]] = row[0]
  
INPUTCODES_byName = {}
for row in INPUTS_TABLE:
  INPUTCODES_byName[row[0]] = row[1]

# local_event_Input = LocalEvent({'title': 'Input', 'group': 'Input', 'order': next_seq(), 'schema': {'type': 'string', 'enum': INPUTS_STR}})

local_event_InputCode = LocalEvent({'title': 'Actual', 'group': 'Input Code', 'order': next_seq(), 'schema': {'type': 'string'}})
local_event_DesiredInputCode = LocalEvent({'title': 'Desired', 'group': 'Input Code', 'order': next_seq(), 'schema': {'type': 'string'}})
local_event_LastInputCodeRequest = LocalEvent({'title': 'Last request', 'group': 'Input Code', 'order': next_seq(), 'schema': {'type': 'string'}}) 

ZERO_DATE_STR = str(date_instant(0))

setID = DEFAULT_SET_ID

# Power signal needs special handling because the panels drop off the network when 
# they're turned off
@after_main
def attachPowerEmitHandlers():
  raw = lookup_local_event('Raw Power')
  desired = lookup_local_event('Desired Power')
  power = lookup_local_event('Power')
  
  def handler(arg):
    rawValue = raw.getArg()
    desiredValue = desired.getArg()
    
    if desiredValue == 'On':
      if rawValue == 'Off':
        power.emit('Partially On')
      else:
        # pass through the raw value
        power.emit(rawValue)
      
    elif desiredValue == 'Off':
      if rawValue == 'On':
        power.emit('Partially Off')
      else:
        # the raw value could be UNKNOWN or OFF here because
        # they disappear off the network
        power.emit('Off')
        
  # attach handlers
  desired.addEmitHandler(handler)
  raw.addEmitHandler(handler)

def powerHandler(state=''):
  if state.lower() == 'on':
    local_event_DesiredPower.emit('On')
    
  elif state.lower() == 'off':
    local_event_DesiredPower.emit('Off')
    
  else:
    console.warn('Unknown power state specified, must be On or Off')
    return
  
  local_event_LastPowerRequest.emit(str(date_now()))
  
  timer_powerSyncer.setDelay(0.3)

Action('Power', powerHandler, {'group': 'Power', 'schema': {'type': 'string', 'enum': ['On', 'Off']}})

# NOTE ABOUT POWER: 
#       This uses the 'SCREEN OFF' command as opposed to the 'POWER' command so
#       the arguments needs to be interpretted within that context. At first glance
#       may seem flipped.
  

# e.g. 'a 01 OK01x'
def handlePowerResp(data):
  if data == '00':    # yes, '00' for ON! (see important note above)
    local_event_RawPower.emit('On') 
    
  elif data == '01':  # yes, '01' for OFF! (see important note above)
    local_event_RawPower.emit('Off')
      
  else:
    local_event_RawPower.emit('Unknown-%s' % data)

def setPowerState(state):
  log('setPowerState(%s) called' % state)
  
  if state:
    cmd = '00' # yes, '00' for OFF! (see note above)
  else:
    cmd = '01' 
    
  # Using the "Screen Power = Off" command here NOT the main Power command
  # otherwise risk the power going off for good (WOL can be very flakey)
  tcp.request('kd %s %s\r' % (setID, cmd), 
              lambda resp: checkHeaderAndHandleData(resp, 'd', handlePowerResp))
  
  # when turning on, do a few more things for good measure
  if state: # (turn on)
    # try WOL too
    lookup_local_action("Send WOL Packet").call()
    
    # and try Mains Power on
    lookup_local_action("Main Power").call('On')
    
  else: # (turn off)
    tcp.send('kd %s %s' % (setID, '01')) 
    
def getPowerState():
  log('getPowerState called')

  # this actually polls the 'SCREEN OFF' state
  tcp.request('kd %s ff\r' % setID, 
              lambda resp: checkHeaderAndHandleData(resp, 'd', handlePowerResp))
  
timer_powerPoller = Timer(getPowerState, 15.0)
  
def syncPower():
  log('syncPower called')
  
  last = date_parse(local_event_LastPowerRequest.getArg() or ZERO_DATE_STR)
  if date_now().getMillis() - last.getMillis() > 60000:
    return
  
  desired = local_event_DesiredPower.getArg()
  actual = local_event_RawPower.getArg()
  if desired == actual:
    # nothing to do
    timer_powerSyncer.setInterval(120)
    return
  
  if desired == 'On':
    setPowerState(True)
  elif desired == 'Off':
    setPowerState(False)
    
  timer_powerSyncer.setDelay(15.0)  

timer_powerSyncer = Timer(syncPower, 60.0)




def inputCodeHandler(code):
  local_event_DesiredInputCode.emit(code)
  local_event_LastInputCodeRequest.emit(str(date_now()))
  
  timer_inputCodeSyncer.setDelay(0.3)
  
Action('Input Code', inputCodeHandler, {'group': 'Input Code', 'schema': {'type': 'string'}})

def handleInputCodeResp(arg):
  local_event_InputCode.emit(int(arg))
    
def setInputCode(code):
  log('setInputCode(%s) called' % code)
  
  tcp.send('xb %s %s' % (setID, code))
  
    
def getInputCode():
  if local_event_RawPower.getArg() != 'On':
    log('Power is not On; ignoring input get request')
    return
  
  getInputCodeNow()
    
def getInputCodeNow():
  log('getInputCodeNow called')
  
  # e.g. resp: 'b 01 OK90'

  def handleData(data):
    local_event_InputCode.emit(data)

  tcp.request('xb %s ff\r' % setID, 
              lambda resp: checkHeaderAndHandleData(resp, 'b', handleData))
  
timer_inputCodePoller = Timer(getInputCode, 15.0, 20.0)  
  
def syncInputCode():
  log('syncInputCode called')
  last = date_parse(local_event_LastInputCodeRequest.getArg() or ZERO_DATE_STR)
  if date_now().getMillis() - last.getMillis() > 60000:
    return
  
  desired = local_event_DesiredInputCode.getArg()
  actual = local_event_InputCode.getArg()
  if desired == actual:
    # nothing to do
    timer_inputCodeSyncer.setInterval(120)
    return
  
  if local_event_RawPower.getArg() != 'On':
    console.log('Power is not on; ignoring input set request')
    return
  
  setInputCode(desired)
    
  timer_inputCodeSyncer.setDelay(15.0)  

timer_inputCodeSyncer = Timer(syncInputCode, 60.0)

SETTINGS_GROUP = "Settings & Info"

# Serial number ---

Event('Serial Number', {'group': SETTINGS_GROUP, 'order': next_seq(), 'schema': {'type': 'string'}})
Action('Get Serial Number', lambda arg: tcp.request('fy %s ff\r' % setID, lambda resp: checkHeaderAndHandleData(resp, 'y', lambda data: lookup_local_event('Serial Number').emit(data))), 
       {'group': SETTINGS_GROUP, 'order': next_seq()})

Timer(lambda: lookup_local_action('Get Serial Number').call(), 15, 5*60)


# Temperature ---

Event('Temperature', {'desc': 'Inside temperature', 'group': SETTINGS_GROUP, 'order': next_seq(), 'schema': {'type': 'integer'}})
Action('Get Temperature', lambda arg: tcp.request('dn %s ff\r' % setID, lambda resp: checkHeaderAndHandleData(resp, 'n', lambda data: lookup_local_event('Temperature').emit(int(data, 16)))), 
       {'group': SETTINGS_GROUP, 'order': next_seq()})

Timer(lambda: lookup_local_action('Get Temperature').call(), 15, 5*60)


# Main Power ---

Event('Main Power', {'group': SETTINGS_GROUP, 'order': next_seq(), 'schema': {'type': 'string', 'enum': ['On', 'Off']}})
Action('Get Main Power', lambda arg: tcp.request('ka %s ff\r' % setID, lambda resp: checkHeaderAndHandleData(resp, 'a', lambda data: lookup_local_event('Main Power').emit('Off' if data == '00' else ('On' if data == '01' else 'Unknown %s' % data)))), 
       {'group': SETTINGS_GROUP, 'order': next_seq()})

def handleMainPowerSet(arg):
  if arg == 'On':
    cmd = '01'
  elif arg == 'Off':
    cmd = '00'
  else:
    raise Exception('Unknown MainPower state %s' % arg)
    
  tcp.request('ka %s %s\r' % (setID, cmd), 
              lambda resp: checkHeaderAndHandleData(resp, 'a', lambda data: lookup_local_event('Main Power').emit('Off' if data == '00' else ('On' if data == '01' else 'Unknown %s' % data))))

Action('Main Power', handleMainPowerSet, {'group': SETTINGS_GROUP, 'order': next_seq(), 'schema': {'type': 'string', 'enum': ['On', 'Off']}})
  
Timer(lambda: lookup_local_action('Get Main Power').call(), 15, 5*60)


# Automatic Standy ---

Event('Automatic Standy', {'group': SETTINGS_GROUP, 'order': next_seq(), 'schema': {'type': 'string'}})
Action('Get Automatic Standy', lambda arg: tcp.request('mn %s ff\r' % setID, lambda resp: checkHeaderAndHandleData(resp, 'n', lambda data: lookup_local_event('Automatic Standy').emit(data))), 
       {'group': SETTINGS_GROUP, 'order': next_seq()})

Action('Automatic Standy', lambda arg: tcp.request('mn %s %s\r' % (setID, cmd), lambda resp: checkHeaderAndHandleData(resp, 'n', lambda data: lookup_local_event('Automatic Standy').emit(data))),
       {'group': SETTINGS_GROUP, 'order': next_seq(), 'schema': {'type': 'string', 'enum': ['00', '01', '02', '03']}})
  
Timer(lambda: lookup_local_action('Get Automatic Standy').call(), 15, 5*60)


# LG protocol specific
def checkHeaderAndHandleData(resp, cmdChar, dataHandler):
  # e.g. 'a 01 OK01x'
  
  # Would like to check for x but delimeters are filtered out
  # if resp[-1:]  != 'x':
  #   console.warn('End-of-message delimiter "x" was missing')
  #   return
  
  if len(resp) < 2:
    console.warn('Response was missing or too small')
    return
  
  if resp[0] != cmdChar:
    console.warn('Response did not match expected command (expected "%s", got "%s")' % (cmdChar, resp[0]))
    return
    
  if not 'OK' in resp:
    console.warn('Response is not positive acknowledgement (no "OK")')
    return
  
  # get the data between the OK and the 'x'
  dataPart = resp[resp.find('OK')+2:]
  
  if dataHandler:
    dataHandler(dataPart)


# TCP related

def connected():
  console.info('TCP CONNECTED')
  
  # flush the request queue
  tcp.clearQueue()
      
def disconnected():
  console.info('TCP DISCONNECTED')
  
  # immediately trip this value
  local_event_RawPower.emit('Unknown')
  
def timeout():
  log('timeout')
  
  # flush the request queue
  tcp.clearQueue()
  
  local_event_RawPower.emit('Unknown')
  
def received(line):
  lastReceive[0] = system_clock()
  
  log('RECV: [%s]' % line)
    
def sent(line):
  log('SENT: [%s]' % line)

# maintain a TCP connection
tcp = TCP(connected=connected, disconnected=disconnected, 
          received=received, sent=sent, timeout=timeout,
          receiveDelimiters='\r\nx', # notice the 'x' at the end of all responses
          sendDelimiters='\r')

def main(arg = None):
  console.info('Script started')
  
  global setID
  if param_setID != None and len(param_setID) > 0:
    setID = param_setID
  
  dest = '%s:%s' % (param_ipAddress, param_adminPort or DEFAULT_ADMINPORT)
  console.log('Connecting to %s...' % dest)
  tcp.setDest(dest)
  
  # set WOL dest which can only be done during 'main'
  wol.setDest('%s:9999' % param_broadcastIPAddress)
  
def log(data):
  if local_event_DebugShowLogging.getArg():
    console.info(data)

def local_action_SendWOLPacket(arg=None):
  """{"title": "Send", "group": "Wake-on-LAN"}"""
  console.info('SendWOLPacket')
  
  hw_addr = param_macAddress.replace('-', '').replace(':', '').decode('hex')
  macpck = '\xff' * 6 + hw_addr * 16
  wol.send(macpck)

# for status checks
lastReceive = [0]

# roughly, the last contact  
local_event_LastContactDetect = LocalEvent({'group': 'Status', 'title': 'Last contact detect', 'schema': {'type': 'string'}})
  
def statusCheck():
  diff = (system_clock() - lastReceive[0])/1000.0 # (in secs)
  now = date_now()
  
  if diff > status_check_interval+15:
    # Now using "SCREEN OFF" command which does not disrupt po
    # so section below is now commented out
    
    # these panels often turn off their network on power off
    # if local_event_Power.getArg() == 'Off':
    #   local_event_Status.emit({'level': 0, 'message': 'OK (missing but likely Off)'})
    #   return
    
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
    local_event_LastContactDetect.emit(str(now))
    local_event_Status.emit({'level': 0, 'message': 'OK'})
    
status_check_interval = 75
status_timer = Timer(statusCheck, status_check_interval)
  
# for acting as a power slave
def remote_event_Power(arg):
  lookup_local_action('power').call(arg)
