'''
Basic, limited Panasonic protocol, suitable for some Panasonic displays, will be expaned over time.

Supports **PROTOCOL 2** (ensure selected in device).

* rev. 3 WORKAROUND: set polling to 5 mins to suppress flip flopping
* rev. 4 UPDATE: allow IP address binding (see AMX Beacon, SSDP address, or custom address provider recipes)
  * extended timeout tolerances
  * **Disallow Power Off** options to support equipment that do not handle loss of signal
  * various improvements
'''

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

# <!-- IP addressing

param_ipAddress = Parameter({ 'order': 0, 'schema': { 'type': 'string', 'hint': '(overrides remote binding)' }})

local_event_IPAddress = LocalEvent( { 'group': 'Addressing', 'order': next_seq(), 'schema': { 'type': 'string' }})

def remote_event_ipAddress(arg):
  if not is_blank(param_ipAddress):
    return                          # param takes precedence over any binding

  elif arg != local_event_IPAddress.getArg():
    console.info('IP address updated remotely - %s - restarting...' % arg)
    local_event_IPAddress.emit(arg) # IP address changed so
    _node.restart()                 # restart node!

# -->

DEFAULT_PORT = 1024
param_port = Parameter({ 'schema': { 'type': 'integer', 'hint': '(default %s)' % DEFAULT_PORT }})


DEFAULT_USERNAME = 'dispadmin'
param_username = Parameter({'order': next_seq(), 'schema': {'type': 'string', 'hint': '(default %s)' % DEFAULT_USERNAME}})

DEFAULT_PASSWORD = '@Panasonic'
param_password = Parameter({'order': next_seq(), 'schema': {'type': 'string', 'hint': '(default %s)' % DEFAULT_PASSWORD}})

local_event_RawPower = LocalEvent({ 'group': 'Power', 'schema': { 'type': 'string', 'enum': [ 'On', 'Off' ] }})
local_event_DesiredPower = LocalEvent({ 'group': 'Power', 'schema': { 'type': 'string', 'enum': [ 'On', 'Off' ] }})
local_event_Power = LocalEvent({ 'group': 'Power', 'schema': { 'type': 'string', 'enum': [ 'On', 'Partially On', 'Partially Off', 'Off' ] }})
local_event_PowerOn = LocalEvent({ 'group': 'Power', 'schema': { 'type': 'boolean' }})
local_event_PowerOff = LocalEvent({ 'group': 'Power', 'schema': { 'type': 'boolean' }})

local_event_TCPState = LocalEvent({'title': 'TCP state', 'order': 1, 'group': 'TCP', 'schema': {'type': 'string', 'order': 1, 'enum': ['Connected', 'Disconnected']}})

import hashlib # for authentication

def main():
  if param_disabled:
    return console.warn('Disabled, nothing to do')
  
  ipAddress = param_ipAddress
  if is_blank(ipAddress):
    ipAddress = local_event_IPAddress.getArg()    # from remote binding
  else:
    console.info('(using IP address parameter)')
    local_event_IPAddress.emit(ipAddress)

  if is_blank(ipAddress):
    return console.warn('No IP address set or received yet!')

  port = param_port
  if not port: # if blank, zero or None, use default
    port = DEFAULT_PORT

  tcpAddr = '%s:%s' % (ipAddress, port)
  console.info('Will connect to "%s" on port %s...' % (ipAddress, port))
  tcp.setDest(tcpAddr)
    
def local_action_Power(arg=None):
  '{"group": "Power", "schema": {"type": "string", "enum": ["On", "Off"]}}'
  if arg not in ['On', 'Off']:
    raise Exception('Power arg must be On or Off')

  console.info('POWER %s requested!' % arg)
  
  local_event_DesiredPower.emit(arg)
  
  tcp.drop()
  tcp.clearQueue()
  
  timer_powerSyncer.setDelay(0.001)

local_event_DisallowPowerOff = LocalEvent({ 'group': 'Power', 'order': next_seq(), 'schema': { 'type': 'boolean' },
                                            'desc': 'Is Powering Off disallowed? This is normally done by device dependency (remote event), e.g. do not turn off if an attached multiplayer is on)' })

def remote_event_DisallowPowerOff(arg):
  local_event_DisallowPowerOff.emit(arg)
  syncPower.call()
 
@local_action({'group': 'Power', 'order': next_seq()})  
def syncPower():
  lastSet = lookup_local_action('Power').getTimestamp() or date_parse('1990')
  
  # only keep trying if we're within 1.5 minute of the request
  if (date_now().getMillis() - lastSet.getMillis()) > 90000:
    log(2, '(POWER: been more than 90s; nothing to do)')
    return
  
  arg = local_event_DesiredPower.getArg()
  raw = local_event_RawPower.getArg()
  
  if arg == raw:
    log(2, '(POWER: desired and raw are both "%s"; nothing to do)' % arg)
    return

  if arg == 'On':
    console.info('POWER: forcing power to On')
    makeRequest('PON', handle_powerResp)
    
  elif arg == 'Off':
    if local_event_DisallowPowerOff.getArg():
      console.warn('POWER: want to turn power Off but Disallowed for now')
      return

    console.info('POWER: forcing power to Off')
    makeRequest('POF', handle_powerResp)
  
timer_powerSyncer = Timer(lambda: syncPower.call(), 10, 0)

_previousRawPower = None
  
def handle_powerResp(resp):
  if resp in ['QPW:1', 'PON', '1', '001']:
    lastReceive[0] = system_clock()
    arg = 'On'
      
  elif resp in ['QPW:0', 'POF', '0', '000']:
    lastReceive[0] = system_clock()
    arg = 'Off'
      
  else:
    console.warn('Unexpected feedback from power request. resp:[%s]' % resp)
    return

  local_event_RawPower.emit(arg)

  global _previousRawPower
  if _previousRawPower != None and _previousRawPower != arg: # log change in detected power state
    console.info('Power is %s' % arg)

  _previousRawPower = arg
  
@local_action({'group': 'Power', 'order': next_seq()}) 
def PollPower(arg=None):
  makeRequest('QPW', handle_powerResp)
  
poller_power = Timer(lambda: lookup_local_action('PollPower').call(), 10, 5)  
  
@after_main
def computePower():
  def handler(ignore):
    rawArg = local_event_RawPower.getArg() or 'Unknown'
    desiredArg = local_event_DesiredPower.getArg() or 'Unknown'

    lastTimeSet = lookup_local_action('Power').getTimestamp() or date_parse('1990')

    # ignore if been more than a minute
    if (date_now().getMillis() - lastTimeSet.getMillis()) > 90000:
      # fallback to Raw
      local_event_Power.emitIfDifferent(rawArg)

    elif rawArg == desiredArg:
      local_event_Power.emit(desiredArg)

    else:
      local_event_Power.emit('Partially %s' % desiredArg)

    arg = local_event_Power.getArg()
    local_event_PowerOn.emitIfDifferent(arg == 'On')
    local_event_PowerOff.emitIfDifferent(arg == 'Off')
  
  local_event_RawPower.addEmitHandler(handler)
  local_event_DesiredPower.addEmitHandler(handler)
  
# [ Input ---

INPUTS = ['AV1', 'AV2', 'HM1', 'HM2', 'DV1', 'PC1', 'DL1', 'Off']

local_event_DesiredInput = LocalEvent({'group': 'Input', 'order': next_seq(), 'schema': {'type': 'string', 'enum': INPUTS}})

local_event_RawInput = LocalEvent({'group': 'Input', 'order': next_seq(), 'schema': {'type': 'string' }})

local_event_Input = LocalEvent({'group': 'Input', 'order': next_seq(), 'schema': {'type': 'string', 'enum': INPUTS + ['Partially %s' % i for i in INPUTS]}})

# compose Input event based on Raw and Desired
@after_main
def computeInput():
  def handler(ignore):
    raw = local_event_RawInput.getArg()
    desired = local_event_DesiredInput.getArg()
    
    lastTimeSet = Input.getTimestamp() or date_parse('1990')

    # ignore if been more than a minute
    if (date_now().getMillis() - lastTimeSet.getMillis()) > 90000:
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
      
  powerArg = local_event_Power.getArg()
  
  if powerArg in ['Off', 'Partially Off']:
    local_event_RawInput.emit('Off')
      
  if powerArg != 'On':
    log(2, 'INPUT: Power is not On, so not querying input')
    return

  log(2, 'INPUT: Querying input (power is On so can)')
  makeRequest('QMI', handleResp)
  
poller_input = Timer(lambda: lookup_local_action('PollInput').call(), 13, 8)  # out of sync with power
  
@local_action({'group': 'Input', 'order': next_seq()})  
def SyncInput():
  lastSet = lookup_local_action('Input').getTimestamp() or date_parse('1990')
  
  # only keep trying if we're within 1 minute of the request
  if (date_now().getMillis() - lastSet.getMillis()) > 90000:
    log(2, '(INPUT: been more than 90s; nothing to do)')
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
    # projectors respond with '1' or '0'
    if resp  == '1': # projectors response with "1" or "0"
        local_event_SignalStatus.emit('SIGNAL')
        return
    
    elif '----' in resp or resp == '0': # projectors response with "1" or "0"
      if local_event_SignalStatus.getArg() != 'NO SIGNAL':
        local_event_FirstNoSignal.emit(str(date_now()))
        local_event_SignalStatus.emit('NO SIGNAL')
        
    elif not resp.startswith('M'):
      warn(1, 'unexp resp polling signal status')
      return
        
    else:
      local_event_SignalStatus.emit(resp)
      
  powerArg = local_event_Power.getArg()
  
  if powerArg in ['Off', 'Partially Off']:
    local_event_RawInput.emit('Off')
      
  if powerArg != 'On':
    log(2, 'SIGNALSTATUS: Power is not On, so not querying signal status')
    return
  
  log(2, 'SIGNALSTATUS: Querying')
  makeRequest('QSF', handleResp)
  
# seems to be safe to poll even while power is Off
poller_signal = Timer(lambda: PollSignalStatus.call(), 10, 10)

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
    log(1, 'Using Panasonic network protocol unprotected')
    _authPrefix = '00'
    
  elif parts[1] == '1':
    log(1, 'Using Panasonic network protocol protected')
    
    randomPart = parts[2]
    toBeHashed = '%s:%s:%s' % (param_username or DEFAULT_USERNAME, param_password or DEFAULT_PASSWORD, randomPart)
    hsh = hashlib.md5(toBeHashed).hexdigest()
    _authPrefix = '%s00' % hsh

# any requests pending
_reqPending = False

def makeRequest(cmd, onResp):
  global _reqPending

  if local_event_TCPState.getArg() != 'Connected':
    # not connected, use best effort by delaying a call
    if _reqPending:
      log(2, 'make_req: operation already pending; dropping request [%s]' % cmd)
      # and fall through...

    else:
      # make the delayed call
      def delayedCall():
        global _reqPending   # clear flag and make request
        _reqPending = False

        log(2, 'make_req: operation already pending')
        doMakeRequest(cmd, onResp)

      log(2, 'make_req: not connected so delaying request by 2s')
      _reqPending = True
      call(delayedCall, 2)

  else:
    # connected, so can make request immediately
    doMakeRequest(cmd, onResp)


def doMakeRequest(cmd, onResp):
  def trapResp(data):
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
  log(1, 'tcp_connected')
  local_event_TCPState.emit('Connected')
  
  tcp.clearQueue()
  
def received(data):
  log(3, 'tcp_recv: [%s]' % data)
  
  if 'NTCONTROL ' in data:
    prepareAuth(data)
  
def sent(data):
  log(3, 'tcp_sent: [%s] stripped' % data.strip())
  
def disconnected():
  log(1, 'tcp_disconnected')
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
      message = 'Never been monitored'
      
    else:
      previousContact = date_parse(previousContactValue)
      message = 'Unmonitorable %s' % formatPeriod(previousContact)
      
    local_event_Status.emit({'level': 2, 'message': message})
    return
    
  if local_event_Power.getArg() == 'On' and local_event_SignalStatus.getArg() == 'NO SIGNAL':
    local_event_Status.emit({'level': 1, 'message': 'Power On but no signal %s' % formatPeriod(date_parse(local_event_FirstNoSignal.getArg()))})
    return
  
  local_event_Status.emit({'level': 0, 'message': 'OK'})
  
  local_event_LastContactDetect.emit(str(now))
  
# TODO: setting this to 5 mins while figure out why it flip flops
status_check_interval = 60 * 5 # was 75
status_timer = Timer(statusCheck, status_check_interval)

def formatPeriod(dateObj, asInstant=False):
  if dateObj == None:       return 'for unknown period'

  now = date_now()
  diff = (now.getMillis() - dateObj.getMillis()) / 1000 / 60 # in mins
  
  if diff < 0:              return 'never ever'
  elif diff == 0:           return 'for <1 min' if not asInstant else '<1 min ago'
  elif diff < 60:           return ('for <%s mins' if not asInstant else '<%s mins ago') % diff
  elif diff < 60*24:        return ('since %s' if not asInstant else 'at %s') % dateObj.toString('h:mm a')
  else:                     return ('since %s' if not asInstant else 'on %s') % dateObj.toString('E d-MMM h:mm a')

# --->


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