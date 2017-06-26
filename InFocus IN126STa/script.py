'Link to manual - http://www.infocus.com/resources/documents/IN11xa-IN12xa-IN212xa%20RS232.pdf'

DEFAULT_ADMINPORT = 10008

# Extron Bridge 2001 - 2004

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

def powerHandler(state=''):
  if state.lower() == 'on':
    local_event_DesiredPower.emit('On')
    setPowerState(True)
    
  elif state.lower() == 'off':
    local_event_DesiredPower.emit('Off')
    setPowerState(False)
    
  else:
    console.warn('Unknown power state specified, must be On or Off')
    return
  
  local_event_LastPowerRequest.emit(str(date_now()))

Action('Power', powerHandler, {'schema': {'type': 'string', 'enum': ['On', 'Off']}, 'group':'Power'})

def handlePowerResp(resp):
  arg = cleanResponse(resp)
  
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
  tcp.send('(PWR%s)' % ('1' if state else '0'))
    
def getPowerState(arg):
  tcp.request('(PWR?)', handlePowerResp)  

Action('GetPower', getPowerState, {'group': 'Status'})

# general protocol related

def cleanResponse(data):
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
  lookup_local_action('Power').call(arg)  