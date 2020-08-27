'''
Legacy recipe - works with PM and other Nexia models (default IP is 192.168.1.101)

Use Mk2 recipe if possible.
'''

# TODO:
# - For Maxtrix Mixer blocks, only cross-point muting is done.

TELNET_TCPPORT = 23

param_Disabled = Parameter({'schema': {'type': 'boolean'}})
param_IPAddress = Parameter({'title': 'IP address', 'schema': {'type': 'string'}})

DEFAULT_DEVICE = 1

param_InputBlocks = Parameter({'schema': {'type': 'array', 'items': {'type': 'object', 'properties': {
          'label': {'type': 'string', 'order': 1},
          'device': {'type': 'integer', 'hint': DEFAULT_DEVICE, 'order': 2},
          'instance': {'type': 'integer', 'desc': 'Instance ID or tag', 'order': 3},
          'index': {'type': 'integer', 'desc': 'Input index', 'order': 4}}}}})

param_FaderBlocks = Parameter({'schema': {'type': 'array', 'items': {'type': 'object', 'properties': {
          'label': {'type': 'string', 'order': 1},
          'device': {'type': 'integer', 'hint': DEFAULT_DEVICE, 'order': 2},
          'instance': {'type': 'integer', 'desc': 'Instance ID or tag', 'order': 3},
          'index': {'type': 'integer', 'desc': 'Input index', 'order': 4}}}}})

param_SourceSelectBlocks = Parameter({'schema': {'type': 'array', 'items': {'type': 'object', 'properties': {
          'label': {'type': 'string', 'order': 1},
          'device': {'type': 'integer', 'hint': DEFAULT_DEVICE, 'order': 2},
          'instance': {'type': 'integer', 'desc': 'Instance ID or tag', 'order': 3},
          'sourceCount': {'type': 'integer', 'desc': 'The number of sources being routed', 'order': 4}}}}})

param_MeterBlocks = Parameter({'schema': {'type': 'array', 'items': {'type': 'object', 'properties': {
          'label': {'type': 'string', 'order': 1},
          'type': {'type': 'string', 'enum': ['Peak', 'RMS', 'Presence'], 'order': 2},
          'device': {'type': 'integer', 'hint': DEFAULT_DEVICE, 'order': 3},
          'instance': {'type': 'integer', 'desc': 'Instance ID or tag', 'order': 4},
          'index': {'type': 'integer', 'desc': 'Meter index', 'order': 5}}}}})

param_MatrixMixerBlocks = Parameter({'schema': {'type': 'array', 'items': {'type': 'object', 'properties': {
          'label': {'type': 'string', 'order': 1},
          'device': {'type': 'integer', 'hint': DEFAULT_DEVICE, 'order': 3},
          'instance': {'type': 'integer', 'desc': 'Instance ID or tag', 'order': 4},
          'inputNames': {'type': 'string', 'desc': 'Comma separated list of simple labels', 'order': 5},
          'outputNames': {'type': 'string', 'desc': 'Comma separated list of simple labels', 'order': 6}}}}})

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

def parseResp(resp, onSuccess):
  if resp == '+OK':
    pass
    
  elif '-ERR' in resp:
    console.warn('Got bad resp: %s' % resp)
    return
  
  # any successful resp has its callback called
  onSuccess(resp)

INPUTGAIN_SCHEMA = {'type': 'integer', 'desc': '0, 6, 12, 18, 24, 30, 36, 42, 48, 54, 60, 66'}
  
@after_main
def bindInputs():
  for info in param_InputBlocks or []:
    initNumberValue('Input', 'INPGAIN', info['label'], 
                      getOrDefault(info.get('device'), DEFAULT_DEVICE), 
                      info['instance'], info['index'], isInteger=True)
    
@after_main
def bindFaders():
  for info in param_FaderBlocks or []:
    initNumberValue('Fader', 'FDRLVL', info['label'], 
                      getOrDefault(info.get('device'), DEFAULT_DEVICE), 
                      info['instance'], info['index'])
    
    initBoolValue('Fader Muting', 'FDRMUTE', info['label'], 
                      getOrDefault(info.get('device'), DEFAULT_DEVICE), 
                      info['instance'], info['index'])

@after_main
def bindMatrixMixers():
  for info in param_MatrixMixerBlocks or []:
    for inputNum, inputName in enumerate(info['inputNames'].split(',')):
      for outputNum, outputName in enumerate(info['outputNames'].split(',')):
        initBoolValue('Matrix Mixer Crosspoint Muting', 'MMMUTEXP', 
                          '%s - %s - %s' % (info['label'], inputName.strip(), outputName.strip()),
                          getOrDefault(info.get('device'), DEFAULT_DEVICE), 
                          info['instance'], inputNum+1, index2=outputNum+1)


def initBoolValue(controlType, cmd, label, dev, inst, index1, index2=None):
  if index2 == None:
    name = '%s %sx%sx%s' % (controlType, dev, inst, index1)
  else:
    name = '%s %sx%sx%sx%s' % (controlType, dev, inst, index1, index2)
    
  title = '%s ("%s")' % (name, label)
  group = '%s %s:%s' % (controlType, dev, inst)
  schema = {'type': 'boolean'}
  
  signal = Event(name, {'title': title, 'group': group, 'order': next_seq(), 'schema': schema})
  
  # some cmds take in index1 and index2
  index = index1 if index2 == None else '%s %s' % (index1, index2)
    
  getter = Action('Get ' + name, lambda arg: tcp.request('GET %s %s %s %s\n' % (dev, cmd, inst, index), 
                          lambda resp: parseResp(resp, lambda arg: signal.emit(arg == '1'))),
                 {'title': 'Get', 'group': group, 'order': next_seq()})
  
  setter = Action(name, lambda arg: tcp.request('SET %s %s %s %s %s\n' % (dev, cmd, inst, index, '1' if arg == True else '0'), 
                          lambda resp: parseResp(resp, 
                            lambda result: signal.emit(arg))), # NOTE: uses the original 'arg' here
                  {'title': title, 'group': group, 'order': next_seq(), 'schema': schema})
  
  Timer(lambda: getter.call(), random(120,150), random(10,15))
  
  # and come conveniece derivatives
  
  toggle = Action(name + " Toggle", lambda arg: setter.call(not signal.getArg()), {'title': 'Toggle', 'group': group, 'order': next_seq()})
  
  inverted = Event(name + " Inverted", {'title': 'Muting Inverted', 'group': group, 'order': next_seq(), 'schema': schema})
  signal.addEmitHandler(lambda arg: inverted.emit(not arg))

def initNumberValue(controlType, cmd, label, dev, inst, index1, isInteger=False, index2=None):
  if index2 == None:
    name = '%s %sx%sx%s' % (controlType, dev, inst, index1)
  else:
    name = '%s %sx%sx%sx%s' % (controlType, dev, inst, index1, index2)
    
  title = '%s ("%s")' % (name, label)
  group = '%s %s:%s' % (controlType, dev, inst)
  schema = {'type': 'integer' if isInteger else 'number'}
  
  signal = Event(name, {'title': title, 'group': group, 'order': next_seq(), 'schema': schema})
  
  # some cmds take in index1 and index2
  index = index1 if index2 == None else '%s %s' % (index1, index2)
    
  getter = Action('Get ' + name, lambda arg: tcp.request('GET %s %s %s %s\n' % (dev, cmd, inst, index), 
                          lambda resp: parseResp(resp, lambda arg: signal.emit(int(float(arg)) if isInteger else float(arg)))),
                 {'title': 'Get', 'group': group, 'order': next_seq()})
  
  setter = Action(name, lambda arg: tcp.request('SET %s %s %s %s %s\n' % (dev, cmd, inst, index, arg), 
                          lambda resp: parseResp(resp, 
                            lambda result: signal.emit(arg))), # NOTE: uses the original 'arg' here
                  {'title': title, 'group': group, 'order': next_seq(), 'schema': schema})
  
  Timer(lambda: getter.call(), random(120,150), random(10,15))
  
@after_main
def bindSourceSelects():
  for info in param_SourceSelectBlocks or []:
    initSourceSelect(info['label'], getOrDefault(info.get('device'), DEFAULT_DEVICE), 
                      info['instance'], info['sourceCount'])
  
def initSourceSelect(label, dev, inst, sourceCount):
  name = 'Source Select %sx%s' % (dev, inst)
  title = '%s ("%s")' % (name, label)
  group = '%s %s:%s' % ("Source Select", dev, inst)
  
  signal = Event(name, {'title': title, 'group': group, 'order': next_seq(), 'schema': {'type': 'integer'}})
  
  getter = Action('Get ' + name, lambda arg: tcp.request('GET %s SRCSELSRC %s 1\n' % (dev, inst), 
                          lambda resp: parseResp(resp, lambda result: signal.emit(int(result)))),
                 {'title': 'Get', 'group': group, 'order': next_seq()})
  
  # safe to use title here remembering within brackets is extraneous
  setter = Action(name, lambda arg: tcp.request('SET %s SRCSELSRC %s 1 %s\n' % (dev, inst, int(arg)), 
                          lambda resp: parseResp(resp, 
                            lambda result: signal.emit(int(arg)))), # NOTE: uses the original 'arg' here
                  {'title': title, 'group': group, 'schema': {'type': 'integer'}})
  
  Timer(lambda: getter.call(), random(120,150), random(10,15))


@after_main
def bindMeterBlocks():
  for info in param_MeterBlocks or []:
    initMeters(info['type'], info['label'], getOrDefault(info.get('device'), DEFAULT_DEVICE), 
                     info['instance'], info['index'])
    
def initMeters(meterType, label, dev, inst, index):
  name = '%s Meter %sx%sx%s' % (meterType, dev, inst, index)
  title = '%s ("%s")' % (name, label)
  
  schema = {'type': 'number'}
  
  if meterType == 'Peak':
    cmd = 'PKMTRLVL'
  elif meterType == 'RMS':
    cmd = 'RMSMTRLVL'
  elif meterType == 'Presence':
    cmd = 'SPMTRSTATE'
    schema['type'] = 'boolean'
    
  group = '%s Meter %s:%s:%s' % (meterType, dev, inst, index)

  signal = Event(name, {'title': title, 'group': group, 'order': next_seq(), 'schema': schema})
  
  def handleResult(result):
    if meterType == 'Presence':
      signal.emit(result == '1')
      
    else:
      signal.emit(float(result))
  
  def poll():
    tcp.request('GET %s %s %s %s\n' % (dev, cmd, inst, index), 
                lambda resp: parseResp(resp, handleResult))
  
  Timer(poll, 0.4, random(10,15))
    
  
# FDRLVL

  
  

# --- protocol>

 
# <tcp ---
  
TELNET_ECHO_OFF = '\xFF\xFE\x01'  
  
def tcp_connected():
  console.info('tcp_connected')
  tcp.clearQueue()
  
def tcp_received(data):
  log(3, 'tcp_recv [%s]' % data)
  
  # indicate a parsed packet (for status checking)
  lastReceive[0] = system_clock()
  
  if data == 'Welcome to the Biamp Telnet server':
    # immediately turn off local echo
    tcp.send(TELNET_ECHO_OFF)
    return
  
def tcp_sent(data):
  log(3, 'tcp_sent [%s]' % data)
  
def tcp_disconnected():
  console.warn('tcp_disconnected')
  
def tcp_timeout():
  console.warn('tcp_timeout')

tcp = TCP(connected=tcp_connected, received=tcp_received, sent=tcp_sent, disconnected=tcp_disconnected, timeout=tcp_timeout,
         sendDelimiters='')

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