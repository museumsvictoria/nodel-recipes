'''
Sharp LAN and serial protocol.

At least works with:

 * Sharp PN65SC1 - touchscreen LCD Monitor, serial, **38400** baud,8,N,1, [manual](https://support.sharp.net.au/downloads/opmanuals/PN65SC1_om.pdf) (starts page 32)
 * Sharp PN-HW431 - signage display, LAN [manual](https://www.sharp.co.uk/cps/rde/xbcr/documents/documents/Marketing/Operational_manuals/PNHW861-HW751-HW651-HW551-HW501-HW431_manual_English.pdf)
 
_rev 3_ better use of discrete inputs 
'''

param_disabled = Parameter({ 'title': 'Disabled?', 'schema': { 'type': 'boolean' } })

param_password = Parameter({'title': 'Password (network only)', 'schema': {'type': 'string'}})

param_username = Parameter({'title': 'Username (network only)', 'schema': {'type': 'string'}})

param_ipAddress = Parameter({ 'schema': {'type': 'string' }})

DEFAULT_LAN_PORT = 10008
param_LANControl = Parameter({ 'title': 'LAN control?', 'schema': { 'type': 'boolean' }})

DEFAULT_SERIAL_PORT = 4999
param_port = Parameter({ 'title': 'Port (for serial)', 'schema': {'type': 'integer', 'hint': '(default %s for Global Cache)' % DEFAULT_SERIAL_PORT }})



# -->

# <!-- tables

INPUTS = ( ('D-SUB', '2'),
           ('HDMI1', '10'),
           ('HDMI2', '13'),
           ('HDMI3', '18'),
           ('DisplayPort', '14'),
           ('OPTION', '21') )

INPUT_NAMES = [ x for x, y in INPUTS ]
INPUTS_byName = dict(( (x, y) for x, y in INPUTS ))
INPUTS_byCode = dict(( (y, x) for x, y in INPUTS ))

# -->

# <!-- main entry-point

def main():
  if param_disabled:
    return console.warn('Is disabled; nothing to do')
  
  if is_blank(param_ipAddress):
    return console.warn('No IP address is specified; cannot continue')
  
  dest = '%s:%s' % (param_ipAddress, param_port or DEFAULT_SERIAL_PORT)
  console.info('Will connected to [%s]' % dest)
  
  tcp.setDest(dest)

# -->

# <!-- managed power and input

local_event_Power = LocalEvent({ 'group': 'Power', 'order': next_seq(), 'schema': { 'type': 'string', 'enum': [ 'Partially On', 'On', 'Partially Off', 'Off' ]}})
local_event_PowerOn = LocalEvent({ 'group': 'Power', 'title': 'On', 'order': next_seq(), 'schema': { 'type': 'boolean' }})
local_event_PowerOff = LocalEvent({ 'group': 'Power', 'title': 'Off', 'order': next_seq(), 'schema': { 'type': 'boolean' }})

local_event_DesiredPower = LocalEvent({ 'group': 'Power', 'order': next_seq(), 'schema': { 'type': 'string', 'enum': [ 'On', 'Off' ]}})

@local_action({ 'group': 'Power', 'order': next_seq(), 'schema': { 'type': 'string', 'enum': [ 'On', 'Off' ]}})
def Power(arg):
  console.info('Power(%s)' % arg)
  
  if arg not in [ 'On', 'Off' ]:
    return console.warn('power: bad arg - %s' % arg)
  
  local_event_DesiredPower.emit(arg)
  syncIfNecessary()

@local_action({ 'group': 'Power', 'title': 'On', 'order': next_seq() })  
def PowerOn(ignore):
  Power.call('On')
  
@local_action({ 'group': 'Power', 'title': 'Off', 'order': next_seq() })  
def PowerOff(ignore):
  Power.call('Off')

local_event_Input = LocalEvent({ 'group': 'Input', 'order': next_seq(), 'schema': { 'type': 'string' }})

local_event_DesiredInput = LocalEvent({ 'group': 'Input', 'order': next_seq(), 'schema': { 'type': 'string' }})

@local_action({ 'group': 'Input', 'order': next_seq(), 'schema': { 'type': 'string', 'enum': INPUT_NAMES }})
def Input(arg):
  console.info('Input(%s)' % arg)
  
  if arg in INPUT_NAMES:
    local_event_DesiredPower.emit('On')
    local_event_DesiredInput.emit(arg)
        
  else:
    return console.warn('input: bad arg - %s' % arg)
    
  syncIfNecessary()
  
@after_main
def add_discrete_inputs():
  for name in INPUT_NAMES:
    add_discrete_input(name)

def add_discrete_input(name):
  e = create_local_event('Input %s' % name, { 'group': 'Input', 'order': next_seq(), 'schema': { 'type': 'boolean' }})
  
  def handle_feedback(ignore):
    e.emitIfDifferent(name in local_event_Input.getArg() and 'On' in local_event_Power.getArg())
    
  local_event_Input.addEmitHandler(handle_feedback)
  local_event_Power.addEmitHandler(handle_feedback)
  
  def handler(arg):
    Input.call(name)
  
  a = create_local_action('Input %s' % name, handler, { 'group': 'Input', 'order': next_seq() })
  
def syncIfNecessary():
  log(2, 'syncIfNecessary')
  
  # only sync if operation has been within the last 5 mins
  now = date_now().getMillis()
  lastAction = max((Power.getTimestamp() or date_parse('1990')).getMillis(), (Input.getTimestamp() or date_parse('1990')).getMillis())
  
  if now - lastAction > 5 * 60000: # millis here
    log(1, 'sync: has been more than 5 mins since last Input or Power action; will back-off and not do anything')
    _syncer.setInterval(3600) # secs here
    return
  
  log(1, 'sync: (interval will be 4 seconds from now)')
  _syncer.setInterval(4)
  
  # power first
  rawPower = local_event_RawPower.getArg()
  desiredPower = local_event_DesiredPower.getArg()
  
  if desiredPower == None:
    # nothing to do
    log(2, 'sync: (desiredPower == None)')
    return
  
  # re-interpret into On or Off
  if rawPower in ['Normal', 'Input Signal Waiting']:
    rawPower = 'On'
  elif rawPower == 'Standby':
    rawPower = 'Off'
  
  if desiredPower != rawPower:
    console.info('sync: setting power (current: %s, desired: %s)' % (rawPower, desiredPower))
    RawPower.call(desiredPower)
    return
  
  # power state is where we want it now
  
  if rawPower == 'Off':
    # don't bother doing anything with inputs
    log(2, 'sync: (rawPower == Off; not bothering doing anything with inputs)')
    return
  
  # otherwise, check input
  rawInput = local_event_RawInput.getArg()
  desiredInput = local_event_DesiredInput.getArg()
  
  if desiredInput == 'Off':
    # nothing to do, power will be off if here anyway
    log(2, 'sync: (desiredInput == Off)')
    return
  
  if rawInput != desiredInput:
    console.info('sync: setting input (current: %s, desired: %s)' % (rawInput, desiredInput))
    RawInput.call(desiredInput)
    return
  
  log(2, 'sync: (end of method)')
  
_syncer = Timer(syncIfNecessary, 15, 5, stopped=True) # this interval will change
  
  
@after_main
def aggregate_feedback():
  def handler(ignore):
    # power first
    desiredPower = local_event_DesiredPower.getArg()
    rawPower = local_event_RawPower.getArg()
    
    log(2, 'aggregate_feedback: initial: desiredInput:%s rawPower:%s' % (desiredPower, rawPower))      
    
    # re-interpret into On or Off
    if rawPower in ['Normal', 'Input Signal Waiting']:
      rawPower = 'On'
    elif rawPower == 'Standby':
      rawPower = 'Off'
      
    log(2, 'aggregate_feedback: after: desiredInput:%s rawPower:%s' % (desiredPower, rawPower))      
    
    if desiredPower == None or rawPower == None:
      log(2, 'aggregate_feedback: desiredPower == None or rawPower == None')
      power = rawPower or 'Unknown'
      
    elif desiredPower != rawPower:
      log(2, 'aggregate_feedback: desiredPower != rawPower')
      power = 'Partially %s' % desiredPower
      
    else:
      log(2, 'aggregate_feedback: else')
      power = rawPower
      
    local_event_Power.emit(power)
    local_event_PowerOn.emit('On' in power)
    local_event_PowerOff.emit('Off' in power)
    
    # now input
    desiredInput = local_event_DesiredInput.getArg()
    rawInput = 'Off' if rawPower == 'Off' else local_event_RawInput.getArg()
    
    if desiredInput == None or rawInput == None:
      i = rawInput or 'Unknown'
      
    elif rawInput != desiredInput:
      i = 'Partially %s' % desiredInput
      
    else:
      i = rawInput
      
    local_event_Input.emit(i)
      
  local_event_RawPower.addEmitHandler(handler)
  local_event_DesiredPower.addEmitHandler(handler)
  local_event_RawInput.addEmitHandler(handler)
  local_event_DesiredInput.addEmitHandler(handler)

# -->

# <!--- protocol and raw operations

def assertOK(context, resp):
  if resp not in [ 'OK', 'WAIT' ]: console.warn('%s: resp was %s' % (context, resp))
  # otherwise fine
  
def stopIfError(context, resp, onSuccess=None):
  if 'ERR' in resp:
    if local_event_RawPower.getArg() == 'Normal':
      console.warn('%s: resp was in error - %s' % (context, resp))
  elif onSuccess != None:
    onSuccess(resp)

# info

local_event_Model = LocalEvent({ 'group': 'Information', 'order': next_seq(), 'schema': { 'type': 'string' }})

@local_action({ 'group': 'Information', 'order': next_seq() })
def Model():
  if local_event_Power.getArg() == 'On':
    tcp.request('INF1????', lambda resp: stopIfError('model', resp, lambda arg: local_event_Model.emit(arg)))

_modelPoller = Timer(lambda: Model.call(), 5*60, 5, stopped=True) # every 5 minutes, first after 5


local_event_SerialNo = LocalEvent({ 'group': 'Information', 'order': next_seq(), 'schema': { 'type': 'string' }})

@local_action({ 'group': 'Information', 'order': next_seq() })
def SerialNo():
  if local_event_Power.getArg() == 'On':
    tcp.request('SRNO????', lambda resp: stopIfError('serialno', resp, lambda arg: local_event_SerialNo.emit(arg)))

_serialNoPoller = Timer(lambda: SerialNo.call(), 5*60, 5, stopped=True) # every 5 minutes, first after 5

# power control
  
local_event_RawPower = LocalEvent({ 'group': 'Raw', 'order': next_seq(), 'schema': { 'type': 'string' }})
  
@local_action({ 'group': 'Raw', 'order': next_seq() })
def RawPowerPoll(arg):
  def handle(resp):
    if resp == '0':
      arg = 'Standby'
    elif resp == '1':
      arg = 'Normal'
    elif resp == '2':
      arg = 'Input Signal Waiting'
    else:
      return console.warn('rawpowerpoll: unexpected feedback - %s' % resp)
    
    global _lastReceive
    _lastReceive = system_clock() # indicate monitoring ok
    
    local_event_RawPower.emit(arg)
  
  tcp.request('POWR????', handle)
  
_powerPoller = Timer(lambda: RawPowerPoll.call(), 5, 5, stopped=True) # poll every 5 seconds  

@local_action({ 'group': 'Raw', 'order': next_seq(), 'schema': { 'type': 'string' } })
def RawPower(arg):
  console.info('rawpower(%s)' % arg)
  
  if arg in ['Standby', 'Off']:
    value = '0'
  elif arg == 'On':
    value = '1'
  else:
    return console.warn('rawpower: bad arg - %s' % arg)
    
  tcp.request('POWR%4s' % value, lambda resp: assertOK('rawpower', resp)) # pad the arg


# input mode selection

local_event_RawInput = LocalEvent({ 'group': 'Raw', 'order': next_seq(), 'schema': { 'type': 'string' }})
  
@local_action({ 'group': 'Raw', 'order': next_seq() })
def RawInputPoll(arg):
  def handle(resp):
    # is response a valid input code
    name = INPUTS_byCode.get(resp)
    
    if name == None:
      if local_event_RawPower.getArg() == 'Normal':
        return console.warn('rawinputpoll: unexpected resp - %s' % resp)
      
    local_event_RawInput.emit(name)
  
  tcp.request('INPS????', handle)
  
_inputPoller = Timer(lambda: RawInputPoll.call(), 5, 5, stopped=True) # poll every 5 seconds  

@local_action({ 'group': 'Raw', 'order': next_seq(), 'schema': { 'type': 'string', 'enum': INPUT_NAMES } })
def RawInput(arg):
  console.info('rawinput(%s)' % arg)
  
  code = INPUTS_byName.get(arg)
  
  if code == None:
    return console.warn('rawinput: unexpected resp - %s' % arg)
  
  tcp.request('INPS%4s' % code, lambda resp: assertOK('rawinput', resp)) # pad the arg

# protocol and raw operations --!>


# <!-- TCP

def tcp_connected():
  console.info('tcp_connected')
  if not param_LANControl:
    _inputPoller.start()
    _powerPoller.start()
    _modelPoller.start()
    _serialNoPoller.start()
    _syncer.start()
  
  # else wait to deal with Login / Password (see below)
  
def tcp_disconnected():
  console.warn('tcp_disconnected')
  _inputPoller.stop()
  _powerPoller.stop()
  _modelPoller.stop()
  _serialNoPoller.stop()
  _syncer.stop()
  
  tcp.clearQueue()
  
def tcp_timeout():
  log(0, 'TCP timeout!')
  tcp.drop()
  tcp.clearQueue()

def tcp_sent(data):
  log(1, "tcp_sent [%s]" % data)

def tcp_received(line):
  log(1, "tcp_received [%s]" % line)
  
  if param_LANControl:
    if line == 'Login':
      tcp.send(param_username or '\r')
    
    elif line == 'Password':
      tcp.request(param_password or '\r', handlePasswordResp)
    
def handlePasswordResp(resp):
  if resp == 'OK':
    _inputPoller.start()
    _powerPoller.start()
    _modelPoller.start()
    _serialNoPoller.start()
    _syncer.start()
    
  else:
    console.warn('Did not receive OK after sending username / password, will timeout and reconnect')
    
  
tcp = TCP(connected=tcp_connected, 
          disconnected=tcp_disconnected, 
          sent=tcp_sent,
          received=tcp_received,
          timeout=tcp_timeout, 
          sendDelimiters='\r', # NOTE: '\r' not '\n' 
          receiveDelimiters='\r\n:') # NOTE: includes ':'

# tcp --!>


# <!-- status

local_event_Status = LocalEvent({'title': 'Status', 'group': 'Status', 'order': 9990, "schema": { 'title': 'Status', 'type': 'object', 'properties': {
        'level': {'title': 'Level', 'order': 1, 'type': 'integer'},
        'message': {'title': 'Message', 'order': 2, 'type': 'string'}
    } } })

_lastReceive = 0

# roughly, the last contact  
local_event_LastContactDetect = LocalEvent({'group': 'Status', 'title': 'Last contact detect', 'schema': {'type': 'string'}})
  
def statusCheck():
  diff = (system_clock() - _lastReceive)/1000.0 # (in secs)
  now = date_now()
  
  if diff > status_check_interval+15:
    previousContactValue = local_event_LastContactDetect.getArg()
    
    if previousContactValue == None:
      message = 'Always been missing.'
      
    else:
      previousContact = date_parse(previousContactValue)
      message = 'Missing %s' % formatPeriod(previousContact)
      
    local_event_Status.emit({'level': 2, 'message': message})
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
  elif diff < 60*24:        return 'since %s' % dateObj.toString('h:mm a')
  else:                     return 'since %s' % dateObj.toString('E d-MMM h:mm a')
  
# status --!>
  

# <!-- logging

local_event_LogLevel = LocalEvent({'group': 'Debug', 'order': 10000+next_seq(), 'desc': 'Use this to ramp up the logging (with indentation)',  
                                   'schema': {'type': 'integer'}})

def warn(level, msg):
  if (local_event_LogLevel.getArg() or 0) >= level:
    console.warn(('  ' * level) + msg)

def log(level, msg):
  if (local_event_LogLevel.getArg() or 0) >= level:
    console.log(('  ' * level) + msg)

# --!>