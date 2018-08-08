"Extron  IN1606 or IN1608 Presentation switcher"

# Useful resources
#  * Setup guide 
#     - http://media.extron.com/download/files/userman/68-1916-51_A.pdf
#     
#  * User guide   
#     - http://media.extron.com/download/files/userman/68-2290-01_F.pdf


param_ipAddress = Parameter({"title":"IP address", "schema":{"type":"string", "description":"The IP description.", "desc":"The IP address to connect to.", "hint":"192.168.100.1"}})
DEFAULT_PORT = 23
param_port = Parameter({"title":"Port", "schema":{"type":"integer", "description":"The TCP port.", "hint":DEFAULT_PORT}})

MAX_INPUT = 6
param_maxInput = Parameter({'schema': {'type': 'integer', 'hint': MAX_INPUT}})

local_event_Greeting = LocalEvent({'title': 'Greeting', 'group': 'Greeting', 'order': 1, 'schema' : {'type' : 'string'}})
local_event_GreetingFirmwareDate = LocalEvent({'title': 'Firmware date', 'group': 'Greeting', 'order': 2, 'schema' : {'type' : 'string'}})

ESC = '\x1b'

@before_main
def initRuntimeParams():
  global INPUT_COUNT
  INPUT_COUNT = param_maxInput or MAX_INPUT
  
@before_main
def initInputLabels():
  for i in range(1, INPUT_COUNT+1):
    Event('Input %s Label' % i, {'group': 'Input', 'order': next_seq(), 'schema': {'type': 'string'}})

@before_main
def bindAfterLastPoll():
  lookup_local_event('Input %s Label' % INPUT_COUNT).addEmitHandler(lambda arg: lateBindOnce())
    
# this is done after the last label is polled
def lateBindOnce():
  if lookup_local_event('Video Input') != None: # only do once
    return
  
  INPUT_LISTS = ['Input %s' % i for i in range(1, INPUT_COUNT + 1)]
  
  videoInputSignal = Event('Video Input', 
                           {'group': 'Input', 'order': next_seq(), 'schema': {'type': 'string', 'enum': INPUT_LISTS}})
  videoInputSignal.addEmitHandler(lambda arg: [lookup_local_event('Input %s Video' % i).emit(arg == 'Input %s' % i) for i in range(1, INPUT_COUNT+1)])
  
  videoInputAction = Action('Video Input', lambda arg: lookup_local_action('%s Video' % arg).call(), 
                            {'group': 'Input', 'order': next_seq(), 'schema': {'type': 'string', 'enum': INPUT_LISTS}})
  
  audioInputSignal = Event('Audio Input', 
                           {'group': 'Input', 'schema': {'type': 'string', 'enum': INPUT_LISTS}})
  audioInputSignal.addEmitHandler(lambda arg: [lookup_local_event('Input %s Audio' % i).emit(arg == 'Input %s' % i) for i in range(1, INPUT_COUNT+1)])
  
  audioInputAction = Action('Audio Input', lambda arg: lookup_local_action('%s Audio' % arg).call(), 
                            {'group': 'Input', 'order': next_seq(), 'schema': {'type': 'string', 'enum': INPUT_LISTS}})
  
  # both
  inputAction = Action('Input', lambda arg: lookup_local_action('%s' % arg).call(), 
                            {'group': 'Input', 'order': next_seq(), 'schema': {'type': 'string', 'enum': INPUT_LISTS}})
  
  # initialise all inputs
  for i in range(1, INPUT_COUNT+1):
    bindInput(i)
    
  # signal presence in one hit
  def handleSignalResp(arg):
    # e.g. 0*0*0*0*0*0*0*0
    if not (arg.startswith('0') or arg.startswith('1')):
      console.warn('Unexpected signal_resp; got [%s]' % arg)
      return
      
    for i, state in enumerate(arg.split('*')):
      # state is '1' or '0'
      e = lookup_local_event('Input %s Signal' % (i+1))
      if e: e.emit(state == '1')
      
  getAudio = Action('Get Audio Input', 
                    lambda ignore: tcp.request('$', lambda resp: lookup_local_event('Audio Input').emit('Input %s' % int(resp))))
  Timer(lambda: getAudio.call(), 5.33 + (next_seq() % 10)/3)  
  
  getVideo = Action('Get Video Input', 
                    lambda ignore: tcp.request('$', lambda resp: lookup_local_event('Video Input').emit('Input %s' % int(resp))))
  Timer(lambda: getVideo.call(), 5.33 + (next_seq() % 10)/3)
    
  getSignal = Action('Get Signal', lambda ignore: tcp.request(ESC+'0LS', handleSignalResp))
  Timer(lambda: getSignal.call(), 5.33 + (next_seq() % 10)/3)
  
  # output video muting
  outputVideoMutingSignal = Event('Output Video Muting', {'group': 'Video Output', 'order': next_seq(), 'schema': {'type': 'boolean'}})
  
  def handleVideoMuteResp(arg):
    if arg == 'Vmt1':
      outputVideoMutingSignal.emit(True)
    elif arg == 'Vmt0':
      outputVideoMutingSignal.emit(False)
  
  setOutputMute = Action('Output Video Muting',
                         lambda arg: tcp.request('1B' if arg else '0B', handleVideoMuteResp), 
                         {'group': 'Video Output', 'order': next_seq(), 'schema': {'type': 'boolean'}})
  
  def pollOutputMuting():
    tcp.request('B', lambda resp: outputVideoMutingSignal.emit(False if resp == '0' else True))
    
  Timer(pollOutputMuting, 10)
    
  
def bindInput(inputNum):
  inputName = 'Input %s' % inputNum
  
  labelSignal = lookup_local_event('Input %s Label' % inputNum)
  label = labelSignal.getArg() if labelSignal != None else None
  label = '"%s"' % label if label != None else inputName
  
  audioSelected = Event('%s Audio' % inputName, {'title': '%s Audio' % label, 'group': 'Inputs Audio', 'order': next_seq(), 'schema': {'type': 'boolean'}})
  
  videoSelected = Event('%s Video' % inputName, {'title': '%s Video' % label, 'group': 'Inputs Video', 'order': next_seq(), 'schema': {'type': 'boolean'}})
  
  def handleResp(resp):
    # e.g. In1 Aud
    # or   In1 RGB
    # or   In1 All     
    #      (sometimes uses leading zero e.g. In01 XXX)
    if resp.startswith('In%s' % inputNum) or resp.startswith('In0%s' % inputNum):
      AUDIO = 'Aud' in resp or 'All' in resp
      VIDEO = 'RGB' in resp or 'All' in resp
      
      if not AUDIO and not VIDEO:
        console.warn('Neither AUDIO nor VIDEO was flagged in response')
        return
      
      if AUDIO:
        lookup_local_event('Audio Input').emit('Input %s' % inputNum)
        
      if VIDEO:
        lookup_local_event('Video Input').emit('Input %s' % inputNum)
        
    else:
      console.warn('Unexpected audio_resp: [%s]' % resp)
    
  selectAudio = Action('%s Audio' % inputName, 
                       lambda ignore: tcp.request('%s$' % inputNum, handleResp), 
                       {'title': '%s Audio' % label, 'group': 'Input Audio', 'order': next_seq()})
  
  selectVideo = Action('%s Video' % inputName, 
                       lambda ignore: tcp.request('%s&' % inputNum, handleResp), 
                       {'title': '%s Video' % label, 'group': 'Inputs Video', 'order': next_seq()})
  
  selectBoth = Action('%s' % inputName, 
                       lambda ignore: tcp.request('%s!' % inputNum, handleResp), 
                       {'title': label, 'group': 'Input (A & V)', 'order': next_seq()})
  
  signal = Event('%s Signal' % inputName, {'title': label, 'group': 'Inputs Signal', 'order': next_seq(), 'schema': {'type': 'boolean'}})
  
def main():
    address = '%s:%s' % (param_ipAddress , param_port or DEFAULT_PORT)
    console.info('Will connect to "%s"' % address)
    tcp.setDest(address)

# this is called once on TCP connect
def pollLabel(i):
  log(1, 'pollLabel %s' % i)
  
  tcp.request(ESC+'%sNI' % i, lambda arg: lookup_local_event('Input %s Label' % i).emit(arg))

# AUDIO GROUPS:
# (taken from manual, page 46)
#
# SPECIAL GROUPS (Group - 'GRPM' data in data)
# 1 = program volume
# 2 = program mute
# 3 = mic volume
# 4 = mic mute
# 5 = bass
# 6 = treble
# 7 = output mute
# 8 = variable volume

# DSP  groups (DSP - just 'G' or 'M' in data)
# Gain or mute control 
# 40100 = mic 1 (mix volume only)
# 40000 = mic 1 (mute only)
# 40101 = mic 2 (mix volume only)
# 40001 = mic 2 (mute only)
# 60000 = output 1
# 60002 = output 2
# 60004 = variable output L
# 60005 = variable output R
# 60006 = digital output L
# 60007 = digital output R
# 60008 = amplified output L (stereo models) or amplified output (mono models)
# 60009 = amplified output R (stereo models)

@after_main
def bindAllAudioGroups():
  # dsp style (legacy?)
  bindGroupControl('Mic 1', 40100, 'DSP Gain')
  bindGroupControl('Mic 1', 40000, 'DSP Muting')
  bindGroupControl('Mic 2', 40101, 'DSP Gain')
  bindGroupControl('Mic 2', 40001, 'DSP Muting')
  bindGroupControl('Output 1', 60000, 'DSP Gain')
  bindGroupControl('Output 2', 60002, 'DSP Gain')
  bindGroupControl('Variable Output L', 60004, 'DSP Gain')
  bindGroupControl('Variable Output R', 60005, 'DSP Gain')
  bindGroupControl('Digital Output L', 60006, 'DSP Gain')
  bindGroupControl('Digital Output R', 60008, 'DSP Gain')
  bindGroupControl('Amplified Output L', 60008, 'DSP Gain')
  bindGroupControl('Amplified Output R', 60009, 'DSP Gain')
  
  # group style
  bindGroupControl('Program', 1, 'Group Gain')
  bindGroupControl('Program', 2, 'Group Muting')
  bindGroupControl('Mic', 3, 'Group Gain')
  bindGroupControl('Mic', 4, 'Group Muting')
  bindGroupControl('Bass', 5, 'Group Gain')
  bindGroupControl('Treble', 6, 'Group Gain')
  bindGroupControl('Output', 7, 'Group Muting') # these look odd, by 
  bindGroupControl('Variable', 8, 'Group Gain') # in manual these *are* mute vs gain

def bindGroupControl(name, i, typee):
  group = name
  
  if 'Gain' in typee:
    schema = {'type': 'integer', 'min': -50, 'max': 12, 'format': 'range'}
  
    gainEvent = Event('%s Gain' % name, {'title': 'Gain', 'group': '"%s"' % group, 'order': next_seq(), 'schema': schema})
  
    def parseGainResp(resp):
      log(2, 'parse_gain_resp: "%s" %s #%s resp:[%s]' % (name, typee, i, resp))
      
      # e.g. "GrpmD02*-00293"
      # or   "-00293"
      if resp.startswith('Grpm') or resp.startswith('Dsg'):
        dB = parseInt(resp[resp.find('*')+1:])/10.0
      else:
        dB = parseInt(resp)/10.0
      
      gainEvent.emit(dB)
    
    # e.g. group 2, -29.3 dB:
    #      "\x1BD2*-293GRPM"
    def onGain(arg):
      if typee.startswith('Group'):
        tcp_request(ESC+'D%s*%sGRPM' % (i, arg*10), parseGainResp)
      elif typee == 'DSP Gain':
        tcp_request(ESC+'G%s*%sAU' % (i, arg*10), parseGainResp)
      
    Action('%s Gain' % name, onGain, {'title': 'Gain', 'group': '"%s"' % group, 'order': next_seq(), 'schema': schema})
  
    # poller
    def onPoll():
      if typee.startswith('Group'):
        tcp_request(ESC+'D%sGRPM' % i, parseGainResp)
      elif typee.startswith('DSP'):
        tcp_request(ESC+'G%sAU' % i, parseGainResp)
        
    Timer(onPoll, 5.33 + (next_seq() % 10)/3)
    
  elif 'Muting' in typee:
    schema = {'type': 'boolean'}
  
    mutingEvent = Event('%s Muting' % name, {'title': 'Muting', 'group': '"%s"' % group, 'order': next_seq(), 'schema': schema})
  
    def parseMuteResp(resp):
      log(3, 'parse_mute_resp: "%s" %s #%s resp:[%s]' % (name, typee, i, resp))
      # e.g. GrpmD1*+00001
      # or   GrpmD1*+00000
      if resp.startswith('Grpm') or resp.startswith('Dsm'):
        state = parseInt(resp[resp.find('*')+1:]) == 1
      else:
        state = parseInt(resp) == 1
      
      mutingEvent.emit(state)
  
    # muting
    def onMute(arg):
      if typee.startswith('Group'):
        tcp_request(ESC+'D%s*%sGRPM' % (i, '1' if arg == True else '0'), parseMuteResp)
      elif typee.startswith('DSP'):
        tcp_request(ESC+'M%s*%sAU' % (i, '1' if arg == True else '0'), parseMuteResp)
      
    Action('%s Muting' % name, onMute, {'title': 'Muting', 'group': '"%s"' % group, 'order': next_seq(), 'schema': schema})
    
    def onPoll():
      if typee.startswith('Group'):
        tcp_request(ESC+'D%sGRPM' % i, parseMuteResp)
      elif typee == 'DSP Gain':
        tcp_request(ESC+'M%sAU' % i, parseMuteResp)

    # poller
    Timer(onPoll, 5.33 + (next_seq() % 10)/3)
  

# TCP

local_event_CommsState = LocalEvent({'group': 'Comms', 'schema': {'type': 'string'}})
local_event_CommsTimeout = LocalEvent({'group': 'Comms'})

def connected():
  console.info('TCP connected')
  local_event_CommsState.emit('Connected')
    
  tcp.receive(lambda resp: local_event_Greeting.emit(resp))
  tcp.receive(lambda resp: local_event_GreetingFirmwareDate.emit(resp))
  
  # set verbose mode to get full-duplex feedback (default for RS232 not TCP)
  tcp.request(ESC+'1CV', lambda resp: '' if resp.lower().startswith('vrb1') else console.error('Was not able to set verbose level; driver may not be reliable'))
  
  for i in range(1, INPUT_COUNT+1):
    pollLabel(i)
  
  readyToSend[0] = True
  
def tcp_request(arg, resp):
  if not readyToSend[0]:
    raise Exception('Not ready to send')
    
  tcp.request(arg, resp)
    
def received(data):
  log(3, 'tcp_recv [%s]' % data)
  lastReceive[0] = system_clock()

def sent(data):
  log(3, 'tcp_send [%s]' % data)

readyToSend = [False]
  
def do_send(data):
  if not readyToSend[0]:
    raise Exception('Not ready to send')
    
def disconnected():
  console.warn('TCP disconnected')
  local_event_CommsState.emit('Disconnected')
  
  readyToSend[0] = False
    
def timeout():
  local_event_CommsTimeout.emit()
  tcp.drop()
  tcp.clearQueue()
  
tcp = TCP(connected=connected, 
          received=received,
          sent=sent, 
          disconnected=disconnected,
          sendDelimiters='\r\n', receiveDelimiters='\r\n', 
          timeout=timeout)

# STATIC CONVENIENCE
def parseInt(s):
  '''For Extron responses, parses "+0000" or "-000.1" safely'''
  return int(s[1:]) if s.startswith('+') else int(s)


ERROR_CODES = { 
  'E01': 'Invalid input number',
  'E10': 'Invalid command',
  'E11': 'Invalid present number',
  'E13': 'Invalid port number',
  'E14': 'Not valid for this configuration',
  'E18': 'Invalid command for signal type',
  'E22': 'Busy',
  'E24': 'Privilege violation',
  'E25': 'Device not present',
  'E26': 'Maximum number of connections exceeded',
  'E28': 'Bad filename of file not found'
}


# status ---

local_event_Status = LocalEvent({'title': 'Status', 'order': 9990, "schema": { 'title': 'Status', 'type': 'object', 'properties': {
        'level': {'title': 'Level', 'order': next_seq(), 'type': 'integer'},
        'message': {'title': 'Message', 'order': next_seq(), 'type': 'string'}
    } } })

# for status checks

lastReceive = [0]

# roughly, the last contact  
local_event_LastContactDetect = LocalEvent({'group': 'Status', 'title': 'Last contact detect', 'schema': {'type': 'string'}})
  
def statusCheck():
  # lampUseHours = local_event_LampUseHours.getArg() or 0
  
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
    return
    
  else:
    local_event_Status.emit({'level': 0, 'message': 'OK'})
  
  local_event_LastContactDetect.emit(str(now))  
  
status_check_interval = 75
status_timer = Timer(statusCheck, status_check_interval)


# <logging ---

local_event_LogLevel = LocalEvent({'group': 'Debug', 'order': 10000+next_seq(), 'schema': {'type': 'integer'}})

def warn(level, msg):
  if local_event_LogLevel.getArg() >= level:
    console.warn(('  ' * level) + msg)

def log(level, msg):
  if local_event_LogLevel.getArg() >= level:
    console.log(('  ' * level) + msg)    

# --->
