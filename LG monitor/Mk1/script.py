'No direct network port available. Link to main manual (see page 71) - http://www.lg.com/us/commercial/documents/MAN_SE3B_SE3KB_SL5B.pdf and others (see script)'

# 2nd manual: https://hf-files-oregon.s3.amazonaws.com/hdpjustaddpower_kb_attachments/2016/08-19/536f965c-5e2f-473f-8e3f-aacfac49601f/LG%20Published%20RS232C%20Guide.pdf
# 3rd manual: http://www.lg.com/us/commercial/documents/SM3C-B_Manual.pdf

# rev. history
# - legacy screen option

DEFAULT_ADMINPORT = 9761
DEFAULT_BROADCASTIP = '192.168.1.255'

# general device status
local_event_Status = LocalEvent({'order': -100, 'group': 'Status', 'schema': {'type': 'object', 'title': 'Status', 'properties': {
        'level': {'type': 'integer'},
        'message': {'type': 'string'}
      }}})

DEFAULT_SET_ID = '001' # sometimes this is 01

param_ipAddress = Parameter({'title': 'IP address', 'schema': {'type': 'string'}})
param_setID = Parameter({'title': 'Set ID (hex)', 'desc': 'with 2 leading zeros (on most models), e.g. 001...9, a, b, c, d, e, f, 010 (= decimal 16)', 'schema': {'type': 'string', 'hint': 'e.g. 001, 01f (set 31), etc.'}})
param_broadcastIPAddress = Parameter({'title': 'Broadcast IP address', 'schema': {'type': 'string', 'hint': DEFAULT_BROADCASTIP}})
param_adminPort = Parameter({'title': 'Admin port', 'schema': {'type': 'integer', 'hint': DEFAULT_ADMINPORT}})
param_macAddress = Parameter({'title': 'MAC address', 'schema': {'type': 'string'}})
param_useSerialGateway = Parameter({'title': 'Use serial gateway node?', 'schema': {'type': 'boolean'}})

param_oldScreenBehaviour = Parameter({'title': 'Old screen behaviour?', 'desc': 'Ignore "screenPowerOff" (backlight control), "automaticStandby"', 'schema': {'type': 'boolean'}})

wol = UDP( # dest='10.65.255.255:9999' % , # set after main
          sent=lambda arg: console.info('wol: sent [%s]' % arg),
          ready=lambda: console.info('wol: ready (ignored if serial)'), received=lambda arg: console.info('wol: received [%s]'))

POWER_STATES = ['On', 'Input Waiting', 'Unknown', 'Turning On', 'Turning Off', 'Off']
local_event_Power = LocalEvent({'title': 'Power', 'group': 'Power', 'order': next_seq(), 'schema': {'type': 'string', 'enum': POWER_STATES + ['Partially On', 'Partially Off']}})
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
  desired = lookup_local_event('Desired Power')
  power = lookup_local_event('Power')
  
  mainPower = lookup_local_event('MainPower')
  screenPowerOff = lookup_local_event('ScreenPowerOff')
  
  def handler(arg):
    desiredValue = desired.getArg()
    mainPowerValue = mainPower.getArg()
    screenPowerOffValue = screenPowerOff.getArg()
    
    if mainPowerValue == 'Off':
      rawValue = 'Off'
    else:
      rawValue = 'Off' if screenPowerOffValue == True else 'On'
    
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
  mainPower.addEmitHandler(handler)
  screenPowerOff.addEmitHandler(handler)

def powerHandler(state=''):
  if state.lower() == 'on':
    local_event_DesiredPower.emit('On')
    
  elif state.lower() == 'off':
    local_event_DesiredPower.emit('Off')
    
  else:
    console.warn('Unknown power state specified, must be On or Off')
    return
  
  local_event_LastPowerRequest.emit(str(date_now()))
  
  timer_powerSyncer.setDelay(0.1)

Action('Power', powerHandler, {'group': 'Power', 'schema': {'type': 'string', 'enum': ['On', 'Off']}})

# NOTE ABOUT POWER: 
#       This uses the 'SCREEN OFF' command as opposed to the 'POWER' command so
#       the arguments needs to be interpretted within that context. At first glance
#       may seem flipped.

screenPowerOffEvent = Event('ScreenPowerOff', {'group': 'Power', 'order': next_seq(), 'schema': {'type': 'boolean'}})

# e.g. 'a 01 OK01x'
def handleScreenOffResp(data):
  if data == '01':
    screenPowerOffEvent.emit(True) 
    
  elif data == '00':
    screenPowerOffEvent.emit(False)
      
  else:
    log(1, 'screenPowerOff unknown resp - %s' % data)

@local_action({'group': 'Power', 'order': next_seq(), 'schema': {'type': 'boolean'}})
def setScreenPowerOff(state):
  log(1, 'set_screenpoweroff(%s) called' % state)
  
  cmd = '01' if state else '00'
    
  transportRequest('set_screenpoweroff(%s)' % state, 'kd %s %s\r' % (setID, cmd), 
              lambda resp: checkHeaderAndHandleData(resp, 'd', handleScreenOffResp))
@local_action({'group': 'Power', 'order': next_seq()})
def getScreenPowerOff():
  log(1, 'get_screenpoweroff called')

  # this actually polls the 'SCREEN OFF' state
  
  if mainPowerEvent.getArg() != 'On':
    log(2, 'ignoring get_screenoff; main power not on')
    return

  transportRequest('get_screenpoweroff', 'kd %s ff\r' % setID, 
              lambda resp: checkHeaderAndHandleData(resp, 'd', handleScreenOffResp))
  
timer_powerPoller = Timer(lambda: getScreenPowerOff.call(), 15.0)
  
def syncPower():
  log(1, 'syncPower called')
  
  last = date_parse(local_event_LastPowerRequest.getArg() or ZERO_DATE_STR)
  if date_now().getMillis() - last.getMillis() > 90000:
    log(2, 'syncPower - nothing to do; last power request was more than 90s ago')
    timer_powerSyncer.setInterval(90)
    return
  
  desired = local_event_DesiredPower.getArg()
  
  mainPower = lookup_local_event('Main Power').getArg()
  screenPowerOff = lookup_local_event('Screen Power Off').getArg()
  
  if mainPower == 'Off':
    rawPower = 'Off'
  
  else:
    rawPower = 'Off' if screenPowerOff == True else 'On'
  
  if desired == rawPower:
    # nothing to do
    console.info('syncPower - nothing to do; desired and actual are the same ("%s"); will settle if idle of 90s' % desired)
    return
  
  if desired == 'On':
    # try WOL for good measure
    log(2, 'syncPower - desired is ON; sending WoL...')
    lookup_local_action("Send WOL Packet").call()
    
    if mainPower == 'Off':
      log(2, "...turning on MainPower (it's Off right now)")
      lookup_local_action('MainPower').call('On')
      
    log(2, "...turning making sure ScreenPowerOff=False")
    setScreenPowerOff.call(False)
    
  elif desired == 'Off':
    if param_oldScreenBehaviour:
      log(2, 'syncPower - desired is OFF; using old screen behaviour so MainPower=Off')
      lookup_local_action('MainPower').call('Off')
      
    else:
      log(2, 'syncPower - desired is OFF; just setting ScreenPowerOff=True')
      setScreenPowerOff.call(True)
    
  timer_powerSyncer.setDelay(7.5)

timer_powerSyncer = Timer(syncPower, 60.0)




def inputCodeHandler(code):
  local_event_DesiredInputCode.emit(code)
  local_event_LastInputCodeRequest.emit(str(date_now()))
  
  timer_inputCodeSyncer.setDelay(0.3)
  
Action('Input Code', inputCodeHandler, {'group': 'Input Code', 'schema': {'type': 'string'}})

def handleInputCodeResp(arg):
  local_event_InputCode.emit(int(arg))
    
def setInputCode(code):
  log(1, 'setInputCode(%s) called' % code)
  
  transportSend('set_inputcode(%s)' % code, 'xb %s %s' % (setID, code))
  
    
def getInputCode():
  if lookup_local_event('MainPower').getArg() != 'On' or lookup_local_event('ScreenPowerOff').getArg() == True:
    log(1, 'getInputCode - Power is not On; ignoring input get request')
    return
  
  getInputCodeNow()
    
def getInputCodeNow():
  log(1, 'getInputCodeNow called')
  
  # e.g. resp: 'b 01 OK90'

  def handleData(data):
    local_event_InputCode.emit(data)

  transportRequest('get_inputcode', 'xb %s ff\r' % setID, 
              lambda resp: checkHeaderAndHandleData(resp, 'b', handleData))
  
timer_inputCodePoller = Timer(getInputCode, 15.0, 20.0)  
  
def syncInputCode():
  log(1, 'syncInputCode called')
  last = date_parse(local_event_LastInputCodeRequest.getArg() or ZERO_DATE_STR)
  if date_now().getMillis() - last.getMillis() > 60000:
    return
  
  desired = local_event_DesiredInputCode.getArg()
  actual = local_event_InputCode.getArg()
  if desired == actual:
    # nothing to do
    timer_inputCodeSyncer.setInterval(120)
    return
  
  if mainPowerEvent.getArg() != 'On':
    console.log('Power is not on; ignoring input set request')
    return
  
  setInputCode(desired)
    
  timer_inputCodeSyncer.setDelay(15.0)  

timer_inputCodeSyncer = Timer(syncInputCode, 60.0)

SETTINGS_GROUP = "Settings & Info"

# Serial number ---

Event('Serial Number', {'group': SETTINGS_GROUP, 'order': next_seq(), 'schema': {'type': 'string'}})
Action('Get Serial Number', lambda arg: transportRequest('get_serialnumber', 'fy %s ff\r' % setID, lambda resp: checkHeaderAndHandleData(resp, 'y', lambda data: lookup_local_event('Serial Number').emit(data))), 
       {'group': SETTINGS_GROUP, 'order': next_seq()})

Timer(lambda: lookup_local_action('Get Serial Number').call(), 5*60, 15)


# Temperature ---

Event('Temperature', {'desc': 'Inside temperature', 'group': SETTINGS_GROUP, 'order': next_seq(), 'schema': {'type': 'integer'}})

@local_action({'group': SETTINGS_GROUP, 'order': next_seq()})
def GetTemperature():
  if mainPowerEvent.getArg() != 'On':
    log(2, 'ignoring get_insidetemp; main power not on')
    return
  
  transportRequest('get_insidetemp', 'dn %s ff\r' % setID, lambda resp: checkHeaderAndHandleData(resp, 'n', lambda data: lookup_local_event('Temperature').emit(int(data, 16))))  

Timer(lambda: lookup_local_action('Get Temperature').call(), 5*60, 15)


# Main Power ---

mainPowerEvent = Event('Main Power', {'group': 'Power', 'order': next_seq(), 'schema': {'type': 'string', 'enum': ['On', 'Off']}})
Action('Get Main Power', lambda arg: transportRequest('get_mainpower', 'ka %s ff\r' % setID, lambda resp: checkHeaderAndHandleData(resp, 'a', lambda data: lookup_local_event('Main Power').emit('Off' if data == '00' else ('On' if data == '01' else 'Unknown %s' % data)))), 
       {'group': 'Power', 'order': next_seq()})

def handleMainPowerSet(arg):
  if arg == 'On':
    cmd = '01'
  elif arg == 'Off':
    cmd = '00'
  else:
    raise Exception('Unknown MainPower state %s' % arg)
    
  transportRequest('set_mainpower(%s)' % arg, 'ka %s %s\r' % (setID, cmd), 
              lambda resp: checkHeaderAndHandleData(resp, 'a', lambda data: lookup_local_event('Main Power').emit('Off' if data == '00' else ('On' if data == '01' else 'Unknown %s' % data))), urgent=True)

Action('Main Power', handleMainPowerSet, {'group': 'Power', 'order': next_seq(), 'schema': {'type': 'string', 'enum': ['On', 'Off']}})
  
Timer(lambda: lookup_local_action('Get Main Power').call(), 5*60, 15)


# Automatic Standy ---

AUTOSTANDBY_MAP = [
    ('00', 'Off'),     # 00: Off (Will not turn off after 4/6/8 hours)
    ('01', '4 Hours'), # 01: 4 hours (Off after 4 hours)
    ('02', '6 Hours'), # 02: 6 hours (Off after 6 hours)
    ('03', '8 Hours')  # 03: 8 hours (Off after 8 hours)
]

AUTOSTANDBY_NAMES = [name for code, name in AUTOSTANDBY_MAP]
AUTOSTANDBY_NAMES_BY_CODE = dict([(code, name) for code, name in AUTOSTANDBY_MAP])
AUTOSTANDBY_CODES_BY_NAME = dict([(name, code) for code, name in AUTOSTANDBY_MAP])

@after_main
def initAutomaticStandBySetting():
  automaticStandbySignal = Event('Automatic Standby', {'group': SETTINGS_GROUP, 'order': next_seq(), 'schema': {'type': 'string', 'enum': AUTOSTANDBY_NAMES}})

  @local_action({'group': SETTINGS_GROUP, 'order': next_seq()})
  def GetAutomaticStandby():
    if param_oldScreenBehaviour:
      log(1, '(old screen so ignoring get_automaticstandby setting)')
      return
    
    if mainPowerEvent.getArg() != 'On':
      log(1, 'ignoring get_automaticstandby; main power not on')
      return
  
    transportRequest('get_automaticstandby', 'mn %s ff\r' % setID, 
                                       lambda resp: checkHeaderAndHandleData(resp, 'n', 
                                             lambda data: automaticStandbySignal.emit(AUTOSTANDBY_NAMES_BY_CODE.get(data, 'UNKNOWNCODE_%s' % data))))
  


  setAutomaticStandbyAction = Action('Automatic Standy', 
                                  lambda arg: transportRequest('set_automaticstandby', 'mn %s %s\r' % (setID, AUTOSTANDBY_CODES_BY_NAME[arg]), 
                                      lambda resp: checkHeaderAndHandleData(resp, 'n', 
                                          lambda data: automaticStandbySignal.emit(data))), 
                                  {'group': SETTINGS_GROUP, 'order': next_seq(), 'schema': {'type': 'string', 'enum': AUTOSTANDBY_NAMES}})
  
  if not param_oldScreenBehaviour:
    Timer(lambda: GetAutomaticStandby.call(), 5*60, 15) # every 5 mins, first after 15


# Abnormal state ---
# (taken from 2nd manual)

ABNORMAL_STATES = [
   (0, 'Normal'),              # 0  Normal (Power on and signal exist)
   (1, 'No Signal Power On'),  # 1  No signal (Power on)
   (2, 'Off by Remote'),       # 2  Turn the monitor off by remote control
   (3, 'Off by Sleep'),        # 3  Turn the monitor off by sleep time function
   (4, 'Off by RS-232'),       # 4  Turn the monitor off by RS-232C function
   (6, 'AC Down'),             # 6  AC down
   (7, 'Off by Time'),         # 8  Turn the monitor off by off time function
   (9, 'Off by Auto')          # 9  Turn the monitor off by auto off function
]

ABNORMAL_STATES_NAMES = [name for code, name in ABNORMAL_STATES]
ABNORMAL_STATES_NAMES_BY_CODE = dict([(code, name) for code, name in ABNORMAL_STATES])

Event('Abnormal State', {'group': 'Error Status', 'order': next_seq(), 'schema': {'type': 'string', 'enum': ABNORMAL_STATES_NAMES}})

def handle_AbnormalStateData(data):
  name = ABNORMAL_STATES_NAMES_BY_CODE.get(int(data), 'UNKNOWN_CODE_%s' % data)
  lookup_local_event('Abnormal State').emit(name)
  
@local_action({'group': 'Error Status', 'order': next_seq()})
def GetAbnormalState(arg):
  if mainPowerEvent.getArg() != 'On':
    log(2, 'ignoring get_abnormalstate; main power not on')
    return
  
  transportRequest('get_abnormalstate', 'kz %s ff\r' % setID, lambda resp: checkHeaderAndHandleData(resp, 'z', handle_AbnormalStateData))

Timer(lambda: lookup_local_action('Get Abnormal State').call(), 30, 10) # get every 30 seconds, first after 10

# Wake-On-LAN (WOL) ---

ONOFF_NAMES_BY_CODE = { 0: 'Off', 1: 'On' }
ONOFF_CODES_BY_NAME = { 'Off': '00', 'On': '01' }

@after_main
def initWakeOnLANSetting():
  if param_oldScreenBehaviour:
    console.log('(old screen so ignoring get_wol setting)')
    return
  
  Event('Wake-On-LAN', {'group': SETTINGS_GROUP, 'order': next_seq(), 'schema': {'type': 'string', 'enum': ['On', 'Off']}})

  def handle_WOLData(data):
    lookup_local_event('Wake-On-LAN').emit(ONOFF_NAMES_BY_CODE.get(int(data), 'UNKNOWNCODE_%s' % data))  

  Action('Get Wake-On-LAN', lambda arg: transportRequest('get_wol', 'fw %s ff\r' % setID, lambda resp: checkHeaderAndHandleData(resp, 'w', handle_WOLData)), 
         {'group': SETTINGS_GROUP, 'order': next_seq()})

  Action('Wake-On-LAN', lambda arg: transportRequest('set_wol', 'fw %s %s\r' % (setID, ONOFF_CODES_BY_NAME[arg]), lambda resp: checkHeaderAndHandleData(resp, 'w', handle_WOLData)),
         {'group': SETTINGS_GROUP, 'order': next_seq(), 'schema': {'type': 'string', 'enum': ['On', 'Off']}})

  Timer(lambda: lookup_local_action('Get Wake-On-LAN').call(), 5*60, 15) # every 5 mins, first after 15

# No Signal Power Off  ---
# (from 3rd manual)
NSPO_DESC = 'Sets the monitor to enter Automatic Standby mode if there is no signal for 15 minutes'

Event('No Signal Power Off', {'group': SETTINGS_GROUP, 'desc': NSPO_DESC, 'order': next_seq(), 'schema': {'type': 'string', 'enum': ['On', 'Off']}})

def handle_NSPOData(data):
  lookup_local_event('No Signal Power Off').emit(ONOFF_NAMES_BY_CODE.get(int(data), 'UNKNOWNCODE_%s' % data))  

Action('Get No Signal Power Off', lambda arg: transportRequest('get_nosignalpoweroff', 'fg %s ff\r' % setID, lambda resp: checkHeaderAndHandleData(resp, 'g', handle_NSPOData)), 
       {'group': SETTINGS_GROUP, 'desc': NSPO_DESC, 'order': next_seq()})

Action('No Signal Power Off', lambda arg: transportRequest('set_nosignalpoweroff', 'fg %s %s\r' % (setID, ONOFF_CODES_BY_NAME[arg]), lambda resp: checkHeaderAndHandleData(resp, 'g', handle_NSPOData)),
       {'group': SETTINGS_GROUP, 'desc': NSPO_DESC, 'order': next_seq(), 'schema': {'type': 'string', 'enum': ['On', 'Off']}})
  
Timer(lambda: lookup_local_action('Get No Signal Power Off').call(), 5*60, 15) # every 5 mins, first after 15



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
  
def timeout():
  console.warn('timeout - flushing all request queues')
  
  # flush the request queue
  tcp.clearQueue()
  queue.clearQueue()
  
# <!-- gateway

queue = request_queue()
  
remote_action_GatewaySetSend = RemoteAction()

def remote_event_GatewaySetReceive(arg):
  log(1, 'gateway_recv: [%s]' % arg)
  
  lastReceive[0] = system_clock()
  
  queue.handle(arg)

def transportRequest(ctx, data, resp, urgent=False):
  if param_useSerialGateway:
    def handler():
      log(1, 'gateway_send for %s: [%s]' % (ctx, data.strip()))
    
      # for TCP:
      # tcp.sendNow(data)
    
      # for Serial Gateway
      remote_action_GatewaySetSend.call(data)
    
    if urgent:
      queue.clearQueue()
    
    queue.request(handler, resp)
    
  else:
    log(1, 'tcp_request for %s: [%s]' % (ctx, data.strip()))
    tcp.request(data, resp)
  
def transportSend(data):
  if param_useSerialGateway:
    def handler():
      log(1, 'gateway_send: [%s]' % data)
      tcp.sendNow(data)
    
    queue.send(handler)
    
  else:
    tcp.send(data)

# --!>
  
def received(line):
  lastReceive[0] = system_clock()
  
  log(2, 'RECV: [%s]' % line.strip())
    
def sent(line):
  log(2, 'SENT: [%s]' % line.strip())

# maintain a TCP connection
tcp = TCP(connected=connected, disconnected=disconnected, 
          received=received, sent=sent, timeout=timeout,
          receiveDelimiters='\r\nx', # notice the 'x' at the end of all responses
          sendDelimiters='\r')

def main(arg = None):
  global setID
  if param_setID != None and len(param_setID) > 0:
    setID = param_setID
    
  if not param_useSerialGateway:
    dest = '%s:%s' % (param_ipAddress, param_adminPort or DEFAULT_ADMINPORT)
    console.log('Connecting to %s...' % dest)
    tcp.setDest(dest)
    
  else:
    console.log('Using serial gateway; make sure "Gateway" remote actions and events are specified')
  
  # set WOL dest which can only be done during 'main'
  wol.setDest('%s:9999' % param_broadcastIPAddress)

def local_action_SendWOLPacket(arg=None):
  """{"title": "Send", "group": "Wake-on-LAN"}"""
  if is_blank(param_macAddress):
    log(2, '(ignoring SendWOLPacket; no MAC address used)')
    return
  
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
    
  # is online, so check for any internal error conditions
  
  elif local_event_Power.getArg() == 'On' and lookup_local_event('Abnormal State').getArg() == 'No Signal Power On':
    # on but no video signal
    local_event_Status.emit({'level': 1, 'message': 'Display is on but no video signal detected'})
  
  else:
    # everything is good
    local_event_LastContactDetect.emit(str(now))
    local_event_Status.emit({'level': 0, 'message': 'OK'})
    
status_check_interval = 75
status_timer = Timer(statusCheck, status_check_interval)
  
# for acting as a power slave
def remote_event_Power(arg):
  if arg == 1 or arg == 'On':
    lookup_local_action('power').call('On')
  
  elif arg == 0 or arg == 'Off':
    lookup_local_action('power').call('Off')
  
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