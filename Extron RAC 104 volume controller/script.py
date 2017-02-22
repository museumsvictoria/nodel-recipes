'''Extron RAC volume and tone controller - see recipe for manual URL.'''

# * http://media.extron.com/download/files/userman/RAC104manualforwebRevC.pdf
#
# NOTE: this driver may not have all functions implemented

param_disabled = Parameter({"title":"Disabled", "group":"Comms", "schema":{"type":"boolean"}})
param_address = Parameter({"title": "Address", "schema": {"type": "string", "hint": "HOST:TCPPORT"}})

local_event_Status = LocalEvent({'group': 'Status', 'order': 9999 + next_seq(), 'schema': {'type': 'object', 'title': 'Status', 'properties': {
      'level': {'type': 'integer', 'order': next_seq(), 'title': 'Level'},
      'message': {'type': 'string', 'order': next_seq(), 'title': 'Message'} }} })

def main():
  if param_disabled == True:
    console.warn('Recipe disabled! Nothing to do.')
    return
  
  else:
    tcp.setDest(param_address)
    
  for channel in [1, 2, 3, 4]:
    initOutputVolChannel(channel)
    initInputMutingChannel(channel)
    
  # bind stereo
  volE = Event('Ch A Pair Vol', {'group': 'Channel A Pair', 'order': next_seq(), 'schema': {'type': 'number'}})
  ch1VolEvent = lookup_local_event('Ch 1 Output Vol')
  ch2VolEvent = lookup_local_event('Ch 2 Output Vol')
  ch1VolEvent.addEmitHandler(lambda arg: volE.emit(arg)) # pick Ch1 as master
  
  ch1VolAction = lookup_local_action('Ch 1 Output Vol')
  ch2VolAction = lookup_local_action('Ch 2 Output Vol')
  
  def volHandler(arg):
    ch1VolAction.call(arg)
    ch2VolAction.call(arg)
    
  volA = Action('Ch A Pair Vol', volHandler, {'group': 'Channel A Pair', 'order': next_seq(), 'schema': {'type': 'number'}})
  
  volE = Event('Ch A Pair Mute', {'group': 'Channel A Pair', 'order': next_seq(), 'schema': {'type': 'boolean'}})
  ch1MuteEvent = lookup_local_event('Ch 1 Mute')
  ch2MuteEvent = lookup_local_event('Ch 2 Mute')
  ch1MuteEvent.addEmitHandler(lambda arg: volE.emit(arg)) # pick Ch1 as master
  
  ch1MuteAction = lookup_local_action('Ch 1 Mute')
  ch2MuteAction = lookup_local_action('Ch 2 Mute')
  
  def muteHandler(arg):
    ch1MuteAction.call(arg)
    ch2MuteAction.call(arg)
    
  muteA = Action('Ch A Pair Mute', muteHandler, {'group': 'Channel A Pair', 'order': next_seq(), 'schema': {'type': 'boolean'}})
  

# volume ------------------------------------------------    
    
def initOutputVolChannel(channel):
  volEvent = Event('Ch %s Output Vol' % channel, {'title': 'Ch. %s' % channel, 'group': 'Volume', 'order': next_seq(), 'schema': {'type': 'number'}})
  
  def handleResp(resp):
    # e.g. Vol1*080   (channel 1)
    if resp.startswith('Vol'):
      # from a 'set'
      ch = int(resp[3])
      vol = int(resp[5:])
      
      if ch != channel:
        return # ignore stray
        
    else:
      # from a 'poll'
      vol = int(resp)
      
    volEvent.emit(vol)
      
  volAction = Action('Ch %s Output Vol' % channel, 
                     lambda arg: tcp.request('%s*%sV' % (channel, arg), handleResp), 
                     {'title': 'Ch. %s' % channel, 'group': 'Volume', 'order': next_seq(), 'schema': {'type': 'number'}})
  
  volPollAction = Action('Ch %s Poll Output Vol' % channel, 
                         lambda arg: tcp.request('%sV' % (channel), handleResp), 
                         {'title': 'Poll Ch. %s' % channel, 'group': 'Volume', 'order': next_seq(), })
  
  # periodic poller (mix up starting times)
  poller = Timer(lambda: volPollAction.call(), 10, 5+channel)
  
# input muting ------------------------------------------------    
    
def initInputMutingChannel(channel):
  muteEvent = Event('Ch %s Mute' % channel, {'title': 'Ch. %s' % channel, 'group': 'Muting', 'order': next_seq(), 'schema': {'type': 'boolean'}})
  
  def handleResp(resp):
    # e.g. '0' or '1' (unmuted or muted)
    # or 'Amt1*1'
    if resp.startswith('Amt'):
      ch = int(resp[3])
      state = int(resp[5:])
      if ch != channel:
        return # ignore stray
      
    else:
      state = int(resp)

    muteEvent.emit(state == 1)
      
  muteAction = Action('Ch %s Mute' % channel, 
                     lambda arg: tcp.request('%s*%sZ' % (channel, '1' if arg else '0'), handleResp), 
                     {'title': 'Ch. %s' % channel, 'group': 'Muting', 'order': next_seq(), 'schema': {'type': 'boolean'}})
  
  mutePollAction = Action('Ch %s Mute Poll' % channel, 
                         lambda arg: tcp.request('%sZ' % (channel), handleResp), 
                         {'title': 'Poll Ch. %s' % channel, 'group': 'Muting', 'order': next_seq(), })
  
  # periodic poller (mix up starting times)
  poller = Timer(lambda: mutePollAction.call(), 5, 5+channel)
    
# Comms related events for diagnostics ----

local_event_Connected = LocalEvent({'group': 'Comms', 'order': 9999 + next_seq()})
local_event_Received = LocalEvent({'group': 'Comms', 'order': 9999 + next_seq()})
local_event_Sent = LocalEvent({'group': 'Comms', 'order': 9999 + next_seq()})
local_event_Disconnected = LocalEvent({'group': 'Comms', 'order': 9999 + next_seq()})
local_event_Timeout = LocalEvent({'group': 'Comms', 'order': 9999 + next_seq()})

def connected():
  console.info('tcp: connected!')
  
  local_event_Connected.emit()
  local_event_Status.emit({'level': 0, 'message': 'OK'})
    
def received(data):
  log('tcp_received', data)
  local_event_Received.emit(data)

def sent(data):
  log('tcp_sent', data)
  local_event_Sent.emit(data)
    
def disconnected():
  console.info('tcp: disconected')
  
  local_event_Status.emit({'level': 2, 'message': 'Missing'})
  local_event_Disconnected.emit()
  
def timeout():
  console.warn('tcp: comms timeout')
  
  local_event_Status.emit({'level': 2, 'message': 'Missing'})
  local_event_Timeout.emit()
  
  tcp.clearQueue()
  tcp.drop()

tcp = TCP(connected=connected, received=received, sent=sent, disconnected=disconnected, sendDelimiters='\r', receiveDelimiters='\r\n', timeout=timeout)

local_event_Debug = LocalEvent({'title': 'Debug?', 'schema': {'type': 'boolean'}})

def log(context, data=''):
  if local_event_Debug.getArg():
    console.log('[%s] %s' % (context, data))
    
  
  
# example comms:
# 12-21 11:54:03.41 [tcp_sent] Z
# 12-21 11:54:03.43 [tcp_received] 0 0 0 0
# 12-21 11:54:11.25 [tcp_sent] 1V
# 12-21 11:54:11.28 [tcp_received] 070
# 12-21 11:54:25.08 [tcp_sent] 1*80V
# 12-21 11:54:25.11 [tcp_received] Vol1*080
# 12-21 12:15:03.35 [tcp_sent] 1Z
# 12-21 12:15:03.36 [tcp_received] 0
# 12-21 12:35:09.53 [tcp_sent] 1*1Z
# 12-21 12:35:09.55 [tcp_received] Amt1*1
  
