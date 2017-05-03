'''See manual at http://www.alcorn.com/library/manuals/man_dvm8500.pdf'''

local_event_DebugShowLogging = LocalEvent({'group': 'Debug', 'schema': {'type': 'boolean'}})

UDP_PORT = 2638

param_ipAddress = Parameter({'title': 'IP address', 'schema': {'type': 'string'}})

local_event_DeviceStatus = LocalEvent({'schema': {'type': 'object', 'title': '...', 'properties': {
      'level': {'type': 'integer', 'title': 'Level', 'order': 1},
      'message': {'type': 'string', 'title': 'Message', 'order': 2}}}})

# this needs some special filtering to deal with file lists on multiple UDP packets:
# e.g. RECV: "VID00001.MPG\r\n"
#      RECV  "PLY00000.LST\r\n"
# NOTE: only these packets have a '\n' at the end.

listBuffer = list()

local_event_LastContact = LocalEvent({'group': 'Status', 'type': 'string'})

# will set status as missing if been more than 10s since last contact
def isOnline_handler():
  if date_now().getMillis() - date_parse(local_event_LastContact.getArg() or ZERO_DATE_STR).getMillis() < 45000:
    local_event_DeviceStatus.emit({'level': 0, 'message': 'OK'})
  else:
    local_event_DeviceStatus.emit({'level': 1, 'message': 'Missing'})
    
timer_isOnline = Timer(isOnline_handler, 45.0) # check every 45s

def udp_received(src, data):
  if local_event_DebugShowLogging.getArg():
    console.log('udp RECV from %s [%s]' % (src, data.replace('\r', '\\r').replace('\n', '\\n')))
    
  now = date_now()
  local_event_LastContact.emit(str(now))
  
  if data.startswith('---'): # end of the file list
    queue.handle('\r'.join(listBuffer))
    del listBuffer[:]
    return
    
  elif data.endswith('\n'): # is part of a list

    if len(listBuffer) > 256: # ensure no unbounded leak
      return

    listBuffer.append(data.strip()) # add to list and consume
    return
    
  
  # drop the 'src' and sanitise the data  
  queue.handle(data.strip())
  
def udp_sent(data):
  if local_event_DebugShowLogging.getArg():
    console.log('udp SENT [%s]' % data)

udp = UDP(sent=udp_sent, # 'dest' set in 'main'
          ready=lambda: console.info('udp READY'), 
          received=udp_received)

def timeout():
  # local_event_DeviceStatus.emit('Missing')
  pass

queue = request_queue(timeout=timeout)

def main(arg = None):
  print 'Nodel script started.'
  
  udp.setDest('%s:%s' % (param_ipAddress, UDP_PORT))
  
# handles responses to simple requests
def handleReqResp(name, resp, success=None):
  if resp=='R':
    console.info('(%s success)' % name)
    
    if success:
      success()
      
  else:
    console.warn('(%s failure [resp: %s])' % (name, ERROR_CODE_BY_VALUE.get(resp, resp)))
    
  # prod the status update (100ms)
  print 'Prodding timer...'
  timer_status.setDelay(0.1)    
  
# ---- Command Error Codes (page 60) ----
ERROR_CODE_TABLE = [ ('E01', 'Hardware Error'),
                     ('E04', 'Feature Not Available'),
                     ('E06', 'Invalid Argument'),
                     ('E12', 'Search Error') ]
ERROR_CODE_BY_VALUE = {}
for row in ERROR_CODE_TABLE:
  ERROR_CODE_BY_VALUE[row[0]] = row[1]
  
ERROR_CODES = [ row[1] for row in ERROR_CODE_TABLE ]


# ---- 'Status' (page 50) ----
STATUS_CODE_TABLE= [ ('P00', 'Error'), # (resp, code)
                     ('P01', 'Stopped'),
                     ('P04', 'Playing'),
                     ('P05', 'Stilled/Searched'),
                     ('P06', 'Paused')]
STATUS_CODES_BY_RESP = {}
for row in STATUS_CODE_TABLE:
  STATUS_CODES_BY_RESP[row[0]] = row[1]
  
STATUS_CODES = [ row[1] for row in STATUS_CODE_TABLE ]
STATUS_CODES.append('Unknown')
STATUS_CODES.append('Missing')
  
# --- Timer: Status and Clip requests ---

def status_timerHandler():
  lookup_local_action('request status').call()
  lookup_local_action('request clip').call()

# refresh the status every 10 seconds
timer_status = Timer(status_timerHandler, 10)

# --- Timer: Long poll for files listing ---

def longPoll_timerHandler():
  lookup_local_action('list files').call()
  lookup_local_action('request audio volume').call()  

timer_longPoll = Timer(longPoll_timerHandler, 30)

# ---- 'Status Request' (page 50) ----
local_event_Status = LocalEvent({'schema': { 'type': 'string', 'enum': STATUS_CODES }})

def local_action_RequestStatus(arg=None):
  queue.request(lambda: udp.send('?P\r'), 
                lambda arg: local_event_Status.emit(STATUS_CODES_BY_RESP.get(arg, 'Unknown')))

# ---- 'Clip Request' (page 51) ----

local_event_Clip = LocalEvent({'group': 'Status', 'schema': { 'type': 'string'}})

def local_action_RequestClip(arg=None):
  '''{"group": "Status"}'''
  queue.request(lambda: udp.send('?C\r'), 
                lambda arg: local_event_Clip.emit(arg))
  
# ---- 'List Files' (page 51) ----

local_event_FileList = LocalEvent({'title': 'File List', 'group': 'Status', 'schema': { 
    'type': 'array', 'title': 'Files', 'items': {
        'type': 'object', 'properties': {
          'filename': {'title': 'Filename', 'type': 'string'}
    } } }})

def local_action_ListFiles(arg=None):
  '''{"group": "Status"}'''
  def handler(resp):
    rawList = resp.split('\r')
    
    fileList = list()
    
    for raw in [x.strip() for x in rawList]:
      if raw == '':
        continue
        
      fileList.append({'filename': raw})
    
    local_event_FileList.emit(fileList)
  
  queue.request(lambda: udp.send('?D\r'), handler)  
  
# ---- (end)

group = 'Playback'  
  
# ---- 'Search file' (page 46) ----

def searchFile(fileOrNumber):
  queue.request(lambda: udp.send('%sSE\r' % fileOrNumber),
                lambda resp: handleReqResp('SearchFile', resp))

Action('Search File by Number', 
       lambda arg: searchFile(arg), 
       { 'title': 'Search File by Number', 'group': group + ' - Search File', 'order': next_seq(), 
         'desc': 'Searches (loads) content given a file number', 'schema': {'type': 'integer'} })

Action('Search File by Filename', 
       lambda arg: searchFile('"%s"' % arg), 
       { 'title': 'Search File by Filename', 'group': group + ' - Search File', 'order': next_seq(), 
         'desc': 'Searches (loads) content given filename', 'schema': {'type': 'string'} })
       
       
# ---- 'Play' (page 47) ----
def bindAction():
  name = 'Play'
  
  def play():
    queue.request(lambda: udp.send('PL\r'),
                  lambda resp: handleReqResp(name, resp))

  Action(name, lambda arg: play(), 
         { 'title': name, 'group': group, 'order': next_seq(), 
           'desc': 'Plays after a Search command has been used' })

bindAction()

# ---- 'Play File' (page 47) ----
def bindAction():
  name = 'Play File'
  
  def handler(numberOrFilename):
    queue.request(lambda: udp.send('%sPL\r' % numberOrFilename),
                  lambda resp: handleReqResp(name, resp))

  Action('Play File by Number', lambda arg: handler(arg), 
         { 'title': 'Play File by Number', 'group': group + ' - ' + name, 'order': next_seq(), 'schema': {'type': 'integer'} })
  
  Action('Play File by Filename', lambda arg: handler('"%s"' % arg), 
         { 'title': 'Play File by Filename', 'group': group + ' - ' + name, 'order': next_seq(), 'schema': {'type': 'string'} })

bindAction()

# ---- 'Play File' (page 4.87) ----
def bindAction():
  name = 'Loop File'
  
  def handler(numberOrFilename):
    queue.request(lambda: udp.send('%sLP\r' % numberOrFilename),
                  lambda resp: handleReqResp(name, resp))

  Action('Loop File by Number', lambda arg: handler(arg), 
         { 'title': 'Loop File by Number', 'group': group + ' - ' + name, 'order': next_seq(), 'schema': {'type': 'integer'} })
  
  Action('Loop File by Filename', lambda arg: handler('"%s"' % arg), 
         { 'title': 'Loop File by Filename', 'group': group + ' - ' + name, 'order': next_seq(), 'schema': {'type': 'string'} })

bindAction()

# ---- 'Loop Play' (page 47) ----
def bindAction():
  name = 'Loop Play'
  
  def loopPlay():
    queue.request(lambda: udp.send('LP\r'),
                  lambda resp: handleReqResp(name, resp))

  Action(name, lambda arg: loopPlay(), 
         { 'title': name, 'group': group, 'order': next_seq(), 
           'desc': 'Loop Plays after a Search command has been used' })

bindAction()

# ---- 'Play Next' (page 48) ----
def bindAction():
  name = 'Play Next'
  
  def playNext(numberOrFilename):
    queue.request(lambda: udp.send('%sPN\r' % numberOrFilename),
                  lambda resp: handleReqResp(name, resp))

  Action('Play Next by Number', lambda arg: playNext(arg), 
         { 'title': 'Play Next by Number', 'group': group + ' - ' + name, 'order': next_seq(), 'schema': {'type': 'integer'} })
  
  Action('Play Next by Filename', lambda arg: playNext('"%s"' % arg), 
         { 'title': 'Play Next by Filename', 'group': group + ' - ' + name, 'order': next_seq(), 'schema': {'type': 'string'} })

bindAction()

# ---- 'Loop Next' (page 48) ----
def bindAction():
  name = 'Loop Next'
  
  def loopNext(numberOrFilename):
    queue.request(lambda: udp.send('%sLN\r' % numberOrFilename),
                  lambda resp: handleReqResp(name, resp))

  Action('Loop Next by Number', lambda arg: loopNext(arg), 
         { 'title': 'Loop Next by Number', 'group': group + ' - ' + name, 'order': next_seq(), 'schema': {'type': 'integer'} })
  
  Action('Loop Next by Filename', lambda arg: loopNext('"%s"' % arg), 
         { 'title': 'Loop Next by Filename', 'group': group + ' - ' + name, 'order': next_seq(), 'schema': {'type': 'string'} })

bindAction()

# ---- 'Still' (page 49) ----
def bindAction():
  name = 'Still'
  
  def still():
    queue.request(lambda: udp.send('ST\r'),
                  lambda resp: handleReqResp(name, resp))

  Action(name, lambda arg: still(), 
         { 'title': name, 'group': group, 'order': next_seq(), 
           'desc': 'Holds current frame' })

bindAction()

# ---- 'Pause' (page 49) ----
def bindAction():
  name = 'Pause'
  
  def pause():
    queue.request(lambda: udp.send('PA\r'),
                  lambda resp: handleReqResp(name, resp))

  Action(name, lambda arg: pause(), 
         { 'title': name, 'group': group, 'order': next_seq(), 
           'desc': 'Pauses (black frame)' })

bindAction()
  
# ---- 'Stop' (page 49) ----
def bindAction():
  name = 'Stop'
  
  def stop():
    queue.request(lambda: udp.send('RJ\r'),
                  lambda resp: handleReqResp(name, resp))

  Action(name, lambda arg: stop(), 
         { 'title': name, 'group': group, 'order': next_seq() })

bindAction()

# ---- 'Audio Mute' (page 49) ----
def bindAction():
  name = 'Audio Mute'
  
  metadata = { 'title': name, 'group': group + ' - ' + name, 'order': next_seq(), 
           'schema': {'type': 'string', 'enum': ['On', 'Off']}}
  
  event = Event(name, metadata)
  
  def audioMute(state):
    # state forced to lower case
    queue.request(lambda: udp.send('%sAD\r' % ('0' if state == 'on' else '1')),
                  lambda resp: handleReqResp(name, resp, lambda: event.emit('Mute' if state == 'mute' else 'Unmute')))

  Action(name, lambda arg: audioMute(arg.lower()), metadata)

bindAction()

# ---- 'Video Mute' (page 50) ----
def bindAction():
  name = 'Video Mute'
  
  metadata = { 'title': name, 'group': group + ' - ' + name, 'order': next_seq(), 
           'schema': {'type': 'string', 'enum': ['Black', 'Normal']}}
  
  event = Event(name, metadata)
  
  def handler(state):
    # state forced to lower case
    queue.request(lambda: udp.send('%sVD\r' % ('0' if state == 'black' else '1')),
                  lambda resp: handleReqResp(name, resp, lambda: event.emit('Black' if state == 'black' else 'Normal')))

  Action(name, lambda arg: handler(arg.lower()), metadata)

bindAction()
  
# ---- 'Audio Volume' (page 50) ----
def bindAction():
  name = 'Audio Volume'
  
  metadata = { 'title': name, 'group': group + ' - ' + name, 'order': next_seq(), 
               'schema': {'type': 'integer', 'format': 'range', 'min': 0, 'max': 100} }
  
  event = Event(name, metadata)
  
  def handler(arg):
    # state forced to lower case
    queue.request(lambda: udp.send('%s%%AD\r' % arg),
                  lambda resp: handleReqResp(name, resp, lambda: event.emit(arg)))

  Action(name, lambda arg: handler(arg), metadata)

bindAction()

# ---- 'Request Audio Volume' (page 59) ----
def bindAction():
  name = 'Request Audio Volume'
  
  metadata = { 'title': 'Request', 'group': group + ' - Audio Volume', 'order': next_seq() }
  
  def handler(arg):
    queue.request(lambda: udp.send('%AD\r'),
                  lambda resp: lookup_local_event('Audio Volume').emit(int(resp)))

  Action(name, lambda arg: handler(arg), metadata)

bindAction()

# for acting as a mute slave
def remote_event_Mute(arg):
  lookup_local_action('Audio Mute').call(arg)  
  
# reserved for power slave action
local_event_Power = LocalEvent({'title': 'Power', 'schema': { 'type': 'string', 'enum': ['On', 'Off']}})

def local_action_Power(arg=None):
  """{"title": "Power", "schema": { "type": "string", "enum": ["On", "Off"]}}"""
  local_event_Power.emit(arg)
  
  # Play and Pause actions associated with power
  if arg == 'On':
    lookup_local_action('Play').call()
  
  if arg == 'Off':
    lookup_local_action('Pause').call()
  
def remote_event_Power(arg):
  lookup_local_action('power').call(arg)
  
ZERO_DATE_STR = str(date_instant(0))
