'''Sangean DAB radio.'''

import xml.etree.ElementTree as ET

# Dynamic parameters
param_ipAddress = Parameter({"title":"IP address", "desc":"The IP address to connect to.","schema":{"type":"string"},"value":"192.168.100.1","order":0})
param_pin = Parameter({"title": "PIN", "desc":"The PIN used within the device.","schema":{"type":"string"},"value":"1234", "order": 1})

# holds mode info by key
modes = {}

# holds mode actions by ID
modeActions = {}

# holds mode events by ID
modeEvents = {}


# holds eq presets infos by key
eqPresets = {}


# holds the presets by mode ID
# e.g. { 'DAB': { '0' : presetInfo } }
presets = {}

# holds the current list
listItems = {}


# holds the current session ID
current_sid = None

def main(arg = None):
    print 'Nodel script started.'
    
    call_delayed(4, delayBegin)

def delayBegin():
    createSession()
    
    local_action_getValidModes()

# returns a new session ID
def createSession():
    url = 'http://%s:2244/fsapi/CREATE_SESSION?pin=%s' % (param_ipAddress, param_pin)
    print 'getting data... url=%s' % url
    data = getURL(url)
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

# Gets valid modes,
# Response is something like:
# <fsapiResponse>
#	<status>FS_OK</status>
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
local_event_Mode = LocalEvent({"group": "Modes", "schema": {"type": "string"}})

def local_action_getValidModes(ignore=None):
    '{"group": "Modes"}'
    data = getURL('http://%s:2244/fsapi/LIST_GET_NEXT/netRemote.sys.caps.validModes/-1?pin=%s&sid=%s&maxItems=65536' % (param_ipAddress, param_pin, current_sid))
    e_fsResponse = ET.fromstring(data)
    e_items = e_fsResponse.findall('item')
    for e_item in e_items:
        modeInfo = {}
        
        key = e_item.attrib['key']
        
        modeInfo['key'] = key
        
        for e_field in e_item:
            if e_field.attrib.get('name') == 'id':
                modeInfo['id'] = e_field.find('c8_array').text
                
            elif e_field.attrib.get('name') == 'selectable':
                modeInfo['selectable'] = (e_field.find('u8').text == '1')
            
            elif e_field.attrib.get('name') == 'label':
                modeInfo['label'] = e_field.find('c8_array').text
        
        modes[key] = modeInfo
        
    bindModes()
    
    print modes
    
def bindModes():
    for key in modes:
        modeInfo = modes[key]
        # skip non-selectable modes
        if not modeInfo['selectable']:
            continue
            
        id = modeInfo['id']
        label = modeInfo['label']
            
        # use function to force closure on 'modeInfo' variable
        def bindAction(tmpModeInfo):
            action = Action(tmpModeInfo['id'], lambda arg: local_action_setMode(tmpModeInfo['key']), { 'title': label, 'group': 'Modes'})
            modeActions[id] = action
        
        if modeActions.get(id) is None:
            bindAction(modeInfo)
    
# Get power and mode state.
# Response is like:
# <fsapiResponse>
# <status>FS_OK</status>
#     <value> <u32>1</u32> </value>
# </fsapiResponse>
def local_action_getMode(ignore=None):
    '{"group": "Modes"}'
    data = getURL('http://%s:2244/fsapi/GET/netRemote.sys.mode?pin=%s&sid=%s' % (param_ipAddress, param_pin, current_sid))
    e_fsResponse = ET.fromstring(data)
    key = e_fsResponse.find('value').find('u32').text
    modeInfo = modes.get(key)
    if modeInfo is None:
        return None
      
    print 'currentMode: %s' % modeInfo
    
    local_event_Mode.emit(modeInfo['id'])
    
    return modeInfo
    
def local_action_setMode(mode):
    '{"group": "Modes", "schema": {"type": "string"} }'
    url = 'http://%s:2244/fsapi/SET/netRemote.sys.mode?pin=%s&sid=%s&value=%s' % (param_ipAddress, param_pin, current_sid, mode)
    data = getURL(url)
    print url
    print data

# Local events this Node provides
local_event_Power = LocalEvent({"title": "Power", "group": "Power", "order": 1, "schema": {"type": "string", "enum": ["On", "Off"]}})

def local_action_PowerOn(arg = None):
  """{"title":"Power on","desc":"Controls the power state.","group":"Power","order": 0}"""
  local_action_Power('On')
    
def local_action_PowerOff(arg = None):
  """{"title":"Power off","desc":"Controls the power state.","group":"Power","order": 1}"""
  local_action_Power('Off')

# Local actions this Node provides
def local_action_Power(arg = None):
  """{"title":"Power","desc":"Controls the power state.","group":"Power","order": 0, "schema": {"type": "string", "enum": ["On", "Off"]}}"""
  
  if arg is None:
    return
  
  elif arg == "On":
    data = "http://%s:2244/fsapi/SET/netRemote.sys.power?pin=%s&sid=%s&value=1" % (param_ipAddress, param_pin, current_sid)
    print 'sending %s' % data
    getURL(data)
  
  elif arg == "Off":
    data = "http://%s:2244/fsapi/SET/netRemote.sys.power?pin=%s&sid=%s&value=0" % (param_ipAddress, param_pin, current_sid)
    print 'sending %s' % data
    getURL(data)

  else:
    return
  
  local_event_Power.emit(arg)
  
def local_action_getPower(ignore=None):
    '{"group": "Power"}'
    data = getURL('http://%s:2244/fsapi/GET/netRemote.sys.power?pin=%s&sid=%s' % (param_ipAddress, param_pin, current_sid))
    e_fsResponse = ET.fromstring(data)
    value = e_fsResponse.find('value').find('u8').text == '1'
    
    if value:
    	local_event_Power.emit('On')
    else:
        local_event_Power.emit('Off')

        
local_event_Scrobble = LocalEvent({"group": "Play info", "schema": {"type": "string"}})

def local_action_getScrobble(ignore):
    '{"group": "Play info"}'
    data = getURL('http://%s:2244/fsapi/GET/netRemote.play.scrobble?pin=%s&sid=%s' % (param_ipAddress, param_pin, current_sid))
    e_fsResponse = ET.fromstring(data)
    value = e_fsResponse.find('value').find('u8').text
    
    local_event_Scrobble.emit(value)

    
local_event_FriendlyName = LocalEvent({"group": "System info", "schema": {"type": "string"}})

def local_action_getFriendlyName(ignore):
    '{"group": "System info"}'
    data = getURL('http://%s:2244/fsapi/GET/netRemote.sys.info.friendlyName?pin=%s&sid=%s' % (param_ipAddress, param_pin, current_sid))
    e_fsResponse = ET.fromstring(data)
    value = e_fsResponse.find('value').find('c8_array').text
    
    local_event_FriendlyName.emit(value)


local_event_DABScan = LocalEvent({"group": "Navigation", "schema": {"type": "string"}})

def local_action_getDABScan(ignore):
    '{"group": "Navigation"}'
    data = getURL('http://%s:2244/fsapi/GET/netRemote.nav.action.dabScan?pin=%s&sid=%s' % (param_ipAddress, param_pin, current_sid))
    e_fsResponse = ET.fromstring(data)
    # value = e_fsResponse.find('value').find('c8_array').text
    
    local_event_DABScan.emit(data)

    
local_event_DABFreqList = LocalEvent({"group": "System info", "schema": {"type": "string"}})

def local_action_getDABFreqList(ignore):
    '{"group": "System info"}'
    data = getURL('http://%s:2244/fsapi/GET/netRemote.sys.caps.dabFreqList?pin=%s&sid=%s' % (param_ipAddress, param_pin, current_sid))
    e_fsResponse = ET.fromstring(data)
    # value = e_fsResponse.find('value').find('c8_array').text
    
    local_event_DABFreqList.emit(data) 

    
local_event_Frequency = LocalEvent({"group": "Play info", "schema": {"type": "string"}})

def local_action_getFrequency(ignore):
    '{"group": "Play info"}'
    data = getURL('http://%s:2244/fsapi/GET/netRemote.play.frequency?pin=%s&sid=%s' % (param_ipAddress, param_pin, current_sid))
    local_event_Frequency.emit(data)

    
local_event_SerivceIdsFmRdsPi = LocalEvent({"group": "Play info", "schema": {"type": "string"}})
    
def local_action_getSerivceIdsFmRdsPi(ignore):
    '{"group": "Play info"}'
    data = getURL('http://%s:2244/fsapi/GET/netRemote.play.serviceIds.fmRdsPi?pin=%s&sid=%s' % (param_ipAddress, param_pin, current_sid))
    
    local_event_SerivceIdsFmRdsPi.emit(data)
    

# Gets eq presets,
# Response is something like:
# <fsapiResponse>
# <status>FS_OK</status>
# <item key="0"><field name="label"><c8_array>My EQ</c8_array></field></item>
# <item key="1"><field name="label"><c8_array>Normal</c8_array></field></item>
# <item key="2"><field name="label"><c8_array>Flat</c8_array></field></item>
# <item key="3"><field name="label"><c8_array>Jazz</c8_array></field></item>
# <item key="4"><field name="label"><c8_array>Rock</c8_array></field></item>
# <item key="5"><field name="label"><c8_array>Movie</c8_array></field></item>
def local_action_getEqPresets(ignore):
    '{"group": "Eq presets"}'
    data = getURL('http://%s:2244/fsapi/LIST_GET_NEXT/netRemote.sys.caps.eqPresets/-1?pin=%s&sid=%s&maxItems=65536' % (param_ipAddress, param_pin, current_sid))
    e_fsResponse = ET.fromstring(data)
    e_items = e_fsResponse.findall('item')
    for e_item in e_items:
        eqPresetInfo = {}
        
        key = e_item.attrib['key']
        
        eqPresetInfo['key'] = key
        
        for e_field in e_item:
            if e_field.attrib.get('name') == 'label':
                eqPresetInfo['label'] = e_field.find('c8_array').text
        
        eqPresets[key] = eqPresetInfo
        
    print eqPresets

    
local_event_Repeat = LocalEvent({"group": "Play info", "schema": {"type": "boolean"}})

def local_action_getRepeat(ignore):
    '{"group": "Play info"}'
    data = getURL('http://%s:2244/fsapi/GET/netRemote.play.repeat?pin=%s&sid=%s' % (param_ipAddress, param_pin, current_sid))
    e_fsResponse = ET.fromstring(data)
    value = e_fsResponse.find('value').find('u8').text == '1'
    local_event_Repeat.emit(value)

    
local_event_VolumeSteps = LocalEvent({"group": "Play info", "schema": {"type": "integer"}})

def local_action_getVolumeSteps(ignore):
    '{"group": "System info"}'
    data = getURL('http://%s:2244/fsapi/GET/netRemote.sys.caps.volumeSteps?pin=%s&sid=%s' % (param_ipAddress, param_pin, current_sid))
    e_fsResponse = ET.fromstring(data)
    value = int(e_fsResponse.find('value').find('u8').text)
    local_event_VolumeSteps.emit(value)

    
local_event_PlayInfoName = LocalEvent({"group": "Play info", "schema": {"type": "string"}})

def local_action_getPlayInfoName(ignore):
    '{"group": "Play info"}'
    data = getURL('http://%s:2244/fsapi/GET/netRemote.play.info.name?pin=%s&sid=%s' % (param_ipAddress, param_pin, current_sid))
    e_fsResponse = ET.fromstring(data)
    value = e_fsResponse.find('value').find('c8_array').text
    local_event_PlayInfoName.emit(value)

    
local_event_PlayInfoText = LocalEvent({"group": "Play info", "schema": {"type": "string"}})

def local_action_getPlayInfoText(ignore):
    '{"group": "Play info"}'
    data = getURL('http://%s:2244/fsapi/GET/netRemote.play.info.text?pin=%s&sid=%s' % (param_ipAddress, param_pin, current_sid))
    e_fsResponse = ET.fromstring(data)
    value = e_fsResponse.find('value').find('c8_array').text
    local_event_PlayInfoText.emit(value)
    

local_event_PlayCaps = LocalEvent({"group": "Play info", "schema": {"type": "string"}})

def local_action_getPlayCaps(ignore):
    '{"group": "Play info"}'
    data = getURL('http://%s:2244/fsapi/GET/netRemote.play.caps?pin=%s&sid=%s' % (param_ipAddress, param_pin, current_sid))
    e_fsResponse = ET.fromstring(data)
    value = int(e_fsResponse.find('value').find('u32').text)
    local_event_PlayCaps.emit(value)

    
local_event_PlayStatus = LocalEvent({"group": "Play info", "schema": {"type": "string"}})

def local_action_getPlayStatus(ignore):
    '{"group": "Play info"}'
    data = getURL('http://%s:2244/fsapi/GET/netRemote.play.status?pin=%s&sid=%s' % (param_ipAddress, param_pin, current_sid))
    e_fsResponse = ET.fromstring(data)
    value = int(e_fsResponse.find('value').find('u8').text)
    local_event_PlayStatus.emit(value)
    

local_event_PlayInfoGraphicURI = LocalEvent({"group": "Play info", "schema": {"type": "string"}})

def local_action_getPlayInfoGraphicURI(ignore):
    '{"group": "Play info"}'
    data = getURL('http://%s:2244/fsapi/GET/netRemote.play.info.graphicUri?pin=%s&sid=%s' % (param_ipAddress, param_pin, current_sid))
    e_fsResponse = ET.fromstring(data)
    value = e_fsResponse.find('value').find('c8_array').text
    local_event_PlayInfoGraphicURI.emit(value)
    

local_event_Shuffle = LocalEvent({"group": "Play info", "schema": {"type": "boolean"}})

def local_action_getRepeat(ignore):
    '{"group": "Play info"}'
    data = getURL('http://%s:2244/fsapi/GET/netRemote.play.shuffle?pin=%s&sid=%s' % (param_ipAddress, param_pin, current_sid))
    e_fsResponse = ET.fromstring(data)
    value = e_fsResponse.find('value').find('u8').text == '1'
    local_event_Shuffle.emit(value)
    

local_event_Volume = LocalEvent({"group": "Play info", "schema": {"type": "integer"}})

def local_action_getVolume(ignore):
    '{"group": "Play info"}'
    data = getURL('http://%s:2244/fsapi/GET/netRemote.sys.audio.volume?pin=%s&sid=%s' % (param_ipAddress, param_pin, current_sid))
    e_fsResponse = ET.fromstring(data)
    value = int(e_fsResponse.find('value').find('u8').text)
    local_event_Volume.emit(value)
    

local_event_PlayInfoArtist = LocalEvent({"group": "Play info", "schema": {"type": "string"}})

def local_action_getPlayInfoArtist(ignore):
    '{"group": "Play info"}'
    data = getURL('http://%s:2244/fsapi/GET/netRemote.play.info.artist?pin=%s&sid=%s' % (param_ipAddress, param_pin, current_sid))
    e_fsResponse = ET.fromstring(data)
    value = e_fsResponse.find('value').find('c8_array').text
    local_event_PlayInfoArtist.emit(value)

    
local_event_PlayInfoAlbum = LocalEvent({"group": "Play info", "schema": {"type": "string"}})

def local_action_getPlayInfoAlbum(ignore):
    '{"group": "Play info"}'
    data = getURL('http://%s:2244/fsapi/GET/netRemote.play.info.album?pin=%s&sid=%s' % (param_ipAddress, param_pin, current_sid))
    e_fsResponse = ET.fromstring(data)
    value = e_fsResponse.find('value').find('c8_array').text
    local_event_PlayInfoAlbum.emit(value)    


local_event_AudioMute = LocalEvent({"group": "Play info", "schema": {"type": "string"}})

def local_action_getAudioMute(ignore):
    '{"group": "Play info"}'
    data = getURL('http://%s:2244/fsapi/GET/netRemote.sys.audio.mute?pin=%s&sid=%s' % (param_ipAddress, param_pin, current_sid))
    e_fsResponse = ET.fromstring(data)
    value = e_fsResponse.find('value').find('u8').text == '1'
    local_event_AudioMute.emit(value)

    
local_event_NavState = LocalEvent({"group": "Navigation", "schema": {"type": "integer"}})

def local_action_getNavState(ignore):
    '{"group": "Navigation"}'
    data = getURL('http://%s:2244/fsapi/GET/netRemote.nav.state?pin=%s&sid=%s' % (param_ipAddress, param_pin, current_sid))
    e_fsResponse = ET.fromstring(data)
    value = int(e_fsResponse.find('value').find('u8').text)
    local_event_NavState.emit(value)
    
def local_action_setNavState(state):
    '{"group": "Navigation", "schema": {"type": "integer"}}'
    data = getURL('http://%s:2244/fsapi/SET/netRemote.nav.state?pin=%s&sid=%s&value=%s' % (param_ipAddress, param_pin, current_sid, state))
    print 'setNavState response: %s' % data
    
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

local_event_CurrentPresets = LocalEvent({"title": "Current presets", "group": "Presets", 
                                         "schema": {"type":"array","title":"Items","items":{"type":"object","properties":{"key":{"order":1,"type":"string","title":"Key"},"name":{"order":2,"type":"string","title":"Name"}}},"order":3}})

def local_action_listPresetsForCurrentMode(ignore=None):
    '{"group": "Presets"}'
    # get the current mode
    modeInfo = local_action_getMode()
    
    modeId = modeInfo['id']
    
    modePresets = presets.get(modeId)
    if modePresets is None:
        modePresets = {}
        presets[modeId] = modePresets
  
    presetsList = list()
  
    data = data = getURL('http://%s:2244/fsapi/LIST_GET_NEXT/netRemote.nav.presets/-1?pin=%s&sid=%s&maxItems=20' % (param_ipAddress, param_pin, current_sid))
    e_fsResponse = ET.fromstring(data)
    e_items = e_fsResponse.findall('item')
    for e_item in e_items:
        presetInfo = {}
        
        key = e_item.attrib['key']
        name = None
        
        presetInfo['key'] = key
        
        for e_field in e_item:
            if e_field.attrib.get('name') == 'name':
                name = e_field.find('c8_array').text
                presetInfo['name'] = name
        
        modePresets[key] = presetInfo
        
        presetsList.append({'key': key, 'name': name})
        
    local_event_CurrentPresets.emit(presetsList)
    
# select preset
def local_action_selectPreset(value):
    '{"group": "Presets", "schema": {"type": "integer"}}'
    data = getURL('http://%s:2244/fsapi/SET/netRemote.nav.action.selectPreset?pin=%s&sid=%s&value=%s' % (param_ipAddress, param_pin, current_sid, value))
    print 'selectPreset response: %s' % data
    
    
    
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

local_event_SelectionList = LocalEvent({"title": "Selection", "group": "Navigation", "schema": {"type":"array","title":"Items","items":{"type":"object","properties":{"key":{"order":1,"type":"string","title":"Key"},"name":{"order":2,"type":"string","title":"Name"}},},"order":3}})

def local_action_listItems(ignore=None):
    '{"group": "Navigation"}'
    data = data = getURL('http://%s:2244/fsapi/LIST_GET_NEXT/netRemote.nav.list/-1?pin=%s&sid=%s&maxItems=100' % (param_ipAddress, param_pin, current_sid))
    e_fsResponse = ET.fromstring(data)
    e_items = e_fsResponse.findall('item')
    
    listItems.clear()
    signalItems = list()
    
    for e_item in e_items:
        itemInfo = {}
        
        key = e_item.attrib['key']
        
        itemInfo['key'] = key
        
        for e_field in e_item:
            if e_field.attrib.get('name') == 'name':
                itemInfo['name'] = e_field.find('c8_array').text
                
            elif e_field.attrib.get('name') == 'type':
                itemInfo['type'] = e_field.find('u8').text
                
            elif e_field.attrib.get('name') == 'subtype':
                itemInfo['subtype'] = e_field.find('u8').text
        
        listItems[key] = itemInfo
        
        signalItems.append({ 'key': itemInfo['key'], 'name': itemInfo['name']})
        
    local_event_SelectionList.emit(signalItems)
    
def local_action_selectItem(value):
    '{"group": "Navigation", "schema": {"type": "integer"}}'
    data = getURL('http://%s:2244/fsapi/SET/netRemote.nav.action.selectItem?pin=%s&sid=%s&value=%s' % (param_ipAddress, param_pin, current_sid, value))
    e_fsResponse = ET.fromstring(data)
    e_items = e_fsResponse.find('status')
    if e_items.text != 'FS_OK':
        print 'Request failure - response was [%s]' % data
    

# def navigate
# 'Back'??
# http://192.168.178.97:2244/fsapi/SET/netRemote.nav.action.navigate?pin=1234&sid=%s&value=4294967295
def local_action_Back(value):
    '{"group": "Navigation"}'
    data = getURL('http://%s:2244/fsapi/SET/netRemote.nav.action.navigate?pin=%s&sid=%s&value=4294967295' % (param_ipAddress, param_pin, current_sid))


# Navigate to item 5
# http://192.168.178.97:2244/fsapi/SET/netRemote.nav.action.navigate?pin=1234&sid=%s&value=5
def local_action_NavigateTo(value):
    '{"group": "Navigation", "schema": {"type": "integer"}}'
    data = getURL('http://%s:2244/fsapi/SET/netRemote.nav.action.navigate?pin=%s&sid=%s&value=%s' % (param_ipAddress, param_pin, current_sid, value))

def local_action_Pause(ignore = None):
    '{"group": "Play control" }'
    data = getURL('http://%s:2244/fsapi/SET/netRemote.play.control?pin=%s&sid=%s&value=2' % (param_ipAddress, param_pin, current_sid))

    
def local_action_Play(ignore = None):
    '{"group": "Play control" }'
    data = getURL('http://%s:2244/fsapi/SET/netRemote.play.control?pin=%s&sid=%s&value=1' % (param_ipAddress, param_pin, current_sid))

    
def local_action_Skip(ignore = None):
    '{"group": "Play control" }'
    data = getURL('http://%s:2244/fsapi/SET/netRemote.play.control?pin=%s&sid=%s&value=3' % (param_ipAddress, param_pin, current_sid))

def local_action_Previous(ignore = None):
    '{"group": "Play control" }'
    data = getURL('http://%s:2244/fsapi/SET/netRemote.play.control?pin=%s&sid=%s&value=4' % (param_ipAddress, param_pin, current_sid))
    

def local_action_setVolume(volume):
    '{"group": "Play control", "schema": {"type": "integer"}}'
    data = getURL('http://%s:2244/fsapi/SET/netRemote.sys.audio.volume?pin=%s&sid=%s&value=%s' % (param_ipAddress, param_pin, current_sid, volume))
    
# position (seek)
# http://192.168.178.97:2244/fsapi/SET/netRemote.play.position?pin=1234&sid=22389622&value=165785    
def local_action_setPosition(position):
    '{"group": "Play control", "schema": {"type": "integer"}}'
    data = getURL('http://%s:2244/fsapi/SET/netRemote.play.position?pin=%s&sid=%s&value=%s' % (param_ipAddress, param_pin, current_sid, position))

    
# duration
# http://192.168.178.97:2244/fsapi/GET/netRemote.play.info.duration?pin=1234&sid=22389622
# resp: <fsapiResponse><status>FS_OK</status><value><u32>246050</u32></value></fsapiResponse>
local_event_Duration = LocalEvent({"group": "Play info", "schema": {"type": "integer"}})

def local_action_getDuration(ignore):
    '{"group": "Play info"}'
    data = getURL('http://%s:2244/fsapi/GET/netRemote.play.info.duration?pin=%s&sid=%s' % (param_ipAddress, param_pin, current_sid))
    e_fsResponse = ET.fromstring(data)
    value = int(e_fsResponse.find('value').find('u32').text)
    local_event_Duration.emit(value)
    

