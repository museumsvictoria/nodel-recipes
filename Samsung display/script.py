'''Samsung serial driver - manual http://www.samsung.com/us/pdf/UX_DX.pdf'''

DEFAULT_TCP_PORT = 1515 # Samsung's default port
DEFAULT_SETID = 0

param_ipAddress = Parameter({"value":"192.168.100.1","title":"IP address","order":0, "schema":{"type":"string"}})
param_port = Parameter({"title": "TCP port", "order":0, "schema": {"type": "integer", 'hint': DEFAULT_TCP_PORT}})
param_id = Parameter({"title": "Set ID", "order": 0, "schema": {"type":"integer", 'hint': 0}})

param_mainInputCode = Parameter({'title': 'Main Input Code', 'desc': 'The input (source) for the "ensure" actions and events', 'schema': {'type': 'string'}})

local_event_DebugShowLogging = LocalEvent({'group': 'Debug', 'order': 9999, 'schema': {'type': 'boolean'}})

# general device status
local_event_Status = LocalEvent({'order': -100, 'group': 'Status', 'schema': {'type': 'object', 'title': '...', 'properties': {
        'level': {'type': 'integer', 'title': 'Value'},
        'message': {'type': 'string', 'title': 'String'}
      }}})

powerEvent = Event('Power', {'group': 'Power', 'order': next_seq(), 'schema': {'type': 'string', 'enum': ['On', 'Off']}})
local_event_DesiredPower = LocalEvent({'group': 'Power', 'order': next_seq(), 'schema': {'type': 'string', 'enum': ['On', 'Off']}})

local_event_Volume = LocalEvent({'group': 'Audio', 'order': next_seq(), 'schema': {'type': 'integer'}})
local_event_Mute = LocalEvent({'group': 'Audio', 'order': next_seq(), 'schema': {'type': 'string', 'enum': ['Mute', 'Unmute']}})

# this table is incomplete
INPUT_CODE_TABLE = [ ('1F', 'PC'),
                     ('1E', 'BNC'),
                     ('18', 'DVI'),
                     ('0C', 'AV'),
                     ('04', 'S-Video'),
                     ('08', 'Component'),
                     ('20', 'MagicNet'),
                     ('1f', 'DVI_VIDEO'),
                     ('30', 'RF(TV)'),
                     ('40', 'DTV'),
                     ('21', 'HDMI') ]
inputCodeEvent = Event('InputCode', {'group': 'Input code', 'order': next_seq(), 'schema': {'type': 'string'}})
local_event_DesiredInputCode = LocalEvent({'group': 'Input code', 'order': next_seq(), 'schema': {'type': 'string'}})

def handle_displayStatusTimer():
  getDisplayStatusAction.call()

# poll every 30s
timer_deviceStatus = Timer(handle_displayStatusTimer, 30)

def main(arg = None):
  if param_ipAddress == None or len(param_ipAddress.strip())==0:
    console.warn('No IP address set!')
    return
  
  print 'Nodel script started.'
  
  global param_id, param_port
  
  if param_id == None:
    param_id = DEFAULT_SETID
  
  if param_port == None or param_port==0:
    param_port = DEFAULT_TCP_PORT
    console.log('(using default Samsung TCP port %s; set port if a serial-bridge is being used)' % param_port)
    
  power_timer.stop()
  inputCode_timer.stop()
  
  address = '%s:%s' % (param_ipAddress, param_port)
  
  console.info('Will connect to [%s], setID:%s...' % (address, param_id))
  tcp.setDest(address)

local_event_TCPStatus = LocalEvent({'group': 'Comms', 'order': next_seq(), 'schema': {'type': 'string', 'enum': ['Connected', 'Disconnected', 'Timeout']}})  
  
def connected():
  console.info('TCP connected')
  local_event_TCPStatus.emitIfDifferent('Connected')
  
  # wait a second and poll
  timer_deviceStatus.setDelay(1.0)
  
recvBuffer = list()

# data can be fragmented so need a special request queue to manage the protocol
  
def received(data):
  lastReceive[0] = system_clock()
  log('RECV: [%s]' % data.encode('hex'))
    
  # aa-ff-00-09-41-00-01-00-00-14-10-00-00-6e
  #
  # aa   ff   00   09      41 ('A')    00
  # HDR  CMD  ID   length  ACK         R->Cmd
  # +0   1    2    3       4           5  
  
  if len(recvBuffer) == 0:
    if data[0] != chr(0xaa):
      console.log('bad header; throwing away...')
      return
  
  recvBuffer.extend(data)
  
  processBuffer()
      
def processBuffer():
  for x in range(300): # avoiding an infinite loop
    bufferLen = len(recvBuffer)
    if bufferLen < 5:
      # not big enough yet
      return
  
    # got at least 4 bytes (fourth holds the length)
    messageLen = ord(recvBuffer[3])
  
    fullLen = 4 + messageLen + 1
  
    if len(recvBuffer) >= fullLen:
      message = ''.join(recvBuffer[:fullLen])
      del recvBuffer[:fullLen]
      
      log('Pushing buffer [%s]' % message.encode('hex'))
      
      queue.handle(message)
      
      # might be more, so continue...
      
    else:
      return
  
def sent(data):
  if local_event_DebugShowLogging.getArg():
    print 'SENT: [%s]' % data.encode('hex')
  
def disconnected():
  console.warn('TCP disconnected')
  local_event_TCPStatus.emitIfDifferent('Disconnected')
  tcp.drop()
  tcp.clearQueue()
  
def tcptimeout():
  console.warn('TCP timeout')
  local_event_TCPStatus.emitIfDifferent('Timeout')
  tcp.drop()
  tcp.clearQueue()
  
tcp = TCP(connected=connected, received=received, sent=sent, disconnected=disconnected, 
          timeout=tcptimeout, 
          sendDelimiters=None, receiveDelimiters=None, binaryStartStopFlags=None)

def protocolTimeout():
  console.log('protocol timeout; flushing buffer')
  queue.clearQueue()
  del recvBuffer[:]
  

queue = request_queue(timeout=protocolTimeout)

# power ----

def quickPowerCheck():
  current = powerEvent.getArg()
  desired = local_event_DesiredPower.getArg()  
  ok = False
  
  if desired == None or current == desired:
    if power_timer.isStarted(): # only log if enforcer active
      console.info('power: done checking state - states match or desired is none)')
    power_timer.stop()
    ok = True
    
  return current, desired, ok

def enforcePower():
  current, desired, ok = quickPowerCheck()
  
  if ok:
    return
  
  if (date_now().getMillis() - date_parse(local_event_LastPowerRequest.getArg()).getMillis()) > 75000 :
    console.warn('power: giving up enforcing state - waited more than 1m15s.')
    power_timer.stop()
    return
  
  console.info('power: state (still) does not match desired, setting to "%s"' % desired)
  forcePowerAction.call(desired)

power_timer = Timer(enforcePower, 25, stopped=True)
power_timer.stop()
  
local_event_LastPowerRequest = LocalEvent({'group': 'Power', 'order': next_seq(), 'schema': {'type': 'string'}})

def forcePower(arg):
  console.info('forcePower("%s")' % arg)
  
  state = True if arg != 'Off' else False
  msg = '\x11%s\x01%s' % (chr(int(param_id)), '\x01' if state else '\x00')
  checksum = sum([ord(c) for c in msg]) & 0xff
  queue.request(lambda: tcp.send('\xaa%s%s' % (msg, chr(checksum))), lambda arg: checkHeader(arg))
  
forcePowerAction = Action('ForcePower', lambda arg: forcePower(arg), {'title': 'Force', 'group': 'Power', 'order': next_seq(), 'schema': {'type': 'string', 'enum': ['On', 'Off']}})

def local_action_TurnOn(arg=None):
  """{"title":"On","desc":"Turns this node on.","group":"Power","caution":"Ensure hardware is in a state to be turned on.","order":1}"""
  powerAction.call('On')
  
def local_action_TurnOff(arg=None):
  """{"title":"Off","desc":"Turns this node on.","group":"Power","caution":"Ensure hardware is in a state to be turned on.","order":2}"""
  # example response after off: aa ff 00 03 41 11 00 54
  powerAction.call('Off')
  
def setPower(state):
  local_event_LastPowerRequest.emit(str(date_now()))
  local_event_DesiredPower.emit(state)
  
  if not power_timer.isStarted():
    enforcePower()
    power_timer.start()
    
powerAction = Action('Power', lambda arg: setPower(arg), {'group': 'Power', 'schema': {'type': 'string', 'enum': ['On', 'Off']}})
  
# input code ----

def quickInputCodeCheck():
  current = inputCodeEvent.getArg()
  desired = local_event_DesiredInputCode.getArg()
  ok = False
  
  if desired == None or current == desired:
    if inputCode_timer.isStarted(): # only log if enforcer active
      console.info('inputCode: done checking state - states match or desired is none')
    inputCode_timer.stop()
    ok = True  

  return current, desired, ok

def enforceInputCode():
  current, desired, ok = quickInputCodeCheck()
  
  if ok:
    return
  
  if (date_now().getMillis() - date_parse(local_event_LastInputCodeRequest.getArg()).getMillis()) > 75000 :
    console.warn('inputCode: giving up enforcing state - waited more than 1m15s.')
    inputCode_timer.stop()
    return
  
  # check power first
  desiredPower = local_event_DesiredPower.getArg()
  if desiredPower == 'Off':
    console.warn('inputCode: desired power state is off; aborting input code request')
    inputCode_timer.stop()
    return
  
  power = powerEvent.getArg()
  if power != 'On':
    console.info('inputCode: power is not on, turning on so input code can be chosen')
    powerAction.call('On')
    return  
  
  console.info('inputCode: state (still) does not match desired, setting to "%s"' % desired)
  forceInputCodeAction.call(desired)

inputCode_timer = Timer(enforceInputCode, 25, stopped=True)
inputCode_timer.stop()
  
local_event_LastInputCodeRequest = LocalEvent({'group': 'Input code', 'order': next_seq(), 'schema': {'type': 'string'}})  
  
def forceInputCode(arg):
  console.info('forceInputCode("%s")' % arg)
  
  msg = '\x14%s\x01%s' % (chr(int(param_id)), arg.decode('hex'))
  checksum = sum([ord(c) for c in msg]) & 0xff
  queue.request(lambda: tcp.send('\xaa%s%s' % (msg, chr(checksum))), lambda resp: checkHeader(resp, lambda: inputCodeEvent.emit(arg)))

forceInputCodeAction = Action('Force Input Code', forceInputCode, {'title': 'Force', 'group': 'Input code', 'order': next_seq(), 'schema': {'type': 'string'}})

def setInputCode(arg=None):
  local_event_LastInputCodeRequest.emit(str(date_now()))
  local_event_DesiredInputCode.emit(arg)
  
  if not inputCode_timer.isStarted():
    inputCode_timer.start()
    enforceInputCode()
  
setInputCodeAction = Action('Input Code', setInputCode, {'group': 'Input code', 'order': next_seq(), 'schema': {'type': 'string'}})  
  
# ensure state ----

local_event_State = LocalEvent({'general': 'State', 'order': next_seq(), 'schema': {'type': 'string', 'enum': ['On', 'Off', 'Partial', 'Unknown']}})
  
def checkState(arg=None):
  inputCode = inputCodeEvent.getArg()
  power = powerEvent.getArg()
  
  if power == 'Off':
    local_event_State.emit('Off')
    
  elif power == 'On':
    if inputCode in [param_mainInputCode, '', None]:
      local_event_State.emit('On')
    else:
      local_event_State.emit('UnknownInput')
      
  else:
    local_event_State.emit('Unknown')
  
inputCodeEvent.addEmitHandler(checkState)
powerEvent.addEmitHandler(checkState)

def local_action_EnsureState(arg=None):
  '{"group": "State", "schema": {"type": "string", "enum": ["On", "Off"]}}'
  if param_mainInputCode==None or len(param_mainInputCode)==0:
    console.warn('A primary input code has not been set')
    return
  
  if arg == 'On':
    powerAction.call('On')
    setInputCodeAction.call(param_mainInputCode)
    
  elif arg == 'Off':
    powerAction.call('Off')
  
def getDisplayStatus():
  log('getDisplayStatus')
  
  # example response: aaff00094100010000141000006e

  # aa   ff   00   09      41 ('A')    00
  # HDR  CMD  ID   length  ACK         R->Cmd
  # +0   1    2    3       4           5

  # 1:01   2:00    3:00     4:14     5:10     6:00    7:00          6e
  # PRW    VOL     MUTE     INPUT    ASPECT   NTimeNF FTimeNF       CSUM
  # +6     +7      +8       +9       +10      +11     +12           +13
  msg = '\x00%s\x00' % chr(int(param_id))
  checksum = sum([ord(c) for c in msg]) & 0xff
  
  def handleResp(arg):
    checkHeader(arg)
    
    powerEvent.emit('On' if ord(arg[6]) == 1 else 'Off')
    
    local_event_Volume.emit(ord(arg[7]))
    local_event_Mute.emit('Mute' if ord(arg[8]) == 1 else 'Unmute')
    
    inputCodeEvent.emit(arg[9].encode('hex'))
    
    quickPowerCheck()
    quickInputCodeCheck()
  
  queue.request(lambda: tcp.send('\xaa%s%s' % (msg, chr(checksum))), handleResp)
  
getDisplayStatusAction = Action('GetDisplayStatus', lambda arg: getDisplayStatus(), {'group': 'General', 'order': next_seq()})
  
def local_action_ClearMenu(arg=None):
  """{"group": "General", "desc": "Clears the OSD menu"}"""
  console.info('clearMenu()')
  msg = '\x34%s\x01\x00' % chr(int(param_id))
  checksum = sum([ord(c) for c in msg]) & 0xff
  queue.request(lambda: tcp.send('\xaa%s%s' % (msg, chr(checksum))), lambda arg: checkHeader(arg))
  
  
def getIRRemoteControl(arg):
  log('getIRRemoteControl')

  # eg. 'aa ff 00 03 41 36 01 7a
  
  msg = '\x36%s\x00' % chr(int(param_id))
  checksum = sum([ord(c) for c in msg]) & 0xff
  queue.request(lambda: tcp.send('\xaa%s%s' % (msg, chr(checksum))), lambda resp: checkHeader(resp, lambda: irRemoteControlEvent.emit('Enabled' if resp[6] == '\x01' else 'Disabled')))
  
Action('Get IR Remote Control', getIRRemoteControl, {'title': 'Get', 'group': 'IR Remote Control'})
  
def setIRRemoteControl(arg):
  console.info('setIRRemoteControl(%s)' % arg)
  
  if arg != 'Disabled':
    state = True
  else:
    state = False
  
  msg = '\x36%s\x01%s' % (chr(int(param_id)), '\x01' if state else '\x00')
  checksum = sum([ord(c) for c in msg]) & 0xff
  queue.request(lambda: tcp.send('\xaa%s%s' % (msg, chr(checksum))), lambda resp: checkHeader(resp, lambda: irRemoteControlEvent.emit(arg)))

irRemoteControlEvent = Event('IR Remote Control', {'group': 'IR Remote Control', 'schema': {'type': 'string', 'enum': ['Enabled', 'Disabled']}})
Action('IR Remote Control', setIRRemoteControl, {'title': 'Set', 'group': 'IR Remote Control', 'caution': 'Are you sure you want to enable/disable IR remote control?', 'schema': {'type': 'string', 'enum': ['Enabled', 'Disabled']}})


serialNumberEvent = Event('Serial Number', {'group': 'Serial Number', 'schema': {'type': 'string'}})

def getSerialNumber(arg):
  log('getSerialNumber')
  
  msg = '\x0b%s\x00' % chr(int(param_id))
  checksum = sum([ord(c) for c in msg]) & 0xff
  queue.request(lambda: tcp.send('\xaa%s%s' % (msg, chr(checksum))), lambda resp: checkHeader(resp, lambda: serialNumberEvent.emit(resp[6:-4])))
  
Action('GetSerialNumber', getSerialNumber, {'title': 'Get', 'group': 'Serial Number'})

softwareVersionEvent = Event('Software Version', {'group': 'Software Version', 'schema': {'type': 'string'}})

def getSoftwareVersion(arg):
  log('getSoftwareVersion')
  
  msg = '\x0e%s\x00' % chr(int(param_id))
  checksum = sum([ord(c) for c in msg]) & 0xff
  queue.request(lambda: tcp.send('\xaa%s%s' % (msg, chr(checksum))), lambda resp: checkHeader(resp, lambda: softwareVersionEvent.emit(resp[6:-1])))
  
Action('GetSoftwareVersion', getSoftwareVersion, {'title': 'Get', 'group': 'Software Version'})

# All non-critical informational polling should occur here
def local_action_PollNonCriticalInfo(arg=None):
  '''{"title": "Poll non-critical info",  "desc": "This occurs daily in the background", "group": "General"}'''
  lookup_local_action('GetSerialNumber').call()
  lookup_local_action('GetIRRemoteControl').call()
  lookup_local_action('GetSoftwareVersion').call()
  
# non-critical poll every 2 days, first after 15 s
Timer(lambda: lookup_local_action('PollNonCriticalInfo').call(), 3600*48, 15)


def checkHeader(arg, onSuccess=None):
  if arg[0] != '\xaa' or arg[1] != '\xff':
    raise Exception('Bad message structure')
    
  if arg[4] != 'A':
    raise Exception('Bad acknowledgement')
    
  if onSuccess:
    onSuccess()
    
# for status checks

lastReceive = [0]
lastLanded = [0]

local_event_LandingStatus = LocalEvent({'title': 'Landing status', 'group': 'Status', 'order': next_seq(), 
                                        'schema': {'type': 'object', 'title': '...', 'properties':  {
                                            'node':          {'title': 'Node',            'type': 'string', 'order': 1},
                                            'lastLanded':    {'title': 'Last Landed', 'type': 'string', 'order': 2},
                                            'source':        {'title': 'Source',          'type': 'string', 'order': 3},
                                            'url':           {'title': 'URL',             'type': 'string', 'order': 4}}}})

# this is taken from the landing node normally to ensure the panel is checking in
def remote_event_LandingStatus(arg):
  local_event_LandingStatus.emit(arg)
  lastLanded[0] = system_clock()

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
      message = 'Off the network for approx. %s minutes' % roughDiff
      
    local_event_Status.emit({'level': 2, 'message': message})
    return
    
  # it may be contactable on the network, but is it checking in (landing) (if configured to do so i.e. binding is set)
  
  diff = (system_clock() - lastLanded[0])/1000.0
  
  if lookup_remote_event('LandingStatus') != None and diff > 5*60: # arbitrary 5 mins
    previousContactValue = (local_event_LandingStatus.getArg() or {}).get('lastLanded')
    
    if previousContactValue == None:
      message = 'Never "landed"'
      
    else:
      previousContact = date_parse(previousContactValue)
      roughDiff = (now.getMillis() - previousContact.getMillis())/1000/60
      message = 'Last landing was approx. %s minutes ago' % roughDiff
      
    local_event_Status.emit({'level': 2, 'message': message})
    return
  
  else:
    local_event_LastContactDetect.emit(str(now))
    local_event_Status.emit({'level': 0, 'message': 'OK'})

status_check_interval = 75
status_timer = Timer(statusCheck, status_check_interval)
    
def log(msg):
  if local_event_DebugShowLogging.getArg():
    print msg
    
