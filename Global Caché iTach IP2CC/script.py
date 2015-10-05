# coding=utf-8
u"Global Caché iTachIP2CC"
# Handy reference:
# * http://www.globalcache.com/products/itach/ip2ccspecs/
# * http://www.globalcache.com/files/docs/API-iTach.pdf

# param_ipAddress = Parameter({"title":u"IP addréss", "group":"Comms", "schema":{"type":"string", "description":"The IP description.", "desc":"The IP address to connect to.", "hint":"192.168.100.1"}})
param_disabled = Parameter({"title":"Disabled", "group":"Comms", "schema":{"type":"boolean"}})

# the IP address to connect to
ipAddress = None

ITACH_TCPCONTROL = 4998

def main():
    bindFeedbackFunctions()

def local_action_RequestVersion(arg = None):
    '{"title": "Request version" }'
    tcp.request('getversion', lambda resp: local_event_Version.emit(resp))

# Comms related events for diagnostics
local_event_Connected = LocalEvent({'group': 'Comms', 'order': 1})
local_event_Received = LocalEvent({'group': 'Comms', 'order': 2})
local_event_Sent = LocalEvent({'group': 'Comms', 'order': 3})
local_event_Disconnected = LocalEvent({'group': 'Comms', 'order': 4})
local_event_Timeout = LocalEvent({'group': 'Comms', 'order': 5})

local_event_CCport1 = LocalEvent({'title': 'CC port 1', 'group': 'Contact closure ports', 'order': 0, 'schema': {'type': 'boolean'}})
local_event_CCport2 = LocalEvent({'title': 'CC port 2', 'group': 'Contact closure ports', 'order': 1, 'schema': {'type': 'boolean'}})
local_event_CCport3= LocalEvent({'title': 'CC port 3', 'group': 'Contact closure ports', 'order': 2, 'schema': {'type': 'boolean'}})

local_event_Version = LocalEvent({'group': 'Device info', 'order': 0, 'schema': {'type':'string'}})
local_event_Error = LocalEvent({'order':1,'schema':{'title': 'Error details', 'type':'object','properties':{'code':{'type':'string','order':0},'data':{'type':'string','order':1},'desc':{'type':'string','order':2}}}})

def remote_event_BeaconReceiver(arg):
    # print 'Got beacon data:%s' % arg
    
    # get the IP address part from 'sourceaddress'
    
    sourceAddress = arg.get('sourceaddress')
    if sourceAddress is None:
        return
    
    splitPoint = sourceAddress.rfind(':')
    if splitPoint < 0:
        return
      
    global ipAddress
    ipAddress = sourceAddress[:splitPoint]
    
    tcp.setDest('%s:%s' % (ipAddress, ITACH_TCPCONTROL))

def connected():
    local_event_Connected.emit()
    
    local_action_RequestVersion()
    
    syncStates()
    
    ping_timer.setInterval(60)
    ping_timer.start()    
    
def received(data):
    local_event_Received.emit(data)
    
    parseMessage(data)

def sent(data):
    local_event_Sent.emit(data)
    
def disconnected():
    local_event_Disconnected.emit()
    ping_timer.stop()
    
def timeout():
    local_event_Timeout.emit()

tcp = TCP(connected=connected, received=received, sent=sent, disconnected=disconnected, sendDelimiters='\r', receiveDelimiters='\r\n', timeout=timeout)

# 'ping' every 60s
ping_timer = Timer(lambda: local_action_RequestVersion(), 60, stopped=True)

def local_action_OpenCCport1(arg):
    '{"title":"Open","group":"Contact closure port 1", "order": "1"}}'
    tcp.send('setstate,1:1,0')
    tcp.send('getstate,1:1')
    
def local_action_CloseCCport1(arg):
    '{"title":"Close","group":"Contact closure port 1", "order": "2"}}'
    tcp.send('setstate,1:1,1')
    tcp.send('getstate,1:1')    
    
def local_action_OpenCCport2(arg):
    '{"title":"Open","group":"Contact closure port 2", "order": "1"}}'
    tcp.send('setstate,1:2,0')
    tcp.send('getstate,1:2')
    
def local_action_CloseCCport2(arg):
    '{"title":"Close","group":"Contact closure port 2", "order": "2"}}'
    tcp.send('setstate,1:2,1')
    tcp.send('getstate,1:2')    
    
def local_action_OpenCCport3(arg):
    '{"title":"Open","group":"Contact closure port 3", "order": "1"}}'
    tcp.send('setstate,1:3,0')
    tcp.send('getstate,1:3')
    
def local_action_CloseCCport3(arg):
    '{"title":"Close","group":"Contact closure port 3", "order": "2"}}'
    tcp.send('setstate,1:3,1')    
    tcp.send('getstate,1:3')
    
def syncStates():
    tcp.send('getstate,1:1')
    tcp.send('getstate,1:2')
    tcp.send('getstate,1:3')
    
responseFeedbackFunctions = {}
def bindFeedbackFunctions():
    responseFeedbackFunctions['state,1:1,1'] = lambda: local_event_CCport1.emit(True)
    responseFeedbackFunctions['state,1:1,0'] = lambda: local_event_CCport1.emit(False)
    responseFeedbackFunctions['state,1:2,1'] = lambda: local_event_CCport2.emit(True)
    responseFeedbackFunctions['state,1:2,0'] = lambda: local_event_CCport2.emit(False)
    responseFeedbackFunctions['state,1:3,1'] = lambda: local_event_CCport3.emit(True)
    responseFeedbackFunctions['state,1:3,0'] = lambda: local_event_CCport3.emit(False)
    
def parseMessage(data):
    # check for errors
    if data.startswith('ERR'):
        parseErrorMessage(data)
        
    func = responseFeedbackFunctions.get(data)
    if func is not None:
        func()

# Parses an error message, e.g.
# ERR_1:1,008
def parseErrorMessage(data):
    errorCode = data[:data.find(':')]   # e.g. ERR_1
    errorData = data[data.find(':')+1:] # e.g. 1,008
    
    # look up the code
    errorDesc = ERROR_CODES.get(errorCode)
    if errorDesc is None:
        errorDesc = 'General protocol error'
        
    local_event_Error.emit({'code': errorCode, 'desc': errorDesc, 'data': errorData })    
    
ERROR_CODES = {
  'ERR_1': 'Invalid command. Command not found.',
  'ERR_01': 'Invalid command. Command not found.',
  'ERR_2': 'Invalid module address (does not exist).',
  'ERR_02': 'Invalid module address (does not exist).',
  'ERR_3': 'Invalid connector address (does not exist).',
  'ERR_03': 'Invalid connector address (does not exist).',
  'ERR_4': 'Invalid ID value.',
  'ERR_04': 'Invalid ID value.',
  'ERR_5': 'Invalid frequency value.',
  'ERR_05': 'Invalid frequency value.',
  'ERR_6': 'Invalid repeat value.',
  'ERR_06': 'Invalid repeat value.',
  'ERR_7': 'Invalid offset value.', 
  'ERR_07': 'Invalid offset value.',
  'ERR_8': 'Invalid pulse count.', 
  'ERR_08': 'Invalid pulse count.', 
  'ERR_9': 'Invalid pulse data.', 
  'ERR_09': 'Invalid pulse data.', 
  'ERR_10': 'Uneven amount of <on|off> statements.', 
  'ERR_11': 'No carriage return found.', 
  'ERR_12': 'Repeat count exceeded.', 
  'ERR_13': 'IR command sent to input connector.', 
  'ERR_14': 'Blaster command sent to non-blaster connector.', 
  'ERR_15': 'No carriage return before buffer full.', 
  'ERR_16': 'No carriage return.', 
  'ERR_17': 'Bad command syntax.', 
  'ERR_18': 'Sensor command sent to non-input connector.', 
  'ERR_19': 'Repeated IR transmission failure.', 
  'ERR_20': 'Above designated IR <on|off> pair limit.', 
  'ERR_21': 'Symbol odd boundary.', 
  'ERR_22': 'Undefined symbol.', 
  'ERR_23': 'Unknown option.', 
  'ERR_24': 'Invalid baud rate setting.',
  'ERR_25': 'Invalid flow control setting.',
  'ERR_26': 'Invalid parity setting. ERR_27 Settings are locked.' }    
    
seqNum = [0L]
def nextSeqNum():
    seqNum[0] += 1
    return seqNum[0]
  