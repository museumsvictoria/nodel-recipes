"Extron CR48 Four Contact Input and Eight Relay Port IP Link Control Processor"

#  * User guide   
#     - http://media.extron.com/download/files/userman/68-738-05_C_IPL_T_CR48_User_Guide.pdf

DEBUG = 1

param_ipAddress = Parameter({"title":"IP address", "schema":{"type":"string", "description":"The IP description.", "desc":"The IP address to connect to.", "hint":"192.168.100.1"}})
param_port = Parameter({"title":"Port", "schema":{"type":"integer", "description":"The TCP port.", "hint":"2001"}})

local_event_Greeting = LocalEvent({'title': 'Greeting', 'group': 'Greeting', 'order': 1, 
                                     'schema' : {'type' : 'string'}})
local_event_GreetingFirmwareDate = LocalEvent({'title': 'Firmware date', 'group': 'Greeting', 'order': 2, 
                                     'schema' : {'type' : 'string'}})

# General error
local_event_Error = LocalEvent({'title': 'General error', 'group': 'Errors', 'order': 1, 'schema' : {'type' : 'string'}})

def main():
    # inputs
    for inputNum in [1, 2, 3, 4]:
        bindInput(inputNum)

    # relays
    for relayNum in [1, 2, 3, 4, 5, 6, 7, 8]:
        bindRelay(relayNum)  
  
    if param_ipAddress is None or param_port is None:
        msg = 'No IP address or port has been set.'
        console.error(msg)
        local_event_Error.emit(msg)
        return
        
    tcp.setDest('%s:%s' % (param_ipAddress , param_port))
    
# Refreshes a few general states
def refreshState():
    if DEBUG > 0: console.log('refreshState called')
    refreshInputStates()
    refreshRelayStates()
    
def handleTimer():
    if DEBUG > 0: console.log('timer called')
    refreshState()

# create a timer that gets enables when TCP is connected
timer = Timer(handleTimer, 1)
timer.stop()

# the input entries
inputEntries = {}
relayEntries = {}

def bindInput(inputNum):
    order = nextSeqNum() * 100
    
    stateEvent = Event('Input %s' % inputNum, {'title': 'Input %s' % inputNum, 'group': 'Inputs', 'order': order + 1, 'schema': {'type': 'integer'}})
    
    onEvent = Event('Input %s on' % inputNum, {'title': '%s on' % inputNum, 'group': 'Inputs', 'order': order + 2})
    
    offEvent = Event('Input %s off' % inputNum, {'title': '%s off' % inputNum, 'group': 'Inputs', 'order': order + 3})
                                                      
    inputEntry = {}
    inputEntry['inputNum'] = inputNum
    inputEntry['stateEvent'] = stateEvent
    inputEntry['onEvent'] = onEvent
    inputEntry['offEvent'] = offEvent
                                                    
    inputEntries[inputNum] = inputEntry
    
def bindRelay(relayNum):
    order = nextSeqNum() * 100
    
    statusEvent = Event('Relay %s' % relayNum, 
                        {'title': 'Relay %s' % relayNum, 'group': 'Relays', 'order': order, 
                         'schema' : {'type':'boolean'}})
    
    def handleResp(resp):
        if resp.startswith('E'):
            local_event_Error.emit('Relay function failed, received "%s"' % resp)
            return
            
        # otherwise assume the response was okay
    
    pulseAction = Action('Pulse %s' % relayNum, 
                         lambda pulseTime: tcp.request('%s*3*%sO' % (relayNum, pulseTime), lambda resp: handleResp(resp)),
                        {'title': 'Pulse %s' % relayNum, 'group': 'Relays', 'order': order + 1, 
                        'schema': {'type': 'integer', 'title': 'Pulse time', 'desc': 'Pulse time in 20 milliseconds per count'}})
    
    onAction = Action('Relay %s on' % relayNum, lambda ignore: tcp.request('%s*1O' % relayNum, lambda resp: handleResp(resp)),
                        {'title': '%s on' % relayNum, 'group': 'Relays', 'order': order + 2})
                      
    offAction = Action('Relay %s off' % relayNum, lambda ignore: tcp.request('%s*0O' % relayNum, lambda resp: handleResp(resp)),
                        {'title': '%s off' % relayNum, 'group': 'Relays', 'order': order + 3})
                   
    toggleAction = Action('Relay %s toggle' % relayNum, lambda ignore: tcp.request('%s*2O' % relayNum, lambda resp: handleResp(resp)),
                        {'title': '%s toggle' % relayNum, 'group': 'Relays', 'order': order + 4})
    
    relayEntry = { 'relayNum': relayNum,
                   'statusEvent': statusEvent,
                   'pulseAction': pulseAction,
                   'onAction': onAction,
                   'offAction': offAction,
                   'toggleAction': toggleAction }
                          
    relayEntries[relayNum] = relayEntry

# parses an input response which is just a number
def parseInputFeedback(inputEntry, resp):
    inputEntry['stateEvent'].emit(int(resp))
                          
def refreshInputStates():
    for inputEntry in inputEntries.values():
    	tcp.request('%s]' % inputEntry['inputNum'], lambda resp: parseInputFeedback(inputEntry, resp))

def parseRelayFeedback(relayEntry, resp):
    if resp == '1':
        relayEntry['statusEvent'].emit(True)
                          
    elif resp == '0':
        relayEntry['statusEvent'].emit(False)
                          
    else:
        local_event_Error.emit('Unknown response for relay feedback, "%s"' % resp)                         

def refreshRelayStates():
    for relayEntry in relayEntries.values():
    	tcp.request('%sO' % relayEntry['relayNum'], lambda resp: parseRelayFeedback(relayEntry, resp))
    
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
    local_event_Error.emit(errorMsg)
    
    
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
    console.log('Timer started. delay:%s interval:%s' % (timer.getDelay(), timer.getInterval()))
  
def received(data):
    local_event_Received.emit(data)
    
    if DEBUG > 0: console.log('(received [%s]' % data)

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
