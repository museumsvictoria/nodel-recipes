'''Sangean DAB radio.'''

param_Disabled = Parameter({'schema': {'type': 'boolean'}})

param_Port = Parameter({'schema': {'type': 'integer', 'hint': '2244 (default)'}})

param_ipAddress = Parameter({'title': 'IP address', 'schema': {'type': 'string'}})

param_PIN = Parameter({'title': 'PIN', 'schema': {'type': 'string', 'hint': '1234 (default)'}})

import xml.etree.ElementTree as ET # for XML ops
from threading import RLock        # for single-call HTTP

# holds mode info
modes = []

# holds mode actions by ID
modeActions = {}

# holds mode events by ID
modeEvents = {}

# holds the presets by mode ID
# e.g. { 'DAB': { '0' : presetInfo } }
presets = {}

# holds the current list
listItems = {}


# holds the current session ID
current_sid = None

# the info poll, updates after 10s then every 15s
info_poller = Timer(lambda: refreshInfo(), 10, 15)

# sync up the items every 12 hours (after 15s)
item_syncer = Timer(lambda: refreshItems(), 12*60*60, 15)

def main(arg=None):
    if param_Disabled:
      console.warn('Disabled! nothing to do')
      return
    
    call(init_session, 1)

def init_session():
    createSession()
    
    getValidModes.call()
    
httpLock = RLock()
  
# returns a new session ID
def createSession():
    url = 'http://%s:%s/fsapi/CREATE_SESSION?pin=%s' % (param_ipAddress, param_Port or 2244, param_PIN or '1234')
    
    try:
      httpLock.acquire()
      
      data = get_url(url)
      
    finally:
      httpLock.release()
      
    print 'got data.'
    e_fsResponse = ET.fromstring(data)
    
    print 'finding session'
    e_sessionId = e_fsResponse.find('sessionId')
    
    sid = e_sessionId.text
    
    print 'Establishing a new session ID...'
    
    global current_sid
    current_sid = sid
  
    print '(session ID is %s)' % sid
    
    return sid

def debugForceNewSession():
  url = 'http://%s:%s/fsapi/CREATE_SESSION?pin=%s' % (param_ipAddress, param_Port or 2244, param_PIN or '1234')
    
  try:
    httpLock.acquire()
    data = get_url(url)
  finally:
    httpLock.release()
  
  print 'got data: [%s]' % data
  
def performRawOp(endPoint, params=None):
  query = {'pin': param_PIN or '1234', 'sid': current_sid}
  for x in params or []:
    query[x] = str(params[x])
    
  url = 'http://%s:%s/fsapi/%s' % (param_ipAddress, param_Port or 2244, endPoint)
  
  # try twice, assume it's a session issue
  
  # light log
  log(2, '%s?%s' % (endPoint, query))
  
  # heavy log
  log(3, 'url:%s query:%s' % (url, query))
  
  try:
    try:
      httpLock.acquire()
      result = get_url(url, query=query)
      
    finally:
      httpLock.release()
      
    lastReceive[0] = system_clock()
    return result
  
  except:
    console.warn('performOp failure [%s]. Creating new session and trying again...' % endPoint)
    
    createSession()
    
    # restamp SID
    query['sid'] = current_sid
    
    log(1, '(retry) url:%s query:%s' % (url, query))
    
    return get_url(url, query=query)

def performOp(endPoint, params=None, rawResult=False):
    data = performRawOp(endPoint, params)

    if rawResult:
        return data

    e_fsResponse = ET.fromstring(data.encode('utf-8'))

    e_statusText = e_fsResponse.find('status').text
    if e_statusText != 'FS_OK' and e_statusText != 'FS_LIST_END':
        raise Exception('Bad response - [%s] for URL [%s] params [%s]' % (e_statusText, endPoint, params))

    return e_fsResponse

# Refreshes all volatile info and ensure the nav_state is set
# so operations can occur
def refreshInfo():
  log(2, 'refreshInfo')
  
  local_action_getPlayInfoName()
  local_action_getPlayInfoText()
  local_action_getPlayStatus()
  local_action_getNavState()
  
  # ensure nav state
  if local_event_NavState.getArg() != 1:
    log(1, 'Nav State is not set, setting...')
    lookup_local_action('SetNavState').call(1) 
    
def refreshItems():
  log(1, 'refreshItems')
  
  lookup_local_action('listItems').call()
  
# <!--- modes
  
# Gets valid modes,
# Response is something like:
# <fsapiResponse><status>FS_OK</status>
#	<item key="0">
#		<field name="id"><c8_array>IR</c8_array></field>
#		<field name="selectable"><u8>1</u8></field>
#		<field name="label"><c8_array>Internet radio</c8_array></field>
#	</item>
#	<item key="1">
#		<field name="id"><c8_array>MP</c8_array></field>
#		<field name="selectable"><u8>1</u8></field>
#		<field name="label"><c8_array>Music player</c8_array></field>
#	</item>
#    ...
#
local_event_Mode = LocalEvent({'group': 'Modes', 'schema': {'type': 'string'}})

local_event_Modes = LocalEvent({'group': 'Modes', 'schema': {'type': 'array', 'items': {'type': 'object', 'properties': {
          'key': {'type': 'string', 'order': 1},
          'value': {'type': 'string', 'order': 2}}}}})

@local_action({'group': 'Modes', 'order': next_seq()})
def getValidModes():
    e_fsResponse = performOp('LIST_GET_NEXT/netRemote.sys.caps.validModes/-1', {'maxItems': '65536'})
    e_items = e_fsResponse.findall('item')
    
    del modes[:]
    
    for e_item in e_items:
        modeInfo = {}
        
        key = e_item.attrib['key']
        
        modeInfo['key'] = key
        
        for e_field in e_item:
            if e_field.attrib.get('name') == 'id':
                modeInfo['id'] = e_field.find('c8_array').text
                
            elif e_field.attrib.get('name') == 'selectable':
                # only include selectable mods
                if e_field.find('u8').text != '1':
                  modeInfo = None
                  break
            
            elif e_field.attrib.get('name') == 'label':
                modeInfo['label'] = e_field.find('c8_array').text
        
        if modeInfo != None:
          modes.append(modeInfo)
    
    local_event_Modes.emit([{'key': item['id'], 'value': item['label']} for item in modes])
    
    bindModes()
    
    listPresets.call()
    
def bindModes():
  for modeInfo in modes:
    key = modeInfo['key']
    
    id = modeInfo['id']
    label = modeInfo['label']
            
    # use function to force closure on 'modeInfo' variable
    def bindAction(tmpModeInfo):
      action = Action(tmpModeInfo['id'], lambda arg: Mode.call(tmpModeInfo['id']), 
                      { 'title': label, 'order': next_seq(), 'group': 'Modes'})
            
      modeActions[id] = action
        
    if modeActions.get(id) is None:
      bindAction(modeInfo)

@local_action({'group': 'Modes', 'order': next_seq()})
def getMode():
  if local_event_Power.getArg() != 'On':
    log(2, 'Ignoring GetMode; Power not On')
    return
  
  doGetMode()
  
mode_poller = Timer(lambda: getMode.call(), 60, 15) # poll mode every minute, first after 15s
    
def doGetMode():
  e_fsResponse = performOp('GET/netRemote.sys.mode')
  key = e_fsResponse.find('value').find('u32').text
  
  result = [item for item in modes if item['key'] == key]
  
  if not result:
    return None
  
  currentModeInfo = result[0]
      
  log(1, 'currentMode %s' % currentModeInfo)
    
  local_event_Mode.emit(currentModeInfo['id'])
    
  return currentModeInfo

@local_action({'group': 'Modes', 'order': next_seq(), 'schema': {'type': 'string'}})
def Mode(id):
  result = [item for item in modes if item['id'] == id]
  
  if not result:
    return None
  
  currentModeInfo = result[0]  
  
  performOp('SET/netRemote.sys.mode', params={'value': currentModeInfo['key']})
  doGetMode()
  
  list_syncer.setDelay(2.2)
  
  presets_syncer.setDelay(2)
  
# modes --!>

# <!-- power

local_event_Power = LocalEvent({'title': 'Power', 'group': 'Power', 'order': next_seq(), 'schema': {'type': 'string', 'enum': ['On', 'Off']}})

@local_action({'title': 'On', 'group': 'Power', 'order': next_seq()})
def PowerOn():
  lookup_local_action('Power').call('On')
    
@local_action({'title': 'Off', 'group': 'Power', 'order': next_seq()})
def PowerOff():
  lookup_local_action('Power').call('Off')

@local_action({'group': 'Power', 'order': next_seq(), 'schema': {'type': 'string', 'enum': ['On', 'Off']}})
def Power(arg):
  if arg == "On":    performOp('SET/netRemote.sys.power', params={'value': 1})
  elif arg == "Off": performOp('SET/netRemote.sys.power', params={'value': 0})

  local_event_Power.emit(arg)
  
@local_action({'group': 'Power', 'order': next_seq()})
def getPower():
    e_fsResponse = performOp('GET/netRemote.sys.power')
    value = e_fsResponse.find('value').find('u8').text == '1'
    
    if value: local_event_Power.emit('On')
    else:     local_event_Power.emit('Off')
      
power_poller = Timer(lambda: getPower.call(), 60, 15) # poll mode every minute, first after 15s      

# power ---!>
        
local_event_FriendlyName = LocalEvent({'group': 'System info', 'order': next_seq(), 'schema': {'type': 'string'}})

@local_action({'group': 'System info', 'order': next_seq()})
def getFriendlyName(ignore):
    e_fsResponse = performOp('GET/netRemote.sys.info.friendlyName')
    value = e_fsResponse.find('value').find('c8_array').text
    
    local_event_FriendlyName.emit(value)


local_event_DABScan = LocalEvent({"group": "Navigation", "schema": {"type": "string"}})

def local_action_getDABScan(ignore):
    '{"group": "Navigation"}'
    raw = performOp('GET/netRemote.nav.action.dabScan', rawResult=True)
    
    local_event_DABScan.emit(raw)
    
local_event_PlayInfoName = LocalEvent({"group": "Play info", "schema": {"type": "string"}})

def local_action_getPlayInfoName(ignore=None):
    '{"group": "Play info"}'
    e_fsResponse = performOp('GET/netRemote.play.info.name')
    value = e_fsResponse.find('value').find('c8_array').text
    local_event_PlayInfoName.emit((value or '').strip())

    
local_event_PlayInfoText = LocalEvent({"group": "Play info", "schema": {"type": "string"}})

def local_action_getPlayInfoText(ignore=None):
    '{"group": "Play info"}'
    e_fsResponse = performOp('GET/netRemote.play.info.text')
    value = e_fsResponse.find('value').find('c8_array').text
    local_event_PlayInfoText.emit((value or '').strip())

    
local_event_PlayCaps = LocalEvent({"group": "Play info", "schema": {"type": "string"}})

def local_action_getPlayCaps(ignore=None):
    '{"group": "Play info"}'
    e_fsResponse = performOp('GET/netRemote.play.caps')
    value = int(e_fsResponse.find('value').find('u32').text)
    local_event_PlayCaps.emit(value)

    
# 1=buffering/loading, 2=playing, 3=paused, 5=stopped?
    
local_event_PlayStatus = LocalEvent({"group": "Play info", "schema": {"type": "string"}})

def local_action_getPlayStatus(ignore=None):
    '{"group": "Play info"}'
    e_fsResponse = performOp('GET/netRemote.play.status')
    value = int(e_fsResponse.find('value').find('u8').text)
    
    if value == 1:   valueText = 'Buffering/Loading'
    elif value == 2: valueText = 'Playing'
    elif value == 3: valueText = 'Paused'
    elif value == 5: valueText = 'Not Playing'
    else:            valueText = 'Not Ready (ERR#%s)' % value
    
    local_event_PlayStatus.emit(valueText)
    

local_event_PlayInfoGraphicURI = LocalEvent({"group": "Play info", "schema": {"type": "string"}})

def local_action_getPlayInfoGraphicURI(ignore=None):
    '{"group": "Play info"}'
    e_fsResponse = performOp('GET/netRemote.play.info.graphicUri')
    value = e_fsResponse.find('value').find('c8_array').text
    local_event_PlayInfoGraphicURI.emit(value)
    
local_event_PlayInfoArtist = LocalEvent({"group": "Play info", "schema": {"type": "string"}})

def local_action_getPlayInfoArtist(ignore=None):
    '{"group": "Play info"}'
    e_fsResponse = performOp('GET/netRemote.play.info.artist')
    value = e_fsResponse.find('value').find('c8_array').text
    local_event_PlayInfoArtist.emit(value)

local_event_PlayInfoAlbum = LocalEvent({"group": "Play info", "schema": {"type": "string"}})

def local_action_getPlayInfoAlbum(ignore=None):
    '{"group": "Play info"}'
    e_fsResponse = performOp('GET/netRemote.play.info.album')
    value = e_fsResponse.find('value').find('c8_array').text
    local_event_PlayInfoAlbum.emit(value)    

    
local_event_NavState = LocalEvent({"group": "Navigation", "schema": {"type": "integer"}})

def local_action_getNavState(ignore=None):
    '{"group": "Navigation"}'
    e_fsResponse = performOp('GET/netRemote.nav.state')
    value = int(e_fsResponse.find('value').find('u8').text)
    local_event_NavState.emit(value)
    
def local_action_setNavState(state):
    '{"group": "Navigation", "schema": {"type": "integer"}}'
    data = performOp('SET/netRemote.nav.state', params={'value': state}, rawResult=True)
    print 'setNavState response: %s' % data

# <!-- presets
    
# <fsapiResponse>
# <status>FS_OK</status>
# <item key="0">
#    <field name="name"><c8_array>triple j</c8_array></field>
# </item>
# <item key="1">
#     <field name="name"><c8_array>1116 SEN</c8_array></field>
# </item>
# <item key="2">
#     <field name="name"><c8_array>Double J</c8_array></field>
# </item>
# <item key="3">
#     <field name="name"><c8_array>774 ABCMelbourne</c8_array></field>
# </item>
# <item key="4">
# ...

# NOTE: the list of presets signals and actions are created dynamically
presets_syncer = Timer(lambda: listPresets.call(), 10, 10)

@local_action({'group': 'Presets', 'order': next_seq()})
def listPresets():
    log(1, 'List Presets called')
  
    e_fsResponse = performOp('LIST_GET_NEXT/netRemote.nav.presets/-1', params={'maxItems': 20})
    e_items = e_fsResponse.findall('item')
    
    size = len(e_items)
    
    for e_item in e_items:
        key = e_item.attrib['key']
        presetNum = int(key) + 1
        name = None
        
        for e_field in e_item:
            if e_field.attrib.get('name') == 'name':
                name = e_field.find('c8_array').text
        
        presetNameSignal = lookup_local_event('Preset %s Name' % presetNum)
        
        if presetNameSignal != None:
          # already set up
          presetNameSignal.emit(name or 'unassigned')
          continue
          
        # otherwise initialise actions and signals
          
        presetNameSignal = Event('Preset %s Name' % presetNum, {'group': 'Presets', 'order': next_seq(), 'schema': {'type': 'string'}})
        presetNameSignal.emit(name or 'unassigned')
        
        presetSelectedSignal = Event('Preset %s Selected' % presetNum, {'group': 'Presets', 'order': next_seq(), 'schema': {'type': 'boolean'}})
        
        # need this for variable capture within loops
        bindPreset(key, presetNum, size)
        
def bindPreset(key, presetNum, size):
  def storeHandler(ignore):
    addPreset.call(key)
    
  Action('Preset %s Store' % presetNum, storeHandler, {'group': 'Presets', 'order': next_seq()})  
  
  def handler(ignore):
    selectPreset.call(key)

    for i in range(1, size+1): # set boolean 'selected' on all the preset signals
      lookup_local_event('Preset %s Selected' % i).emitIfDifferent(i == presetNum)

  action = Action('Preset %s Select' % presetNum, handler, {'group': 'Presets', 'order': next_seq()})
    
@local_action({'group': 'Presets', 'order': next_seq(), 'schema': {'type': 'integer'}})
def selectPreset(value):
  performOp('SET/netRemote.nav.action.selectPreset', params={'value': value})
  
  listPresets.call()
    
@local_action({'group': 'Presets', 'order': next_seq(), 'schema': {'type': 'integer'}})
def addPreset(value):
  performOp('SET/netRemote.play.addPreset', params={'value': value})
  
# presets --!>
    
# <fsapiResponse>
# <status>FS_OK</status>
# <item key="9">
#   <field name="name"><c8_array>1116 SEN</c8_array></field>
#   <field name="type"><u8>1</u8></field>
#   <field name="subtype"><u8>1</u8></field>
# </item>
# <item key="15">
#   <field name="name"><c8_array>1377 3MP</c8_array></field>
#   <field name="type"><u8>1</u8></field>
#   <field name="subtype"><u8>1</u8></field>
# </item>
# <item key="20">
#   <field name="name"><c8_array>3AW</c8_array></field>
#   <field name="type"><u8>1</u8></field>
#   <field name="subtype"><u8>1</u8>
# ...
# http://192.168.178.97:2244/fsapi/LIST_GET_NEXT/netRemote.nav.list/-1?pin=1234&sid=987043723&maxItems=20
#
# and then at the end:
# <fsapiResponse>
#   <status>FS_LIST_END</status>
# </fsapiResponse>

local_event_SelectionList = LocalEvent({'group': 'Navigation', 'order': next_seq(), 'schema': {'type': 'array', 'items': { 'type': 'object', 'properties': {
          'key': {'order': 1, 'type': 'string'},
          'value': {'order': 2,' type': 'string'}
        }}}})

local_event_SelectionFolders = LocalEvent({'group': 'Navigation', 'order': next_seq(), 'schema': {'type': 'array', 'items': { 'type': 'object', 'properties': {
          'key': {'order': 1, 'type': 'string'},
          'value': {'order': 2,' type': 'string'}
        }}}})

@local_action({'group': 'Navigation', 'order': next_seq()})
def ListItems(ignore=None):
  log(1, "List Items called")
  
  if local_event_Power.getArg() != 'On':
    console(2, 'ignoring ListItems; power is not on')
    return
  
  doListItems()
  
list_syncer = Timer(lambda: ListItems.call(), 10, 10)
  
def doListItems():
  # first of many operations
  e_fsResponse = performOp('LIST_GET_NEXT/netRemote.nav.list/-1', params={'maxItems': 10})
  
  listItems.clear()
  signalItems = list()
  
  folderItems = list()
    
  for x in range(20): # limit to 20 screens incase of infinintely long list
      # break out if at end of list
      status = e_fsResponse.find('status')
      if status == 'FS_LIST_END':
        break
      
      # otherwise get next page worth
      
      lastKey = None
      
      e_items = e_fsResponse.findall('item')
      for e_item in e_items:
        itemInfo = {}
        
        key = e_item.attrib['key']
        
        itemInfo['key'] = key
        lastKey = key
        
        for e_field in e_item:
            if e_field.attrib.get('name') == 'name':
                itemInfo['name'] = e_field.find('c8_array').text
                
            elif e_field.attrib.get('name') == 'type':
                itemInfo['type'] = e_field.find('u8').text
                
            elif e_field.attrib.get('name') == 'subtype':
                itemInfo['subtype'] = int(e_field.find('u8').text)
        
        listItems[key] = itemInfo
        
        subType = itemInfo['subtype']
        if subType == 1:
          signalItems.append({ 'key': itemInfo['key'], 'value': itemInfo['name']})
          
        elif subType == 0:
          folderItems.append({ 'key': itemInfo['key'], 'value': itemInfo['name']})
      
      if lastKey == None:
        break

      # next op using last key  
      e_fsResponse = performOp('LIST_GET_NEXT/netRemote.nav.list/%s' % lastKey, params={'maxItems': 10})
        
  local_event_SelectionList.emit(signalItems)
  local_event_SelectionFolders.emit(folderItems)
    
def local_action_selectItem(value):
    '{"group": "Navigation", "schema": {"type": "integer"}}'
    e_fsResponse = performOp('SET/netRemote.nav.action.selectItem', params={'value': value})
    list_syncer.setDelay(1.5)

# def navigate
# 'Back'??
# http://192.168.178.97:2244/fsapi/SET/netRemote.nav.action.navigate?pin=1234&sid=%s&value=4294967295
def local_action_Back(value):
    '{"group": "Navigation"}'
    performOp('SET/netRemote.nav.action.navigate', params={'value': 4294967295})


# Navigate to item 5
# http://192.168.178.97:2244/fsapi/SET/netRemote.nav.action.navigate?pin=1234&sid=%s&value=5
def local_action_NavigateTo(value):
    '{"group": "Navigation", "schema": {"type": "integer"}}'
    performOp('SET/netRemote.nav.action.navigate', params={'value': value})
    
    list_syncer.setDelay(1.5)

def local_action_Pause(ignore = None):
    '{"group": "Play control" }'
    performOp('SET/netRemote.play.control', params={'value': 2})
    
def local_action_Play(ignore = None):
    '{"group": "Play control" }'
    performOp('SET/netRemote.play.control', params={'value': 1})
    
def local_action_Skip(ignore = None):
    '{"group": "Play control" }'
    performOp('SET/netRemote.play.control', params={'value': 3})

def local_action_Previous(ignore = None):
    '{"group": "Play control" }'
    performOp('SET/netRemote.play.control', params={'value': 4})

def local_action_setVolume(volume):
    '{"group": "Play control", "schema": {"type": "integer"}}'
    performOp('SET/netRemote.sys.audio.volume', params={'value': volume})
    
# position (seek)
# http://192.168.178.97:2244/fsapi/SET/netRemote.play.position?pin=1234&sid=22389622&value=165785    
def local_action_setPosition(position):
    '{"group": "Play control", "schema": {"type": "integer"}}'
    performOp('SET/netRemote.play.position', params={'value': position})
    
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
    # update contact info
    local_event_LastContactDetect.emit(str(now))
    
    # TODO: check internal device status if possible

    local_event_LastContactDetect.emit(str(now))
    local_event_Status.emit({'level': 0, 'message': 'OK'})
    
status_check_interval = 75
status_timer = Timer(statusCheck, status_check_interval)

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