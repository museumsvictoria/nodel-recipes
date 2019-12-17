'''NEC LCD'''

# taken from there (large) manuals:
# *  Product manual with plain example strings
#     - http://www.support.nec-display.com/dl_service/data/display_en/manual/x555uns/X555UNS_X555UNV_UN551S_UN551VS_manual_EN_v5.pdf
#
# * More detailed RS232 protocol:
#     - http://au.nec.com/en_AU/media/docs/products/displays/V801-TM_ExternalControl.pdf

DEFAULT_TCPPORT = 7142

param_Disabled = Parameter({'schema': {'type': 'boolean'}})

param_IPAddress = Parameter({'title': 'IP address', 'schema': {'type': 'string'}})

DEFAULT_MONITORID = 1
param_MonitorID = Parameter({'schema': {'type': 'integer', 'hint': DEFAULT_MONITORID}})

param_PowerOnInput = Parameter({'title': '"Power On" Input', 'desc': 'Select this input when Power On is called.', 'order': next_seq(), 'schema': {'type': 'string'}})

@after_main
def validate_parameters():
  global param_MonitorID
  
  if param_MonitorID == None:
    param_MonitorID = DEFAULT_MONITORID

# <main ---
  
def main():
  if param_Disabled:
    console.warn('Disabled! nothing to do')
    return
  
  if is_blank(param_IPAddress):
    console.warn('No IP address set; nothing to do')
    return
  
  dest = '%s:%s' % (param_IPAddress, DEFAULT_TCPPORT)
  
  local_event_TCPConnection.emit('Disconnected')
  
  console.info('Will connect to [%s]' % dest)
  tcp.setDest(dest)

# --->

# <power ---
local_event_Power = LocalEvent({'group': 'Power', 'order': next_seq(), 'schema': {'type': 'string', 'enum': ['On', 'Partially On',  'Partially Off', 'Off']}})

local_event_DesiredPower = LocalEvent({'group': 'Power', 'order': next_seq(), 'schema': {'type': 'string', 'enum': ['On', 'Off']}})

@local_action({'group': 'Power', 'order': next_seq(), 'schema': {'type': 'string', 'enum': ['On', 'Off']}})
def power(arg):
  console.info('Power(%s) called' % arg)
  
  local_event_DesiredPower.emit(arg)
  lookup_local_action('forcePower').call(arg)
  
  timer_powerSyncer.start()
  
@after_main
def bindPowerSignals():
  rawPower = lookup_local_event('RawPower')
  desiredPower = lookup_local_event('DesiredPower')
  power = lookup_local_event('Power')
  
  powerAction = lookup_local_action('Power')
  
  def onChange(arg):
    desiredPowerState = desiredPower.getArg()
    rawPowerState = rawPower.getArg()
    
    # re-interpret raw power state
    if rawPowerState in ['Stand-By', 'Suspend']:
      rawPowerState = 'Off'
    
    powerTimestamp = powerAction.getTimestamp()
    diff = date_now().getMillis() - (powerTimestamp.getMillis() if powerTimestamp != None else 0)
    if diff > 60000: # more than a minute, ignore
      power.emit(rawPowerState)
      
    elif desiredPowerState == 'On':
      if rawPowerState == 'On':
        power.emit('On')
      else:
        power.emit('Partially On')
        
    elif desiredPowerState == 'Off':
      if rawPowerState == 'Off':
        power.emit('Off')
      else:
        power.emit('Partially Off')

    else:
      power.emit(rawPowerState)
    
  rawPower.addEmitHandler(onChange)
  desiredPower.addEmitHandler(onChange)
  
def powerSyncer():
  powerTimestamp = power.getTimestamp()
  diff = date_now().getMillis() - (powerTimestamp.getMillis() if powerTimestamp != None else 0)
  if diff > 60000: # more than a minute, ignore
    console.warn('power_sync: been more than 60s, aborting power sync')
    timer_powerSyncer.stop()
    return
  
  rawArg = lookup_local_event('RawPower').getArg()
  desiredArg = lookup_local_event('DesiredPower').getArg()
  
  if desiredArg != None and rawArg != desiredArg:
    console.warn('power_sync: power states are different; will try force(raw: %s, desired: %s)' % (rawArg, desiredArg))
    lookup_local_action('forcePower').call(desiredArg)
    
  else:
    console.info('power_sync: power states are same (or not present); syncer will shutdown after a 15s stability period')
    
  if diff > 15000:
    console.info('power_sync: syncer shut down')
    timer_powerSyncer.stop()
    return

timer_powerSyncer = Timer(powerSyncer, 5, stopped=True)

@after_main
def bindPowerOnInput():
  if is_blank(param_PowerOnInput):
    return
  
  console.info('Config: will select input "%s" when Power On occurs' % param_PowerOnInput)
  
  def handler(arg):
    if arg == 'On':
      console.info('Automatically selecting input "%s" if not selected' % param_PowerOnInput)
      input.call(param_PowerOnInput)
    
  lookup_local_action('Power').addCallHandler(handler)

# --->

# <input ---

local_event_Input = LocalEvent({'group': 'Input', 'order': next_seq(), 'schema': {'type': 'string'}})

local_event_DesiredInput = LocalEvent({'group': 'Input', 'order': next_seq(), 'schema': {'type': 'string'}})

@local_action({'group': 'Input', 'order': next_seq(), 'schema': {'type': 'string'}})
def input(arg):
  console.info('Input("%s") called' % arg)
  
  local_event_DesiredInput.emit(arg)
  lookup_local_action('forceInput').call(arg)
  
  timer_inputSyncer.start()
  
@after_main
def bindInputSignals():
  rawInput = lookup_local_event('RawInput')
  desiredInput = lookup_local_event('DesiredInput')
  input = lookup_local_event('Input')
  inputAction = lookup_local_action('Input')
  
  def onChange(arg):
    desiredInputState = desiredInput.getArg()
    rawInputState = rawInput.getArg()
    
    inputTimestamp = inputAction.getTimestamp()
    diff = date_now().getMillis() - (inputTimestamp.getMillis() if inputTimestamp != None else 0)
    if diff > 60000: # more than a minute, ignore
      input.emit(rawInputState)

    elif desiredInputState == None or rawInputState == None:
      input.emit(rawInputState or 'Unknown')
      return

    elif desiredInputState != rawInputState:
      input.emit('Partially %s' % desiredInputState)

    else:
      input.emit(rawInputState)
    
  rawInput.addEmitHandler(onChange)
  desiredInput.addEmitHandler(onChange)
  
def inputSyncer():
  inputTimestamp = input.getTimestamp()
  diff = date_now().getMillis() - (inputTimestamp.getMillis() if inputTimestamp != None else 0)
  if diff > 60000: # more than a minute, ignore
    console.warn('input_sync: been more than 60s, aborting input sync')
    timer_inputSyncer.stop()
    return
  
  rawArg = lookup_local_event('RawInput').getArg()
  desiredArg = lookup_local_event('DesiredInput').getArg()
  
  if desiredArg != None and rawArg != desiredArg:
    console.warn('input_sync: input states are different; will try force(raw: %s, desired: %s)' % (rawArg, desiredArg))
    lookup_local_action('forceInput').call(desiredArg)
    
  else:
    console.info('input_sync: input states are same (or not present); syncer will shutdown after a 15s stability period')
    
  if diff > 15000:
    console.info('input_sync: syncer shut down')
    timer_inputSyncer.stop()
    return

timer_inputSyncer = Timer(inputSyncer, 5, stopped=True)

# --->


# <protocol & operations ---

SOH = '\x01'
STX = '\x02'
ETX = '\x03'

MSGTYPE_CMD       = 'A'
MSGTYPE_CMD_REPLY = 'B'
MSGTYPE_GET       = 'C'
MSGTYPE_GET_REPLY = 'D'
MSGTYPE_SET       = 'E'
MSGTYPE_SET_REPLY = 'F'

RESERVED = '0'
  
local_event_RawPower = LocalEvent({'group': 'Raw', 'order': next_seq(), 
                                   'schema': {'type': 'string', 'enum': ['On', 'Stand-By', 'Suspend', 'Off']}})
  
@local_action({'group': 'Raw', 'order': next_seq(), 'schema': {'type': 'string', 'enum': ['On', 'Off']}})
def forcePower(arg):
  ctx = 'forcePower'
  log(1, ctx)
  
  idd = chr(ord('A') + param_MonitorID-1)
  SRC = '0'
  
  msgLen = '0C'
  
  header =    SOH + RESERVED + idd + SRC + MSGTYPE_CMD + msgLen
  
  power = '0001' if arg == 'On' else '0004'
  
  preCmd = header +    STX+'C203D6'+ power +ETX
  
  cmd = preCmd + chk(preCmd)
  
  def handleResp(resp):
    # e.g. SOH-'0'-'0'-Monitor ID-'B'-'0'-'E'
    #      STX-'0'-'0'-'C'-'2'-'0'-'3'-'D'-'6'-'0'-'0'-'0'-'1'-ETX
    resultCode = resp[7:9]
    if resultCode != '00':
      console.warn('%s: result code was not NO ERROR [%s]' % (ctx, resp))
      return
    
    lastReceive[0] = system_clock() # protocol ok
    
    powerMode = resp[15:19]
    
    if powerMode == '0001':
      local_event_RawPower.emit('On')
      
    elif powerMode == '0003':
      # suspend (power save)
      local_event_RawPower.emit('Suspend')
      
    elif powerMode == '0004':
      # off (same as IR power off)
      local_event_RawPower.emit('Off')
      
    else:
      console.warn('%s: unknown power mode [%s]' % (ctx, powerMode))
  
  tcp.request(cmd, handleResp)  
  
@local_action({'group': 'Raw', 'order': next_seq()})
def forceGetPower():
  ctx = 'forceGetPower'
  log(1, ctx)
  
  idd = chr(ord('A') + param_MonitorID-1)
  
  header =    SOH+'0%s0A06' % (idd)
  
  preCmd = header +    STX+'01D6'+ETX
  
  cmd = preCmd + chk(preCmd)
  
  def handleResp(resp):
    # e.g. SOH-'0'-'0'-Monitor ID-'B'-'1'-'2'
    #      STX-'0'-'2'-'0'-'0'-'D'-'6'-'0'-'0'-'0'-'0'-'0'-'4'-'0'-'0'-'0'-'1'-ETX - BCC - CR
    resultCode = resp[9:11]
    if resultCode != '00':
      console.warn('%s: result code was not NO ERROR [%s]' % (ctx, resp))
      return
    
    lastReceive[0] = system_clock() # protocol ok
    
    powerMode = resp[19:23]
    
    if powerMode == '0001':
      local_event_RawPower.emit('On')
      
    elif powerMode == '0002': 
      # stand-by (power save)
      local_event_RawPower.emit('Stand-By')
      
    elif powerMode == '0003':
      # suspend (power save)
      local_event_RawPower.emit('Suspend')
      
    elif powerMode == '0004':
      # off (same as IR power off)
      local_event_RawPower.emit('Off')
      
    else:
      console.warn('%s: unknown power mode [%s]' % (ctx, powerMode))
  
  tcp.request(cmd, handleResp)
  
Timer(lambda: lookup_local_action('forceGetPower').call(), 15, 6)

def chk(data):
  toCheck = data[1:]
  
  x = 0
  for c in toCheck:
    x = x^ord(c)
    
  return chr(x)

local_event_RawInput = LocalEvent({'group': 'Raw', 'order': next_seq(), 
                                   'schema': {'type': 'string'}})

@local_action({'group': 'Raw', 'order': next_seq(), 'schema': {'type': 'string', 'hint': '11 (for HDMI)'}})
def forceInput(arg):
  # 01 30 41 30 45 30 41 02 30 30 36 30 30 30 31 31 03 72 0d'
  # SOH - 0 - A - 0 - E - 0 - A   STX - 00---60   0011  ETX
  #      RES-ID -SRC-SET-LENGTH   STX-  OPpg/code value
  
  ctx = 'forceInput'
  log(1, ctx)
  
  idd = chr(ord('A') + param_MonitorID-1)
  SRC = '0'
  
  msgLen = '0A'
  
  header =    SOH + RESERVED + idd + SRC + MSGTYPE_SET + msgLen
  
  OPPAGE_OPCODE = '0060'
  
  inputt = '00' + arg
  
  preCmd = header +    STX+OPPAGE_OPCODE+ inputt +ETX
  
  cmd = preCmd + chk(preCmd)
  
  def handleResp(resp):
    #      SOH    0   0    A         F   1   2
    #      STX - 00     - 00         - 60       - 00   - 0088 - 0011
    #          - RESULT - OPCODEPAGE - OPCODE   - TYPE - MAX  - VALUE
    #
    # e.g. SOH-'0'-'0'-Monitor ID-'B'-'0'-'E'
    #      STX-'0'-'0'-'C'-'2'-'0'-'3'-'D'-'6'-'0'-'0'-'0'-'1'-ETX
    resultCode = resp[7:9]
    if resultCode != '00':
      console.warn('%s: result code was not NO ERROR [%s]' % (ctx, resp))
      return
    
    lastReceive[0] = system_clock() # protocol ok
    
    local_event_RawInput.emit(resp[21:23])
  
  tcp.request(cmd, handleResp)
  
@local_action({'group': 'Raw', 'order': next_seq()})
def forceGetInput(arg):
  ctx = 'forceGetInput'
  log(1, ctx)
  
  idd = chr(ord('A') + param_MonitorID-1)
  SRC = '0'
  
  msgLen = '06'
  
  header = SOH + RESERVED + idd + SRC + MSGTYPE_GET + msgLen
  
  OPPAGE_OPCODE = '0060'
  preCmd = header +    STX+OPPAGE_OPCODE+ ETX
  cmd = preCmd + chk(preCmd)
  
  def handleResp(resp):
    #      SOH    0   0    A         F   1   2
    #      STX - 00     - 00         - 60       - 00   - 0088 - 0011
    #          - RESULT - OPCODEPAGE - OPCODE   - TYPE - MAX  - VALUE
    #
    # e.g. SOH-'0'-'0'-Monitor ID-'B'-'0'-'E'
    #      STX-'0'-'0'-'C'-'2'-'0'-'3'-'D'-'6'-'0'-'0'-'0'-'1'-ETX
    resultCode = resp[7:9]
    if resultCode != '00':
      console.warn('%s: result code was not NO ERROR [%s]' % (ctx, resp))
      return
    
    lastReceive[0] = system_clock() # protocol ok
    
    local_event_RawInput.emit(resp[21:23])
  
  tcp.request(cmd, handleResp)

Timer(lambda: lookup_local_action('forceGetInput').call(), 15, 6)
  

  
# volume ---
local_event_RawVolume = LocalEvent({'group': 'Raw', 'order': next_seq(), 'schema': {'type': 'integer'}})

@local_action({'group': 'Raw', 'order': next_seq(), 'schema': {'type': 'integer', 'min': 0, 'max': 100}})
def forceVolume(arg):
  ctx = 'forceVolume'
  log(1, ctx)
  idd = chr(ord('A') + param_MonitorID-1)
  SRC = '0'
  msgLen = '0A'
  header =    SOH + RESERVED + idd + SRC + MSGTYPE_SET + msgLen
  OPPAGE_OPCODE = '0062'
  
  vol = '00' + chr(arg).encode('hex') # (arg would be 0 - 100 integer)
  
  preCmd = header +    STX+OPPAGE_OPCODE+ vol + ETX
  cmd = preCmd + chk(preCmd)
  
  def handleResp(resp):
    resultCode = resp[7:9]
    if resultCode != '00':
      console.warn('%s: result code was not NO ERROR [%s]' % (ctx, resp))
      return
    
    lastReceive[0] = system_clock() # protocol ok
    
    rawHex = resp[21:23] # e.g. '64'
    local_event_RawVolume.emit(ord(rawHex.decode('hex')))
  
  tcp.request(cmd, handleResp)
  
@local_action({'group': 'Raw', 'order': next_seq()})
def forceGetVolume(arg):
  ctx = 'forceGetVolume'
  log(1, ctx)
  
  idd = chr(ord('A') + param_MonitorID-1)
  SRC = '0'
  msgLen = '06'
  header = SOH + RESERVED + idd + SRC + MSGTYPE_GET + msgLen
  
  OPPAGE_OPCODE = '0062'
  preCmd = header +    STX+OPPAGE_OPCODE+ ETX
  cmd = preCmd + chk(preCmd)
  
  def handleResp(resp):
    resultCode = resp[7:9]
    if resultCode != '00':
      console.warn('%s: result code was not NO ERROR [%s]' % (ctx, resp))
      return
    
    lastReceive[0] = system_clock() # protocol ok
    
    rawHex = resp[21:23] # e.g. '64'
    local_event_RawVolume.emit(ord(rawHex.decode('hex')))
  
  tcp.request(cmd, handleResp)

Timer(lambda: lookup_local_action('forceGetVolume').call(), 15, 6)

# managed doesn't differ much from raw in this case
local_event_Volume = LocalEvent({'group': 'Volume', 'order': next_seq(), 'schema': {'type': 'integer'}})

after_main(lambda: local_event_RawVolume.addEmitHandler(lambda arg: local_event_Volume.emit(arg))) 

@local_action({'group': 'Volume', 'order': next_seq(), 'schema': {'type': 'integer', 'min': 0, 'max': 100}})
def volume(arg):
  forceVolume.call(arg)

# volume -->

# <!--- mute

local_event_RawAudioMute = LocalEvent({'group': 'Raw', 'order': next_seq(), 'schema': {'type': 'boolean'}})

@local_action({'group': 'Raw', 'order': next_seq(), 'schema': {'type': 'boolean'}})
def forceAudioMute(arg):
  ctx = 'forceAudioMute'
  log(1, ctx)
  idd = chr(ord('A') + param_MonitorID-1)
  SRC = '0'
  msgLen = '0A'
  header =    SOH + RESERVED + idd + SRC + MSGTYPE_SET + msgLen
  OPPAGE_OPCODE = '008D'
  
  muteArg = '00' + chr(1 if arg else 2).encode('hex') 
  
  preCmd = header +    STX+OPPAGE_OPCODE+ muteArg + ETX
  cmd = preCmd + chk(preCmd)
  
  def handleResp(resp):
    resultCode = resp[7:9]
    if resultCode != '00':
      console.warn('%s: result code was not NO ERROR [%s]' % (ctx, resp))
      return
    
    lastReceive[0] = system_clock() # protocol ok
    
    rawHex = resp[21:23] # e.g. '64'
    
    muteValue = ord(rawHex.decode('hex')) == 1
    local_event_RawAudioMute.emit(muteValue)
  
  tcp.request(cmd, handleResp)
  
@local_action({'group': 'Raw', 'order': next_seq()})
def forceGetAudioMute(arg):
  ctx = 'forceGetAudioMute'
  log(1, ctx)
  
  idd = chr(ord('A') + param_MonitorID-1)
  SRC = '0'
  msgLen = '06'
  header = SOH + RESERVED + idd + SRC + MSGTYPE_GET + msgLen
  
  OPPAGE_OPCODE = '008D'
  preCmd = header + STX + OPPAGE_OPCODE + ETX
  cmd = preCmd + chk(preCmd)
  
  def handleResp(resp):
    resultCode = resp[7:9]
    if resultCode != '00':
      console.warn('%s: result code was not NO ERROR [%s]' % (ctx, resp))
      return
    
    lastReceive[0] = system_clock() # protocol ok
    
    rawHex = resp[21:23] # e.g. '64'
    muteValue = ord(rawHex.decode('hex')) == 1
    local_event_RawAudioMute.emit(muteValue)
  
  tcp.request(cmd, handleResp)    

Timer(lambda: forceGetAudioMute.call(), 15, 6)

local_event_AudioMute = LocalEvent({'group': 'Audio Mute', 'order': next_seq(), 'schema': {'type': 'boolean'}})

after_main(lambda: local_event_RawAudioMute.addEmitHandler(lambda arg: local_event_AudioMute.emit(arg))) 

@local_action({'group': 'Audio Mute', 'order': next_seq(), 'schema': {'type': 'boolean'}})
def AudioMute(arg):
  forceAudioMute.call(arg)

# mute ---!>


# --- protocol & operations>

  
# <tcp ---

local_event_TCPConnection = LocalEvent({'group': 'Comms', 'schema': {'type': 'string', 'enum': ['Connected', 'Disconnected']}})

  
def tcp_connected():
  console.info('tcp_connected')
  
  local_event_TCPConnection.emit('Connected')
  
  tcp.clearQueue()
  
def tcp_received(data):
  log(3, 'tcp_recv [%s]' % data)
  
def tcp_sent(data):
  log(3, 'tcp_sent [%s]' % data)
  
def tcp_disconnected():
  console.warn('tcp_disconnected')
  
  local_event_TCPConnection.emit('Disconnected')
  
def tcp_timeout():
  console.warn('tcp_timeout')

tcp = TCP(connected=tcp_connected, received=tcp_received, sent=tcp_sent, disconnected=tcp_disconnected, timeout=tcp_timeout,
          sendDelimiters='\r', receiveDelimiters='\r')

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
  
  if diff > (status_check_interval*2):
    previousContactValue = local_event_LastContactDetect.getArg()
    
    if previousContactValue == None:
      message = 'Always been missing'
      
    else:
      previousContact = date_parse(previousContactValue)
      message = 'Off the network %s' % formatPeriod(previousContact)
      
    local_event_Status.emit({'level': 2, 'message': message})
    
  else:
    # update contact info
    local_event_LastContactDetect.emit(str(now))
    local_event_Status.emit({'level': 0, 'message': 'OK'})
    
status_check_interval = 75
status_timer = Timer(statusCheck, status_check_interval)

def formatPeriod(dateObj):
  if dateObj == None:       return 'for unknown period'
  
  now = date_now()
  diff = (now.getMillis() - dateObj.getMillis()) / 1000 / 60 # in mins
  
  if diff == 0:             return 'for <1 min'
  elif diff < 60:           return 'for <%s mins' % diff
  elif diff < 60*24:        return 'since %s' % dateObj.toString('h:mm:ss a')
  else:                     return 'since %s' % dateObj.toString('E d-MMM h:mm:ss a')

# --->
