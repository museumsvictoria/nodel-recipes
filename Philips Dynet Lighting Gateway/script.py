param_address = Parameter({ "title":"TCP address", "order":0, "schema": { "type":"string" },
                              "desc": "e.g. 192.168.1.24:2001"})

DYNALITE_SCHEMA = {'type': 'object', 'title': 'Dynalite Message', 'properties': {
        'area': {'type': 'integer', 'title': 'Area', 'order': next_seq()},
        'data0': {'type': 'integer', 'title': 'DATA[0]', 'order': next_seq()},
        'preset': {'type': 'integer', 'title': 'PRESET Preset/Line', 'order': next_seq()},
        'data1': {'type': 'integer', 'title': 'DATA[1] (Channel)', 'order': next_seq(), 'hint': 0},
        'data2': {'type': 'integer', 'title': 'DATA[2]', 'order': next_seq(), 'hint': 0},
        'join': {'type': 'integer', 'title': 'Join', 'order': next_seq(), 'hint': '255'}
      }}

param_customMessages = Parameter({'title': 'Custom messages', 'schema': {'type': 'array', 'items': {
        'type': 'object', 'properties': {
          'label': {'type': 'string', 'title': 'Label', 'order': -10},
          'group': {'type': 'string', 'title': 'Group', 'order': -9},
          'message': DYNALITE_SCHEMA
  }}}})

labelsByKey = {}

param_labelling = Parameter({'title': 'Channel/preset labelling', 'schema': {'type': 'array', 'items': {
        'type': 'object', 'properties': {
          'label': {'type': 'string', 'order': next_seq()},
          'area': {'type': 'integer', 'order': next_seq()},
          'preset': {'title': 'preset/line', 'type': 'integer', 'order': next_seq()},
          'channel': {'title': 'channel', 'type': 'integer', 'order': next_seq()}}}}})

# the area and presets being trapped
local_event_Discovery = LocalEvent({'group': 'Discovery', 'schema': {'type': 'array', 'items': { 
        'type': 'object', 'properties': {
          'area': {'type': 'integer', 'order': 1},
          'preset': {'title': 'Preset/Line', 'type': 'integer', 'order': 2},
          'channel': {'title': 'channel', 'type': 'integer', 'order': 3},
        }}}})

PRESET_THRESHOLD = 16 # incl., 1 to 16 are presets, >16 are channels

# for storing keys in the trapping structure
def createKey(area, presetOrLine, channel):
  if presetOrLine <= PRESET_THRESHOLD:
    return 'Area:%s Preset:%s' % (area, presetOrLine)
  else:
    return 'Area:%s Line:%s Channel:%s' % (area, presetOrLine, channel)
  
def lookupOrCreateSignal(area, presetOrLine, channel, init=False, rawDataToEmit=None):
  key = createKey(area, presetOrLine, channel)
  signal = lookup_local_event(key)
  
  presetKey = 'Area:%s Preset' % (area)
  presetSignal = lookup_local_event(presetKey)
  
  if presetSignal == None:
    presetSignal = Event(presetKey, {'group': 'Area Presets', 'order': 900+presetOrLine, 'schema': {'type': 'string'}})
    
  presetValue = labelsByKey.get(key, str(presetOrLine))
  
  # perform slider value transformation? i.e. instead of 255-0, 0-100%
  if presetOrLine <= PRESET_THRESHOLD:
    transform = False
  else:
    transform = True
    
  title = labelsByKey.get(key)
  if title == None:
    title = '"%s"' % key
  
  if signal == None:
    if presetOrLine <= PRESET_THRESHOLD: 
      schema = {} # stateless
    else:
      # actual range is 255 (off) - 0
      schema = {'type': 'integer', 'format': 'range', 'min': 0, 'max': 100}
      transform = True
    
    signal = Event(key, {'title': title, 'group': 'Area %s' % area, 'order': 1000+presetOrLine, 
                         'schema': schema})
    
    def handler(arg):
      # arg is from 0 - 100
      if transform:
        dynArg = 255 - (arg*255/100)
        sendDynaliteMessage({'area': area, 'preset': presetOrLine, 'data1': channel, 'data2': 5, 'data0': dynArg, 'join': 255})
        signal.emit(arg)
      else:
        dynArg = 100 # the value '100' seems to be used by the dimmer for presets
        sendDynaliteMessage({'area': area, 'preset': presetOrLine, 'data1': 0, 'data2': 0, 'data0': dynArg, 'join': 255})
        signal.emit()
        presetSignal.emit(presetValue)
      
    action = Action(key, handler, {'title': title, 'group': 'Area %s' % area, 'order': 1000+presetOrLine,
                          'schema': schema})
    
    # add to trapping list event so it persists *only* if it on init
    if not init:
      extended = list()
      for entry in local_event_Discovery.getArg() or []:
        extended.append(entry)
      extended.append({'area': area, 'preset': presetOrLine, 'channel': channel})
    
      local_event_Discovery.emit(extended)

  # should we also emit?
  if rawDataToEmit != None:
    if transform:
      # 255-0, 0-100%
      signal.emit((255-rawDataToEmit)*100/255)
    else:
      signal.emit(rawDataToEmit)
      presetSignal.emit(presetValue)
    
  return signal

local_event_LastMessage = LocalEvent({'title': 'Last Dynalite message', 'group': 'Debug', 'schema': DYNALITE_SCHEMA})

def main():
  if param_address == None or param_address.strip() == '':
    console.warn('Address not set; cannot start.')
    return # abort start
  
  for entry in param_labelling or []:
    labelsByKey[createKey(entry['area'], entry['preset'], entry['channel'])] = entry['label']
  
  # sync up the trapping data-structure
  for entry in local_event_Discovery.getArg() or []:
    lookupOrCreateSignal(entry['area'], entry['preset'], entry['channel'], init=True)
  
  tcp.setDest('%s' % param_address)

  for customMessage in param_customMessages or []:
    initCustomMessage(customMessage)

def sendDynaliteMessage(packet=None):
  if packet == None:
    console.warn('No packet given')
    return
    
  area = packet['area']
  data0 = packet['data0']
  preset = packet['preset']
  data1 = packet.get('data1') or 0
  data2 = packet.get('data2') or 0
  join = packet.get('join') or 255
  
  console.info('Sending area:%s data0:%s, preset:%s data1:%s data2:%s join:%s' % (area, data0, preset, data1, data2, join))
               
  
  raw_packet = '%s%s%s%s%s%s%s' % ('\x1c',    # SYNC
                                 chr(area), 
                                 chr(data0),
                                 chr(preset-1),
                                 chr(data1),
                                 chr(data2),
                                 chr(join))
  
  packet = '%s%s' % (raw_packet, chr(getChecksum(raw_packet)))
  
  tcp.send(packet)

sendDynaliteMessageAction = Action('Send Dynalite Message', sendDynaliteMessage, 
      {'group': 'Dynalite', 'order': next_seq(), 'schema': DYNALITE_SCHEMA})

sendDynaliteMessageAction2 = Action('Send Dynalite Message 2', sendDynaliteMessage, 
      {'group': 'Dynalite', 'order': next_seq(), 'schema': DYNALITE_SCHEMA})

sendDynaliteMessageAction3 = Action('Send Dynalite Message 3', sendDynaliteMessage, 
      {'group': 'Dynalite', 'order': next_seq(), 'schema': DYNALITE_SCHEMA})
    

# NO_OP for keeping connection open and status relevant  
  
NO_OP_MSG = {'area': 250, 'data0': 1, 'preset': 1, 'data1': 1, 'data2': 1, 'join': 1}
  
def noOp_ping():
  # sends a "NO OP" down the line to keep the connection open
  sendDynaliteMessageAction.call(NO_OP_MSG)
  
Timer(noOp_ping, 4.5*60) # every 4.5 minutes

def connected():
  console.info('TCP connected')

inputBuffer = list()
  
def received(data):
  debug('received: [%s]' % data.encode('hex'))
  
  lastReceive[0] = system_clock()
  
  for b in data:
    processByteIn(b)
  
def processByteIn(b):
  if len(inputBuffer) == 0:
    if b == '\x1c' or b == '\x5c':
      inputBuffer.append(b)
      return
    
    else:
      console.warn('NO SYNC BYTE YET')
      return
  
  inputBuffer.append(b)
  
  if len(inputBuffer) >= 8:
    handleDynaliteMessage(inputBuffer)
    
    del inputBuffer[:]
    
def handleDynaliteMessage(buff):
  remote_action_NodelTransportForward1.call(''.join(buff).encode('hex'))
  
  sync = '%02x' % ord(buff[0])
  area = ord(buff[1])
  data0 = ord(buff[2])
  preset = ord(buff[3]) + 1
  data1 = ord(buff[4])
  data2 = ord(buff[5])
  join = ord(buff[6])
  checksum = '%02x' % ord(buff[7])
  
  
  local_event_LastMessage.emit({'area': area, 'data0': data0, 'preset': preset, 
                                'data1': data1, 'data2': data2, 'join': join})

  # NOTE: data1 would be the channel
  lookupOrCreateSignal(area, preset, data1, rawDataToEmit=data0)
  
  console.info('RECV: a:%s d0:%s preset:%s data1:%s data2:%s join:%s checksum:%s' %
               (area, data0, preset, data1, data2, join, checksum))

def sent(data):
  debug('sent: [%s]' % data.encode('hex'))
  
def disconnected():
  console.info('TCP disconnected')
  
def timeout():
  console.warn('TCP timeout!')

tcp = TCP(connected=connected, 
          received=received, 
          sent=sent, 
          disconnected=disconnected, 
          timeout=timeout, 
          sendDelimiters=None, 
          receiveDelimiters=None)

def initCustomMessage(customMessage):
  label = customMessage['label']
  group = customMessage.get('group')
  message = customMessage['message']
  
  customAction = Action('%s' % label, lambda arg: sendDynaliteMessageAction.call(message), {'title': label, 'group': '%s (Custom)' % group, 'order': next_seq()})
    
def two_c(v):
    return (~v + 1) & 0xff

def getChecksum(buf):
  t = 0
  for b in buf:
    i = ord(b)
    i2 = two_c(i)
    
    t += i2
    
  return t & 0xff

local_event_Debug = LocalEvent({'title': 'Debug mode?', 'group': 'Debug', 'schema': {'type': 'boolean'}})

def debug(message):
  if local_event_Debug.getArg():
    console.log('DEBUG: %s' % message)

# <--- Status

local_event_Status = LocalEvent({'order': -100, 'group': 'Status', 'schema': {'type': 'object', 'properties': {
        'level': {'type': 'integer', 'title': 'Level'},
        'message': {'type': 'string', 'title': 'Message'}
      }}})
  
lastReceive = [0]  
  
# roughly, the last contact  
local_event_LastContactDetect = LocalEvent({'group': 'Status', 'title': 'Last contact detect', 'schema': {'type': 'string'}})
  
def statusCheck():
  diff = (system_clock() - lastReceive[0])/1000.0 # (in secs)
  now = date_now()
  
  if diff > status_check_interval+15:
    previousContactValue = local_event_LastContactDetect.getArg()
    
    if previousContactValue == None:
      message = 'Always been missing.'
      
    else:
      previousContact = date_parse(previousContactValue)
      roughDiff = (now.getMillis() - previousContact.getMillis())/1000/60
      message = 'Off the network for approx. %s minutes' % roughDiff
      
    local_event_Status.emit({'level': 2, 'message': message})
    return

  local_event_LastContactDetect.emit(str(now))
  local_event_Status.emit({'level': 0, 'message': 'OK'})

status_check_interval = 60*5 # 5 minutes
status_timer = Timer(statusCheck, status_check_interval)

# Status --->

# custom

remote_action_NodelTransportForward1 = RemoteAction()
  
def remote_event_NodelTransportReceive1(arg):
  tcp.send(arg.decode('hex'))