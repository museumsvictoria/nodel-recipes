'''Extron MVC 121 Plus audio mixer - see recipe for manual URL.'''

# * http://media.extron.com/download/files/userman/68-1937-01_B_MVC_121_Plus_UG_.pdf

param_disabled = Parameter({"title":"Disabled", "group":"Comms", "schema":{"type":"boolean"}})
param_address = Parameter({"title": "Address", "schema": {"type": "string", "hint": "HOST:TCPPORT"}})

local_event_Status = LocalEvent({'group': 'Status', 'order': 9999 + next_seq(), 'schema': {'type': 'object', 'title': 'Status', 'properties': {
      'level': {'type': 'integer', 'order': next_seq(), 'title': 'Level'},
      'message': {'type': 'string', 'order': next_seq(), 'title': 'Message'} }} })

def main():
  afterMain()
  
  if param_disabled == True:
    console.warn('Comms disabled')
  else:
    tcp.setDest(param_address)

# Variable output muting ----

group = 'Variable output'

varOutMuting = Event('Var Out Muting', {'title': 'Muting', 'group': group, 'order': next_seq(), 'schema': {'type': 'boolean'}})

def varOutMute(state):
  
  def handleResponse(resp):
    if resp == 'Amt1': varOutMuting.emit(True)
    elif resp == 'Amt0': varOutMuting.emit(False)
  
  tcp.request('1Z' if state == True else '0Z', handleResponse)

Action('Var Out Muting', varOutMute, {'title': 'Muting', 'group': group, 'order': next_seq(), 'schema': {'type': 'boolean'}})

def poll_varOutMute():
  tcp.request('Z', lambda resp: varOutMuting.emit(True) if resp == 'Amt1' else varOutMuting.emit(False))

Timer(poll_varOutMute, 14.9)


# Variable output volume ----

schema = {'type': 'integer', 'min': 0, 'max': 100, 'format': 'range'}
varOutVolume = Event('Var Out Vol', {'title': 'Vol.', 'group': group, 'order': next_seq(), 'schema': schema})
  
def parseVolumeResp(resp):
  # e.g. Vol51 (volume 51%)
  volPos = resp.find('Vol')
  if volPos >= 0:
    level = int(resp[volPos+3:])
  else:
    level = int(resp)
    
  varOutVolume.emit(level)

varOutVolAction = Action('Var Out Vol', lambda arg: tcp.request('%sV' % arg, parseVolumeResp), {'title': 'Vol.', 'group': group, 'order': next_seq(), 'schema': schema})
varOutVolIncr = Action('Var Out Vol Incr', lambda arg: tcp.request('+V', parseVolumeResp), {'title': 'Incr.', 'group': group, 'order': next_seq()})
varOutVolDecr = Action('Var Out Vol Decr', lambda arg: tcp.request('-V', parseVolumeResp), {'title': 'Decr.', 'group': group, 'order': next_seq()})

def handleNudge(arg):
  if arg == 'Up':
    varOutVolIncr.call()
  elif arg == 'Down':
    varOutVolDecr.call()
    
Action('Var Out Vol Nudge', handleNudge, {'title': 'Nudge', 'group': group, 'order': next_seq(), 'schema': {'type': 'string', 'enum': ['Up', 'Down']}})

Timer(lambda: tcp.request('V', parseVolumeResp), 8.77)


# Input (Mic/Lin) Gain or attenuation levels ----

def bindInputGainControls(name, i):
  group, schema = name, {'type': 'integer', 'min': -24, 'max': 12, 'format': 'range'}
  
  gainEvent = Event('%s Gain' % name, {'title': 'Gain', 'group': group, 'order': next_seq(), 'schema': schema})
  
  def parseGainResp(resp):
    # e.g. "In1 Aud1" (input 1, 1 dB)
    # or   "1"
    pos = resp.find('Aud')
    dB = int(resp) if pos < 0 else int(resp[pos+3:])
    gainEvent.emit(dB)
  
  Action('%s Gain' % name, lambda arg: tcp.request('%s*%sG' % (i, arg), parseGainResp), {'title': 'Gain', 'group': group, 'order': next_seq(), 'schema': schema})
  Action('%s Gain Incr' % name, lambda arg: tcp.request('%s+G' % i, parseGainResp), {'title': 'Incr.', 'group': group, 'order': next_seq()})
  Action('%s Gain Decr' % name, lambda arg: tcp.request('%s-G' % i, parseGainResp), {'title': 'Decr.', 'group': group, 'order': next_seq()})
  
  # poller
  Timer(lambda: tcp.request('%sG' % i, parseGainResp), 5.33 + (next_seq() % 10)/3)

bindInputGainControls('Mic 1', 1)
bindInputGainControls('Mic 2', 2)
bindInputGainControls('Line 3', 3)

ESC = '\x1B'

def bindDSPMute(addr, label):
  group, schema = label, {'type': 'boolean'}
  
  event = Event('%s Muting' % label, {'title': 'Muting', 'group': group, 'order': next_seq(), 'schema': schema})
  
  def parseMutingResp(resp):
    # e.g. DsM%ADDR%*1
    event.emit(resp[resp.rfind('*')+1:] == '1')
  
  Action('%s Muting' % label, lambda arg: tcp.request('%sM%s*%sAU' % (ESC, addr, '1' if arg == True else '0'), parseMutingResp), 
             {'title': 'Gain', 'group': group, 'order': next_seq(), 'schema': schema})
  
  # poller
  Timer(lambda: tcp.request('%sM%sAU' % (ESC, addr), parseMutingResp), 5.33 + (next_seq() % 10)/3)

bindDSPMute('60002', 'Fixed Out L')
bindDSPMute('60003', 'Fixed Out R')
  
# Comms related events for diagnostics ----

local_event_Connected = LocalEvent({'group': 'Comms', 'order': 9999 + next_seq()})
local_event_Received = LocalEvent({'group': 'Comms', 'order': 9999 + next_seq()})
local_event_Sent = LocalEvent({'group': 'Comms', 'order': 9999 + next_seq()})
local_event_Disconnected = LocalEvent({'group': 'Comms', 'order': 9999 + next_seq()})
local_event_Timeout = LocalEvent({'group': 'Comms', 'order': 9999 + next_seq()})

def connected():
  local_event_Connected.emit()
  local_event_Status.emit({'level': 0, 'message': 'OK'})
    
def received(data):
  local_event_Received.emit(data)

def sent(data):
  local_event_Sent.emit(data)
    
def disconnected():
  local_event_Status.emit({'level': 2, 'message': 'Missing'})
  local_event_Disconnected.emit()
  
def timeout():
  local_event_Status.emit({'level': 2, 'message': 'Missing'})
  local_event_Timeout.emit()

tcp = TCP(connected=connected, received=received, sent=sent, disconnected=disconnected, sendDelimiters='\r', receiveDelimiters='\r\n', timeout=timeout)


# customisation ------
def afterMain():
  # create stereo action and event
  event = Event('Fixed Out Muting', {'schema': {'type': 'boolean'}})
  
  # bind to R muting state
  lookup_local_event('Fixed Out R Muting').addEmitHandler(lambda arg: event.emit(arg))
  
  action1 = lookup_local_action('Fixed Out L Muting')
  action2 = lookup_local_action('Fixed Out R Muting')
  Action('Fixed Out Muting', lambda arg: (action1.call(arg), action2.call(arg)), {'schema': {'type': 'boolean'}})

  