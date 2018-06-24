'Make sure network standby settings are set to Never off. See http://openrb.com/wp-content/uploads/2012/02/AVR3312CI_AVR3312_PROTOCOL_V7.6.0.pdf'

param_ipAddress = Parameter({"schema": {"title": "IP address", "type":"string"}, "value": "192.168.100.1", "order": 0})

KNOWN_INPUTS = ["PHONO", "CD", "TUNER", "DVD", "BD", "TV", "SAT/CBL", "DVR", "GAME", "GAME2", 
                   "V.AUX", "DOCK", "HDRADIO", "IPOD", "NET/USB", "RHAPSODY", "NAPSTER", "PANDORA",
                   "LASTFM", "FLICKR", "IRADIO", "USB/IPOD", "MPLAY", "BT"]

param_inputs = Parameter({
  "title": "Inputs", "schema": { 
    "type": "array", "title": "Inputs", "items": {
      "type": "object", "title": "Input", "properties": { 
        "name": { "type": "string", "title": "Name", "order": 1 },
        "code": { "type": "string", "title": "Code", 'order': 2, 
          'enum': KNOWN_INPUTS}
  } } } } )

TCPPORT = 23

def main(arg = None):
  # Master Power is handled by function bindMasterPower()
  
  # Main Zone (No Zone Prefix)
  bindPower('Main Zone', 'ZM', '') 
  bindVolume('Main Zone', 'MV', '')
  bindMuting('Main Zone', 'MU', '')
  bindInputs('Main Zone', 'SI', '')
  
  # Zone 2
  bindPower('Zone 2', 'Z2', 'Zone 2') # groupName: Zone 2, zoneCode: Z2, zonePrefix=Zone 2
  bindVolume('Zone 2', 'Z2', 'Zone 2')
  bindMuting('Zone 2', 'Z2MU', 'Zone 2')
  bindInputs('Zone 2', 'Z2', 'Zone 2')  
  
  # Zone 3
  bindPower('Zone 3', 'Z3', 'Zone 3')
  bindVolume('Zone 3', 'Z3', 'Zone 3')
  bindMuting('Zone 3', 'Z3MU', 'Zone 3')
  bindInputs('Zone 3', 'Z3', 'Zone 3')
  
  dest = '%s:%s' % (param_ipAddress, TCPPORT)
  console.info('Will connect to [%s]' % dest)
  
  tcp.setDest(dest)
  
def connected():
  console.info('Connected')
  tcp.clearQueue()
  
def disconnected():
  console.warn('Disconnected')
  
def sent(data):
  log(3, 'sent: [%s]' % data)

def timeout():
  console.warn('Timeout!')
  
def received(data):
  lastReceive[0] = system_clock()
  log(4, 'recv: [%s]' % data)
  
  parseFeedback(data)

tcp = TCP(connected=connected, received=received, sent=sent, disconnected=disconnected, sendDelimiters='\r', receiveDelimiters='\r', timeout=timeout)
  
callbacksByData = {}
callbacksAndPrefixesList = list()
  
def parseFeedback(resp):
  callback = callbacksByData.get(resp)
  
  if callback != None:
    log(2, 'matched: [%s]' % resp)
    callback(resp)
    return
    
  for (prefix, callback) in callbacksAndPrefixesList:
    if resp.startswith(prefix):
      log(2, 'matched: [%s]' % resp)
      arg = resp[len(prefix):].strip()
      callback(arg)
      return
    
  log(3, '(ignored: [%s])' % resp)

# ZM Power (Main Zone)
# zoneCode: e.g. ZM or Z3, etc.
# NOTE: Master Power is handled in bindMasterPower()
def bindPower(groupName, zoneCode, zonePrefix):
  group = '%s Power' % groupName # e.g. Main Zone Power
  
  powerEvent = Event('%sPower' % zonePrefix, { 'group' : group, 'order': next_seq(), 'schema': { 'type': 'string', 'enum': ['On', 'Off'] } } )
  powerOnEvent = Event('%sPowerOn' % zonePrefix, { 'group' : group, 'order': next_seq(), 'schema': { 'type': 'boolean' } } )
  powerOffEvent = Event('%sPowerOff' % zonePrefix, { 'group' : group, 'order': next_seq(), 'schema': { 'type': 'boolean' } } )
  
  # e.g.
  # >> ZMON / ZMOFF
  # << ZMON / ZMOFF
  
  def handlePowerResp(state):
    if state:
      powerEvent.emitIfDifferent('On')
      powerOnEvent.emitIfDifferent(True)
      powerOffEvent.emitIfDifferent(False)
      
    else:
      powerEvent.emitIfDifferent('Off')
      powerOnEvent.emitIfDifferent(False)
      powerOffEvent.emitIfDifferent(True)
    
  callbacksByData['%sON' % zoneCode] = lambda resp: handlePowerResp(True)
  callbacksByData['%sOFF' % zoneCode] = lambda resp: handlePowerResp(False)
  
  powerOn = Action('%sPower on' % zonePrefix, lambda arg: tcp.send('%sON' % zoneCode), { 'title': 'On', 'group' : group, 'order': next_seq() })
  powerOff = Action('%sPower off' % zonePrefix, lambda arg: tcp.send('%sOFF' % zoneCode), { 'title': 'Off', 'group' : group, 'order': next_seq() })
  
  Timer(lambda: tcp.request('%s?' % zoneCode, lambda resp: parseFeedback(resp)), 10) # poll every 10s

def nullFunc(arg=None):
  pass
  
def bindVolume(groupName, zoneCode, zonePrefix):
  group = '%s Volume' % groupName
  
  volumeEvent = Event('%sVolume' % zonePrefix, { 'group' : group, 'order': next_seq(), 'schema': { 'type': 'integer', "format":"range", "min": 0, "max": 100} })
  
  volumeUp = Action('%sVolume up' % zonePrefix, lambda arg: tcp.send('%sUP' % zoneCode), {'title': 'Up', 'group': group, 'order': next_seq()})
  volumeDown = Action('%sVolume down' % zonePrefix, lambda arg: tcp.send('%sDOWN' % zoneCode), {'title': 'Down', 'group': group, 'order': next_seq()})
  
  def volumeHandler(arg):
    s = str(arg) if arg > 9 else '0%s' % arg
    tcp.send('%s%s' % (zoneCode, s))
  
  volume = Action('%sVolume' % zonePrefix, volumeHandler, { 'group' : group, 'order': next_seq(), 'schema': { 'type': 'integer', "format":"range", "min": 0, "max": 100} })
  
  def volumeRespHandler(arg):
    if len(arg) == 3:
      vol = float(arg) / 10
    else:
      vol = int(arg)
    
    volumeEvent.emitIfDifferent(vol)
    
  callbacksAndPrefixesList.append(('%sMAX' % zoneCode, nullFunc))
  callbacksAndPrefixesList.append(('%s' % zoneCode, volumeRespHandler))
  
  Timer(lambda: tcp.request('%s?' % zoneCode, lambda resp: parseFeedback(resp)), 10)
  
def bindMuting(groupName, zoneCode, zonePrefix):
  group = '%s Muting' % groupName
  
  mutingEvent = Event('%sMuting' % zonePrefix, { 'group' : group, 'order': next_seq(), 'schema': { 'type': 'boolean' } } )
  
  def mute(state):
    if state == True:
      tcp.send('%sON' % zoneCode)
      
    elif state == False:
      tcp.send('%sOFF' % zoneCode)
  
  muteOn = Action('%sMute on' % zonePrefix, lambda arg: mute(True), { 'title': 'On', 'group' : group, 'order': next_seq() })
  muteOff = Action('%sMute off' % zonePrefix, lambda arg: mute(False), { 'title': 'Off', 'group' : group, 'order': next_seq() })
  
  muteToggle = Action('%sMute toggle' % zonePrefix, lambda arg: mute(False if mutingEvent.getArg() == True else True), 
                      { 'title': 'Toggle', 'group' : group, 'order': next_seq() })
  
  callbacksByData['%sON' % zoneCode] = lambda resp: mutingEvent.emitIfDifferent(True)
  callbacksByData['%sOFF' % zoneCode] = lambda resp: mutingEvent.emitIfDifferent(False)
  
  Timer(lambda: tcp.request('%s?' % zoneCode, lambda resp: parseFeedback(resp)), 10)

UNMAPPED_INPUT_CALLBACK = lambda arg: warn(1, 'Unmapped input; ignoring')
  
def bindInputs(groupTitle, zoneCode, zonePrefix):
  group = '%s Inputs' % groupTitle # e.g. Main Zone Inputs
  
  if param_inputs == None:
    console.warn('No named inputs were configured')
    return
  
  # prepopulate all known inputs callbacks; will be overridden by bindInput() later on
  for inputCode in KNOWN_INPUTS:
    callbacksByData['%s%s' % (zoneCode, inputCode)] = UNMAPPED_INPUT_CALLBACK
  
  interlockGroup = list()
  
  for inputInfo in param_inputs:
    bindInput(group, zoneCode, zonePrefix, interlockGroup, inputInfo['name'], inputInfo['code'])
  
def bindInput(group, zoneCode, zonePrefix, interlockGroup, name, code):
  inputEvent = Event('%sInput %s' % (zonePrefix, name), { 'title': name, 'group' : group, 'order': next_seq(), 'desc': 'Input "%s" will be selected.' % code, 
                                         'schema': { 'type': 'boolean' } } )
  
  interlockGroup.append(inputEvent)
  
  def selectInput():
    tcp.send('%s%s' % (zoneCode, code))
  
  def handleInputResponse(arg=None):
    for e in interlockGroup:
      if e == inputEvent:
        inputEvent.emitIfDifferent(True)
      else:
        e.emitIfDifferent(False)
  
  action = Action('%sInput %s' % (zonePrefix, name), lambda arg: tcp.send('%s%s' % (zoneCode, code)), { 'title': name, 'group' : group, 'order': next_seq() })
  
  callbacksByData['%s%s' % (zoneCode, code)] = handleInputResponse
  
  Timer(lambda: tcp.request('%s?' % zoneCode, lambda resp: parseFeedback(resp)), 10)

# NOTE: Master Power is treated differently to Main, Z2, and Z3. 
#       It has slightly different parameters.
@after_main
def bindMasterPower():
  group = 'Master Power'
  
  powerEvent = Event('MasterPower', { 'group' : group, 'order': next_seq(), 'schema': { 'type': 'string', 'enum': ['On', 'Off'] } } )
  powerOnEvent = Event('MasterPowerOn', { 'group' : group, 'order': next_seq(), 'schema': { 'type': 'boolean' } } )
  powerOffEvent = Event('MasterPowerOff', { 'group' : group, 'order': next_seq(), 'schema': { 'type': 'boolean' } } )
  
  # >> PWON / PWSTANBY 
  # << PWON / PWSTANBY
  
  def handlePowerResp(state):
    if state:
      powerEvent.emitIfDifferent('On')
      powerOnEvent.emitIfDifferent(True)
      powerOffEvent.emitIfDifferent(False)
      
    else:
      powerEvent.emitIfDifferent('Off')
      powerOnEvent.emitIfDifferent(False)
      powerOffEvent.emitIfDifferent(True)
    
  callbacksByData['PWON'] = lambda resp: handlePowerResp(True)
  callbacksByData['PWSTANDBY'] = lambda resp: handlePowerResp(False)
  
  powerOn = Action('Master Power on', lambda arg: tcp.send('PWON'), { 'title': 'On', 'group' : group, 'order': next_seq() })
  powerOff = Action('Master Power off', lambda arg: tcp.send('PWSTANDBY'), { 'title': 'Off', 'group' : group, 'order': next_seq() })  
  
  Timer(lambda: tcp.request('PW?', lambda resp: parseFeedback(resp)), 10) # poll every 10s
    
# status ---

local_event_Status = LocalEvent({'title': 'Status', 'group': 'Status', 'order': 9990, "schema": { 'title': 'Status', 'type': 'object', 'properties': {
        'level': {'title': 'Level', 'order': next_seq(), 'type': 'integer'},
        'message': {'title': 'Message', 'order': next_seq(), 'type': 'string'}
    } } })

# <status ---

lastReceive = [0]

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
      if roughDiff < 60:
        message = 'Missing for approx. %s mins' % roughDiff
      elif roughDiff < (60*24):
        message = 'Missing since %s' % previousContact.toString('h:mm:ss a')
      else:
        message = 'Missing since %s' % previousContact.toString('h:mm:ss a, E d-MMM')
      
    local_event_Status.emit({'level': 2, 'message': message})
    
  else:
    local_event_LastContactDetect.emit(str(now))
    local_event_Status.emit({'level': 0, 'message': 'OK'}) 
  
status_check_interval = 75
status_timer = Timer(statusCheck, status_check_interval)  

# status --->

# <logging ---

local_event_LogLevel = LocalEvent({'group': 'Debug', 'order': 10000+next_seq(), 'schema': {'type': 'integer'}})

def warn(level, msg):
  if local_event_LogLevel.getArg() >= level:
    console.warn(('  ' * level) + msg)

def log(level, msg):
  if local_event_LogLevel.getArg() >= level:
    console.log(('  ' * level) + msg)    

# --->
