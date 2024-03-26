'''
**LG display** with serial or LAN control. For some older monitors certain functions will not work and report "no positive acknowledgement" in the console.

`REV 4.240326`

**POSSIBLE INPUT CODES**
  
* To be sure, check your own model!

    * **20**: AV **40**: COMPONENT **60**: RGB **70**: DVI-D (PC) **80**: DVI-D (DTV) **91**: HDMI2 (DTV) **90**: HDMI1 (DTV) **92**: OPS/HDMI3/DVI-D (DTV) 
    * **A0**: HDMI1 (PC), **A1**: HDMI2 (PC) **A2**: OPS/HDMI3/DVI-D (PC) **95**: OPS/DVI-D (DTV) **A5**: OPS/DVI-D (PC) 
    * **96**: HDMI3/DVI-D (DTV) **A6**: HDMI3/DVI-D (PC) **97**: HDMI3/HDMI2/DVI-D (DTV) **A7**: HDMI3/HDMI2/DVI-D (PC) **98**: OPS (DTV) **C1**: DISPLAYPORT/USB-C (DTV)
    * **A8**: OPS (PC) **99**: HDMI2/OPS (DTV) **A9**: HDMI2/OPS (PC) **C0**: DISPLAYPORT (DTV) **D0**: DISPLAYPORT (PC) 
    * **D1**: DISPLAYPORT/USB-C (PC) **C2**: HDMI3 (DTV) **D2**: HDMI3 (PC) **C3**: HDBaseT (DTV) **D3**: HDBaseT (PC) **E0**: SuperSign webOS Player
    * **E1**: Others **E2**: Multi Screen **E3**: Play via URL
 
**MANUALS**

* Just an assortment of online manuals (LG relocate them from time to time).

   * [USER MANUAL - LG Digial Signage (Monitor Signage) - ENG.pdf](https://gscs-b2c.lge.com/downloadFile?fileId=DnofFZpS006rsciVwoXKTw)

**REVISION HISTORY**

 * rev. 4: discrete inputs, discrete power states, volume
 * rev. 3: IP address using binding
    * **Input Code** tidy up
    * added **Audio Mute**
    * recipe header tidy up
 * rev. 2: legacy screen option

'''

DEFAULT_ADMINPORT = 9761

# general device status
local_event_Status = LocalEvent({'order': -100, 'group': 'Status', 'schema': {'type': 'object', 'title': 'Status', 'properties': {
        'level': {'type': 'integer'},
        'message': {'type': 'string'}
      }}})

DEFAULT_SET_ID = '001' # sometimes this is 01

param_ipAddress = Parameter({'title': 'IP address', 'schema': {'type': 'string', 'hint': '(overrides binding)'}})
param_setID = Parameter({'title': 'Set ID (hex)', 'desc': 'with 2 leading zeros (on most models), e.g. 001...9, a, b, c, d, e, f, 010 (= decimal 16) or sometimes without leading zeros', 'schema': {'type': 'string', 'hint': 'e.g. 001, 01f (set 31), sometimes no leading zeros, etc.'}})
param_adminPort = Parameter({'title': 'Admin port', 'schema': {'type': 'integer', 'hint': DEFAULT_ADMINPORT}})
param_macAddress = Parameter({'title': 'MAC address (for Wake-on-LAN)', 'schema': {'type': 'string'}})
param_useSerialGateway = Parameter({'title': 'Use serial gateway node? (when daisy-chaining)', 'schema': {'type': 'boolean'}})

param_oldScreenBehaviour = Parameter({'title': 'Old screen behaviour?', 'desc': 'Ignore "screenPowerOff" (backlight control), "automaticStandby"', 'schema': {'type': 'boolean'}})

param_inputsInUse = Parameter({ 'title': 'Inputs In Use', 'schema': { 'type': 'array', 'items': { 'type': 'object', 'properties': {
  'inputCode': { 'type': 'string', 'hint': '(e.g. "a0" is HDMI1, see info header)', 'order': 1 },
  'name': { 'type': 'string', 'hint': '(optional, affects binding names, e.g. "HDMI 1")', 'order': 1 },  
  'label': { 'type': 'string', 'hint': '(descriptive only e.g. "Matrix Switcher Output 2")', 'order': 2 }}}}})

wol = UDP( dest='255.255.255.255:9',
          sent=lambda arg: console.info('wol: sent [%s]' % arg),
          ready=lambda: console.info('wol: ready (ignored if serial)'), received=lambda arg: console.info('wol: received [%s]'))

POWER_STATES = ['On', 'Input Waiting', 'Unknown', 'Turning On', 'Turning Off', 'Off']
local_event_Power = LocalEvent({'title': 'Power', 'group': 'Power', 'order': next_seq(), 'schema': {'type': 'string', 'enum': POWER_STATES + ['Partially On', 'Partially Off']}})
local_event_PowerOn = LocalEvent({ 'group': 'Power', 'order': next_seq(), 'schema': { 'type': 'boolean' }})
local_event_PowerOff = LocalEvent({ 'group': 'Power', 'order': next_seq(), 'schema': { 'type': 'boolean' }})
local_event_DesiredPower = LocalEvent({'title': 'Desired', 'group': 'Power', 'order': next_seq(), 'schema': {'type': 'string', 'enum': ['On', 'Off']}}) 
local_event_LastPowerRequest = LocalEvent({'title': 'Last request', 'group': 'Power', 'order': next_seq(), 'schema': {'type': 'string'}}) 

local_event_IPAddress = LocalEvent({ 'group': 'Addressing', 'order': next_seq(), 'schema': { 'type': 'string' }})

def remote_event_IPAddress(arg):
  if not is_blank(param_ipAddress): return
  previous = local_event_IPAddress.getArg()
  if arg != previous:
    console.info('IP address changed / updated to %s, previously %s; will restart...' % (arg, previous))
    local_event_IPAddress.emit(arg)
    _node.restart()

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
        
    powerArg = power.getArg() or EMPTY
    local_event_PowerOn.emit('On' in powerArg)
    local_event_PowerOff.emit('Off' in powerArg)
        
  # attach handlers
  desired.addEmitHandler(handler)
  mainPower.addEmitHandler(handler)
  screenPowerOff.addEmitHandler(handler)

@local_action({'group': 'Power', 'order': next_seq(), 'schema': { 'type': 'string', 'enum': [ 'On', 'Off' ] }})
def Power(arg):
  lcState = str(arg).lower().strip()

  if lcState in ['true', 'on', '1']:
    doPower(True)
  elif lcState in ['false', 'off', '0']:
    doPower(False)
  else:
    console.warn("Power: unknown arg - %s" % arg)

@local_action({'group': 'Power', 'order': next_seq() })
def PowerOn():
  doPower(True)

@local_action({'group': 'Power', 'order': next_seq() })
def PowerOff():
  doPower(False)

def doPower(state):
  arg = 'On' if state else 'Off'
  console.info("Power(%s) called" % arg)
  local_event_DesiredPower.emit(arg)

  local_event_LastPowerRequest.emit(str(date_now()))
  
  timer_powerSyncer.setDelay(0.1)


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
              lambda resp: checkHeaderAndHandleData(resp, 'd', handleScreenOffResp, ctx='get_screenpoweroff'))
  
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


# <!-- Input Code

@after_main
def initInputsInUse():
  if len(param_inputsInUse or EMPTY) == 0:
    return console.info('NOTE: No "Inputs In Use" were configured')
  
  for info in param_inputsInUse:
    initInputInUse(info)
    
def initInputInUse(info):
  code = info['inputCode']
  nameOrCode = code if is_blank(info['name']) else info['name']
  label = info['label']
  title = '%s' % nameOrCode if is_blank(info['label']) else '%s ("%s")' % (nameOrCode, label)
  
  e = Event('Input %s' % nameOrCode, { 'title': title, 'group': 'Inputs In Use', 'order': next_seq(), 'schema': { 'type': 'boolean' }})
  
  def handler(arg):    
    if 'On' not in local_event_Power.getArg():
      console.info('Input %s called, power was not on, powering on!' % title)
      Power.call('On')
    else:
      console.info('Input %s called' % title)
      
    InputCode.call(code)
  
  a = Action('Input %s' % nameOrCode, handler, {  'title': title, 'group': 'Inputs In Use', 'order': next_seq() })
  
  def event_handler(arg):
    e.emit(code == local_event_InputCode.getArg() and local_event_PowerOn.getArg())
  
  local_event_InputCode.addEmitHandler(event_handler)
  local_event_PowerOn.addEmitHandler(event_handler)

@local_action({ 'group': 'Input Code', 'order': next_seq(), 'schema': { 'type': 'string' }})
def InputCode(arg):
  console.info('InputCode(%s)' % arg)
  local_event_DesiredInputCode.emit(arg)
  local_event_LastInputCodeRequest.emit(str(date_now()))
  timer_inputCodeSyncer.setDelay(0.3)
    
def setInputCode(code):
  log(1, 'setInputCode(%s) called' % code)
  
  transportRequest('set_inputcode', 'xb %s %s' % (setID, code), 
              lambda resp: checkHeaderAndHandleData(resp, 'b', lambda arg: local_event_InputCode.emit(arg), ctx='set_inputcode'))
    
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
              lambda resp: checkHeaderAndHandleData(resp, 'b', handleData, ctx='get_inputcode'))
  
timer_inputCodePoller = Timer(getInputCode, 15.0, 20.0)  
  
def syncInputCode():
  log(1, 'syncInputCode: called')
  last = date_parse(local_event_LastInputCodeRequest.getArg() or ZERO_DATE_STR)
  if date_now().getMillis() - last.getMillis() > 60000:
    log(1, 'syncInputCode: has been a long time since InputCode request; will not enforce')
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

# Input Code --!>

SETTINGS_GROUP = "Settings & Info"

# Serial number ---

Event('Serial Number', {'group': SETTINGS_GROUP, 'order': next_seq(), 'schema': {'type': 'string'}})
Action('Get Serial Number', lambda arg: transportRequest('get_serialnumber', 'fy %s ff\r' % setID, lambda resp: checkHeaderAndHandleData(resp, 'y', lambda data: lookup_local_event('Serial Number').emit(data), ctx='get_serialnumber')), 
       {'group': SETTINGS_GROUP, 'order': next_seq()})

Timer(lambda: lookup_local_action('Get Serial Number').call(), 5*60, 15)


# Temperature ---

Event('Temperature', {'desc': 'Inside temperature', 'group': SETTINGS_GROUP, 'order': next_seq(), 'schema': {'type': 'integer'}})

@local_action({'group': SETTINGS_GROUP, 'order': next_seq()})
def GetTemperature():
  if mainPowerEvent.getArg() != 'On':
    log(2, 'ignoring get_insidetemp; main power not on')
    return
  
  transportRequest('get_insidetemp', 'dn %s ff\r' % setID, lambda resp: checkHeaderAndHandleData(resp, 'n', lambda data: lookup_local_event('Temperature').emit(int(data, 16)), ctx='get_insidetemp'))  

Timer(lambda: lookup_local_action('Get Temperature').call(), 5*60, 15)


# Main Power ---

mainPowerEvent = Event('Main Power', {'group': 'Power', 'order': next_seq(), 'schema': {'type': 'string', 'enum': ['On', 'Off']}})
Action('Get Main Power', lambda arg: transportRequest('get_mainpower', 'ka %s ff\r' % setID, 
         lambda resp: checkHeaderAndHandleData(resp, 'a', lambda data: lookup_local_event('Main Power').emit('Off' if data == '00' else ('On' if data == '01' else 'Unknown %s' % data)), ctx='get_mainpower')), 
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
                                             lambda data: automaticStandbySignal.emit(AUTOSTANDBY_NAMES_BY_CODE.get(data, 'UNKNOWNCODE_%s' % data)), ctx='get_automaticstandby'))
  


  setAutomaticStandbyAction = Action('Automatic Standy', 
                                  lambda arg: transportRequest('set_automaticstandby', 'mn %s %s\r' % (setID, AUTOSTANDBY_CODES_BY_NAME[arg]), 
                                      lambda resp: checkHeaderAndHandleData(resp, 'n', 
                                          lambda data: automaticStandbySignal.emit(data))), 
                                  {'group': SETTINGS_GROUP, 'order': next_seq(), 'schema': {'type': 'string', 'enum': AUTOSTANDBY_NAMES}})
  
  if not param_oldScreenBehaviour:
    Timer(lambda: GetAutomaticStandby.call(), 5*60, 15) # every 5 mins, first after 15
    
# <!-- audio mute (ke)

@after_main
def initAudioMute():
  group = 'Audio Mute'
  signal = Event('Audio Mute', {'group': group, 'order': next_seq(), 'schema': {'type': 'boolean' }})

  def handle_resp(data):
    if data == '01':   value = True
    elif data == '00': value = False
    else:
      return console.warn('audio_mute: got unknown resp - %s' % data)
    
    signal.emit(value)  

  getter = Action('Get Audio Mute', lambda arg: transportRequest('get_audiomute', 'ke %s ff\r' % setID, lambda resp: checkHeaderAndHandleData(resp, 'e', handle_resp, ctx='get_audiomute')),
         {'group': group, 'order': next_seq()})
  
  def handler(arg):
    if arg in [ True, 1, 'On', 'ON', 'on' ]:       value = '01'
    elif arg in [ False, 0, 'Off', 'OFF', 'off' ]: value = '00'
    else:
      return console.warn('audio_mute: unknown arg - %s' % arg)
    
    transportRequest('set_audiomute', 'ke %s %s\r' % (setID, value), lambda resp: checkHeaderAndHandleData(resp, 'e', handle_resp))    

  setter = Action('Audio Mute', handler, {'group': group, 'order': next_seq(), 'schema': {'type': 'boolean'}})

  Timer(lambda: getter.call(), 5, 15) # every 5 secs, first after 15  

# -->

# <!-- volume

# Volume ---

@after_main
def initVolumeOperation():
  volEvent = Event('Volume', { 'group': 'Audio', 'order': next_seq(), 'schema': {'type': 'integer' }})

  def handle_VolData(data):
    volEvent.emit(int(data, 16))

  getVolAction = Action('Get Volume', lambda arg: transportRequest('get_vol', 'kf %s ff\r' % setID, lambda resp: checkHeaderAndHandleData(resp, 'f', handle_VolData)), 
         { 'group': 'Audio', 'order': next_seq() })
  
  def action_handler(arg):
    transportRequest('set_volume', 'kf %s %s\r' % (setID, '%0.2x' % arg), lambda resp: checkHeaderAndHandleData(resp, 'f', handle_VolData))

  Action('Volume', action_handler, { 'group': 'Audio', 'order': next_seq(), 'schema': {'type': 'integer' }})

  Timer(lambda: getVolAction.call(), 15, 5) # every 15 seconds, first after 5
  
# -->

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
  
  transportRequest('get_abnormalstate', 'kz %s ff\r' % setID, lambda resp: checkHeaderAndHandleData(resp, 'z', handle_AbnormalStateData, ctx='get_abnormalstate'))

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

  Action('Get Wake-On-LAN', lambda arg: transportRequest('get_wol', 'fw %s ff\r' % setID, lambda resp: checkHeaderAndHandleData(resp, 'w', handle_WOLData, ctx='get_wol')), 
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

Action('Get No Signal Power Off', lambda arg: transportRequest('get_nosignalpoweroff', 'fg %s ff\r' % setID, lambda resp: checkHeaderAndHandleData(resp, 'g', handle_NSPOData, ctx='get_nosignalpoweroff')), 
       {'group': SETTINGS_GROUP, 'desc': NSPO_DESC, 'order': next_seq()})

Action('No Signal Power Off', lambda arg: transportRequest('set_nosignalpoweroff', 'fg %s %s\r' % (setID, ONOFF_CODES_BY_NAME[arg]), lambda resp: checkHeaderAndHandleData(resp, 'g', handle_NSPOData)),
       {'group': SETTINGS_GROUP, 'desc': NSPO_DESC, 'order': next_seq(), 'schema': {'type': 'string', 'enum': ['On', 'Off']}})
  
Timer(lambda: lookup_local_action('Get No Signal Power Off').call(), 5*60, 15) # every 5 mins, first after 15



# LG protocol specific
def checkHeaderAndHandleData(resp, cmdChar, dataHandler, ctx=None):
  # e.g. 'a 01 OK01x'
  
  # Would like to check for x but delimeters are filtered out
  # if resp[-1:]  != 'x':
  #   console.warn('End-of-message delimiter "x" was missing')
  #   return
  ctx = '%s: ' % ctx if ctx != None else ''
  
  if len(resp) < 2:
    console.warn(ctx + 'Response was missing or too small')
    return
  
  if resp[0] != cmdChar:
    console.warn(ctx + 'Response did not match expected command (expected "%s", got "%s")' % (cmdChar, resp[0]))
    return
    
  if not 'OK' in resp:
    console.warn(ctx + 'Response is not positive acknowledgement (no "OK")')
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
    ipAddress = param_ipAddress if not is_blank(param_ipAddress) else local_event_IPAddress.getArg()
      
    if is_blank(ipAddress):
      console.warn('No IP address to use!')
    else:
      # we have an IP address, update and use
      local_event_IPAddress.emit(ipAddress)
      dest = '%s:%s' % (ipAddress, param_adminPort or DEFAULT_ADMINPORT)
      console.log('Connecting to %s...' % dest)
      tcp.setDest(dest)
    
  else:
    console.log('Using serial gateway; make sure "Gateway" remote actions and events are specified')
  
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
        message = 'Missing since %s' % previousContact.toString('h:mm a')
      else:
        message = 'Missing since %s' % previousContact.toString('h:mm a, E d-MMM')
      
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
