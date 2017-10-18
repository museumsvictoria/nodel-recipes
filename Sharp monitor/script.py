'Link to manual (protocol starts on page 33) - http://siica.sharpusa.com/portals/0/downloads/Manuals/PN_R603_R703_Operation_Manual.pdf'

DEFAULT_ADMINPORT = 10008

param_ipAddress = Parameter({'title': 'IP address', 'schema': {'type': 'string'}})
param_adminPort = Parameter({'title': 'Admin port', 'schema': {'type': 'integer', 'hint': DEFAULT_ADMINPORT}})
param_password = Parameter({'title': 'Password', 'schema': {'type': 'string'}})
param_username = Parameter({'title': 'Username', 'schema': {'type': 'string'}})

local_event_DebugShowLogging = LocalEvent({'group': 'Debug', 'schema': {'type': 'boolean'}})

# general device status
local_event_Status = LocalEvent({'order': -100, 'group': 'Status', 'schema': {'type': 'object', 'title': 'Status', 'properties': {
        'level': {'type': 'integer', 'title': 'Value'},
        'message': {'type': 'string', 'title': 'String'}
      }}})

statusInfo = { 'lastError': 0,
                   'error': 'None',
                  'lastOK': system_clock() }

def handleStatusCheck():
  if statusInfo['lastError'] > statusInfo['lastOK']:
    local_event_Status.emitIfDifferent({'level': 2, 'message': statusInfo['error'] or 'Error'})
    
  else:
    local_event_Status.emitIfDifferent({'level': 0, 'message': 'OK'})
    
timer_statusCheck = Timer(handleStatusCheck, 30)

POWER_STATES = ['On', 'Input Waiting', 'Unknown', 'Turning On', 'Turning Off', 'Off']
local_event_Power = LocalEvent({'title': 'Power', 'group': 'Power', 'order': next_seq(), 'schema': {'type': 'string', 'enum': POWER_STATES}})
local_event_DesiredPower = LocalEvent({'title': 'Desired Power', 'group': 'Power', 'order': next_seq(), 'schema': {'type': 'string', 'enum': ['On', 'Off']}}) 
local_event_LastPowerRequest = LocalEvent({'title': 'Last request', 'group': 'Power', 'order': next_seq(), 'schema': {'type': 'string'}}) 

INPUTS_TABLE = [ ('DVI-I',         1),
                 ('D-SUB[RGB]',    2),
                 ('D-SUB[COMPONENT]', 3),
                 ('D-SUB[VIDEO]', 4),
                 ('HDMI1[AV]',    9),
                 ('HDMI1[PC]',    10),
                 ('HDMI2[AV]',    12),
                 ('HDMI2[PC]',    13),
                 ('DisplayPort',  14) ]
INPUTS_STR = [row[0] for row in INPUTS_TABLE]
INPUTS_STR.append('Unknown')

INPUTNAMES_byCode = {}
for row in INPUTS_TABLE:
  INPUTNAMES_byCode[row[1]] = row[0]
  
INPUTCODES_byName = {}
for row in INPUTS_TABLE:
  INPUTCODES_byName[row[0]] = row[1]

# local_event_Input = LocalEvent({'title': 'Input', 'group': 'Input', 'order': next_seq(), 'schema': {'type': 'string', 'enum': INPUTS_STR}})

local_event_InputCode = LocalEvent({'title': 'Actual', 'group': 'Input Code', 'order': next_seq(), 'schema': {'type': 'integer'}})
local_event_DesiredInputCode = LocalEvent({'title': 'Desired', 'group': 'Input Code', 'order': next_seq(), 'schema': {'type': 'integer'}})
local_event_LastInputCodeRequest = LocalEvent({'title': 'Last request', 'group': 'Input Code', 'order': next_seq(), 'schema': {'type': 'string'}}) 

ZERO_DATE_STR = str(date_instant(0))

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

Action('Power', powerHandler, {'schema': {'type': 'string', 'enum': ['On', 'Off']}})

def handlePowerResp(resp):
  arg = cleanSharpResponse(resp)
  
  statusInfo['lastOK'] = system_clock()
  
  if arg == '1':
    local_event_Power.emit('On')
      
  elif arg == '0':
    local_event_Power.emit('Off')
      
  elif arg == '2':
    local_event_Power.emit('Input Waiting')
      
  else:
    local_event_Power.emit('Unknown')
    
def setPowerState(state):
  tcp.send('POWR000%s' % ('1' if state else '0'))
    
def getPowerState():
  tcp.request('POWR   ?', handlePowerResp)
  
timer_powerPoller = Timer(getPowerState, 15.0)  
  
def syncPower():
  last = date_parse(local_event_LastPowerRequest.getArg() or ZERO_DATE_STR)
  if date_now().getMillis() - last.getMillis() > 60000:
    return
  
  desired = local_event_DesiredPower.getArg()
  actual = local_event_Power.getArg()
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
  
Action('Input Code', inputCodeHandler, {'schema': {'type': 'integer'}})

def handleInputCodeResp(resp):
  arg = cleanSharpResponse(resp)
  
  local_event_InputCode.emit(int(arg))
    
def setInputCode(code):
  tcp.send('INPS00%s' % (code if code >= 10 else '0%s' % code))
    
def getInputCode():
  tcp.request('INPS   ?', handleInputCodeResp)
  
timer_inputCodePoller = Timer(getInputCode, 15.0)  
  
def syncInputCode():
  last = date_parse(local_event_LastInputCodeRequest.getArg() or ZERO_DATE_STR)
  if date_now().getMillis() - last.getMillis() > 60000:
    return
  
  desired = local_event_DesiredInputCode.getArg()
  actual = local_event_InputCode.getArg()
  if desired == actual:
    # nothing to do
    timer_inputCodeSyncer.setInterval(120)
    return
  
  setInputCode(desired)
    
  timer_inputCodeSyncer.setDelay(15.0)  

timer_inputCodeSyncer = Timer(syncInputCode, 60.0)


# general protocol related

# sharp response can be:
# '0' - No set ID
# '0 004' - using set ID
def cleanSharpResponse(data):
  parts = data.split(' ')

  if len(parts) == 1:
    return data
  else:
    # strip out the last part
    return data[:data.rfind(' ')]


# TCP related

def connected():
  console.info('TCP connected')
      
def disconnected():
  console.info('TCP disconnected')
  
def timeout():
  statusInfo['lastError'] = system_clock()
  statusInfo['error'] = 'Comms timeout'
  
def received(line):
  if local_event_DebugShowLogging.getArg():
    console.info('RECV: [%s]' % line)
  
  if line == 'Login':
    tcp.send(param_username or '\r')
    
  elif line == 'Password':
    tcp.request(param_password or '\r', handlePasswordResp)

def handlePasswordResp(resp):
  if resp != 'OK':
    statusInfo['error'] = 'Authentication Failure'
    statusInfo['lastError'] = system_clock()    
    
def sent(line):
  if local_event_DebugShowLogging.getArg():
    console.info('SENT: [%s]' % line)

# maintain a TCP connection
tcp = TCP(connected=connected, disconnected=disconnected, 
          received=received, sent=sent, timeout=timeout,
          receiveDelimiters='\r\n:', # including ':'
          sendDelimiters='\r')

def main(arg=None):
  print 'Nodel script started.'
  
  dest = '%s:%s' % (param_ipAddress, param_adminPort or DEFAULT_ADMINPORT)
  console.log('Connecting to %s...' % dest)

  tcp.setDest(dest)
  
  
# for acting as a power slave
def remote_event_Power(arg):
  lookup_local_action('power').call(arg)  