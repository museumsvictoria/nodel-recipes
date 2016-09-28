'''Extron DTP switch - see http://media.extron.com/download/files/userman/68-2349-01_C.pdf'''

param_ipAddress = Parameter({"desc":"The IP address to connect to.","schema":{"type":"string"},"value":"192.168.100.1","title":"Address","order":0})

param_inputs = Parameter({"title": "Inputs",
                       "schema": { "type": "array", "title": "Inputs", 
                                   "items": {
                                       "type": "object",
                                       "title": "Input",        
                                       "properties": { 
                                           "num": { "type": "integer", "title": "Number", "order": 0 },          
                                           "name": { "type": "string", "title": "Name", "order": 1 },
                                           "noAudio": { "type": "boolean", "title": "No audio?", 'order': 2},
                                           "noVideo": { "type": "boolean", "title": "No video?", 'order': 3}
                                       } } } } )

param_outputs = Parameter({"title": "Outputs",
                       "schema": { "type": "array", "title": "Outputs", 
                                   "items": {
                                       "type": "object",
                                       "title": "Output",
                                       "properties": { 
                                           "num": { "type": "integer", "title": "Number", "order": 0 },          
                                           "name": { "type": "string", "title": "Name", "order": 1 },
                                           "noAudio": { "type": "boolean", "title": "No audio?", 'order': 2},
                                           "noVideo": { "type": "boolean", "title": "No video?", 'order': 3}
                                       } } } } )

local_event_SystemFirmware = LocalEvent({'group': 'System', 'title': 'Firmware', 'order': next_seq(), 'schema': {'type': 'string'}})
local_event_IntroGreeting = LocalEvent({'group': 'System', 'title': 'Greeting', 'order': next_seq(), 'schema': {'type': 'string'}})
local_event_IntroDate = LocalEvent({'group': 'System', 'title': 'GreetingDate', 'order': next_seq(), 'schema': {'type': 'string'}})

callbacksByToken = {}
inputNamesByNumber = {}

audioOutputSignalsByNumber = {}
videoOutputSignalsByNumber = {}

audioTieSignals = {}
videoTieSignals = {}

def connected():
  print 'connected'
  
  # Over direct TCP might receive:
  #   "Copyright 2015, Extron Electronics, DTPCP84, V1.02, 60-1368-01"
  #   "Wed, 21 Sep 2016 16:39:23"
  #
  # over serial, won't receive anything
  
  timer_poller.start()
  
  # to avoid interference with the greeting, delay start
  def afterDelay():
    # set up verbose mode to keep track of updates
    tcp.request('\x1B1CV', lambda resp: console.log('Verbose mode response %s' % resp)), 5
    sync_all_ties()
  
  call_safe(afterDelay, 6)

def received(data):
  print 'received: [%s]' % data
  
  # slurp the introduction and firmware date first
  if 'Copyright' in data:
    local_event_IntroGreeting.emit(data)
    tcp.receive(lambda resp: local_event_IntroDate.emit(resp)) 
    return
  
  if data.startswith('Out'):
    parseTieFeedback(data)
    return
  
  for token in callbacksByToken:
    if token in data:
      callback = callbacksByToken[token]
      callback(data)      
  
def sent(data):
  print 'sent: [%s]' % data
  
def disconnected():
  print 'disconnected'
  timer_poller.stop()
  
def timeout():
  console.warn('TCP timeout')

tcp = TCP(connected=connected, 
          received=received, 
          sent=sent, 
          disconnected=disconnected, 
          timeout=timeout, 
          sendDelimiters='\r\n', 
          receiveDelimiters='\r\n')

def handle_keepalive():
  tcp.send('q')

def main(arg = None):
  print 'Nodel script started.'
  
  if len(param_ipAddress or '') == 0:
    console.warn('No IP address has been configured; cannot start')
    return
  
  else:
    tcp.setDest('%s:23' % param_ipAddress)
  
  initInputsTable()
  
  # init audio groups
  for groupInfo in param_groups or []:
    bindGroupControl(groupInfo['name'], groupInfo['number'], groupInfo['type'])  
  
  bindAllNamedTies()  
  
def initInputsTable():
  if param_inputs == None or len(param_inputs) == 0:
    console.warn('Note: no inputs configured')
    return
  
  for input in param_inputs:
    inputNamesByNumber[input['num']] = input['name']
    
  inputNamesByNumber[0] = 'mute'
  
def bindAllNamedTies():
  if param_outputs == None or len(param_outputs) == 0:
    console.warn('Note: no outputs configured')
    return  
  
  for output in param_outputs:
    bindOutput(output)
    
    # set up interlock for every 
    audioInterlock = list()
    videoInterlock = list()
    
    # "mute" input
    bindInputToOutput(0, output, audioInterlock, videoInterlock)
    
    for input in param_inputs:
      bindInputToOutput(input, output, audioInterlock, videoInterlock)
      
def bindOutput(output):
  outputNum = output['num']
  outputName = output['name']
  outputLabel = outputNum
  outputNoAudio = output['noAudio']
  outputNoVideo = output['noVideo']
  
  title = '"%s"' % outputName
  
  eventSchema = {'type': 'object', 'title': 'State', 'properties': {
      'input': {'type': 'integer', 'title': 'Input', 'order': 1},
      'name': {'type': 'string', 'title': 'Name', 'order': 2}}}
  
  actionSchema = {'type': 'integer'}

  if not outputNoAudio:
    name = 'Output %s audio' % outputNum
    group = '"%s" output (audio)' % outputName
    event = Event(name, {'title': 'State', 'group': group, 'order': next_seq(), 'schema': eventSchema})
    numEvent = Event('%s input num' % name, {'title': 'Input num', 'group': group, 'order': next_seq(), 'schema': {'type': 'integer'}})
    
    audioOutputSignalsByNumber[outputNum] = (event, numEvent)
    
    def audioHandler(arg=None):
      performTie(int(arg), outputNum, 'audio')
      
    action = Action(name, audioHandler, {'title': 'Switch', 'group': group, 'order': next_seq(), 'schema': actionSchema})
    
  if not outputNoVideo:
    name = 'Output %s video' % outputNum
    group = '"%s" output (video)' % outputName
    event = Event(name, {'title': 'State', 'group': group, 'order': next_seq(), 'schema': eventSchema})
    numEvent = Event('%s input num' % name, {'title': 'Input num', 'group': group, 'order': next_seq(), 'schema': {'type': 'integer'}})                     
    
    videoOutputSignalsByNumber[outputNum] = (event, numEvent)
    
    def videoHandler(arg=None):
      performTie(int(arg), outputNum, 'video')
      
    action = Action(name, videoHandler, {'title': 'Switch', 'group': group, 'order': next_seq(), 'schema': actionSchema})
    
  if not outputNoAudio and not outputNoVideo:
    name = 'Output %s' % outputNum
    group = '"%s" output' % outputName
    
    def handler(arg=None):
      performTie(int(arg), outputNum)
      
    action = Action(name, handler, {'title': 'Switch', 'group': group, 'order': next_seq(), 'schema': actionSchema})  
      
def bindInputToOutput(input, output, audioInterlock, videoInterlock):
  if input == 0:
    inputNum = 0
    inputName = '(mute)'
    inputLabel = 'Mute'
    inputNoAudio = False
    inputNoVideo = False
  else:
    inputNum = input['num']
    inputName = input['name']
    inputLabel = inputNum
    inputNoAudio = input['noAudio']
    inputNoVideo = input['noVideo']
  
  outputNum = output['num']
  outputName = output['name']
  outputLabel = outputNum
  outputNoAudio = output['noAudio']
  outputNoVideo = output['noVideo']
  
  console.info('Binding input:[%s: noAudio:%s, noVideo:%s], output:[%s: noAudio:%s, noVideo:%s]' %
              (inputName, inputNoAudio, inputNoVideo, outputName, outputNoAudio, outputNoVideo))
  
  if inputNoAudio != True and outputNoAudio != True:
    # offer audio ties
    group = '"%s" output (audio)' % outputName
    tieName = 'Input %s Output %s audio' % (inputLabel, outputLabel)
    tieLabel = '"%s"' % inputName
    
    audioEvent = Event(tieName, {'title': tieLabel, 'group': group, 'order': next_seq(), 'schema': {'type': 'boolean'}})
    audioInterlock.append(audioEvent)
    audioTieSignals['Output:%s Input:%s' % (inputNum, outputNum)] = {'event': audioEvent, 'interlock': audioInterlock}
    
    def audioHandler(arg=None):
      performTie(inputNum, outputNum, 'audio')
      
    audioAction = Action(tieName, audioHandler, {'title': tieLabel, 'group': group, 'order': next_seq()})
    
  if inputNoVideo != True and outputNoVideo != True:
    # offer video ties
    group = '"%s" output (video)' % outputName
    tieName = 'Input %s Output %s video' % (inputLabel, outputLabel)
    tieLabel = '"%s"' % inputName
    
    videoEvent = Event(tieName, {'title': tieLabel, 'group': group, 'order': next_seq(), 'schema': {'type': 'boolean'}})
    videoInterlock.append(videoEvent)
    videoTieSignals['Output:%s Input:%s' % (inputNum, outputNum)] = {'event': videoEvent, 'interlock': videoInterlock}
    
    def videoHandler(arg=None):
      performTie(inputNum, outputNum, 'video')
      
    videoAction = Action(tieName, videoHandler, {'title': tieLabel, 'group': group, 'order': next_seq()})    
  
  if inputNoVideo != True and outputNoVideo != True and inputNoAudio != True and outputNoAudio != True:
    # offer audio/video ties
    group = '%s output' % outputName
    tieName = 'Input %s Output %s both' % (inputLabel, outputLabel)
    tieLabel = 'Tie "%s"' % inputName
  
    def handler(arg=None):
      performTie(inputNum, outputNum)
    
    action = Action(tieName, handler, {'title': tieLabel, 'group': group, 'order': next_seq()})
    
def handle_polltimer():
  # if nothing else, query the firmware
  tcp.request('q', lambda arg: local_event_SystemFirmware.emitIfDifferent(arg))
  
  #tcp.request('\x1BD1GRPM', lambda resp: handleProgramVolFeedback(pollValue=resp))
  
timer_poller = Timer(handle_polltimer, 10)

def sync_all_ties():
  for output in param_outputs:
    syncTie(output['num'])
      
def syncTie(outputNum):
  tcp.request('%s%%' % outputNum, lambda resp: handleTieFeedback(False, True, int(resp), outputNum))
  tcp.request('%s$' % outputNum, lambda resp: handleTieFeedback(True, False, int(resp), outputNum))

def local_action_Tie(arg=None):
  """{"group": "Ties", "title": "Tie A/V", "schema": { "title": "Tie", "type": "object", "properties":
       { "input": { "type": "integer", "title": "Input" },
         "output": { "type": "integer", "title": "Output" } } } }"""
  performTie(arg['input'], arg['output'])

def local_action_TieVideo(arg=None):
  """{"group": "Ties", "title": "Tie video", "schema": { "title": "Tie", "type": "object", "properties":
       { "input": { "type": "integer", "title": "Input" },
         "output": { "type": "integer", "title": "Output" } } } }"""
  performTie(arg['input'], arg['output'], av='video')
  
def local_action_TieAudio(arg=None):
  """{"group": "Ties", "title": "Tie audio", "schema": { "title": "Tie", "type": "object", "properties":
       { "input": { "type": "integer", "title": "Input" },
         "output": { "type": "integer", "title": "Output" } } } }"""
  performTie(arg['input'], arg['output'], av='audio')

# ('av' can be 'video', 'audio' or 'both', None, etc.)
def performTie(input, output, av=None):
  if av == 'video':
  	tcp.request('%s*%s%%' % (input, output), parseTieFeedback)
    
  elif av == 'audio':
    tcp.request('%s*%s$' % (input, output), parseTieFeedback)
    
  else:
    # tie both
    tcp.request('%s*%s!' % (input, output), parseTieFeedback)

def parseTieFeedback(arg):
  print 'ParseTieFeedback: [%s]' % arg
  
  # examples:
  # Out04 In01 Vid    or
  # Out08 In01 All    or
  # Out08 In01 Aud
  
  if 'All' in arg:
    audio = True
    video = True
  
  elif 'Aud' in arg:
    audio = True
    video = False
  
  elif 'Vid' in arg:
    audio = False
    video = True
  
  else:
    console.info('Unknown tie type')
    return
    
  o = -1
  i = -1
    
  for part in arg.split(' '):
    if part.startswith('Out'):
      o = int(part[3:])
    elif part.startswith('In'):
      i = int(part[2:])
      
  if o < 0 or i < 0:
    console.warn('Excepted tie feedback')
    return
  
  handleTieFeedback(audio, video, i, o)
  
def handleTieFeedback(audio, video, i, o):
  console.info('Handling tie feedback: %s, %s, %s, %s' % (audio, video, i, o))
  
  # handle direct output state
  event = None
  if audio:
    event, numEvent = audioOutputSignalsByNumber.get(o, (None, None))
    if event != None:
      event.emit({'input': i, 'name': inputNamesByNumber.get(i)}) # emit full state
      numEvent.emit(i) # and emit input number
     
  if video:
    event, numEvent = videoOutputSignalsByNumber.get(o, (None, None))
    if event != None:
      event.emit({'input': i, 'name': inputNamesByNumber.get(i)}) # emit full state
      numEvent.emit(i) # and emit input number
    
  
  # lookup specific tie event info
  key = 'Output:%s Input:%s' % (i, o)
  
  if audio:
    eventInfo = audioTieSignals.get(key)
    if eventInfo != None:
      event = eventInfo['event']
      interlock = eventInfo['interlock']
    
      for other in interlock:
        if other == event:
          event.emitIfDifferent(True)
        else:
          other.emitIfDifferent(False)
        
  if video:
    eventInfo = videoTieSignals.get(key)
    if eventInfo != None:
      event = eventInfo['event']
      interlock = eventInfo['interlock']
    
      for other in interlock:
        if other == event:
          event.emitIfDifferent(True)
        else:
          other.emitIfDifferent(False)
          
          
# volume groups
param_groups = Parameter({'title': 'Groups', 'schema': {'type': 'array', 'items': {
        'type': 'object', 'properties': {
          'name': {'type': 'string', 'title': 'Name', 'order': 1},
          'number': {'type': 'integer', 'title': 'Group number', 'order': 2},
          'type': {'type': 'string','title': 'Type', 'enum': ['Gain', 'Muting'], 'order': 3}
  }}}})

def bindGroupControl(name, i, typee):
  group = name
  
  if typee == 'Gain':
    schema = {'type': 'integer', 'min': -50, 'max': 12, 'format': 'range'}
  
    gainEvent = Event('%s Gain' % name, {'title': 'Gain', 'group': '"%s"' % group, 'order': next_seq(), 'schema': schema})
  
    def parseGainResp(resp):
      # e.g. "GrpmD02*-00293"
      # or   "-00293"
      if resp.startswith('Grpm'):
        dB = parseInt(resp[resp.find('*')+1:])/10.0
      else:
        dB = parseInt(resp)/10.0
      
      gainEvent.emit(dB)
    
    # e.g. group 2, -29.3 dB:
    #      "\x1BD2*-293GRPM"
    Action('%s Gain' % name, lambda arg: tcp.request('\x1BD%s*%sGRPM' % (i, arg*10), parseGainResp), {'title': 'Gain', 'group': '"%s"' % group, 'order': next_seq(), 'schema': schema})
  
    # poller
    Timer(lambda: tcp.request('\x1BD%sGRPM' % i, parseGainResp), 5.33 + (next_seq() % 10)/3)
    
  elif typee == 'Muting':
    schema = {'type': 'boolean'}
  
    mutingEvent = Event('%s Muting' % name, {'title': 'Muting', 'group': '"%s"' % group, 'order': next_seq(), 'schema': schema})
  
    def parseMuteResp(resp):
      # e.g. GrpmD1*+00001
      # or   GrpmD1*+00000
      if resp.startswith('Grpm'):
        state = parseInt(resp[resp.find('*')+1:]) == 1
      else:
        state = parseInt(resp) == 1
      
      mutingEvent.emit(state)
  
    # muting
    Action('%s Muting' % name, lambda arg: tcp.request('\x1BD%s*%sGRPM' % (i, '1' if arg == True else '0'), parseMuteResp), 
           {'title': 'Muting', 'group': '"%s"' % group, 'order': next_seq(), 'schema': schema})

    # poller
    Timer(lambda: tcp.request('\x1BD%sGRPM' % i, parseMuteResp), 5.33 + (next_seq() % 10)/3)

def parseInt(s):
  '''For Extron responses, parses "+0000" or "-000.1" safely'''
  return int(s[1:]) if s.startswith('+') else int(s)
                 
def log(arg):
  console.log(arg)
