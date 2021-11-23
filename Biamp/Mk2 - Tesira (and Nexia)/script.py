'''Works with Tesira models using the Tesira Text Protocol (TTP)'''

# TODO:
# - For Maxtrix Mixer blocks, only cross-point muting is done.

TELNET_TCPPORT = 23

param_Disabled = Parameter({'schema': {'type': 'boolean'}})
param_IPAddress = Parameter({'title': 'IP address', 'schema': {'type': 'string'}})

# TODO REMOVE DEFAULT_DEVICE = 1

param_InputBlocks = Parameter({'title': 'Input blocks', 'schema': {'type': 'array', 'items': {'type': 'object', 'properties': {
          'instance': {'type': 'string', 'desc': 'Instance ID or tag', 'order': 1},
          'inputNames': {'type': 'string', 'desc': 'Comma separated list of simple labels starting at input #1; use "ignore" to ignore an input', 'order': 2}}}}})

param_LevelBlocks = Parameter({'title': 'Level blocks', 'schema': {'type': 'array', 'items': {'type': 'object', 'properties': {
          'instance': {'type': 'string', 'desc': 'Instance ID or tag', 'order': 1},
          'names': {'type': 'string', 'desc': 'Comma separated list of simple labels starting at #1; use "ignore" to ignore', 'order': 2}}}}})

param_MuteBlocks = Parameter({'title': 'Mute blocks', 'schema': {'type': 'array', 'items': {'type': 'object', 'properties': {
          'instance': {'type': 'string', 'desc': 'Instance ID or tag', 'order': 1},
          'names': {'type': 'string', 'desc': 'Comma separated list of simple labels starting at #1; use "ignore" to ignore', 'order': 2}}}}})

param_SourceSelectBlocks = Parameter({'title': 'Source-Select blocks', 'schema': {'type': 'array', 'items': {'type': 'object', 'properties': {
          'instance': {'type': 'string', 'desc': 'Instance ID or tag', 'order': 3},
          'sourceCount': {'type': 'integer', 'desc': 'The number of sources being routed', 'order': 4}}}}})

param_MeterBlocks = Parameter({'title': 'Meter blocks', 'schema': {'type': 'array', 'items': {'type': 'object', 'properties': {
          'type': {'type': 'string', 'enum': ['Peak', 'RMS', 'Presence'], 'order': 1},
          'instance': {'type': 'string', 'desc': 'Instance ID or tag', 'order': 2},
          'names': {'type': 'string', 'desc': 'Comma separated list of simple labels starting at #1; use "ignore" to ignore', 'order': 3}}}}})

param_MatrixMixerBlocks = Parameter({'title': 'Matrix Mixer blocks', 'schema': {'type': 'array', 'items': {'type': 'object', 'properties': {
          'label': {'type': 'string', 'order': 1},
          'instance': {'type': 'string', 'desc': 'Instance ID or tag', 'order': 4},
          'inputNames': {'type': 'string', 'desc': 'Comma separated list of simple labels', 'order': 5},
          'outputNames': {'type': 'string', 'desc': 'Comma separated list of simple labels', 'order': 6}}}}})

param_StandardMixerBlocks = Parameter({'title': 'Standard Mixer blocks', 'schema': {'type': 'array', 'items': {'type': 'object', 'properties': {
          'label': {'type': 'string', 'order': 1},
          'instance': {'type': 'string', 'desc': 'Instance ID or tag', 'order': 4},
          'inputNames': {'type': 'string', 'desc': 'Comma separated list of simple labels', 'order': 5},
          'outputNames': {'type': 'string', 'desc': 'Comma separated list of simple labels', 'order': 6},
          'ignoreCrossPoints': {'type': 'boolean', 'desc': 'Ignore cross-point states to reduce number of controls', 'order': 7}
        }}}})

# <main ---
  
def main():
  if param_Disabled:
    console.warn('Disabled! nothing to do')
    return
  
  if is_blank(param_IPAddress):
    console.warn('No IP address set; nothing to do')
    return
  
  dest = '%s:%s' % (param_IPAddress, TELNET_TCPPORT)
  
  console.info('Will connect to [%s]' % dest)
  tcp.setDest(dest)

# --- main>

# <protocol ---

def parseResp(rawResp, onSuccess):
  # e.g: [+OK "value":-64.697762]

  resp = rawResp.strip()
  
  if resp == '+OK':
    onSuccess(None)
    
  elif '-ERR' in resp:
    console.warn('Got bad resp: %s' % resp)
    return
  
  else:
    # any successful resp has its callback called
    valuePos = resp.find('"value":')
  
    if valuePos > 0: onSuccess(resp[valuePos+8:])
    else:            console.warn('no value in resp; was [%s]' % resp)


INPUTGAIN_SCHEMA = {'type': 'integer', 'desc': '0, 6, 12, 18, 24, 30, 36, 42, 48, 54, 60, 66'}
  
@after_main
def bindInputs():
  for info in param_InputBlocks or []:
    for inputNum, inputName in enumerate(info['inputNames'].split(',')):
      if inputName == 'ignore':
        continue
        
      initNumberValue('Input', 'gain', inputName, info['instance'], inputNum+1, isInteger=True)
    
@after_main
def bindLevels():
  for info in param_LevelBlocks or []:
    levelInstance = info['instance']
    for num, name in enumerate(info['names'].split(',')):
      initNumberValue('Level', 'level', name, levelInstance, num+1)
      initBoolValue('Level Muting', 'mute', name, levelInstance, num+1)
      
@after_main
def bindMutes():
  for info in param_MuteBlocks or []:
    instance = info['instance']
    
    names = (info['names'] or '').strip()
    if len(names) > 0:
      for num, name in enumerate([x.strip() for x in names.split(',')]):
        initBoolValue('Mute', 'mute', name, instance, num+1)
        
    else:
      initBoolValue('Mute', 'mute', 'All', instance, 1)

@after_main
def bindMatrixMixers():
  for info in param_MatrixMixerBlocks or []:
    instance = info['instance']
    label = info['label']
    
    for inputNum, inputName in enumerate(info['inputNames'].split(',')):
      inputName = inputName.strip()
      
      for outputNum, outputName in enumerate(info['outputNames'].split(',')):
        outputName = outputName.strip()
        
        initBoolValue('Crosspoint State', 'crosspointLevelState', 
                          '%s - %s - %s' % (label, inputName.strip(), outputName),
                          instance, inputNum+1, index2=outputNum+1)
        
        initNumberValue('Crosspoint Level', 'crosspointLevel', 
                          inputName,
                          instance, inputNum+1, index2=outputNum+1, 
                          group='"%s %s"' % (label, outputName))
        
        
@after_main
def bindStandardMixers():
  for info in param_StandardMixerBlocks or []:
    instance = info['instance']
    
    if not info.get('ignoreCrossPoints'): # skip cross-points
      for inputNum, inputName in enumerate(info['inputNames'].split(',')):
        inputName = inputName.strip()
      
        for outputNum, outputName in enumerate(info['outputNames'].split(',')):
          outputName = outputName.strip()
          initBoolValue('Crosspoint State', 'crosspoint', 
                            inputName,
                            instance, inputNum+1, index2=outputNum+1, 
                            group='"%s %s"' % (info['label'], outputName))
        
    # output levels
    for outputNum, outputName in enumerate(info['outputNames'].split(',')):
        outputName = outputName.strip()
        initNumberValue('Output Level', 'outputLevel', 
                          outputName,
                          instance, outputNum+1,
                          group='"%s %s"' % (info['label'], outputName))
        
        initBoolValue('Output Mute', 'outputMute', 
                          outputName,
                          instance, outputNum+1,
                          group='"%s %s"' % (info['label'], outputName))        
        
    # TODO: also expose input levels        

def initBoolValue(controlType, cmd, label, inst, index1, index2=None, group=None):
  if index2 == None:
    name = '%s %s %s' % (inst, index1, controlType)
  else:
    # name collision will occur if dealing with more than 10 in a list
    # so add in a forced delimeter 'x', e.g. '1 11' is same as '11 1' but not '1x11'
    delimeter = ' ' if index1 < 10 and index2 < 10 else ' x ' 
    
    name = '%s %s%s%s %s' % (inst, index1, delimeter, index2, controlType)
    
  title = '"%s" (#%s)' % (label, index1)
  
  if group == None:
    group = inst
    
  schema = {'type': 'boolean'}
  
  signal = Event(name, {'title': title, 'group': group, 'order': next_seq(), 'schema': schema})
  
  # some cmds take in index1 and index2
  index = index1 if index2 == None else '%s %s' % (index1, index2)

  # e.g. Mixer1 get crosspointLevelState 1 1
    
  getter = Action('Get ' + name, lambda arg: tcp_request('%s get %s %s\n' % (inst, cmd, index), 
                          lambda resp: parseResp(resp, lambda arg: signal.emit(arg == '1' or arg == 'true'))),
                 {'title': 'Get', 'group': group, 'order': next_seq()})
  
  setter = Action(name, lambda arg: tcp_request('%s set %s %s %s\n' % (inst, cmd, index, '1' if arg == True else '0'), 
                          lambda resp: parseResp(resp, 
                            lambda result: signal.emit(arg))), # NOTE: uses the original 'arg' here
                  {'title': title, 'group': group, 'order': next_seq(), 'schema': schema})
  
  Timer(lambda: getter.call(), random(120,150), random(5,10))
  
  # and come conveniece derivatives
  
  toggle = Action(name + " Toggle", lambda arg: setter.call(not signal.getArg()), {'title': 'Toggle', 'group': group, 'order': next_seq()})
  
  inverted = Event(name + " Inverted", {'title': '(inverted)', 'group': group, 'order': next_seq(), 'schema': schema})
  signal.addEmitHandler(lambda arg: inverted.emit(not arg))

def initNumberValue(controlType, cmd, label, inst, index1, isInteger=False, index2=None, group=None):
  if index2 == None:
    name = '%s %s %s' % (inst, index1, controlType)
  else:
    # name collision will occur if dealing with more than 10 in a list
    # so add in a forced delimeter 'x', e.g. '1 11' is same as '11 1' but not '1x11'
    delimeter = ' ' if index1 < 10 and index2 < 10 else ' x ' 
    
    name = '%s %s%s%s %s' % (inst, index1, delimeter, index2, controlType)
    
  title = '%s ("%s")' % (name, label)
  
  if group == None:
    group = '%s %s' % (controlType, inst)
    
  schema = {'type': 'integer' if isInteger else 'number'}
  
  signal = Event(name, {'title': title, 'group': group, 'order': next_seq(), 'schema': schema})
  
  # some cmds take in index1 and index2
  index = index1 if index2 == None else '%s %s' % (index1, index2)
    
  getter = Action('Get ' + name, lambda arg: tcp_request('%s get %s %s\n' % (inst, cmd, index), 
                          lambda resp: parseResp(resp, lambda arg: signal.emit(int(float(arg)) if isInteger else float(arg)))),
                 {'title': 'Get', 'group': group, 'order': next_seq()})
  
  setter = Action(name, lambda arg: tcp_request('%s set %s %s %s\n' % (inst, cmd, index, arg), 
                          lambda resp: parseResp(resp, 
                            lambda result: signal.emit(arg))), # NOTE: uses the original 'arg' here
                  {'title': title, 'group': group, 'order': next_seq(), 'schema': schema})
  
  Timer(lambda: getter.call(), random(120,150), random(5,10))
  
@after_main
def bindSourceSelects():
  for info in param_SourceSelectBlocks or []:
    initSourceSelect(info['instance'], info['sourceCount'])
  
def initSourceSelect(inst, sourceCount):
  name = inst
  title = inst
  group = inst
  
  signal = Event(name, {'title': title, 'group': group, 'order': next_seq(), 'schema': {'type': 'integer'}})
  
  getter = Action('Get ' + name, lambda arg: tcp_request('%s get sourceSelection\n' % (inst), 
                          lambda resp: parseResp(resp, lambda result: signal.emit(int(result)))),
                 {'title': 'Get', 'group': group, 'order': next_seq()})
  
  # safe to use title here remembering within brackets is extraneous
  setter = Action(name, lambda arg: tcp_request('%s set sourceSelection %s\n' % (inst, int(arg)), 
                          lambda resp: parseResp(resp, 
                            lambda result: signal.emit(int(arg)))), # NOTE: uses the original 'arg' here
                  {'title': title, 'group': group, 'schema': {'type': 'integer'}})
  
  for i in range(1, sourceCount+1):
    bindSourceItem(inst, i, setter, signal)
  
  Timer(lambda: getter.call(), random(120,150), random(5,10))
  
def bindSourceItem(inst, i, setter, signal):
  name = '%s %s Selected' % (inst, i)
  title = 'Source %s' % i
  group = inst
  
  selectedSignal = Event(name, {'title': title, 'group': inst, 'order': next_seq(), 'schema': {'type': 'boolean'}})
  
  signal.addEmitHandler(lambda arg: selectedSignal.emitIfDifferent(arg == i))

  def handler(arg):
    if arg == None: # toggle if no arg is given
      setter.call(0 if selectedSignal.getArg() else i)
      
    else:           # set the state
      setter.call(i if arg == True else 0)
    
  togglerOrSetter = Action(name, handler, {'title': title, 'group': inst, 'order': next_seq()})

@after_main
def bindMeterBlocks():
  for info in param_MeterBlocks or []:
    meterType = info['type']
    meterInstance = info['instance']
    for num, name in enumerate(info['names'].split(',')):
      initMeters(meterType, name, meterInstance, num+1)
    
def initMeters(meterType, label, inst, index):
  name = '%s %s' % (inst, index)
  title = '"%s"' % label
  
  if meterType == 'Presence':
    cmd = 'present'
    schema = {'type': 'boolean'}
    
  else:
    cmd = 'level'
    schema = {'type': 'number'}
    
  group = inst

  signal = Event(name, {'title': title, 'group': group, 'order': next_seq(), 'schema': schema})
  
  def handleResult(result):
    if meterType == 'Presence':
      signal.emitIfDifferent(result=='true')
      
    else:
      signal.emit(float(result))
  
  def poll():
    tcp_request('%s get %s %s\n' % (inst, cmd, index), 
                lambda resp: parseResp(resp, handleResult))
  
  # start meters much later to avoid being overwhelmed with feedback
  Timer(poll, 0.2, random(30,45))

# only requests *if ready*
def tcp_request(req, onResp):
    if receivedTelnetOptions:
      tcp.request(req, onResp)

# --- protocol>

 
# <tcp ---

# taken from Tesira help file

receivedTelnetOptions = False
  
def tcp_connected():
  console.info('tcp_connected')
  
  global receivedTelnetOptions
  receivedTelnetOptions = False
  
  tcp.clearQueue()
  
def tcp_received(data):
  log(3, 'tcp_recv [%s] -- [%s]' % (data, data.encode('hex')))
  for c in data:
    handleByte(c)

telnetBuffer = list()
recvBuffer = list()
    
def handleByte(c):
  if len(telnetBuffer) > 0:
    # goes into a TELNET frame
    telnetBuffer.append(c)
    
    if len(telnetBuffer) == 3:
      frame = ''.join(telnetBuffer)
      del telnetBuffer[:]
      telnet_frame_received(frame)
    
  elif c == '\xff':
    # start of TELNET FRAME
    telnetBuffer.append(c)
      
  elif c in ['\r', '\n']:
    # end of a NORMAL msg
    msg = ''.join(recvBuffer).strip()
    del recvBuffer[:]
    
    if len(msg) > 0:
      queue.handle(msg)
    
  else:
    # put all other characters into NORMAL msg
    recvBuffer.append(c)
    
    if len(recvBuffer) > 1024:
      console.warn('buffer too big; dropped; was "%s"' % ''.join(recvBuffer))
      del recvBuffer[:]
    
def telnet_frame_received(data):
  log(2, 'telnet_recv [%s]' % (data.encode('hex')))
  
  # reject all telnet options
  if data[0] == '\xFF':
    if data[1] == '\xFB':  # WILL
      tcp.send('\xFF\xFE%s' % data[2]) # send DON'T
      
    elif data[1] == '\xFD': # DO
      tcp.send('\xFF\xFC%s' % data[2]) # send WON'T
      
def msg_received(data):
  log(2, 'msg_recv [%s]' % (data.strip()))
  
  lastReceive[0] = system_clock()

  if 'Welcome to the Tesira Text Protocol Server...' in data:
    global receivedTelnetOptions
    receivedTelnetOptions = True
  
def tcp_sent(data):
  log(3, 'tcp_sent [%s] -- [%s]' % (data, data.encode('hex')))
  
def tcp_disconnected():
  console.warn('tcp_disconnected')

  global receivedTelnetOptions
  receivedTelnetOptions = False
  
def tcp_timeout():
  console.warn('tcp_timeout; dropping (if connected)')
  tcp.drop()
  
def protocolTimeout():
  console.log('protocol timeout; flushing buffer; dropping connection (if connected)')
  queue.clearQueue()
  del recvBuffer[:]
  telnetBuffer[:]

  global receivedTelnetOptions
  receivedTelnetOptions = False
  
  tcp.drop()

tcp = TCP(connected=tcp_connected, received=tcp_received, sent=tcp_sent, disconnected=tcp_disconnected, timeout=tcp_timeout,
          receiveDelimiters='', sendDelimiters='')

queue = request_queue(timeout=protocolTimeout, received=msg_received)

# --- tcp>


# <logging ---

local_event_LogLevel = LocalEvent({'group': 'Debug', 'order': 10000+next_seq(), 'schema': {'type': 'integer'}})

def warn(level, msg):
  if local_event_LogLevel.getArg() >= level:
    console.warn(('  ' * level) + msg)

def log(level, msg):
  if local_event_LogLevel.getArg() >= level:
    console.log(('  ' * level) + msg)    

# --->


# <status and error reporting ---

local_event_LastCommsErrorTimestamp = LocalEvent({'title': 'Last Comms Error Timestamp', 'group': 'Status', 'order': 99999+next_seq(), 'schema': {'type': 'string'}})

# for comms drop-out
lastReceive = [0]

# roughly, the last contact  
local_event_LastContactDetect = LocalEvent({'group': 'Status', 'order': 99999+next_seq(), 'title': 'Last contact detect', 'schema': {'type': 'string'}})

# node status
local_event_Status = LocalEvent({'group': 'Status', 'order': 99999+next_seq(), 'schema': {'type': 'object', 'properties': {
        'level': {'type': 'integer', 'order': 1},
        'message': {'type': 'string', 'order': 2}}}})
  
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
      if roughDiff < 60:
        message = 'Missing for approx. %s mins' % roughDiff
      elif roughDiff < (60*24):
        message = 'Missing since %s' % previousContact.toString('h:mm:ss a')
      else:
        message = 'Missing since %s' % previousContact.toString('h:mm:ss a, E d-MMM')
      
    local_event_Status.emit({'level': 2, 'message': message})
    
  else:
    # update contact info
    local_event_LastContactDetect.emit(str(now))
    
    # TODO: check internal device status if possible

    local_event_LastContactDetect.emit(str(now))
    local_event_Status.emit({'level': 0, 'message': 'OK'})
    
status_check_interval = 75
status_timer = Timer(statusCheck, status_check_interval)

# --->


# <convenience methods ---

def getOrDefault(value, default):
  return default if value == None or is_blank(value) else value

from java.util import Random
_rand = Random()

# returns a random number between an interval
def random(fromm, to):
  return fromm + _rand.nextDouble()*(to - fromm)

# --->