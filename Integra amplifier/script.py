# coding=utf-8

"Integra controller."

# Handy reference:
# https://www.avforums.com/threads/onkyo-tx-nr-1007-webinterface-programming.1107346/page-9#post-15566499

param_ipAddress = Parameter({"title":"IP address", "schema":{"type":"string", "description":"The IP description.", "desc":"The IP address to connect to.", "hint":"192.168.100.1"}})
param_port = Parameter({"title":"Port", "schema":{"type":"integer", "description":"The TCP port.", "hint":"2001"}})

# Refreshes a few general states
def refreshState():
    # do at least one request to ensure a timeout feedback loop
    tcp.request('!1PWRQSTN', None)
    
    local_action_RefreshInput()
    local_action_RefreshAudioMute()
    local_action_RefreshVolume()
    local_action_RefreshRecOut()

# create a timer that enables when TCP is connected
timer = Timer(refreshState, 60)
timer.stop()

local_event_Connected = LocalEvent({'group': 'Comms', 'order': 1})
local_event_Received = LocalEvent({'group': 'Comms', 'order': 2})
local_event_Sent = LocalEvent({'group': 'Comms', 'order': 3})
local_event_Disconnected = LocalEvent({'group': 'Comms', 'order': 4})
local_event_Timeout = LocalEvent({'group': 'Comms', 'order': 5})

local_event_Error = LocalEvent({'group': 'Error', 'order': 1})

def main(arg = None):
    # Script starts here
    print 'Nodel script started.'

    bindInputs()
    bindRecOuts()
    
    tcp.setDest('%s:%s' % (param_ipAddress , param_port))
    
# POWER

local_event_Power = LocalEvent({'group': 'Power', 'order': 1, 
                               'schema': {'title': 'State', 'type':'string'}})
local_event_PowerOn = LocalEvent({'title': 'On', 'group': 'Power', 'order': 2})
local_event_PowerOff = LocalEvent({'title': 'Off', 'group': 'Power', 'order': 3})
    
def local_action_RefreshPower(arg = None):
    '{"title": "Refresh", "group": "Power", "order": 1}'
    tcp.send('!1PWRQSTN')

def local_action_PowerOn(arg = None):
    '{"title": "On", "group": "Power", "order": 2}'
    tcp.send('!1PWR01')
    
def local_action_PowerOff(arg = None):
    '{"title": "Off", "group": "Power", "order": 3}'
    tcp.send('!1PWR00')

    
# AUDIO MUTE

local_event_AudioMute = LocalEvent({'title':'Current', 'group': 'Audio mute', "order": 1, 
                                    'schema': {'title': 'State', 'type':'string'}})
local_event_AudioMuteOn = LocalEvent({'title': 'On', 'group': 'Audio mute', "order": 2})
local_event_AudioMuteOff = LocalEvent({'title': 'Off', 'group': 'Audio mute', "order": 3})

def local_action_RefreshAudioMute(arg = None):
    '{"title": "Refresh", "group": "Audio mute", "order": 1}'
    tcp.send('!1AMTQSTN')    

def local_action_AudioMuteOn(arg = None):
    '{"title": "On", "group": "Audio mute", "order": 2}'
    tcp.send('!1AMT01')
    
def local_action_AudioMuteOff(arg = None):
    '{"title": "Off", "group": "Audio mute", "order": 3}'
    tcp.send('!1AMT00')    
    
    
# VOLUME

local_event_Volume = LocalEvent({'title': 'Volume', 'group': 'Volume', 'order': 0, 
                                 'schema':{"title": "Level", "type": "integer", "format":"range", "min":0, "max":100}})

def local_action_RefreshVolume(arg = None):
    '{"title": "Refresh", "group": "Volume", "order": 0 }'
    tcp.send('!1MVLQSTN')

def local_action_SetVolume(level):
    '{"title": "Set", "group": "Volume", "order": 1, "schema": {"title": "Level", "type": "integer", "format":"range", "min":0, "max":100} }'
    setVolume(level)
    
def setVolume(level):
    if level is None or level < 0 or level > 100:
        console.warn('Level is out of range, 0-100 (%s was provided)' % level)
        return
      
    hexLevel = "%02X" % level
    tcp.send('!1MVL%s' % hexLevel)
    
def local_action_VolumeUp(ignore):
    '{"title": "Up", "group": "Volume", "order": 2 }'
    tcp.send('!1MVLUP')
    
def local_action_VolumeDown(ignore):
    '{"title": "Down", "group": "Volume", "order": 3 }'
    tcp.send('!1MVLDOWN')
    
def local_action_VolumeRamp(deltaSteps):
    u'{"title": "Ramp", "group": "Volume", "desc": "Ramps the volume up or down a number of steps using a positive or negative integer.", "order": 4,  "schema": {"title": "Δ steps", "type": "integer" } }'
    if deltaSteps is None:
        console.warn('Ramp requested with no value.')
    else:
        setVolume(min(100, max(0, local_event_Volume.getArg() + int(deltaSteps))))

    
# def local_action_VolumeUp1Db(level):
#    '{"title": "+1dB", "group": "Volume", "order": 4 }'
#    tcp.send('!1MVLUP1')
    
# def local_action_VolumeDown1Db(level):
#    '{"title": "-1dB", "group": "Volume", "order": 5 }'
#    tcp.send('!1MVLDOWN1')    


# used by INPUT and REC OUT

eventInfosByCmd = {} # { 'label' : '_____', 'event': ______ }
    
# INPUT

local_event_Input = LocalEvent({'title': 'Input', 'group': 'Input', 'order': 0, 
                                'schema':{'title': 'State', 'type': 'string'}})

def local_action_RefreshInput(arg = None):
    '{"title": "Refresh", "group": "Input", "order": 0 }'
    tcp.send('!1SLIQSTN')

inputLabels = (("00", ['VIDEO1', 'VCR/DVR']),
               ("01", ['VIDEO2', 'CBL/SAT']), 
               ("02", ['VIDEO3', 'GAME/TV', 'GAME']), 
               ("03", ['VIDEO4', 'AUX1(AUX)']), 
               ("04", ['VIDEO5', 'AUX2']), 
               ("05", ['VIDEO6', 'PC']), 
               ("06", ['VIDEO7']), 
               ("07", ['Hidden1']), 
               ("08", ['Hidden2']), 
               ("09", ['Hidden3']), 
               ("10", ['DVD', 'BD/DVD']), 
               ("20", ['TAPE(1)', 'TV/TAPE']), 
               ("21", ['TAPE2']), 
               ("22", ['PHONO']), 
               ("23", ['CD', 'TV/CD']), 
               ("24", ['FM']), 
               ("25", ['AM']), 
               ("26", ['TUNER']), 
               ("27", ['MUSIC SERVER', 'P4S', 'DLNA']),
               ("28", ['INTERNET RADIO','iRadio Favorite']),
               ("29", ['USB/USB(Front)']),
               ("2A", ['USB(Rear)']),
               ("2B", ['NETWORK', 'NET']),
               ("2C", ['USB(toggle)']),
               ("40", ['Universal PORT']),
               ("30", ['MULTI CH']),
               ("31", ['XM']),
               ("32", ['SIRIUS']))


def setUpInput(inputCode, labels):
    cmd = '!1SLI%s' % inputCode
    
    eventInfoList = list()
    eventInfosByCmd[cmd] = eventInfoList
    
    def actionHandler(arg = None):
        tcp.send(cmd)
            
    # create an action for each label
    # Using an ordering trick to get naturally input order when
    # more than one label per input code.
    first = True
    for label in labels:
        order = nextSeqNum()
        if first:
            first = False
        else:
            order = order + 1000
        schema = {'title': '"%s"' % label, 'group': 'Input', 'order': order}
    	action = Action('Input ' + label, actionHandler, schema)
        
        event = Event('Input ' + label, schema)
        eventInfo = { 'label' : label, 'event' : event }
        eventInfoList.append(eventInfo)

def bindInputs():
    # Go through the list of labels
    for item in inputLabels :
        setUpInput(item[0], item[1])


# REC OUT

local_event_RecOut = LocalEvent({'title': 'Rec out', 'group': 'Rec out', 'order': 0, 
                                'schema': {'title': 'State', 'type': 'string'}})

def local_action_RefreshRecOut(arg = None):
    '{"title": "Refresh", "group": "Rec out", "order": 0 }'
    tcp.send('!1SLRQSTN')

recOutLabels = (("00", ['VIDEO1']),
               ("01", ['VIDEO2']), 
               ("02", ['VIDEO3']), 
               ("03", ['VIDEO4']), 
               ("04", ['VIDEO5']), 
               ("05", ['VIDEO6']), 
               ("06", ['VIDEO7']), 
               ("10", ['DVD']), 
               ("20", ['TAPE(1)']), 
               ("21", ['TAPE2']), 
               ("22", ['PHONO']), 
               ("23", ['CD']), 
               ("24", ['FM']), 
               ("25", ['AM']), 
               ("26", ['TUNER']), 
               ("27", ['MUSIC SERVER']), 
               ("28", ['INTERNET RADIO']), 
               ("30", ['MULTI CH']), 
               ("31", ['XM']),
               ("7F", ['OFF']),
               ("80", ['SOURCE']))

def setUpRecOut(recordOutCode, labels):
    cmd = '!1SLR%s' % recordOutCode

    recOutEventInfoList = list()
    eventInfosByCmd[cmd] = recOutEventInfoList
    
    def actionHandler(arg = None):
        tcp.send(cmd)
            
    # create an action for each label
    # Using an ordering trick to get naturally rec out order when
    # more than one label per rec out code.
    first = True
    for label in labels:
        order = nextSeqNum()
        if first:
            first = False
        else:
            order = order + 1000
        schema = {'title': '"%s"' % label, 'group': 'Rec out', 'order': order}
    	action = Action('Rec out ' + label, actionHandler, schema)
        
        event = Event('Rec out ' + label, schema)
        eventInfo = { 'label' : label, 'event' : event }
        recOutEventInfoList.append(eventInfo)
        
def bindRecOuts():
    # Go through the list of rec out labels
    for item in recOutLabels:
        setUpRecOut(item[0], item[1])
        
#TCP

# (uncomment for testing)
#def local_action_Send(data):
#    '{"schema": { "title": "Data", "type": "string" } }'
#    tcp.send(data)   

def connected():
    local_event_Connected.emit()
    refreshState()
    timer.start()
  
def received(data):
    local_event_Received.emit(data)
    parseFeedback(data)

def sent(data):
    local_event_Sent.emit(data)
    
def disconnected():
    local_event_Disconnected.emit()
    timer.stop()
    
def timeout():
    local_event_Timeout.emit()
  
tcp = TCP(connected=connected, received=received, sent=sent, disconnected=disconnected, sendDelimiters='\n', receiveDelimiters='\x1a', timeout=timeout)

   
def parseFeedback(data):
    if data == '!1PWR01':
        local_event_PowerOn.emit()
        local_event_Power.emit('On')
        
    elif data == '!1PWR00':
        local_event_PowerOff.emit()
        local_event_Power.emit('Off')
        
    elif data == '!1AMT01':
        local_event_AudioMuteOn.emit()
        local_event_AudioMute.emit('On')
      
    elif data == '!1AMT00':
        local_event_AudioMuteOff.emit()
        local_event_AudioMute.emit('Off')
        
    elif '!1MVL' in data:
        # !1MVL20
        hexVolume = data[5:]
        if hexVolume:
            volume = int(hexVolume, 16)
            local_event_Volume.emit(volume)
            
    else:
        eventInfos = eventInfosByCmd.get(data)
        if eventInfos:
            # emit the event on all matching events
            for eventInfo in eventInfos:
                label = eventInfo['label']
                eventInfo['event'].emit()
            	local_event_Input.emit(label)

seqNum = [0L]
def nextSeqNum():
    seqNum[0] += 1
    return seqNum[0]
    