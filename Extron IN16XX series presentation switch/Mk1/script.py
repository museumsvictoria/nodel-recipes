"Extron  IN1606 or IN1608 Presentation switcher"

# Useful resources
#  * Setup guide 
#     - http://media.extron.com/download/files/userman/68-1916-51_A.pdf
#     
#  * User guide   
#     - http://media.extron.com/download/files/userman/68-2290-01_D.pdf
#     

DEBUG = 1

param_ipAddress = Parameter({"title":"IP address", "schema":{"type":"string", "description":"The IP description.", "desc":"The IP address to connect to.", "hint":"192.168.100.1"}})
param_port = Parameter({"title":"Port", "schema":{"type":"integer", "description":"The TCP port.", "hint":"2001"}})

local_event_Greeting = LocalEvent({'title': 'Greeting', 'group': 'Greeting', 'order': 1, 
                                     'schema' : {'type' : 'string'}})
local_event_GreetingFirmwareDate = LocalEvent({'title': 'Firmware date', 'group': 'Greeting', 'order': 2, 
                                     'schema' : {'type' : 'string'}})

# General error
local_event_GeneralError = LocalEvent({'title': 'General error', 'group': 'Errors', 'order': 1, 'schema' : {'type' : 'string'}})

# input selection
local_event_VideoInput = LocalEvent({'title': 'Current video input', 'group': 'Input selection', 'order': 1, 
                                     'schema' : {'type' : 'string'}})
local_event_AudioInput = LocalEvent({'title': 'Current audio input', 'group': 'Input selection', 'order': 2,
                                     'schema' : {'type' : 'string'}})
local_event_Input = LocalEvent({'title': 'Current input', 'group': 'Input selection', 'order': 3,
                                'schema' : {'type' : 'string'}})

def main():
    bind()
    
    tcp.setDest('%s:%s' % (param_ipAddress , param_port))

    
# Refreshes a few general states
def refreshState():
    local_action_RefreshVideoInput()
    local_action_RefreshAudioInput()
    local_action_RefreshInput()

# create a timer that gets enables when TCP is connected
timer = Timer(refreshState, 60)
timer.stop()

# master list of input entries
# (see bindInput for attributes)
inputEntries = list()

# example: key='01'
inputEntriesByResponse = {}

def bind():
    bindInput(1)
    bindInput(2)
    bindInput(3)
    bindInput(4)
    bindInput(5)
    bindInput(6)
    bindInput(7)
    bindInput(8)

# INPUT SWITCHING
def bindInput(inputValue):
    # create an offset for 'Refresh ...' actions
    inputEntry = {}
    inputEntry['name'] = resolveInputSelection(inputValue)
    inputEntry['value'] = inputValue
    
    inputEntries.append(inputEntry)
    inputEntriesByResponse['0%s' % inputValue] = inputEntry
    
    group = 'Input %s' % inputValue
    
    schema = {'title': 'Select video and audio', 'group': group, 'order': 1}
    event1 = Event('Input %s video and audio select' % inputValue, schema)
    action1 = Action('Input %s video and audio select' % inputValue, lambda arg: selectInputVideoAndAudio(inputValue, event1), schema)
    
    schema = {'title': 'Select video and audio', 'group': group, 'order': 2}
    event2 = Event('Input %s video only select' % inputValue, schema)
    action = Action('Input %s video only select' % inputValue, lambda arg: selectInputVideoOnly(inputValue, event2), schema)
    
    schema = {'title': 'Select audio only', 'group': group, 'order': 3}
    event3 = Event('Input %s audio only select' % inputValue, schema)
    action = Action('Input %s audio only select' % inputValue, lambda arg: selectInputAudioOnly(inputValue, event3), schema)
    
def selectInputVideoAndAudio(inputValue, event):
    tcp.send('%s!' % inputValue)
    event.emit()
    
def selectInputVideoOnly(inputValue, event):
    tcp.send('%s&' % inputValue)
    event.emit()
    
def selectInputAudioOnly(inputValue, event):
    tcp.send('%s$' % inputValue)
    event.emit()
    
def local_action_RefreshVideoInput(arg = None):
    '{ "title": "Refresh video input", "group": "Input selection" }'
    tcp.request('&', lambda resp: handleInputRespAndEmit(resp, local_event_VideoInput))

def local_action_RefreshAudioInput(arg = None):
    '{ "title": "Refresh audio input", "group": "Input selection" }'
    tcp.request('!', lambda resp: handleInputRespAndEmit(resp, local_event_AudioInput))
    
def local_action_RefreshInput(arg = None):
    '{ "title": "Refresh input", "group": "Input selection" }'
    tcp.request('$', lambda resp: handleInputRespAndEmit(resp, local_event_Input))
    
# e.g. '01'
def handleInputRespAndEmit(resp, event):
    inputEntry = inputEntriesByResponse.get(resp)
    if inputEntry is None:
        emitAndRaise('Unexpected input value' + resp)
        
    event.emit(inputEntry['name'])

# Options:
# - 'video and audio'
# - 'video only'
# - 'audio only'
def switchInput(input, option):
    cmd = None
    
    if option == 'video and audio':
        cmd = '!'
    elif option == 'video only':
        cmd = '&'
    elif option == 'audio only':
        cmd = '$'
    else:
        raise Exception('Unknown option - %s' % option)

    tcp.request(input + cmd, lambda resp: parseSwitchInput(resp))

# In
def parseSwitchInputResponse(resp):
    # TODO
    pass
  
  
# VOLUME
# tcp.send('\x1bD1GRPM')
local_event_ProgramVolume = LocalEvent({'title': 'Volume', 'group': 'Program volume', 'order': 0, 
                                 'schema':{"title": "Level", "type": "integer", "format":"range", "min":-1000, "max":0}})

def local_action_SetProgramVolume(level):
    '{"title": "Set", "group": "Program volume", "order": 1, "schema": {"title": "Level", "type": "integer", "format":"range", "min":-1000, "max":0} }'
    setProgramVolume(level)
    
def setProgramVolume(levelArg):
    level = int(levelArg)
    
    tcp.send('\x1bD1*%sGRPM' % level)

  
# general feedback
def parseFeedback(data):
    pass
    # console.log('Got data [%s]' % data)
    
    
# (1-6) (IN1606)
# (1-8) (IN1608)
X1_INPUTS = ["Input 1", "Input 2", "Input 3", "Input 4", "Input 5", "Input 6", "Input 7", "Input 8"]
def resolveInputSelection(value):
    if value < 1 or value > 8:
        raise Exception("no such input (1-8)")
	
    return X1_INPUTS[value - 1]
	
# (1-3)
X2_OUTPUTS = ["HDMI A", "HDMI B", "DTP C"]
def resolveOutputSelection(value):
    if value < 1 or value > 6:
        raise Exception("no such ouput (1-3)")
    
    return X2_OUTPUTS[value - 1]

# (1-6)
X3_INPUT_VIDEO_FORMATS = ["RGB", "YUV", "RGBcvS", "S-video", "Composite", "HDMI"]
def resolveInputVideoFormat(value):
    if value < 1 or value > 6:
        raise Exception("no such input video format (1-3)")
    
    return X3_INPUT_VIDEO_FORMATS[value - 1]
  
# (0-6)
X20_TEST_PATTERNS = ["Off", "Crop", "Alternating pixels", "Color bars", "Grayscale", "Blue mode", "Audio test (pink noise)"]
def resolveTestPattern(value):
    if value < 0 or value > 6:
        raise Exception("no such input video format (1-3)")
    
    return X20_TEST_PATTERNS[value]
  
# (0-2)
X28_VIDEO_OUTPUT_MUTE = ["Unmute", "Mute video", "Mute video and sync"]
def resolveVideoOutputMute(value):
    if value < 0 or value > 2:
        raise Exception("no such video output mute (0-2)")
    
    return X3_INPUT_VIDEO_FORMATS[value - 1]
  
ERROR_CODES = { 
                'E01': 'Invalid input number',
                'E10': 'Invalid command',
                'E11': 'Invalid present number',
                'E13': 'Invalid port number',
                'E14': 'Not valid for this configuration',
                'E18': 'Invalid command for signal type',
                'E22': 'Busy',
                'E24': 'Privilege violation',
                'E25': 'Device not present',
                'E26': 'Maximum number of connections exceeded',
                'E28': 'Bad filename of file not found'
              }
               

def emitAndRaise(errorMsg):
    local_event_GeneralError.emit(errorMsg)
    
    
#TCP
local_event_Connected = LocalEvent({'group': 'Comms', 'order': 1})
local_event_Received = LocalEvent({'group': 'Comms', 'order': 2})
local_event_Sent = LocalEvent({'group': 'Comms', 'order': 3})
local_event_Disconnected = LocalEvent({'group': 'Comms', 'order': 4})
local_event_Timeout = LocalEvent({'group': 'Comms', 'order': 5})

# (uncomment for testing)
def local_action_Send(data):
    '{"schema": { "title": "Data", "type": "string" } }'
    tcp.send(data)   

def connected():
    local_event_Connected.emit()
    
    
    tcp.receive(lambda resp: local_event_Greeting.emit(resp))
    tcp.receive(lambda resp: local_event_GreetingFirmwareDate.emit(resp))
    
    refreshState()
    timer.start()
  
def received(data):
    local_event_Received.emit(data)
    
    if DEBUG > 0: console.log('(received [%s]' % data)
    
    parseFeedback(data)

def sent(data):
    local_event_Sent.emit(data)
    
def disconnected():
    local_event_Disconnected.emit()
    timer.stop()
    
def timeout():
    local_event_Timeout.emit()
  
tcp = TCP(connected=connected, received=received, sent=sent, disconnected=disconnected, sendDelimiters='\r\n', receiveDelimiters='\r\n', timeout=timeout)

seqNum = [0L]
def nextSeqNum():
    seqNum[0] += 1
    return seqNum[0]
