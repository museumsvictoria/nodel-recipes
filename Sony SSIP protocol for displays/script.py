'''
_(rev 4)_

**Sony SSIP & IRCC protocols** for displays

* Tested with Sony FW-85BZ40H

Resources:

 * the script contains some protocol examples, otherwise see [command-definitions](https://pro-bravia.sony.net/develop/integrate/ssip/command-definitions/), [ip-control](https://pro-bravia.sony.net/develop/integrate/ip-control/)
 
_rev 4: exclusive IR control_

'''

DEFAULT_TCPPORT = 20060

param_disabled = Parameter({ 'schema': { 'type': 'boolean' }})

param_ipAddress = Parameter({ 'schema': { 'type': 'string' }})

param_macAddress = Parameter({ 'schema': { 'type': 'string' }})

param_inputsInUse = Parameter({ 'title': 'Inputs In Use', 'schema': { 'type': 'array', 'items': { 'type': 'object', 'properties': {
  'code': { 'type': 'string', 'hint': '(e.g. "10000000x" is HDMIx)', 'order': 1 },
  'label': { 'type': 'string', 'order': 2 }}}}})

param_PresharedKey = Parameter({ 'title': 'Preshared-key (if used)', 'schema': { 'type': 'string' } })

# This recipe primarily uses synchronous operations but handles async NOTIFY packets that can arrive at any time.
#
# Sony packet structure: msgType: 'C'ontrol, 'E'nquire, 'A'nswer, 'N'otify
#                        cmd: 4 bytes
#                        params: 16 bytes
#
# NOTE: an 'A' can result from a 'C' and 'E' and an 'N' can arrivate asynchronously
#
#  e.g. Power Off: >> *S-C-POWR-0000000000000000   # (hyphens have been added for readability here)
#                  << *S-A-POWR-0000000000000000   # answer 
#                  << *S-N-POWR-0000000000000000   # notify
#
# This screen did NOT like overlapping commands which caused corrupted responses e.g. PARAMS part was part of wrong CMDs

def main():
  if param_disabled:
    return console.warn('Disabled! nothing to do')
  
  if is_blank(param_ipAddress):
    return console.warn('No IP address set; nothing to do')
  
  initInputsInUse()
  
  dest = '%s:%s' % (param_ipAddress, DEFAULT_TCPPORT)
  
  local_event_TCPConnection.emit('Disconnected')
  
  console.info('Will connect to [%s]' % dest)
  _tcp.setDest(dest)
  
def initInputsInUse():
  if len(param_inputsInUse or EMPTY) == 0:
    return console.info('NOTE: No "Inputs In Use" were configured')
  
  for info in param_inputsInUse:
    initInputInUse(info)
    
def initInputInUse(info):
  code = info['code']
  label = info['label']
  
  e = Event('Input %s' % code, { 'title': '%s ("%s")' % (code, label), 'group': 'Inputs In Use', 'order': next_seq(), 'schema': { 'type': 'boolean' }})
  
  def handler(arg):    
    if 'On' not in local_event_Power.getArg():
      console.info('Input%s "%s" called, power was not on, powering on!' % (code, label))
      Power.call('On')
    else:
      console.info('Input%s "%s" called' % (code, label))
      
    Input.call(code)
  
  a = Action('Input %s' % code, handler, {  'title': '%s ("%s")' % (code, label), 'group': 'Inputs In Use', 'order': next_seq() })
  
  local_event_Input.addEmitHandler(lambda arg: e.emit(code in arg))

# <!-- operations, protocols & TCP

HEADER = '*S'
SUCCESS = '0000000000000000' # a code indicating success of SET (CONTROL) operations

# holds all the parse functions to call when NOTIFY messages arrive
_notifyHandlers_byCmd = { } # e.g. { 'POWR': handler_func(params) }  

# <!-- power

local_event_RawPower = LocalEvent({ 'group': 'Power', 'order': next_seq(), 'schema':  { 'type': 'string' }})

local_event_DesiredPower = LocalEvent({ 'group': 'Power', 'order': next_seq(), 'schema':  { 'type': 'string', 'enum': [ 'On', 'Off' ] }})

local_event_Power = LocalEvent({ 'group': 'Power', 'order': next_seq(), 'schema':  { 'type': 'string', 'enum': [ 'On', 'Off', 'Partially On', 'Partially Off' ] }})
local_event_PowerOn = LocalEvent({ 'group': 'Power', 'order': next_seq(), 'schema': { 'type': 'boolean' } })
local_event_PowerOff = LocalEvent({ 'group': 'Power', 'order': next_seq(), 'schema': { 'type': 'boolean' } })

def handlePowerParams(params):
  if params == '0000000000000000':   arg = 'Off'
  elif params == '0000000000000001': arg = 'On'
  else:
    console.warn('parse_power_params: unknown resp - %s' % params)
    
  local_event_RawPower.emit(arg)
    
_notifyHandlers_byCmd['POWR'] = handlePowerParams
  
@local_action({ 'group': 'Power', 'order': next_seq() })
def EnquirePower():
  sonyEnquire('POWR', handlePowerParams)
  
timer_enquirePower = Timer(lambda: EnquirePower.call(), 6, stopped=True) # every 6s  

@after_main
def evalPower():
  def handler(ignore):
    raw, desired = local_event_RawPower.getArg(), local_event_DesiredPower.getArg()
    
    if raw == None:       return
    elif desired == None: arg = raw
    elif raw == desired:  arg = raw
    else:                 arg = 'Partially %s' % desired
      
    local_event_Power.emit(arg)
    local_event_PowerOn.emit('On' in arg)
    local_event_PowerOff.emit('Off' in arg)
      
  local_event_DesiredPower.addEmitHandler(handler)
  local_event_RawPower.addEmitHandler(handler)

@local_action({ 'group': 'Power', 'order': next_seq(), 'schema':  { 'type': 'string', 'enum': [ 'On', 'Off' ] }})
def Power(arg):
  # e.g. Power Off: >> *SCPOWR0000000000000000
  #                 << *SAPOWR0000000000000000
  # (and again?     << *SNPOWR0000000000000000
  
  sArg = str(arg).lower()
  
  if sArg in [ '1', 'true', 'on' ]: state = True
  elif sArg in [ '0', 'false', 'off' ]: state = False
  else: return console.warn('Power: unknown arg - %s' % arg)

  console.info('Power(%s) called' % arg)
  
  global _lastIRCommand
  _lastIRCommand = system_clock() - 600000 # safely reset (600s is arbitrary, allows for integer rollover)
  
  local_event_DesiredPower.emit('On' if state else 'Off')
  timer_powerSync.setDelay(0.01)
  
@local_action({ 'group': 'Power', 'order': next_seq() })
def PowerOn(arg):
  Power.call('On')
  
@local_action({ 'group': 'Power', 'order': next_seq() })
def PowerOff(arg):
  Power.call('Off')
  
def syncPower():
  desired = local_event_DesiredPower.getArg()
  raw = local_event_RawPower.getArg()
  
  now = date_now()
  lastAction = Power.getTimestamp() or date_parse('1990')
  diff = now.getMillis() - lastAction.getMillis()
  
  if diff > 60000:
    log(1, 'syncPower: been more than 60s since action, setting interval to 60s')
    timer_powerSync.setInterval(60)
    return
  
  if desired == None:
    return log(1, 'syncPower: desired is not set, nothing to do')
  
  if raw == desired:
    return log(1, 'syncPower: raw is same as desired "%s", so nothing to do' % raw)
  
  # desired different to raw
  if desired == 'On':
    log(1, 'syncPower: desired is On so will attempt to turn on...')
    sonyControl('POWR', '0000000000000001', lambda: EnquirePower.call()) # calls EnsuirePower onsuccess only!
  elif desired == 'Off':
    log(1, 'syncPower: desired is Off so will attempt to turn off...')
    sonyControl('POWR', '0000000000000000', lambda: EnquirePower.call())
    
  log(1, 'syncPower: will check again in 5s...')    
  timer_powerSync.setInterval(5)
  
timer_powerSync = Timer(syncPower, 60, stopped=True) # every min

# -->

# <!-- input

local_event_RawInput = LocalEvent({ 'group': 'Input', 'order': next_seq(), 'schema':  { 'type': 'string' }})

local_event_DesiredInput = LocalEvent({ 'group': 'Input', 'order': next_seq(), 'schema':  { 'type': 'string' }})

local_event_Input = LocalEvent({ 'group': 'Input', 'order': next_seq(), 'schema':  { 'type': 'string' }})

@after_main
def evalInput():
  def handler(ignore):
    raw, desired = local_event_RawInput.getArg(), local_event_DesiredInput.getArg()
    
    if raw == None:
      return
    elif 'On' not in local_event_Power.getArg():
      arg = 'Unknown'
    elif desired == None:
      arg = raw
    elif raw == desired:
      arg = raw
    else:
      arg = 'Partially %s' % desired
      
    local_event_Input.emit(arg)
      
  local_event_DesiredInput.addEmitHandler(handler)
  local_event_RawInput.addEmitHandler(handler)
  local_event_Power.addEmitHandler(handler)

@local_action({ 'group': 'Input', 'order': next_seq(), 'schema':  { 'type': 'string', 'hint': '(e.g. "100000001" is HDMI1)' }})
def Input(arg):
  if is_blank(arg):
    return console.warn('Input - arg was blank')
    
  console.info('Input(%s) called' % arg)
  
  global _lastIRCommand
  _lastIRCommand = system_clock() - 600000 # safely reset (600s is arbitrary, allows for integer rollover)
  
  local_event_DesiredInput.emit(arg)
  timer_inputSync.setDelay(0.01)
    
def syncInput():
  desired = local_event_DesiredInput.getArg()
  raw = local_event_RawInput.getArg()
  
  now = date_now()
  
  if (system_clock() - _lastIRCommand) < 60000:
    log(1, 'syncInput: been less 60s since last IR action, will not do anything')
    return
  
  lastAction = Input.getTimestamp() or date_parse('1990')
  diff = now.getMillis() - lastAction.getMillis()
  
  if diff > 60000:
    log(1, 'syncInput: been more than 60s since action, setting interval to 60s')
    timer_inputSync.setInterval(60)
    return
  
  if desired == None:
    return log(1, 'syncInput: desired is not set, nothing to do')
  
  if raw == desired:
    return log(1, 'syncInput: raw is same as desired "%s", so nothing to do' % raw)
  
  # desired different to raw
  sonyControl('INPT', str(desired).zfill(16), lambda: EnquireInput.call()) # will call EnquireInput on success only!
    
  log(1, 'syncInput: will check again in 5s...')    
  timer_inputSync.setInterval(5)
  
timer_inputSync = Timer(syncInput, 60, stopped=True) # every min

def handleInputParams(params):
  if params == 'FFFFFFFFFFFFFFFF':
    local_event_RawInput.emit(params)
  else:
    local_event_RawInput.emit(str(int(params)))
  
_notifyHandlers_byCmd['INPT'] = handleInputParams
  
@local_action({ 'group': 'Input', 'order': next_seq() })
def EnquireInput():
  if local_event_Power.getArg() == 'On':
    sonyEnquire('INPT', handleInputParams)
  
timer_enquireInput = Timer(lambda: EnquireInput.call(), 6, 3, stopped=True) # every 6s  

# -->
  
# <!-- audio volume

local_event_AudioVolume = LocalEvent({ 'group': 'Audio Volume', 'order': next_seq(), 'schema': { 'type': 'integer' }})

def handleAudioVolumeParams(params):
  local_event_AudioVolume.emit(int(params))
  
_notifyHandlers_byCmd['VOLU'] = handleAudioVolumeParams

@local_action({ 'group': 'Audio Volume', 'order': next_seq() })
def EnquireAudioVolume():
  if local_event_Power.getArg() == 'On':
    sonyEnquire('VOLU', handleAudioVolumeParams)
  
timer_enquireAudioVoume = Timer(lambda: EnquireAudioVolume.call(), 6, 1, stopped=True) # every 6s, stagger first time

@local_action({ 'group': 'Audio Volume', 'order': next_seq(), 'schema': { 'type': 'integer' }})
def AudioVolume(arg):
  if arg == None:
    return console.warn('AudioVolume - arg was blank')
  
  sonyControl('VOLU', str(arg).zfill(16), lambda: EnquireAudioVolume.call())
  
# -->

# <!-- audio mute

local_event_AudioMute = LocalEvent({ 'group': 'Audio Mute', 'order': next_seq(), 'schema': { 'type': 'boolean' }})

def handleAudioMuteParams(params):
  local_event_AudioMute.emit(int(params) == 1)
  
_notifyHandlers_byCmd['AMUT'] = handleAudioMuteParams  

@local_action({ 'group': 'Audio Mute', 'order': next_seq() })
def EnquireAudioMute():
  if local_event_Power.getArg() == 'On':
    sonyEnquire('AMUT', handleAudioMuteParams)
  
timer_enquireAudioMute = Timer(lambda: EnquireAudioMute.call(), 6, 5, stopped=True) # every 6s, stagger first time

@local_action({ 'group': 'Audio Mute', 'order': next_seq(), 'schema': { 'type': 'boolean' }})
def AudioMute(arg):
  sArg = str(arg).lower()
  
  if sArg in [ '1', 'true', 'on' ]:     state = True
  elif sArg in [ '0', 'false', 'off' ]: state = False
  else:
    return console.warn('Unknown arg - %s' % arg)
  
  console.info('AudioMute(%s) called' % arg)
  sonyControl('AMUT', str('1' if state else '0').zfill(16), lambda: EnquireAudioMute.call())
  
@local_action({ 'group': 'Audio Mute', 'order': next_seq() })
def AudioMuteOn():
  AudioMute.call(True)
  
@local_action({ 'group': 'Audio Mute', 'order': next_seq() })
def AudioMuteOff():
  AudioMute.call(False)
  
# -->

# <!--- IR control using the IRCC protocol

# see https://pro-bravia.sony.net/develop/integrate/ircc-ip/ircc-codes/index.html

# curl example:
# curl http://10.78.0.191/sony/ircc -H "X-Auth-PSK: ddffmmggmmddbb33" -H "Content-Type: text/xml; charset=UTF-8" -H "SOAPACTION: \"urn:schemas-sony-com:service:IRCC:1#X_SendIRCC\"" -d @packet.xml -v

IR_SOAP_BODY = '''<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
                    <s:Body><u:X_SendIRCC xmlns:u="urn:schemas-sony-com:service:IRCC:1">
                      <IRCCCode>$IRCODE</IRCCCode>
                    </u:X_SendIRCC></s:Body></s:Envelope>'''

IR_CODE_TABLE =  '''Power AAAAAQAAAAEAAAAVAw==       | Input AAAAAQAAAAEAAAAlAw==      | SyncMenu AAAAAgAAABoAAABYAw== | Hdmi1 AAAAAgAAABoAAABaAw==     | 
                    Hdmi2 AAAAAgAAABoAAABbAw==       | Hdmi3 AAAAAgAAABoAAABcAw==      | Hdmi4 AAAAAgAAABoAAABdAw==    | Num1 AAAAAQAAAAEAAAAAAw==      | 
                    Num2 AAAAAQAAAAEAAAABAw==        | Num3 AAAAAQAAAAEAAAACAw==       | Num4 AAAAAQAAAAEAAAADAw==     | 
                    Num5 AAAAAQAAAAEAAAAEAw==        | Num6 AAAAAQAAAAEAAAAFAw==       | Num7 AAAAAQAAAAEAAAAGAw==     | Num8 AAAAAQAAAAEAAAAHAw==      | 
                    Num9 AAAAAQAAAAEAAAAIAw==        | Num0 AAAAAQAAAAEAAAAJAw==       | Dot(.) AAAAAgAAAJcAAAAdAw==   | CC AAAAAgAAAJcAAAAoAw==        | 
                    Red AAAAAgAAAJcAAAAlAw==         | Green AAAAAgAAAJcAAAAmAw==      | Yellow AAAAAgAAAJcAAAAnAw==   | Blue AAAAAgAAAJcAAAAkAw==      |
                    Up AAAAAQAAAAEAAAB0Aw==          | Down AAAAAQAAAAEAAAB1Aw==       | Right AAAAAQAAAAEAAAAzAw==    | Left AAAAAQAAAAEAAAA0Aw==      | 
                    Confirm AAAAAQAAAAEAAABlAw==     | Help AAAAAgAAAMQAAABNAw==       | Display AAAAAQAAAAEAAAA6Aw==  | 
                    Options AAAAAgAAAJcAAAA2Aw==     | Back AAAAAgAAAJcAAAAjAw==       | Home AAAAAQAAAAEAAABgAw==     | VolumeUp AAAAAQAAAAEAAAASAw==  | 
                    VolumeDown AAAAAQAAAAEAAAATAw==  | Mute AAAAAQAAAAEAAAAUAw==       | Audio AAAAAQAAAAEAAAAXAw==    | ChannelUp AAAAAQAAAAEAAAAQAw== | 
                    ChannelDown AAAAAQAAAAEAAAARAw== | Play AAAAAgAAAJcAAAAaAw==       | Pause AAAAAgAAAJcAAAAZAw==    | Stop AAAAAgAAAJcAAAAYAw==      | 
                    FlashPlus AAAAAgAAAJcAAAB4Aw==   | FlashMinus AAAAAgAAAJcAAAB5Aw== | Prev AAAAAgAAAJcAAAA8Aw==     | Next AAAAAgAAAJcAAAA9Aw==''' # use '|' as row delimiter

IR_CMDS_AND_CODES = [ line.strip().split(' ') for line in IR_CODE_TABLE.split('|') ]
IR_CMDS = [ cmd for cmd, code in IR_CMDS_AND_CODES ]
IRCODES_byCmd = dict(IR_CMDS_AND_CODES)

_lastIRCommand = system_clock() - 600000 # safe init, the 600s is arbitrary

@after_main
def initIRCodes():
  for cmd in IR_CMDS:
    initIRCode(cmd)
    
def initIRCode(cmd):
  code = IRCODES_byCmd[cmd]
  
  def handler(ignore):
    console.info('IR %s called' % cmd)
    headers = { 'SOAPACTION': '"urn:schemas-sony-com:service:IRCC:1#X_SendIRCC"' }
    if not is_blank(param_PresharedKey):
      headers['X-Auth-PSK'] = param_PresharedKey
      
    get_url('http://%s/sony/ircc' % param_ipAddress, headers=headers, 
            contentType='text/xml; charset=UTF-8', 
            post=IR_SOAP_BODY.replace('$IRCODE', code))
    
    global _lastIRCommand
    _lastIRCommand = system_clock()
  
  a = Action('IR %s' % cmd, handler, { 'title': '"%s"' % cmd, 'order': next_seq(), 'group': 'IR commands' })

# -->

_wol = UDP(dest='255.255.255.255:9999',
          sent=lambda arg: console.info('wol: sent packet (size %s)' % len(arg)),
          ready=lambda: console.info('wol: ready'), received=lambda arg: console.info('wol: received [%s]'))

@local_action({'group': 'Power', 'order': next_seq()})
def SendWOLPacket(arg=None):
  console.info('SendWOLPacket')
  
  hw_addr = param_macAddress.replace('-', '').replace(':', '').decode('hex')
  macpck = '\xff' * 6 + hw_addr * 16
  _wol.send(macpck)

def sonyEnquire(cmd, onAnswer):
  '''msgType: ... 'E'nquire ...
     cmd: 4 bytes
     params: 16 bytes'''
  log(1, 'sony_enquire: cmd:%s' % cmd)
  
  parts = [ HEADER, 'E', cmd, '################', '\n' ]
  buffer = ''.join(parts)
  
  def handle_resp(resp):
    log(1, 'sony_enquire_handle_resp: resp:%s' % resp)
    msgType, respCmd, params = parseSonyBuffer(resp)
    
    if msgType == 'N':
      # trap, allow to pass through to notify handler via tcp_recv
      # but try receive next one (call itself again)
      _tcp.receive(handle_resp)
      
    elif msgType == 'A' and respCmd == cmd:
      # got an answer to the cmd
      onAnswer(params)
      
    else:
      console.warn('sony_enquire_handle_resp: unexpected response to cmd %s; was %s' % (cmd, respCmd))
  
  _tcp.request(buffer, handle_resp)
    
def sonyControl(cmd, params, onSuccess):
  '''msgType: ... 'C'ontrol ...
     cmd: 4 bytes
     params: 16 bytes'''
  log(1, 'sony_control: cmd:%s params:%s' % (cmd, params))
    
  parts = [ HEADER, 'C', cmd, params, '\n' ]
  buffer = ''.join(parts)
  
  def handle_resp(resp):
    log(1, 'sony_control_handle_resp: resp:%s' % resp)
    msgType, respCmd, params = parseSonyBuffer(resp)
    
    if msgType == 'N':
      # trap, allow to pass through to notify handler via tcp_recv
      # but try receive next one (call itself again)
      
      # keep receiving (call itself again)
      _tcp.receive(handle_resp)
      
    elif msgType == 'A' and respCmd == cmd:
      # got an answer to the cmd
      if params == SUCCESS:
        onSuccess()
      else:
        console.warn('sony_control_handle_resp: cmd %s with params %s did not return success i.e. FAILED' % (cmd, params))
      
    else:
      console.warn('sony_control_handle_resp: unexpected response to cmd %s; was %s' % (cmd, respCmd))
  
  _tcp.request(buffer, handle_resp)               
  
def handleNotifyMessage(cmd, params):
  console.info('Display Notify received - cmd:%s params:%s' % (cmd, params))
  
  handler = _notifyHandlers_byCmd.get(cmd)
  
  if handler:
    handler(params)
  else:
    console.warn('Ignoring unknown notify message %s. Had params %s' % (cmd, params))

def parseSonyBuffer(buffer):
  '''sonyBuffer has been prechecked for header, footer and length'''
  #  e.g. << *S-A-POWR-0000000000000000   # answer (hyphens are excluded)
  #       << *S-N-POWR-0000000000000000   # notify
  # or
  #       << *S-A-POWR-0000000000000001
  header = buffer[0:2] # will dispose of anyway
  msgType = buffer[2]
  cmd = buffer[3:7]
  params = buffer[7:]
               
  return msgType, cmd, params

local_event_TCPConnection = LocalEvent({ 'group': 'Comms', 'schema': { 'type': 'string', 'enum': [ 'Connected', 'Disconnected' ]}})

def tcp_connected():
  console.info('tcp_connected - will start pollers')
  local_event_TCPConnection.emit('Connected')
  _tcp.clearQueue()
  startTimers()

def startTimers():
  timer_enquirePower.start()
  timer_enquireAudioVoume.start()
  timer_enquireAudioMute.start()
  timer_enquireInput.start()
  
  timer_powerSync.start()
  timer_inputSync.start()
  
def tcp_received(raw):
  data = raw.strip()
  
  if len(data) != 23:
    return log(1, 'tcp_recv: ignoring, bad length - [%s]' % data)
  
  log(3, 'tcp_recv [%s]' % data)
  if not data.startswith('*S'):
    return log(1, 'tcp_recv: ignoring, did not start with correct header')
  
  global _lastReceive
  _lastReceive = system_clock()
  
  msgType, cmd, params = parseSonyBuffer(data)
  if msgType == 'N':
    handleNotifyMessage(cmd, params)
    
  # otherwise everything else is handle syncronously by the Equire and Control (set)

def tcp_sent(data):
  log(3, 'tcp_sent [%s]' % data.strip())
  
def tcp_disconnected():
  console.warn('tcp_disconnected - pollers stopped')  
  local_event_TCPConnection.emit('Disconnected')
  
  timer_enquirePower.stop()
  timer_enquireAudioVoume.stop()
  timer_enquireAudioMute.stop()
  timer_enquireInput.stop()
  
  timer_powerSync.stop()
  timer_inputSync.stop()
  
def tcp_timeout():
  console.warn('tcp_timeout, recycling connection')
  _tcp.drop()
  _tcp.clearQueue()

_tcp = TCP(connected=tcp_connected, received=tcp_received, sent=tcp_sent, disconnected=tcp_disconnected, timeout=tcp_timeout,
           sendDelimiters='\n', receiveDelimiters='\n')

# --- tcp>


# <logging ---

local_event_LogLevel = LocalEvent({'group': 'Debug', 'order': 10000+next_seq(), 'schema': {'type': 'integer'}})

def warn(level, msg):
  if (local_event_LogLevel.getArg() or 0) >= level:
    console.warn(('  ' * level) + msg)

def log(level, msg):
  if (local_event_LogLevel.getArg() or 0) >= level:
    console.log(('  ' * level) + msg)    

# --->


# <status and error reporting ---

# for comms drop-out
_lastReceive = system_clock() - 999999L

# roughly, the last contact  
local_event_LastContactDetect = LocalEvent({'group': 'Status', 'order': 99999+next_seq(), 'title': 'Last contact detect', 'schema': {'type': 'string'}})

# node status
local_event_Status = LocalEvent({'group': 'Status', 'order': 99999+next_seq(), 'schema': { 'type': 'object', 'properties': {
        'level': { 'type': 'integer', 'order': 1 },
        'message': { 'type': 'string', 'order': 2 }}}})
  
def statusCheck():
  diff = (system_clock() - _lastReceive)/1000.0 # (in secs)
  now = date_now()
  
  if diff > (status_check_interval*2):
    previousContactValue = local_event_LastContactDetect.getArg()
    
    if previousContactValue == None:
      message = 'Always been missing'
      
    else:
      previousContact = date_parse(previousContactValue)
      message = 'Missing %s' % formatPeriod(previousContact)
      
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
  else:                     return 'since %s' % dateObj.toString('E d-MMM h:mm a')

# --->
