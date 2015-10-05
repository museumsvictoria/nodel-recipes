'''Neutrino A0816-N DSP driver.'''

# TODO: check 'dst' address to ensure packet's from correct unit.

param_debugDumpTCP = Parameter({"title": "Dump TCP data", "group": "Debugging", "order": 0,
                       "schema": { "type": "boolean" } })

param_mac = Parameter({"title": "MAC address", 
                       "desc": "The MAC address of the Neutrino unit which is used in broadcast protocols, e.g. '00:aa:bb:cc:dd:ee'",
                       "schema": { "type": "string", "hint": "00:aa:bb:cc:dd:ee"}, "order": 0})

param_ip = Parameter({"title": "IP address",
                       "desc": "The TCP address of the Neutrino unit.",
                       "schema": { "type": "string", "hint": "192.168.178.66"}, "order": 0})

# Examples:

#     Order of parameters:
#     'module' 'number', 'channel', 'aux', 'param', value | value_dB

def local_action_AdjustGainExample(arg):
    '{"title": "Adjust Output 7 Gain", "order": 0, "group": "Examples", "desc": "Adjust gain by specifying dB values.", "schema": { "type": "number" }}'
    module = ('OutAnlg0', 12, 6, 0, 0, arg)
    data = buildWritePacket(param_mac, module[0], module[1], module[2], module[3], module[4], value_dB=module[5])
    tcpControl.send(data)

# holds the binary version of param_mac
srcMacDecoded = '000000000000'.decode('hex')   
    
# Driver section:    
    
# holds the meter events by full ID ('$MODNAME_$MOD_NUM.$CH_NUM.$AUX')
meterEventsByFullId = {}

controlEventsByFullId = {}

local_event_TCPConnected = LocalEvent({"title": "TCP connected", "group": "Comms", "order": 1})
local_event_TCPDisconnected = LocalEvent({"title": "TCP disconnected", "group": "Comms", "order": 1})

UDPPORT_METERS_BROADCAST = 10006
UDPPORT_CONTROL_BROADCAST = 10003
UDPPORT_CONTROL = 10001
TCPPORT_CONTROL = 10001

def local_action_TEST(arg = None):
    '{"title":"Fixed test","order":0, "group": "Custom control" }'
    data = buildReadPacket(param_mac, 'SYSTEM_0', 3, 255, 0, 9)
    tcpControl.send(data)

def local_action_Control(arg = None):
    '{"title":"Control","order":0, "group": "Custom control", "schema":{"type":"object","title":"Params","properties":{"module":{"title":"Module","type":"string","order":1},"number":{"title":"Number","type":"integer","order":2},"channel":{"title":"Channel","type":"integer","order":3},"aux":{"title":"Aux","type":"integer","order":4},"param":{"title":"Param","type":"integer","order":5},"value":{"title":"Value","type":"integer","order":6}}}}'
    data = buildWritePacket(param_mac, arg['module'], arg['number'], arg['channel'], arg['aux'], arg['param'], value=arg['value'])
    tcpControl.send(data)

def local_action_ControlDB(arg = None):
    '{"title":"Control dB","order":1, "group": "Custom control", "schema":{"type":"object","title":"Params","properties":{"module":{"title":"Module","type":"string","order":1},"number":{"title":"Number","type":"integer","order":2},"channel":{"title":"Channel","type":"integer","order":3},"aux":{"title":"Aux","type":"integer","order":4},"param":{"title":"Param","type":"integer","order":5},"value":{"title":"Value","type":"number","order":6}}}}'
    data = buildWritePacket(param_mac, arg['module'], arg['number'], arg['channel'], arg['aux'], arg['param'], value_dB=arg['value'])
    tcpControl.send(data)

def local_action_Read(arg = None):
    '{"title":"Read","order":0, "group": "Custom control", "schema":{"type":"object","title":"Params","properties":{"module":{"title":"Module","type":"string","order":1},"number":{"title":"Number","type":"integer","order":2},"channel":{"title":"Channel","type":"integer","order":3},"aux":{"title":"Aux","type":"integer","order":4},"param":{"title":"Param","type":"integer","order":5}}}}'
    data = buildReadPacket(param_mac, arg['module'], arg['number'], arg['channel'], arg['aux'], arg['param'])
    tcpControl.send(data)
    
# (not used for the moment)
def handleControlUDP(source, data):
    pass
    # inHex = ':'.join(x.encode('hex') for x in data)
    # print 'control:   source:%s [%s]' % (source, inHex)

def handleMetersBroadcastUDP(source, data):
    # inHex = ':'.join(x.encode('hex') for x in data)
    packet = NeutrinoPacket(data)
    
    if packet.srcMac != srcMacDecoded:
        print('ignoring MAC')
        return
    
    processNeutrinoPacket(packet)

def handleControlBroadcastUDP(source, data):
    # (uncomment to enable packet dumping)
    # inHex = ':'.join(x.encode('hex') for x in data)
    # print 'recv_control_broadcast: %s' % inHex
    
    packet = NeutrinoPacket(data)
    for payload in packet.packets:
        print 'recv broadcast: %s' % payload
        
    if packet.srcMac != srcMacDecoded:
        print('ignoring MAC')
        return
    
    processNeutrinoPacket(packet)
    
def tcpControlConnected():
    local_event_TCPConnected.emit()
    
def tcpControlReceived(data):
    if param_debugDumpTCP:
        inHex = ':'.join(x.encode('hex') for x in data)
        print 'tcpControlReceivedurce:[%s]' % inHex
    
    packet = NeutrinoPacket(data)
    console.info('tcp: Received packet: %s' % packet)
    processNeutrinoPacket(packet)
    
def tcpControlSent(data):
    if param_debugDumpTCP:
        inHex = ':'.join(x.encode('hex') for x in data)
        print 'tcp control sent: %s' % inHex    
    
def tcpControlDisconnected():
    local_event_TCPDisconnected.emit()
    
udpMetersBroadcast = UDP(source='0.0.0.0:%s' % UDPPORT_METERS_BROADCAST, received = handleMetersBroadcastUDP)
udpControlBroadcast = UDP(source='0.0.0.0:%s' % UDPPORT_CONTROL_BROADCAST, received = handleControlBroadcastUDP)

udpControl = UDP(source='0.0.0.0:0', dest='192.168.178.164:%s' % UDPPORT_CONTROL, received = handleControlUDP)
tcpControl = TCP(connected=tcpControlConnected, received=tcpControlReceived, disconnected=tcpControlDisconnected, sent=tcpControlSent,binaryStartStopFlags='\x04\x05')

# Performs any late initialisation that's required
def lateInit():
    global srcMacDecoded
    srcMacDecoded = macToBits(param_mac)

def main(arg = None):
    # Start your script here.
    print 'Nodel script started.'
    
    lateInit()
  
    tcpControl.setDest("%s:%s" % (param_ip, TCPPORT_CONTROL))
    
def composeID(packet):
    return '%s.%s.%s.%s.%s' % (packet.module, packet.modNum, packet.chanNum, packet.auxNum, packet.paramNum)
    
# processes a packet which may have one or more payload segments
def processNeutrinoPacket(packet):
    if packet.connType == CONN_TYPE_UDP_METER:
        for meterPacket in packet.packets:
        	processMeterPacket(meterPacket)

    elif packet.connType == CONN_TYPE_TCP:
        for controlPacket in packet.packets:
            processControlPacket(controlPacket)
    else:
        console.warn('Received and Ignoring packet type: %s' % CONN_STR(packet.connType))

def processMeterPacket(meterPacket):
    # create events
    fullId = composeID(meterPacket)
    
    # get event if it exists
    event = meterEventsByFullId.get(fullId)
    if event is None:
        event = bindMeter(meterPacket, fullId)
    
    event.emit(meterPacket.value)
    # not adding 'units' as below
    # event.emit('%s %s' % (meterPacket.value, meterPacket.unit))

# create an event and action for a given meter
# (assumes not previously bound)
def bindMeter(meterPacket, fullId):
    order = nextSeq()
    event = Event('%s level' % fullId, {'title': fullId, 
                                        'order': order,
                                        'group': meterPacket.group,
                                        'schema': {'type': 'string'}})

    meterEventsByFullId[fullId] = event
    
    return event
  
def processControlPacket(packet):
    # create events
    fullId = composeID(packet)
    
    # get event if it exists
    event = controlEventsByFullId.get(fullId)
    if event is None:
        event = bindControl(packet, fullId)
        
    event.emit(packet.value)
    # not adding 'units' as below
    # event.emit('%s %s' % (packet.value, packet.unit))

# create an event and action for a given general control packet
# (assumes not previously bound)
def bindControl(packet, fullId):
    order = nextSeq()
    event = Event('%s control' % fullId, {'title': fullId, 
                                          'order': order,
                                          'group': 'Control',
                                          'schema': {'type': 'string'}})

    controlEventsByFullId[fullId] = event
    
    return event
  
CHARS = '0123456789abcdef'

START_FLAG = '\x04'
STOP_FLAG  = '\x05'

MAC_NULL = '\x00\x00\x00\x00\x00\x00'

CONN_TYPE_SERIAL = 0
CONN_TYPE_TCP    = 1
CONN_TYPE_UDP    = 2
CONN_TYPE_UDP_METER = 3
def CONN_STR(value):
    if value == 0: return 'CONN_TYPE_SERIAL'
    elif value == 1: return 'CONN_TYPE_TCP'
    elif value == 2: return 'CONN_TYPE_UDP'
    elif value == 3: return 'CONN_TYPE_UDP_METER'
    else: return 'CONN_TYPE_UNKNOWN_%s' % value

PAYLOAD_TYPE_CONTROL = 0
PAYLOAD_TYPE_CPU     = 1
PAYLOAD_TYPE_MULTIPLE_CONTROL = 2
def PAYLOAD_STR(value):
    if value == 0: return 'PAYLOAD_TYPE_CONTROL'
    elif value == 1: return 'PAYLOAD_TYPE_CPU'
    elif value == 2: return 'PAYLOAD_TYPE_MULTIPLE_CONTROL'
    else: return 'PAYLOAD_TYPE_UNKNOWN_%s' % value


RESULT_CODE_NO_ERROR = 0
def RESULT_CODE_STR(value):
    if value == 0: return 'OK'
    else: return 'ERROR_%s' % value

ACT_TYPE_READ_EXT_WRITE_DSP = 0
ACT_TYPE_READ_DSP           = 1
ACT_TYPE_READ_EXT_WRITE_ANA = 2
ACT_TYPE_RESERVED           = 3
ACT_TYPE_READ_EXC_MUTE_IO   = 4
ACT_TYPE_READ_DSP_ONCHANGE_WRITE_DSP = 5
ACT_TYPE_READ_EXT_WRITE_EXT = 6
ACT_TYPE_READ_EXC_WRITE_EXC_BYPASS_ONPRESET = 7
def ACT_STR(value):
    if value == 0: return 'ACT_TYPE_READ_EXT_WRITE_DSP'
    elif value == 1: return 'ACT_TYPE_READ_DSP'
    elif value == 2: return 'ACT_TYPE_READ_EXT_WRITE_ANA'
    elif value == 3: return 'ACT_TYPE_RESERVED'
    elif value == 4: return 'ACT_TYPE_READ_EXC_MUTE_IO'
    elif value == 5: return 'ACT_TYPE_READ_DSP_ONCHANGE_WRITE_DSP'
    elif value == 6: return 'ACT_TYPE_READ_EXT_WRITE_EXT'
    elif value == 7: return 'ACT_TYPE_READ_EXC_WRITE_EXC_BYPASS_ONPRESET'
    else: return 'ACT_TYPE_UNKNOWN_%s' % value

PARAM_GROUP_GAINS    = 0
PARAM_GROUP_MUTING   = 1
PARAM_GROUP_POLARITY = 2
PARAM_GROUP_METERS_3 = 3
PARAM_GROUP_METERS_5 = 5
PARAM_GROUP_SYSTEM   = 9
  
# Returns (group name, unit, multiplier) for a given param type
def GROUP_LOOKUP(param):
    if param == PARAM_GROUP_SYSTEM:
        return ('System', '%', 0.001)
    elif param == PARAM_GROUP_METERS_5:
        return ('Meters (5)', 'dB', 0.001)
    elif param == PARAM_GROUP_METERS_3:
        return ('Meters (3)', 'dB', 0.001)
    elif param == PARAM_GROUP_GAINS:
        return ('Gains', 'dB', 0.001)
    elif param == PARAM_GROUP_MUTING:
        return ('Muting', '', 1)
    elif param == PARAM_GROUP_POLARITY:
        return ('Polarity', '', 1)
    else:
        return ('Param %s' % param, '?', 1)    

def buildReadPacket(mac, moduleName, moduleNum, channelNum, aux, param):
    print 'module:%s(%s), number:%s(%s), channel:%s(%s), aux:%s(%s), param:%s(%s)' % (
      moduleName, type(moduleName), moduleNum, type(moduleNum), channelNum, type(channelNum), aux, type(aux), param, type(param) )
    
    parts = list()
    
    parts.append(str(START_FLAG))
    parts.append(str(toU16bits(32))) # length
    parts.append(str(toU8bits(0)))            # CRC (ignored)
    parts.append(str(toU8bits(CONN_TYPE_TCP)))# conn. type
    parts.append(str(MAC_NULL))      # source MAC (ignored)
    parts.append(str(macToBits(mac)))    # dest MAC
    parts.append(str(toU8bits(PAYLOAD_TYPE_CONTROL))) # payload type
    parts.append(str(toU8bits(RESULT_CODE_NO_ERROR))) # result code
    parts.append(str(moduleName)) # module name
    parts.append(str(toU8bits(ACT_TYPE_READ_DSP))) # action type
    parts.append(str(toU16bits(moduleNum)))
    parts.append(str(toU8bits(channelNum)))
    parts.append(str(toU8bits(aux)))
    parts.append(str(toU8bits(param)))
    parts.append(str(STOP_FLAG))
    
    return ''.join(parts)
  
def buildWritePacket(mac, moduleName, moduleNum, channelNum, aux, param, value=0, value_dB=None):
    if value_dB is not None:
        value = int(value_dB * 1000)
        
    parts = list()
    
    parts.append(str(START_FLAG))
    parts.append(str(toU16bits(36))) # length
    parts.append(str(chr(0)))        # CRC (ignored)
    parts.append(str(chr(CONN_TYPE_TCP)))# conn. type
    parts.append(str(MAC_NULL))          # source MAC (ignored)
    parts.append(str(macToBits(mac)))    # dest MAC
    parts.append(str(chr(PAYLOAD_TYPE_CONTROL))) # payload type
    parts.append(str(chr(RESULT_CODE_NO_ERROR))) # result code
    parts.append(str(moduleName)) # module name
    parts.append(str(chr(ACT_TYPE_READ_EXT_WRITE_DSP))) # action type
    parts.append(str(toU16bits(moduleNum | 0x8000)))
    parts.append(str(chr(channelNum)))
    parts.append(str(chr(aux)))
    parts.append(str(chr(param)))
    parts.append(str(toU32bits(value)))
    parts.append(str(STOP_FLAG))
    
    return ''.join(parts)
  
class NeutrinoPacket:
    def __init__(self, data):
        self.parse(data)

    def parse(self, data):
        i = 0
        
        checkFlag(data, i, START_FLAG, 'START_FLAG')
        i += 1
        
        self.length = read16(data, i)
        i += 2

        self.crc = read8(data, i)
        i += 1

        self.connType = read8(data, i)
        i += 1

        self.srcMac = readMac(data, i)
        i += 6

        self.dstMac = readMac(data, i)
        i += 6

        self.payloadType = read8(data, i)
        i += 1
        
        self.resultCode = read8(data, i)
        i += 1
        
        if self.length <= 18:
            # this is just an acknowledgement packet
            self.count = 0
            self.packets = ()

        else:
            if self.payloadType == PAYLOAD_TYPE_MULTIPLE_CONTROL:
                # read the length byte
                self.count = read16(data, i)
                i += 2
            else:
                # skip the length byte
                self.count = 1

            self.packets = list()

            for controlIndex in range(self.count):
                if self.connType == CONN_TYPE_UDP_METER:
                    meterPacket = MeterPacket(data, i)
                    i += 18

                    self.packets.append(meterPacket)

                elif self.connType == CONN_TYPE_TCP:
                    controlPacket = ControlReadPacket(data, i)
                    i += 18

                    self.packets.append(controlPacket)
                
        checkFlag(data, i, STOP_FLAG, 'STOP_FLAG')
        i += 1

    # Returns True if the source is correct
    def isFrom(self, srcMac):
        return self.srcMc
                
    def __repr__(self):
        return '[%s, %s, %s, %s packets]' % (
          CONN_STR(self.connType), 
          PAYLOAD_STR(self.payloadType),
          RESULT_CODE_STR(self.resultCode),
          len(self.packets))

class MeterPacket:
    def __init__(self, data, index):
        self.parse(data, index)

    def parse(self, data, i):
        self.module = read8chars(data, i)
        i += 8

        self.actType = read8(data, i)
        i += 1

        self.modNum = read16(data, i)
        i += 2

        self.chanNum = read8(data, i)
        i += 1

        self.auxNum = read8(data, i)
        i += 1

        self.paramNum = read8(data, i)
        i += 1

        value = read32signed(data, i)
        i += 4
        
        # print 'meter: value:%s' % value
        
        paramGroupData = GROUP_LOOKUP(self.paramNum)
        
        self.group = paramGroupData[0]
        
        self.unit = paramGroupData[1]
        
        self.value = value * paramGroupData[2]
        
    def __repr__(self):
        return '[%s: type:%s mod:%s chan:%s aux:%s param:%s value:%s %s]' % (self.module, ACT_STR(self.actType),
                                                                          self.modNum, self.chanNum,
                                                                          self.auxNum, self.paramNum,
                                                                          self.value, self.unit)

class ControlReadPacket:
    def __init__(self, data, index):
        self.parse(data, index)

    def parse(self, data, i):
        self.module = read8chars(data, i)
        i += 8
        print 'mod:%s' % self.module
        
        self.actType = read8(data, i)
        i += 1
        print 'act:%s' % self.actType

        self.modNum = read16(data, i)
        i += 2
        print 'modNum:%s' % self.modNum

        self.chanNum = read8(data, i)
        i += 1
        print 'chanNum:%s' % self.chanNum

        self.auxNum = read8(data, i)
        i += 1
        print 'auxNum:%s' % self.auxNum

        self.paramNum = read8(data, i)
        i += 1
        print 'paramNum:%s' % self.paramNum

        value = read32signed(data, i)
        i += 4
        print 'value:%s' % value
        
        paramGroupData = GROUP_LOOKUP(self.paramNum)
        
        self.group = paramGroupData[0]
        
        self.unit = paramGroupData[1]
        
        self.value = value * paramGroupData[2]
        
        print 'ControlReadPacket:%s' % self

    def __repr__(self):
        return '[%s: type:%s mod:%s chan:%s aux:%s param:%s value:%s]' % (self.module, ACT_STR(self.actType),
                                                                          self.modNum, self.chanNum,
                                                                          self.auxNum, self.paramNum,
                                                                          self.value)  
      
      
# (use chr(b) instead)
def toU8bits(b):
    return chr(b & 0xff)
    
def toU16bits(i):
    return '%s%s' % (chr((i >> 8) & 0xff), chr(i & 0xff))
  
def toU32bits(i):
    return '%s%s%s%s' % (chr((i >> 24) & 0xff), chr((i >> 16) & 0xff), chr((i >> 8) & 0xff), chr(i & 0xff))  
      
def strToBits(data):
    return data.encode('hex')

# where 'mac' is '00:aa:bb:cc:dd:ee' (with or without colons or dashes)
def macToBits(mac):
    # strip out the colons (if any were used)
    mac = mac.replace(':', '')
    mac = mac.replace('-', '')
    return mac.decode('hex')
      
def hexDump(data):    
    return ''.join("\\x%s%s" % (CHARS[ord(x) / 16], CHARS[ord(x) % 16]) for x in data)
  
def checkFlag(data, i, flag, name):
    if data[i] != flag: raise Exception(name + ' missing')

def read8(data, i):    
    return ord(data[i])

def read16(data, i):
    return (ord(data[i]) << 8) + ord(data[i+1])

def read32(data, i):
    return (ord(data[i]) << 24) + (ord(data[i+1]) << 16) + (ord(data[i+2]) << 8) + ord(data[i+3])

# signed 32-bits
def read32signed(data, i):
    x = read32(data, i)
    if x & 0x80000000:
        return -0x100000000 + x
    else:
        return x

def readMac(data, i):
    return '%s%s%s%s%s%s' % (data[i], data[i+1], data[i+2], data[i+3], data[i+4], data[i+5])
  
def read8chars(data, i):
    return '%s%s%s%s%s%s%s%s' % (data[i], data[i+1], data[i+2], data[i+3], data[i+4], data[i+5], data[i+6], data[i+7])  

seqCounter = [-1]

def nextSeq():
  seqCounter[0] += 1
  return seqCounter[0]
    
# tcpControl.send('\x04\x00\x24\x58\x01\x00\x00\x00\x00\x00\x00\x00\x60\x35\x12\x7c\x79\x00\x00\x4d\x61\x74\x72\x69\x78\x4d\x30\x00\x80\x11\x07\x07\x05\x00\x00\x00\x00\x05')