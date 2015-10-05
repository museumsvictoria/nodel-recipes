# coding=utf-8
u"A UPNP beacon signal receiver."

# see http://www.upnp-hacks.org/upnp.html

# example beacon data:
# source: 192.168.178.173.9131
# data:
# HTTP/1.1 200 OK
# CACHE-CONTROL:max-age=1800
# EXT:
# LOCATION:http://10.0.0.138:80/IGD.xml
# SERVER:SpeedTouch 510 4.0.0.9.0 UPnP/1.0 (DG233B00011961)
# ST:urn:schemas-upnp-org:service:WANPPPConnection:1
# USN:uuid:UPnP-SpeedTouch510::urn:schemas-upnp-org:service:WANPPPConnection:1

import xml.etree.ElementTree as ET

eventsByUSN = {}

local_event_discoveryCacheSize = LocalEvent({"title": "Discovery cache size", "order": 0, "schema": {"type": "integer"}})

def multicast_ready():
    print 'UPNP beacon receiver started.'
    
def multicast_received(source, data):
    parseUPNPPacket(source, data)
    
multicast_receiver = UDP(source='239.255.255.250:1900', dest=None, ready=multicast_ready, received=multicast_received)

def main(arg = None):
    print 'UPNP beacon driver loaded.'

def parseUPNPPacket(source, data):
    # split the packet into the elements
    # print 'got data from %s data:%s' % (source, data.encode('hex'))
    
    # split the packet into the elements
    parts = data.split('\r')
    
    info = {}
    lcInfo = {}
    
    usn = None
    
    if len(parts) > 0:
        firstLine = parts[0]
        
        # skip SEARCH requests from clients
        if 'M-SEARCH' in firstLine:
            return
    
    for part in parts:
        # look for equals
        splitPos = part.find(':')
        if splitPos < 0:
            continue
            
        name = part[:splitPos].strip()
        value = part[splitPos+1:].strip()
        
        lcName = plainFieldName(name)
        if lcName == 'usn':
            usn = value
            
        info[name] = value
        lcInfo[lcName] = value
        
    # location = lcInfo.get('location')
    # upnpData = None
    # if location is not None:
    #    upnpData = tryLocation(location)
    #    print 'got upnp data: %s' % upnpData
    #    
    #    for key, value in upnpData:
    #        lcInfo[key] = value
    
    # add the source information too
    info['SourceAddress'] = source
    lcInfo[plainFieldName('SourceAddress')] = source
    
    lookup = usn
    if lookup is None:
        split = source.rfind(':')
        ipAddress = source[:split]
        lookup = ipAddress
        
    event = eventsByUSN.get(lookup)
    if event is None:
        metadata = {'title': '%s beacon' % lookup }
        
        groupList = list()
        
        make = lcInfo.get('server')
        if make: groupList.append(make)
          
        # model = lcInfo.get('nt')
        # if model: groupList.append(model)
          
        group = None
        if len(groupList) > 0:
            group = " - ".join(groupList)
            metadata['group'] = group
            
        props = {}
        for key in info:
            props[plainFieldName(key)] = { "title": key, "type": "string" }
            
        schema = {'type': 'object'}
        schema['title'] = 'Beacon info'
        schema['properties'] = props
        
        metadata['schema'] = schema
        
        event = Event('%s beacon' % lookup, metadata)
        
        eventsByUSN[lookup] = event
        print 'Added beacon info from new device. Metadata was %s' % metadata
        local_event_discoveryCacheSize.emit(len(eventsByUSN))

    event.emit(lcInfo)

def tryLocation(value):
    # print 'tryLocation: %s' % value
    xml = getURL(value)
    
    root = ET.fromstring(xml)
    namespace = root.tag[:root.tag.find('}')+1]
    
    device = root.find(namespace + 'device')
    
    data = {}
    
    for e in device:
        name = e.tag
        name = name[name.rfind('}')+1:]
        data[name.strip()] = e.text.strip()
        
    return data

# converts a field name into a 'safe', plain version possible extending
# compatibility with UI frameworks
def plainFieldName(rawName):
    fieldname = list()
    
    # check if first character is a number (quite often illegal)
    if len(rawName) > 0:
        x = ord(rawName[0])
        if x >= 0x30 and x <= 0x39:            
            fieldname.append('_')
    
    for c in rawName:
        x = ord(c)
            
        if (x >= 0x30 and x <= 0x39) or (x >= 0x41 and x <= 0x5A) or (x >= 0x61 and x <= 0x7a) or x > 0x7f:
            fieldname.append(c)
        else:
            fieldname.append('_')
    
    return ''.join(fieldname).lower()

seqNum = [0L]
def nextSeqNum():
    seqNum[0] += 1
    return seqNum[0]