'''
Philips Display control using Serial / Ethernet Interface Communication Protocol (**SICP**).

**Resources**

 * [The SICP Commands Document V1_99 25 May2017.pdf](https://www.keren.nl/dynamic/media/1/documents/Drivers/The%20SICP%20Commands%20Document%20V1_99%2025%20May2017.pdf)

**Notes**

1. Videowall models do not necessarily support *Video Signal Present?* end *Backlight* control.

**Source input codes**

 * 01 = VIDEO, 02 = S-VIDEO, 03 = COMPONENT, 04 = CVI 2 (not applicable), 05 = VGA, **06 = HDMI 2**, 07 = Display Port 2, 
 * 08 = USB 2, 09 = Card DVI-D, 0A = Display Port 1, 0B= Card OPS, 0C = USB 1, 
 * **0D = HDMI**, 0E= DVI-D, 0F = HDMI3, 10= BROWSER, 11= SMARTCMS, 12= DMS (Digital Media Server), 13= INTERNAL STORAGE, 
 * 14= Reserved, 15= Reserved, 16= Media Player, 17= PDF Player, 18= Custom
 
**changelog**

_rev 11: incl. Video Signal Present & Backlight_
'''

DEFAULT_PORT = 5000 # Philips port

param_MACAddress = Parameter({ 'schema': { 'type': 'string' }})

param_IPAddress = Parameter({ 'schema': { 'type': 'string' }})

param_Port = Parameter({ 'schema': { 'type': 'integer', 'hint': '(5000, Philips default)' }})

param_MonitorID = Parameter({ 'title': 'Monitor ID (optional)', 'order': next_seq(), 'schema': { 'type': 'integer', 'hint': '(def. 1)' }})

param_Group = Parameter({ 'title': 'Group (optional)', 'order': next_seq(), 'schema': { 'type': 'integer', 'hint': '(0, broadcast - see docs)' }})

param_InputSourcesInUse = Parameter({ 'title': 'Input Sources in use', 'order': next_seq(), 'schema': { 'type': 'array', 'items': { 'type': 'object', 'properties': {
  'code': { 'order': 1, 'type': 'string', 'hint': '(e.g. "0D" for HDMI)' },
  'label': { 'order': 2, 'type': 'string' }}}}})

local_event_IPAddress = LocalEvent({ 'group': 'Addressing', 'schema': { 'type': 'string' }})

def remote_event_IPAddress(arg):
  if arg != None and is_blank(param_IPAddress) and arg != local_event_IPAddress.getArg():
    console.info('Notified of IP address change - %s; will restart node...' % arg)
    local_event_IPAddress.emit(arg)
    _node.restart()
    
def main():
  ipAddress = param_IPAddress
  
  if is_blank(ipAddress):
    ipAddress = local_event_IPAddress.getArg()
  
  if is_blank(ipAddress):
    return console.info('No IP address parameter or remote binding present; nothing to do.')
  
  local_event_IPAddress.emit(ipAddress)
  
  for info in param_InputSourcesInUse or EMPTY:
    initInputSourceInUse(info)
    
  dest = '%s:%s' % (ipAddress, param_Port or DEFAULT_PORT)
  console.info('Connecting to %s (%s)' % (dest, 'config from bindings' if is_blank(param_IPAddress) else 'config from parameter'))
  _tcp.setDest(dest)
  
# <!-- operations

# <-- power

local_event_Power = LocalEvent({ 'group': 'Power', 'order': next_seq(), 'schema': { 'type': 'string', 'enum': [ 'On', 'Partially On', 'Partially Off', 'Off' ] }})
local_event_RawPower = LocalEvent({ 'group': 'Power', 'order': next_seq(), 'schema': { 'type': 'string' }})
local_event_DesiredPower = LocalEvent({ 'group': 'Power', 'order': next_seq(), 'schema': { 'type': 'string', 'enum': [ 'On', 'Off' ] }})

_wol = UDP(dest='255.255.255.255:9999',
          sent=lambda arg: console.info('wol: sent packet (size %s)' % len(arg)),
          ready=lambda: console.info('wol: ready'), received=lambda arg: console.info('wol: received [%s]'))

@local_action({'group': 'Power', 'order': next_seq()})
def SendWOLPacket(arg=None):
  console.info('SendWOLPacket')
  
  hw_addr = param_MACAddress.replace('-', '').replace(':', '').decode('hex')
  macpck = '\xff' * 6 + hw_addr * 16
  _wol.send(macpck)

_lastDisallowPowerOnChanged = 0 # (system_clock() based)

local_event_DisallowPowerOn = LocalEvent({ 'group': 'Power', 'order': next_seq(), 'schema': { 'type': 'boolean' },
                                            'desc': 'Is Powering On disallowed? This is normally done by device dependency (remote event), e.g. do not turn on if an attached display is off)' })

def remote_event_SlavePower(arg):
  console.info('SlavePower(%s) received' % arg)
  state = strictlyBoolean('SlavePower', arg)
  if state == True:    Power.call('On')
  elif state == False: Power.call('Off')

@local_action({ 'group': 'Power', 'order': next_seq(), 'schema': { 'type': 'string', 'enum': [ 'On', 'Off' ] } })
def Power(arg):
  console.info('Power(%s)' % arg)
  state = strictlyBoolean('Power', arg)
  local_event_DesiredPower.emit('On' if state else 'Off')
  if state == True:    rawTurnOn.call()
  elif state == False: rawTurnOff.call()

@local_action({ 'group': 'Power', 'order': next_seq() })    
def PowerOn():
  Power.call('On')
  
@local_action({ 'group': 'Power', 'order': next_seq() })    
def PowerOff():
  Power.call('Off')

@after_main
def power_feedback():
  def handler(ignore):
    raw = local_event_RawPower.getArg()
    desired = local_event_DesiredPower.getArg()
    
    if desired == None or desired == raw:
      local_event_Power.emit(raw)
    else:
      local_event_Power.emit('Partially %s' % desired)
  
  local_event_DesiredPower.addEmitHandler(handler)
  local_event_RawPower.addEmitHandler(handler)
  
@local_action({ 'group': 'Raw', 'order': next_seq() })
def getPower():
  def handler(resp):
    if resp == '\x02':
      local_event_RawPower.emit('On')
    elif resp == '\x01':
      local_event_RawPower.emit('Off')
    else:
      console.info('getPower: unknown resp - %s' % resp.encode('hex'))
      
  rawMsgGet('getPower', '\x19', '', handler)

@local_action({ 'group': 'Raw', 'order': next_seq() })
def rawTurnOff():
  log(1, 'rawTurnOff')
  rawMsgSet('rawTurnOff', '\x18', '\x01', lambda ignore: local_event_RawPower.emit('Off'))   # \x01: Power Off, \x02: On

@local_action({ 'group': 'Raw', 'order': next_seq() })  
def rawTurnOn():
  log(1, 'rawTurnOn')
  SendWOLPacket.call()
  rawMsgSet('rawTurnOn', '\x18', '\x02', lambda ignore: local_event_RawPower.emit('On'))   # \x01: Power Off, \x02: On
  
# power -->  

  
# <!-- input source

local_event_InputSource = LocalEvent({ 'group': 'Input Source', 'order': next_seq(), 'schema': { 'type': 'string' }})
local_event_RawInputSource = LocalEvent({ 'group': 'Raw', 'order': next_seq(), 'schema': { 'type': 'string' }})
local_event_DesiredInputSource = LocalEvent({ 'group': 'Input Source', 'order': next_seq(), 'schema': { 'type': 'string' }})

@local_action({ 'group': 'Raw', 'order': next_seq() })
def getInputSource():
  def handler(resp):
    local_event_RawInputSource.emit(resp[0].encode('hex').upper())
      
  rawMsgGet('getInputSource', '\xAD', '', handler)
  
@local_action({ 'group': 'Input Source', 'order': next_seq(), 'schema': { 'type': 'string', 'hint': '(e.g. "OD" for HDMI1)' } })
def InputSource(arg):  
  if is_blank(arg):
    return console.warn('InputSource: no code given')
  
  code = arg.upper()
  console.info('InputSource(%s)' % code)
  
  if local_event_Power.getArg() != 'On':
    console.info('  power not on, will turn on...')
    Power.call('On')
  
  local_event_DesiredInputSource.emit(code)
  rawSetInputSource.call(code)
  
@after_main
def inputsource_feedback():
  def handler(ignore):
    raw = local_event_RawInputSource.getArg()
    desired = local_event_DesiredInputSource.getArg()
    
    if desired == None or desired == raw:
      local_event_InputSource.emit(raw)
    else:
      local_event_InputSource.emit('Partially %s' % desired)
  
  local_event_DesiredInputSource.addEmitHandler(handler)
  local_event_RawInputSource.addEmitHandler(handler)

@local_action({ 'group': 'Raw', 'order': next_seq(), 'schema': { 'type': 'string', 'hint': '(code, e.g. "0D" for HDMI)' }})
def rawSetInputSource(code):
  code = code.upper()        
  log(1, 'rawSetInputSource(%s)')
  # this uses some strange reserved bytes (see reference page 18)
  rawMsgSet('rawSetInputSource', '\xAC', '%s%s\x01\x00' % (code.decode('hex'), code.decode('hex')), lambda ignore: local_event_RawInputSource.emit(code))
  
def initInputSourceInUse(info):
  code = (info['code'] or '').upper()
  label = info['label']
  
  if is_blank(code) or is_blank(label):
    return console.warn('config: A source in use is missing a code or label or both')
  
  siE = create_local_event('Input Source %s' % code, { 'title': '"%s"' % label, 'group': 'Input Source', 'order': next_seq(), 'schema': { 'type': 'boolean' }})
  
  def handler(ignore):
    console.info('InputSource%s "%s" called' % (code, label))
    InputSource.call(code)
  
  siA = create_local_action('Input Source %s' % code, handler, { 'title': '"%s"' % label, 'group': 'Input Source', 'order': next_seq() })
  
  def feedback_handler(arg):
    if local_event_Power.getArg() != 'On':
      siE.emit(False)
    else:
      siE.emit(arg == code)
    
  local_event_InputSource.addEmitHandler(feedback_handler) # compared using upper case
  
# input source -->

# <!-- sync and polling

def pollAndSync():
  now = date_now()
  
  # check last power
  if now.getMillis() - (Power.getTimestamp() or date_parse('1990')).getMillis() > 60000:
    pass # been a minute, so don't do anything
  else:
    # been less than a minute so try and sync
    desiredPowerArg = local_event_DesiredPower.getArg()
    if local_event_Power.getArg() != desiredPowerArg:
      console.log('Power is not in desired state, will try force... (will try for a minute)')
      rawTurnOn.call() if desiredPowerArg == 'On' else rawTurnOff.call()
      
  
  if now.getMillis() - (InputSource.getTimestamp() or date_parse('1990')).getMillis() > 60000:
    pass # been a minute, so don't do anything
  else:
    # been less than a minute so try and sync
    desiredInputSourceArg = local_event_DesiredInputSource.getArg()
    if local_event_InputSource.getArg() != desiredInputSourceArg:
      console.log('Input Source is not in desired state, will try force... (will try for a minute)')
      rawSetInputSource.call(desiredInputSourceArg)  
      
  getPower.call()
  getInputSource.call()  

timer_Poller = Timer(pollAndSync, 5) # every 5s

# sync and polling -->
  
# SICP version, etc.

local_event_SICPImpl = LocalEvent({ 'group': 'Information', 'order': next_seq(), 'schema': { 'type': 'string' }})
local_event_PlatformLabel = LocalEvent({ 'group': 'Information', 'order': next_seq(), 'schema': { 'type': 'string' }})
local_event_PlatformVersion = LocalEvent({ 'group': 'Information', 'order': next_seq(), 'schema': { 'type': 'string' }})

@local_action({ 'group': 'Information', 'order': next_seq() })
def getSICPInfo():
  rawMsgGet('getSICPInfo', '\xA2', '\x00', lambda resp: local_event_SICPImpl.emit(resp)) # SICP impl.
  rawMsgGet('getSICPInfo', '\xA2', '\x01', lambda resp: local_event_PlatformLabel.emit(resp)) # platform label
  rawMsgGet('getSICPInfo', '\xA2', '\x02', lambda resp: local_event_PlatformVersion.emit(resp)) # platform version

local_event_Model = LocalEvent({ 'group': 'Information', 'order': next_seq(), 'schema': { 'type': 'string' }})
local_event_Firmware = LocalEvent({ 'group': 'Information', 'order': next_seq(), 'schema': { 'type': 'string' }})
local_event_BuildDate = LocalEvent({ 'group': 'Information', 'order': next_seq(), 'schema': { 'type': 'string' }})
  
@local_action({ 'group': 'Information', 'order': next_seq() })
def getModelInfo():
  rawMsgGet('getModelInfo', '\xA1', '\x00', lambda resp: local_event_Model.emit(resp)) # model
  rawMsgGet('getModelInfo', '\xA1', '\x01', lambda resp: local_event_Firmware.emit(resp)) # FW
  rawMsgGet('getModelInfo', '\xA1', '\x02', lambda resp: local_event_BuildDate.emit(resp)) # build date
  
  
# <!--- video signal present

local_event_VideoSignalPresent = LocalEvent({ 'group': 'Video Signal', 'order': next_seq(), 'schema': { 'type': 'boolean' }})
  
@local_action({ 'group': 'Video Signal', 'order': next_seq() })
def getVideoSignalPresent():
  def handler(resp):
    if resp == '\x00':   state = False
    elif resp == '\x01': state = True
    else:
      return console.warn('getBacklight: unknown resp - %s' % resp.encode('hex'))
    local_event_VideoSignalPresent.emit(state)
    
  rawMsgGet('getVideoSignalPresent', '\x59', '', handler)

# -->

# <!--- backlight

local_event_Backlight = LocalEvent({ 'group': 'Backlight', 'order': next_seq(), 'schema': { 'type': 'boolean' }})
  
@local_action({ 'group': 'Backlight', 'order': next_seq() })
def getBacklight():
  def handler(resp):
    if resp == '\x00':   state = True
    elif resp == '\x01': state = False
    else:
      return console.warn('getBacklight: unknown resp - %s' % arg.encode('hex'))
    local_event_Backlight.emit(state)
    
  rawMsgGet('getBacklight', '\x71', '', handler)
  
@local_action({ 'group': 'Backlight', 'order': next_seq(), 'schema': { 'type': 'boolean' }})
def Backlight(arg):
  log(1, 'set Backlight(%s)' % arg)
  
  state = strictlyBoolean('Backlight', arg)
  
  rawMsgSet('backlight', '\x72', '\x00' if state else '\x01', lambda ignore: local_event_Backlight.emit(state))

# -->


# PACKET STRUCTURE:
# e.g. mSize:mControl:mGroup:mData0:mData1:mChksum
#       06  :    01  :  00  :  18  :  01  :  1e

def rawMsgGet(context, mData0, mDataX, resp):
  size = 1 + 1 + 1 + 1 + len(mDataX) + 1 # SIZE : CONTROL : GROUP : DATA0: DATAX... : CHKSUM
  monitorID = param_MonitorID or 1
  group = param_Group or 0
  
  msg = ( chr(size), chr(monitorID), chr(group), mData0 ) + tuple(mDataX or '')
  raw = ''.join(msg + (chksum(msg),)) # forced 1 element tuples
  
  log(2, '%s - %s - %s' % (context, mData0.encode('hex'), asByteBuffer(mDataX)))
  
  def handler(rawResp):
    rControl, rGroup, rData0, rDataX = parseRawMessage(rawResp)
    
    if rData0 != mData0:
      return console.warn('%s: bad resp - got "%s", expected "%s"' % (context, rData0.encode('hex'), mData0.encode('hex')))
    else:
      resp(rDataX)
              
  _tcp.request(raw, handler)

def rawMsgSet(context, mData0, mDataX, resp):
  size = 1 + 1 + 1 + 1 + len(mDataX) + 1 # SIZE : CONTROL : GROUP : DATA0: DATAX... : CHKSUM
  monitorID = param_MonitorID or 1
  group = param_Group or 0
  
  msg = ( chr(size), chr(monitorID), chr(group), mData0 ) + tuple(mDataX or '')
  raw = ''.join(msg + (chksum(msg),)) # forced 1 element tuples
  
  log(2, '%s - %s - %s' % (context, mData0.encode('hex'), asByteBuffer(mDataX)))
  
  def handler(rawResp):
    rControl, rGroup, rData0, rDataX = parseRawMessage(rawResp)
    
    if rControl != monitorID: return console.warn('%s: bad resp - unexpected monitor ID - %s' % (context, rControl))
    if rData0 != '\x00': return console.warn('%s: bad resp - data byte was supposed to be 0x00 - %s' % (context, mData0.encode('hex')))
    if rDataX == '\x06': # good resp!
      resp(rDataX)
    elif rDataX == '\x15': return console.warn('%s: got a negative acknowledgement' % context)
    elif rDataX == '\x18': return console.warn('%s: display reports command not available, not relevant or cannot execute' % context)
    else: return console.warn('%s: bad resp - unknown error code(s) - %s' % (context, rDataX.encode('hex')))
    
  _tcp.request(raw, handler)
  
def chksum(msg):
  t = 0
  for b in msg:
    t = t ^ ord(b)
  return chr(t)

def parseRawMessage(msg):
  mSize = ord(msg[0])
  mControl = ord(msg[1])
  mGroup = ord(msg[2])
  mData0 = msg[3]
  mDataX = msg[4:4+mSize-5]
  mChksum = ord(msg[-1])
  
  log(2, 'parseRawMessage: size:%s control:%s group:%s data0:%s data:"%s" chksum:%0.2x' % (mSize, mControl, mGroup, mData0.encode('hex'), mDataX, mChksum))
  
  global _lastReceive
  _lastReceive = system_clock()
  
  return (mControl, mGroup, mData0, mDataX)

# operations --!>

def tcp_connected():
  console.info('tcp_connected')
  _tcp.clearQueue()
  timer_Poller.start()
  
def tcp_received(raw):
  xRaw = raw.encode('hex')
  log(3, 'tcp_received - %s' % ':'.join([ xRaw[i*2:i*2+2] for i in range(len(xRaw)/2)]))
  # parseRawMessage(raw)
  
def tcp_sent(raw):
  xRaw = raw.encode('hex')
  log(3, 'tcp_sent - %s' % ':'.join([ xRaw[i*2:i*2+2] for i in range(len(xRaw)/2)]))

def tcp_disconnected():
  console.warn('tcp_disconnected')
  timer_Poller.stop()

def tcp_timeout():
  console.warn('tcp_timeout - dropping connection')
  _tcp.drop()

_tcp = TCP(connected=tcp_connected, received=tcp_received, sent=tcp_sent, disconnected=tcp_disconnected, timeout=tcp_timeout, 
           sendDelimiters='', receiveDelimiters='')


# <!-- general functions

def asByteBuffer(raw):
  if not raw: return ''
  xRaw = raw.encode('hex')
  return ':'.join([ xRaw[i*2:i*2+2] for i in range(len(xRaw)/2)])

def strictlyBoolean(context, arg):
  if arg in [ True, 'TRUE', 'true', 'True', 1, '1', 'On', 'ON', 'on', '\x01' ]: return True
  if arg in [ False, 'FALSE', 'false', 'FALSE', 0, '0', 'Off', 'OFF', 'off', '\x00' ]: return False
  console.warn('%s: expected a boolean type, got - %s' % (context ,arg))
  return None

# --!>

# <!-- logging and status

local_event_Status = LocalEvent({ 'group': 'Status', 'order': 1, 'schema': { 'type': 'object', 'properties': {
  'level': { 'type': 'integer', 'order': 1 },
  'message': { 'type': 'string', 'order': 2 }}}})

_lastReceive = 0

# roughly, the last contact  
local_event_LastContactDetect = LocalEvent({'group': 'Status', 'title': 'Last contact detect', 'schema': {'type': 'string'}})
  
def statusCheck():
  diff = (system_clock() - _lastReceive)/1000.0 # (in secs)
  now = date_now()
  
  if diff > status_check_interval+15:
    previousContactValue = local_event_LastContactDetect.getArg()
    
    if previousContactValue == None: 
      message = 'Never been monitored'
    else:
      message = 'Unmonitorable %s' % formatPeriod(date_parse(previousContactValue))
      
    local_event_Status.emit({ 'level': 2, 'message': message })
    return
    
  # if local_event_Power.getArg() == 'On' and local_event_SignalStatus.getArg() == 'NO SIGNAL':
  #   local_event_Status.emit({'level': 1, 'message': 'Power On but no signal %s' % formatPeriod(date_parse(local_event_FirstNoSignal.getArg()))})
  #   return
  
  local_event_Status.emit({'level': 0, 'message': 'OK'})
  
  local_event_LastContactDetect.emit(str(now))
  
status_check_interval = 60 # was 75

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

local_event_LogLevel = LocalEvent({ 'group': 'Debug', 'order': 10000+next_seq(), 'desc': 'Use this to ramp up the logging (with indentation)',
                                    'schema': { 'type': 'integer' }})

@local_action({ 'group': 'Debug', 'order': 10000+next_seq() })
def RaiseLogLevel():
  local_event_LogLevel.emit((local_event_LogLevel.getArg() or 0) + 1)

@local_action({ 'group': 'Debug', 'order': 10000+next_seq() })
def LowerLogLevel():
  local_event_LogLevel.emit(max((local_event_LogLevel.getArg() or 0) - 1, 0))

def warn(level, msg):
  if (local_event_LogLevel.getArg() or 0) >= level:
    console.warn(('  ' * level) + msg)

def log(level, msg):
  if (local_event_LogLevel.getArg() or 0) >= level:
    console.log(('  ' * level) + msg)

# --!>