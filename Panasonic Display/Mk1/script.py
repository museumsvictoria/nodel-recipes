'''Basic, limited Panasonic protocol, suitable for some Panasonic displays, will be expaned over time.'''

# taken from page 18:
# - https://bizpartner.panasonic.net/public/system/files/files/fields/field_file/psd/2014/11/20/lf6_lf60u_manual_en_1416462484.pdf
# - https://panasonic.biz/cns/prodisplays/support/commandlist/LF20_SerialCommandList.pdf

# Protocol basics:
# \x02 _______ \x3
#      PON         : power on
#      POFF        : power off
#      QPW         : query power
#           QPW:1  : response: Power is on!
#           QPW:0  : response: Power is off!
#      IMS:HM1     : toggle HDMI
#      QMI         : query source
#          QMI:HM1 : response: HDMI1
#      QSF         # signal check
#          QSF:M--------------------    # no signal
#          QSF:M-1125(1080)/50p         # signal
#      

param_disabled = Parameter({'title':'Disabled?', 'order': next_seq(), 'schema': { 'type': 'boolean' }})
param_ipAddress = Parameter({'title':'IP address', 'order': next_seq(), 'schema': { 'type': 'string' }})

DEFAULT_PORT = 1024
param_port = Parameter({'title': 'Port', 'order': next_seq(), 'schema': { 'type':'integer', 'hint': '(default %s)' % DEFAULT_PORT }})

DEFAULT_USERNAME = 'admin1'
param_username = Parameter({'order': next_seq(), 'schema': {'type': 'string', 'hint': '(default %s)' % DEFAULT_USERNAME}})

DEFAULT_PASSWORD = 'panasonic'
param_password = Parameter({'order': next_seq(), 'schema': {'type': 'string', 'hint': '(default %s)' % DEFAULT_PASSWORD}})

local_event_RawPower = LocalEvent({'group': 'Power', 'schema': {'type': 'string', 'enum': ['On', 'Off']}})
local_event_DesiredPower = LocalEvent({'group': 'Power', 'schema': {'type': 'string', 'enum': ['On', 'Off']}})
local_event_Power = LocalEvent({'group': 'Power', 'schema': {'type': 'string', 'enum': ['On', 'Partially On', 'Partially Off', 'Off']}})

local_event_TCPState = LocalEvent({'title': 'TCP state', 'order': 1, 'group': 'TCP', 'schema': {'type': 'string', 'order': 1, 'enum': ['Connected', 'Disconnected']}})

import hashlib # for authentication

def main():
  if param_disabled or len((param_ipAddress or '').strip()) == 0:
    console.warn('Disabled or no IP address set; nothing to do.')
    return
  
  dest = '%s:%s' % (param_ipAddress, param_port or DEFAULT_PORT)
  console.info('Will establish connection to %s' % dest)
  
  tcp.setDest(dest)
  
def local_action_Power(arg=None):
  '{"group": "Power", "schema": {"type": "string", "enum": ["On", "Off"]}}'
  if arg not in ['On', 'Off']:
    raise Exception('Power arg must be On or Off')
  
  local_event_DesiredPower.emit(arg)
  
  timer_powerSyncer.setDelay(0.001)  
  
@local_action({'group': 'Power', 'order': next_seq()})  
def syncPower():
  lastSet = lookup_local_action('Power').getTimestamp() or date_parse('1990')
  
  # only keep trying if we're within 1 minute of the request
  if (date_now().getMillis() - lastSet.getMillis()) > 60000:
    log(2, '(POWER: been more than 60s; nothing to do)')
    return
  
  arg = local_event_DesiredPower.getArg()
  raw = local_event_RawPower.getArg()
  
  if arg == raw:
    log(2, '(POWER: desired and raw are both "%s"; nothing to do)' % arg)
    return
  
  log(2, 'POWER: forcing power to %s' % arg)
  
  if arg == 'On':
    makeRequest('PON', handle_powerResp)
    
  elif arg == 'Off':
    makeRequest('POF', handle_powerResp)
  
timer_powerSyncer = Timer(lambda: syncPower.call(), 10, 0)  
  
def handle_powerResp(resp):
  if resp in ['QPW:1', 'PON', '1']:
    local_event_RawPower.emit('On')
      
  elif resp in ['QPW:0', 'POF', '0']:
    local_event_RawPower.emit('Off')
      
  else:
    console.warn('Unexpected feedback from power request. resp:[%s]' % resp)

@local_action({'group': 'Power', 'order': next_seq()})
def PollPower(arg=None):
  makeRequest('QPW', handle_powerResp)
  
poller_timer = Timer(lambda: lookup_local_action('PollPower').call(), 10, 5)  
  
@after_main
def computePower():
  def handler(ignore):
    rawArg = local_event_RawPower.getArg() or 'Unknown'
    desiredArg = local_event_DesiredPower.getArg() or 'Unknown'

    lastTimeSet = lookup_local_action('Power').getTimestamp() or date_parse('1990')

    # ignore if been more than a minute
    if (date_now().getMillis() - lastTimeSet.getMillis()) > 60000:
      # fallback to Raw
      local_event_Power.emitIfDifferent(rawArg)

      return

    elif rawArg == desiredArg:
      local_event_Power.emit(desiredArg)

    else:
      local_event_Power.emit('Partially %s' % desiredArg)
  
  local_event_RawPower.addEmitHandler(handler)
  local_event_DesiredPower.addEmitHandler(handler)
  
# [ Input ---

INPUTS = ['AV1', 'AV2', 'HM1', 'HM2', 'DV1', 'PC1', 'DL1', 'Off']

local_event_DesiredInput = LocalEvent({'group': 'Input', 'order': next_seq(), 'schema': {'type': 'string', 'enum': INPUTS}})

local_event_RawInput = LocalEvent({'group': 'Input', 'order': next_seq(), 'schema': {'type': 'string', 'enum': INPUTS}})

local_event_Input = LocalEvent({'group': 'Input', 'order': next_seq(), 'schema': {'type': 'string', 'enum': INPUTS + ['Partially %s' % i for i in INPUTS]}})

# compose Input event based on Raw and Desired
@after_main
def computeInput():
  def handler(ignore):
    raw = local_event_RawInput.getArg()
    desired = local_event_DesiredInput.getArg()
    
    lastTimeSet = Input.getTimestamp() or date_parse('1990')

    # ignore if been more than a minute
    if (date_now().getMillis() - lastTimeSet.getMillis()) > 60000:
      # fallback to Raw
      local_event_Input.emitIfDifferent(raw)
      return

    elif raw == desired:
      local_event_Input.emit(desired)

    else:
      local_event_Input.emit('Partially %s' % desired)
  
  local_event_DesiredInput.addEmitHandler(handler)
  local_event_RawInput.addEmitHandler(handler)
  

@local_action({'group': 'Input', 'order': next_seq(), 'schema': {'type': 'string', 'enum': INPUTS}})
def Input(arg):
  if arg not in INPUTS:
    raise Exception('Unknown input [%s]' % arg)
  
  local_event_DesiredInput.emit(arg)
  
  timer_inputSyncer.setDelay(0.001)
  
@local_action({'group': 'Input', 'order': next_seq()})
def PollInput(arg=None):
  def handleResp(resp):
    if resp.startswith('QMI:'):
      argPart = resp[4:].strip()
      local_event_RawInput.emit(argPart)

    else:
      # presuming the resp is the input
      local_event_RawInput.emit(resp)
      
  rawPowerArg = local_event_RawPower.getArg()
  
  if rawPowerArg in ['Off', 'Partially Off']:
    local_event_RawInput.emit('Off')
      
  if rawPowerArg != 'On':
    log(2, 'INPUT: Power is not On, so not querying input')
    return

  log(2, 'INPUT: Querying input (power is On so can)')
  makeRequest('QMI', handleResp)
  
poller_timer = Timer(lambda: lookup_local_action('PollInput').call(), 10, 5)  
  
@local_action({'group': 'Input', 'order': next_seq()})  
def SyncInput():
  lastSet = lookup_local_action('Input').getTimestamp() or date_parse('1990')
  
  # only keep trying if we're within 1 minute of the request
  if (date_now().getMillis() - lastSet.getMillis()) > 60000:
    log(2, '(INPUT: been more than 60s; nothing to do)')
    return
  
  # only set if powered On
  if local_event_Power.getArg() != 'On':
    log(2, '(INPUT: power is off; nothing to do)')
    return
  
  # otherwise attempt to set within the minute if required
  desiredArg = local_event_DesiredInput.getArg()
  raw = local_event_RawInput.getArg()  
  
  if desiredArg == raw:
    log(2, 'INPUT: (desired and raw are both "%s"; nothing to do)' % desiredArg)
    return
  
  log(2, 'INPUT: forcing INPUT to %s' % desiredArg)
  
  def handleResp(resp):
    if resp == 'IMS':
      local_event_RawInput.emit(desiredArg)
  
  makeRequest('IMS:%s' % desiredArg, handleResp)
  
timer_inputSyncer = Timer(lambda: SyncInput.call(), 10, 0)

# ---]

# <!-- signal check

#          QSF         # signal check
#          QSF:M--------------------    # no signal
#          QSF:M-1125(1080)/50p         # signal

local_event_SignalStatus = LocalEvent({'group': 'Signal', 'order': next_seq(), 'schema': {'type': 'string'}})

local_event_FirstNoSignal = LocalEvent({'group': 'Signal', 'order': next_seq(), 'schema': {'type': 'string'}})

@local_action({'group': 'Signal', 'order': next_seq()})
def PollSignalStatus(arg=None):
  def handleResp(resp):
    if not resp.startswith('M'):
      warn(1, 'unexp resp polling signal status')
      return
    
    elif '----' in resp:
      if local_event_SignalStatus.getArg() != 'NO SIGNAL':
        local_event_FirstNoSignal.emit(str(date_now()))
        local_event_SignalStatus.emit('NO SIGNAL')
    
    else:
      local_event_SignalStatus.emit(resp)
      
  log(2, 'SIGNALSTATUS: Querying')
  makeRequest('QSF', handleResp)
  
# seems to be safe to poll even while power is Off
poller_SignalStatus = Timer(lambda: PollSignalStatus.call(), 10, 5)

# -->

# [ Protocol ---

# e.g. on_connect
#      >> NTCONTROL 1 3f020e71
# 
# hash(__admin_user_name__:__password__:__randnumber__)
# commands:
# HASH + '00' + command + CR

_authPrefix = None # e.g. None                   -- Pure serial
                   #      'caabbccddeeaa00'      -- network protected
                   #      '00'                   -- network unprotected

# assumes network 
def prepareAuth(line): 
  # line e.g. "NTCONTROL 1 3f020e71"
  parts = line.split(' ')
  
  global _authPrefix
  
  if parts[1] == '0':
    console.info('Using Panasonic network protocol unprotected')
    _authPrefix = '00'
    
  elif parts[1] == '1':
    console.info('Using Panasonic network protocol protected')  
    
    randomPart = parts[2]
    toBeHashed = '%s:%s:%s' % (param_username or DEFAULT_USERNAME, param_password or DEFAULT_PASSWORD, randomPart)
    hsh = hashlib.md5(toBeHashed).hexdigest()
    _authPrefix = '%s00' % hsh
    
def makeRequest(cmd, onResp):
  def trapResp(data):
    lastReceive[0] = system_clock()
    log(2, 'panasonic_recv: [%s]' % data)
    onResp(data)
      
  log(2, 'panasonic_send: [%s]' % cmd)
  if _authPrefix == None:
    tcp.request('\x02%s\x03' % cmd, trapResp)
    
  else:
    # add '00 suffix on send and ...
    # drop the '00' prefix from response for network protocol (protected and unprotected)
    tcp.request('%s%s\r' % (_authPrefix, cmd), lambda resp: trapResp(resp[2:])) 

# ]

# [ TCP ---

def connected():
  console.info('Connected!')
  local_event_TCPState.emit('Connected')
  
  tcp.clearQueue()
  
def received(data):
  log(3, 'tcp_recv: [%s]' % data)
  
  if 'NTCONTROL ' in data:
    prepareAuth(data)
  
def sent(data):
  log(3, 'tcp_sent: [%s]' % data)
  
def disconnected():
  console.warn('TCP disconnected')
  local_event_TCPState.emit('Disconnected')
  
  
def timeout():
  console.warn('TCP timeout!')
  
  tcp.clearQueue()
  tcp.drop()

tcp = TCP(connected=connected, 
          received=received, 
          sent=sent, 
          disconnected=disconnected, 
          timeout=timeout,
          sendDelimiters='', 
          receiveDelimiters='\x03\r\n') # \x03 for pure serial
                                        # \r\n for Panasonic network protocol

# status ---

local_event_Status = LocalEvent({'title': 'Status', 'group': 'Status', 'order': 9990, "schema": { 'title': 'Status', 'type': 'object', 'properties': {
        'level': {'title': 'Level', 'order': 1, 'type': 'integer'},
        'message': {'title': 'Message', 'order': 2, 'type': 'string'}
    } } })

# for status checks

lastReceive = [0]

# roughly, the last contact  
local_event_LastContactDetect = LocalEvent({'group': 'Status', 'title': 'Last contact detect', 'schema': {'type': 'string'}})
  
def statusCheck():
  # lampUseHours = local_event_LampUseHours.getArg() or 0
  
  diff = (system_clock() - lastReceive[0])/1000.0 # (in secs)
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
    
  if local_event_Power.getArg() == 'On' and local_event_SignalStatus.getArg() == 'NO SIGNAL':
    local_event_Status.emit({'level': 1, 'message': 'Power On but no signal %s' % formatPeriod(local_event_FirstNoSignal.getArg())})
    return
  
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