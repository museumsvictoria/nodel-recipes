# coding=utf-8
u"Global Caché iTachIP2CC - to update config, go to config URL address directly."
# Handy reference:
# * http://www.globalcache.com/products/itach/ip2sl-pspecs/
# * http://www.globalcache.com/files/docs/API-iTach.pdf

# param_ipAddress = Parameter({"title":u"IP addréss", "group":"Comms", "schema":{"type":"string", "description":"The IP description.", "desc":"The IP address to connect to.", "hint":"192.168.100.1"}})
param_disabled = Parameter({"title":"Disabled", "group":"Comms", "schema":{"type":"boolean"}})

# the IP address to connect to
ipAddress = None

ITACH_TCPCONTROL = 4998

def main():
    bindFeedbackFunctions()

def local_action_RefreshVersion(arg = None):
    '{"title": "Refresh version" }'
    tcp.request('getversion', lambda resp: local_event_Version.emit(resp))
    
def local_action_RefreshSerialPort1Config(arg = None):
    '{"title": "Refresh serial port 1 config" }'
    tcp.send('get_SERIAL,1:1')
    
    # response something like: SERIAL,1:1,19200,FLOW_NONE,PARITY_NO

# Comms related events for diagnostics
local_event_Connected = LocalEvent({'group': 'Comms', 'order': 1})
local_event_Received = LocalEvent({'group': 'Comms', 'order': 2})
local_event_Sent = LocalEvent({'group': 'Comms', 'order': 3})
local_event_Disconnected = LocalEvent({'group': 'Comms', 'order': 4})
local_event_Timeout = LocalEvent({'group': 'Comms', 'order': 5})

local_event_Version = LocalEvent({'group': 'Device info', 'order': 0, 'schema': {'type':'string'}})
local_event_ConfigURL = LocalEvent({'title': 'Config URL', 'group': 'Device info', 'order': 1, 'schema': {'type':'string'}})
local_event_SerialPort1Config = LocalEvent({'order':1, 'schema': {'title': 'Serial port 1 config', 'type':'object','properties':{
        'baudrate':    { 'title': 'Baud rate', 'type':'integer', 'order':0},
        'flowcontrol': { 'title': 'Flow control', 'type':'string', 'order':1},
        'parity':      { 'title': 'Parity', 'type': 'string', 'order':2}}}})
local_event_Error = LocalEvent({'order':1,'schema':{'title': 'Error details', 'type':'object','properties':{
        'code':{'title': 'Code', 'type':'string','order':0},
        'data':{'title': 'Data', 'type':'string','order':1},
        'desc':{'title': 'Description', 'type':'string','order':2}}}})

def remote_event_BeaconReceiver(arg):
    # print 'Got beacon data:%s' % arg
    
    # get the IP address part from 'sourceaddress'
    
    sourceAddress = arg.get('sourceaddress')
    if sourceAddress is not None:
      splitPoint = sourceAddress.rfind(':')
      if splitPoint >= 0:
        global ipAddress
        ipAddress = sourceAddress[:splitPoint]

        tcp.setDest('%s:%s' % (ipAddress, ITACH_TCPCONTROL))
    
    configURL = arg.get('config_url')
    if configURL is not None:
        if local_event_ConfigURL.getArg() != configURL:
            local_event_ConfigURL.emit(configURL)

def connected():
    local_event_Connected.emit()
    
    local_action_RefreshVersion()
    local_action_RefreshSerialPort1Config()
    
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
ping_timer = Timer(lambda: local_action_RefreshVersion(), 60, stopped=True)
    
def syncStates():
    # not needed
    pass
    
responseFeedbackFunctions = {}
def bindFeedbackFunctions():
    # example:
    # responseFeedbackFunctions['state,1:1,1'] = lambda: local_event_CCport1.emit(True)
    
    # IP2SL does not have any static feedback functions
    pass
    
def parseMessage(data):
    # check for errors
    if data.startswith('ERR'):
        parseErrorMessage(data)
        
    elif data.startswith('SERIAL,'):
        parseSerialResponse(data)
        
    func = responseFeedbackFunctions.get(data)
    if func is not None:
        func()

# e.g. SERIAL,1:1,19200,FLOW_NONE,PARITY_NO
def parseSerialResponse(data):
    parts = data.split(',')
    
    if len(parts) >= 5:
        port = parts[1]
        baudrate = int(parts[2])
        flowcontrol = parts[3]
        parity = parts[4]
        
        local_event_SerialPort1Config.emit({'baudrate': baudrate, 'flowcontrol': flowcontrol, 'parity': parity})
    else:
        console.warn('Could not parse response to "SERIAL" command. resp was [%s]' % data)
        
        
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
  