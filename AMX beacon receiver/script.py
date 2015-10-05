# coding=utf-8
u"An AMX beacon signal receiver - listens out on multicast address 239.255.250.250:9131"

# example beacon data:
# source: 192.168.178.173.9131
# data: AMXB<-UUID=GlobalCache_000C1E038995><-SDKClass=Utility><-Make=GlobalCache><-Model=iTachIP2IR>
# <-Revision=710-1005-05><-Pkg_Level=GCPK002><-Config-URL=http://192.168.178.173><-PCB_PN=025-0028-03><-Status=Ready>

eventsByUUID = {}

def multicast_ready():
    print 'AMX beacon receiver started.'
    
def multicast_received(source, data):
    # print 'got: [%s]', data.encode('hex')
  
    if not data.startswith('AMX'):
        # ignore packet
        return
      
    parseAMXBPacket(source, data)
    
multicast_receiver = UDP(source='239.255.250.250:9131', dest=None, ready=multicast_ready, received=multicast_received)

def main(arg = None):
    print 'AMX beacon driver loaded.'

def parseAMXBPacket(source, data):
    # split the packet into the elements
    parts = data.split('<-')
    
    info = {}
    plainInfo = {}
    
    uuid = None
    
    for part in parts:
        part = part.strip()
        if part.endswith('>'):
            part = part[:-1]
            
        # e.g. part: "UUID=GlobalCache_000C1E038995"
        
        # look for equals
        splitPos = part.find('=')
        if splitPos < 0:
            continue
            
        name = part[:splitPos]
        value = part[splitPos+1:]
        
        plainName = plainFieldName(name)
        if plainName == 'uuid':
            uuid = value
        
        info[name] = value
        plainInfo[plainName] = value        
    
    # add the source information too
    info['SourceAddress'] = source
    plainInfo[plainFieldName('SourceAddress')] = source
    
    event = eventsByUUID.get(uuid)
    if event is None:
        metadata = {'title': '%s beacon' % uuid }
        
        groupList = list()
        
        make = plainInfo.get('make')
        if make: groupList.append(make)
          
        model = plainInfo.get('model')
        if model: groupList.append(model)
          
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
        
        event = Event('%s beacon' % uuid, metadata)
        
        print 'Added beacon info from new device. Metadata was %s' % metadata
        
        eventsByUUID[uuid] = event

    event.emit(plainInfo)
    
# converts a field name into a 'safe', plain version possible extending
# compatibility with UI frameworks
def plainFieldName(rawName):
    fieldname = list()
    
    for c in rawName:
        x = ord(c)
        if (x >= 0x30 and x <= 0x39) or (x >= 0x41 and x <= 0x5A) or (x >= 0x61 and x <= 0x7a):
            fieldname.append(c)
        else:
            fieldname.append('_')

    return ''.join(fieldname).lower()

seqNum = [0L]
def nextSeqNum():
    seqNum[0] += 1
    return seqNum[0]