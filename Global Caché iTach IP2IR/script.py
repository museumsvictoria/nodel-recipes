# coding=utf-8
u"Global Caché iTachIP2IR"
# Handy reference:
# * http://www.globalcache.com/products/itach/ip2irspecs/
# * http://www.globalcache.com/files/docs/API-iTach.pdf

# param_ipAddress = Parameter({"title":u"IP address", "group":"Comms", "schema":{"type":"string", "description":"The IP description.", "desc":"The IP address to connect to.", "hint":"192.168.100.1"}})
param_disabled = Parameter({"title":"Disabled", "group":"Comms", "schema":{"type":"boolean"}})

# the IP address to connect to
ipAddress = None

ITACH_TCPCONTROL = 4998

def local_action_RequestVersion(arg = None):
    '{"title": "Request version" }'
    tcp.request('getversion', lambda resp: local_event_Version.emit(resp))

# Comms related events for diagnostics
local_event_Connected = LocalEvent({'group': 'Comms', 'order': 1})
local_event_Received = LocalEvent({'group': 'Comms', 'order': 2})
local_event_Sent = LocalEvent({'group': 'Comms', 'order': 3})
local_event_Disconnected = LocalEvent({'group': 'Comms', 'order': 4})
local_event_Timeout = LocalEvent({'group': 'Comms', 'order': 5})

local_event_IRport1 = LocalEvent({'title': 'IR port 1', 'group': 'IR port activity', 'order': 0})
local_event_IRport2 = LocalEvent({'title': 'IR port 2', 'group': 'IR port activity', 'order': 1})
local_event_IRport3= LocalEvent({'title': 'IR port 3', 'group': 'IR port activity', 'order': 2})

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

def local_action_SendIRport1(arg):
    '{"title":"Send","group":"Sending IR","schema":{"title":"Data", "type":"string"}}'
    sendIR('1:1', arg)
    local_event_IRport1.emit()
    
def local_action_SendIRport2(arg):
    '{"title":"Send","group":"Sending IR","schema":{"title":"Data", "type":"string"}}'
    sendIR('1:2', arg)
    local_event_IRport2.emit()
    
def local_action_SendIRport3(arg):
    '{"title":"Send","group":"Sending IR","schema":{"title":"Data", "type":"string"}}'
    sendIR('1:3', arg)
    local_event_IRport3.emit()
    
# sendir,1:1,14,37878,1,1,171,171,21,64,21,64,21,64,21,22,21,22,21,22,21,22,21,22,
# 21,64,21,64,21,64,21,22,21,22,21,22,21,22,21,22,21,22,21,22,21,22,21,64,21,64,21,
# 22,21,22,21,64,21,64,21,64,21,64,21,22,21,22,21,64,21,64,21,22,21,1778
def sendIR(portAddress, data):
    if param_disabled:
        return
      
    tcp.send('sendir,%s,%s' % (portAddress, data))
    

def bindLEDPortControls(port):
  
  group = 'LED control (PWM)'
  
  def handler(arg=None):
    intesity = arg['intensity']
    time = arg.get('time') or 10
    tcp.send('set_LED_LIGHTING,1:%s,%s,%s' % (port, intesity, time))
    
  Event('LEDPort%s' % port, {"title": "Port %s Intensity" % port, "group": group, "schema": {"type": "integer"}})
    
  Action('LEDPort%s' % port, handler, { "title": "Set", "group": group, "schema": { "type": "object", "title": "Port %s" % port, "properties": { 
              "intensity": { "type": "integer", "max": 100, "min": 0, "format": "range" },
              "time": { "type": "integer", "max": 10, "min": 1, "format": "range" } } } })
  
bindLEDPortControls(1)
bindLEDPortControls(2)
bindLEDPortControls(3)
    
def parseMessage(data):
    # check for errors
    if data.startswith('ERR'):
        parseErrorMessage(data)
        
    elif data.startswith('LED_LIGHTING'):
        parseLEDLightingResponse(data)
        
# e.g. LED_LIGHTING,1:1,27,100
def parseLEDLightingResponse(data):
    # LED_LIGHTING,ADDRESS,CURRENT_INTENSITY,FINAL_INTENSITY
    parts = data.split(',') # all 
    intensityPart = parts[-1:][0]
    addrParts = parts[1].split(':')
    portPart = addrParts[-1:]
        
    event = lookup_local_event('LEDPort%s' % int(portPart[0]))
    event.emit(int(intensityPart))

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
  