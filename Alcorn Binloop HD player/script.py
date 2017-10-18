'''See http://www.alcorn.com/library/manuals/man_blhd_rev1_8.pdf for manual.'''

local_event_DebugShowLogging = LocalEvent({'group': 'Debug', 'schema': {'type': 'boolean'}})

UDP_PORT = 2638

param_ipAddress = Parameter({'title': 'IP address', 'schema': {'type': 'string'}})
param_reproducers = Parameter({'title': 'Num. reproducers', 'schema': {'type': 'integer'}})

def udp_received(src, data):
  if local_event_DebugShowLogging.getArg():
    console.log('udp RECV from %s [%s]' % (src, data))
    
  local_event_Status.emitIfDifferent('OK')
  
  # drop the 'src' and sanitise the data
  queue.handle(data.strip())
  
def udp_sent(data):
  if local_event_DebugShowLogging.getArg():
    console.log('udp SENT [%s]' % data)

udp = UDP(sent=udp_sent, # 'dest' set in 'main'
          ready=lambda: console.info('udp READY'), 
          received=udp_received)

local_event_Status = LocalEvent({'schema': { 'type': 'string', 'enum': ['Unknown', 'OK', 'Missing'] }})

def timeout():
  local_event_Status.emit('Missing')

queue = request_queue(timeout=timeout)

def main(arg = None):
  console.info('Node started')
  
  for i in range(param_reproducers or 0):
    bindReproducer(i+1)
  
  udp.setDest('%s:%s' % (param_ipAddress, UDP_PORT))
  
def handle_backgroundTimer():
  # stagger request
  call(lambda: lookup_local_action('get firmware version').call(), 0.0)
  call(lambda: lookup_local_action('get hardware version').call(), 1.0)
  call(lambda: lookup_local_action('get SMPTE firmware version').call(), 1.5)
  call(lambda: lookup_local_action('get unit ID').call(), 2)
  
# background polling
timer_background = Timer(handle_backgroundTimer, 60, 15)
  
# ---- Some rrror code (taken from DVM Player manual) ----
ERROR_CODE_TABLE = [ ('E01', 'Hardware Error'),
                     ('E04', 'Feature Not Available'),
                     ('E06', 'Invalid Argument'),
                     ('E12', 'Search Error') ]
ERROR_CODE_BY_VALUE = {}
for row in ERROR_CODE_TABLE:
  ERROR_CODE_BY_VALUE[row[0]] = row[1]
  
ERROR_CODES = [ row[1] for row in ERROR_CODE_TABLE ]  
  
# handles responses to simple requests
def handleReqResp(name, resp, success=None):
  if resp=='R':
    console.info('(%s success)' % name)
    
    if success:
      success()
      
  else:
    console.warn('(%s failure [resp: %s])' % (name, ERROR_CODE_BY_VALUE.get(resp, resp)))
      
  
  
# ---- 'Get Firmware' (page 33) ----
local_event_FirmwareVersion = LocalEvent({'group': 'Info', 'schema': { 'type': 'string'}})

def local_action_GetFirmwareVersion(arg=None):
  """{"group": "Info"}"""
  queue.request(lambda: udp.send('?V\r'), 
                lambda resp: local_event_FirmwareVersion.emit(resp))
  
# ---- 'Get Hardware Version' (page 33) ----
local_event_HardwareVersion = LocalEvent({'group': 'Info', 'schema': { 'type': 'string'}})

def local_action_GetHardwareVersion(arg=None):
  """{"group": "Info"}"""
  queue.request(lambda: udp.send('?H\r'), 
                lambda resp: local_event_HardwareVersion.emit(resp)) 
  
# ---- 'Get SMPTE Firmware Version' (page 33) ----
local_event_SMPTEFirmwareVersion = LocalEvent({'group': 'Info', 'schema': { 'type': 'string'}})

def local_action_GetSMPTEFirmwareVersion(arg=None):
  """{"group": "Info"}"""
  queue.request(lambda: udp.send('?S\r'), 
                lambda resp: local_event_SMPTEFirmwareVersion.emit(resp))   
  
# ---- 'Get Unit ID' (page 34) ----
local_event_UnitID = LocalEvent({'group': 'Info', 'schema': { 'type': 'integer'}})

def local_action_GetUnitID(arg=None):
  """{"group": "Info"}"""
  queue.request(lambda: udp.send('ID\r'), 
                lambda resp: local_event_UnitID.emit(resp))
  
# ---- SMTPE group ----  

group = 'SMPTE'

def local_action_SMPTEEnable(arg=None):
  """{"group": "SMPTE"}"""
  queue.request(lambda: udp.send('ES\r'), 
                lambda resp: handleReqResp('SMPTE enable', resp))
                
def local_action_SMPTEDisable(arg=None):
  """{"group": "SMPTE"}"""
  queue.request(lambda: udp.send('DS\r'), 
                lambda resp: handleReqResp('SMPTE disable', resp))
  
def local_action_SMPTEPause(arg=None):
  """{"group": "SMPTE"}"""
  queue.request(lambda: udp.send('PS\r'), 
                lambda resp: handleReqResp('SMPTE pause', resp))
  
def local_action_SMPTEIdle(arg=None):
  """{"group": "SMPTE"}"""
  queue.request(lambda: udp.send('IS\r'), 
                lambda resp: handleReqResp('SMPTE idle', resp))
  
# ---- 'Set SMPTE time' (page 37) ----
def bindAction():
  name = 'SMPTE time'
  
  metadata = { 'title': name, 'group': group, 'order': next_seq(), 'desc': 'A SMPTE time in the format "hh:mm:ss.ff"',
               'schema': {'type': 'string'} }
  
  event = Event(name, metadata)
  
  def handler(arg):
    queue.request(lambda: udp.send('%sCT\r' % arg),
                  lambda resp: handleReqResp(name, resp, lambda: event.emit(arg)))

  Action(name, lambda arg: handler(arg), metadata)

bindAction()

# ---- 'SMPTE time' (page 37) ----
def bindAction():
  name = 'Get SMPTE time'
  
  metadata = { 'title': 'Get', 'group': group, 'order': next_seq() }
  
  def handler(arg):
    queue.request(lambda: udp.send('CT\r'),
                  lambda resp: lookup_local_event('SMPTE time').emit(resp))

  Action(name, lambda arg: handler(arg), metadata)

bindAction()


# ---- 'Set SMPTE time' (page 37) ----
SMPTEMODES_TABLE = [ (0, 'Read'),
                     (1, 'Generate'),
                     (2, 'Generate with V-sync') ]

SMPTEMODES = [row[1] for row in SMPTEMODES_TABLE]

SMPTEMODE_by_value = {}
for row in SMPTEMODES_TABLE:
  SMPTEMODE_by_value[row[0]] = row[1]

SMPTEVALUE_by_mode = {}
for row in SMPTEMODES_TABLE:
  SMPTEVALUE_by_mode[row[1]] = row[0]


def bindAction():
  name = 'SMPTE Mode'
  
  metadata = { 'title': name, 'group': group + ' Mode', 'order': next_seq(), 
               'schema': {'type': 'string', 'enum': SMPTEMODES} }
  
  event = Event(name, metadata)
  
  def handler(arg):
    queue.request(lambda: udp.send('%sSO\r' % SMPTEVALUE_by_mode[arg]),
                  lambda resp: handleReqResp(name, resp, lambda: event.emit(arg)))

  Action(name, lambda arg: handler(arg), metadata)

bindAction()

# ---- 'SMPTE time' (page 37) ----
def bindAction():
  name = 'Get SMPTE Mode'
  
  metadata = { 'title': 'Get', 'group': group + ' Mode', 'order': next_seq() }
  
  def handler(arg):
    queue.request(lambda: udp.send('SO\r'),
                  lambda resp: lookup_local_event('SMPTE Mode').emit(SMPTEMODE_by_value[int(resp)]))

  Action(name, lambda arg: handler(arg), metadata)

bindAction()

# ---- search clip (page 43) ----
def local_action_SearchClipOnReproducer(arg=None):
  """{"group": "Playback - Reproducer", "schema": {"type": "object", "title": "Args", "properties": {
         "fileNumber": {"type": "number", "order": 1, "title": "File number"},
         "reproducer": {"type": "number", "order": 2, "title": "Reproducer"}}}}"""
  query = '%sR%sSE\r' % (arg['fileNumber'], arg['reproducer'])
  queue.request(lambda: udp.send(query),
                  lambda resp: handleReqResp('SearchClipOnReproducer', resp))
  
def local_action_SearchClipOnGroup(arg=None):
  """{"group": "Playback - Group", "schema": {"type": "object", "title": "Args", "properties": {
         "fileNumber": {"type": "number", "order": 1, "title": "File number"},
         "group": {"type": "number", "order": 2, "title": "Group"}}}}"""
  query = '%sG%sSE\r' % (arg['fileNumber'], arg['group'])
  queue.request(lambda: udp.send(query),
                lambda resp: handleReqResp('SearchClipOnGroup', resp))  
  
def local_action_SearchClipOnAll(arg=None):
  """{"group": "Playback - All", "schema": {"type": "number"}}"""
  query = '%s*SE\r' % arg
  queue.request(lambda: udp.send(query),
                lambda resp: handleReqResp('SearchClipOnAll', resp)) 
  

# ---- play / resume (page 43) ----
def local_action_PlayOnReproducer(arg=None):
  """{"group": "Playback - Reproducer", "schema": {"type": "number"}}"""
  query = 'R%sPL\r' % arg
  queue.request(lambda: udp.send(query),
                lambda resp: handleReqResp('PlayOnReproducer', resp))
  
def local_action_PlayOnGroup(arg=None):
  """{"group": "Playback - Group", "schema": {"type": "number"}}"""
  query = 'G%sPL\r' % arg
  queue.request(lambda: udp.send(query),
                lambda resp: handleReqResp('PlayOnGroup', resp)) 
  
def local_action_PlayOnAll(arg=None):
  """{"group": "Playback - All"}"""
  query = '*PL\r'
  queue.request(lambda: udp.send(query),
                lambda resp: handleReqResp('PlayOnAll', resp))

  
# ---- loop / resume (page 43) ----
def local_action_LoopOnReproducer(arg=None):
  """{"group": "Playback - Reproducer", "schema": {"type": "number"}}"""
  query = 'R%sLP\r' % arg
  queue.request(lambda: udp.send(query),
                lambda resp: handleReqResp('LoopOnReproducer', resp))
  
def local_action_LoopOnGroup(arg=None):
  """{"group": "Playback - Group", "schema": {"type": "number"}}"""
  query = 'G%sLP\r' % arg
  queue.request(lambda: udp.send(query),
                lambda resp: handleReqResp('LoopOnGroup', resp)) 
  
def local_action_LoopOnAll(arg=None):
  """{"group": "Playback - All"}"""
  query = '*LP\r'
  queue.request(lambda: udp.send(query),
                lambda resp: handleReqResp('LoopOnAll', resp))

  
# ---- play clip (page 44) ----
def local_action_PlayClipOnReproducer(arg=None):
  """{"group": "Playback - Reproducer", "schema": {"type": "object", "title": "Args", "properties": {
         "fileNumber": {"type": "number", "order": 1, "title": "File number"},
         "reproducer": {"type": "number", "order": 2, "title": "Reproducer"}}}}"""
  query = '%sR%sPL\r' % (arg['fileNumber'], arg['reproducer'])
  queue.request(lambda: udp.send(query),
                  lambda resp: handleReqResp('PlayClipOnReproducer', resp))
  
def local_action_PlayClipOnGroup(arg=None):
  """{"group": "Playback - Group", "schema": {"type": "object", "title": "Args", "properties": {
         "fileNumber": {"type": "number", "order": 1, "title": "File number"},
         "group": {"type": "number", "order": 2, "title": "Group"}}}}"""
  query = '%sG%sPL\r' % (arg['fileNumber'], arg['group'])
  queue.request(lambda: udp.send(query),
                lambda resp: handleReqResp('PlayClipOnGroup', resp))  
  
def local_action_PlayClipOnAll(arg=None):
  """{"group": "Playback - All", "schema": {"type": "number"}}"""
  query = '%s*PL\r' % arg
  queue.request(lambda: udp.send(query),
                lambda resp: handleReqResp('PlayClipOnAll', resp))   


# ---- loop clip (page 44) ----
def local_action_LoopClipOnReproducer(arg=None):
  """{"group": "Playback - Reproducer", "schema": {"type": "object", "title": "Args", "properties": {
         "fileNumber": {"type": "number", "order": 1, "title": "File number"},
         "reproducer": {"type": "number", "order": 2, "title": "Reproducer"}}}}"""
  query = '%sR%sLP\r' % (arg['fileNumber'], arg['reproducer'])
  queue.request(lambda: udp.send(query),
                  lambda resp: handleReqResp('LoopClipOnReproducer', resp))
  
def local_action_LoopClipOnGroup(arg=None):
  """{"group": "Playback - Group", "schema": {"type": "object", "title": "Args", "properties": {
         "fileNumber": {"type": "number", "order": 1, "title": "File number"},
         "group": {"type": "number", "order": 2, "title": "Group"}}}}"""
  query = '%sG%sLP\r' % (arg['fileNumber'], arg['group'])
  queue.request(lambda: udp.send(query),
                lambda resp: handleReqResp('LoopClipOnGroup', resp))  
  
def local_action_LoopClipOnAll(arg=None):
  """{"group": "Playback - All", "schema": {"type": "number"}}"""
  query = '%s*LP\r' % arg
  queue.request(lambda: udp.send(query),
                lambda resp: handleReqResp('LoopClipOnAll', resp)) 
  
  
# ---- sync play (page 45) ----
def local_action_SyncPlayClipOnReproducer(arg=None):
  """{"group": "Playback - Reproducer", "schema": {"type": "object", "title": "Args", "properties": {
         "fileNumber": {"type": "number", "order": 1, "title": "File number"},
         "reproducer": {"type": "number", "order": 2, "title": "Reproducer"}}}}"""
  query = '%sR%sSP\r' % (arg['fileNumber'], arg['reproducer'])
  queue.request(lambda: udp.send(query),
                  lambda resp: handleReqResp('SyncPlayClipOnReproducer', resp))
  
def local_action_SyncPlayClipOnGroup(arg=None):
  """{"group": "Playback - Group", "schema": {"type": "object", "title": "Args", "properties": {
         "fileNumber": {"type": "number", "order": 1, "title": "File number"},
         "group": {"type": "number", "order": 2, "title": "Group"}}}}"""
  query = '%sG%sSP\r' % (arg['fileNumber'], arg['group'])
  queue.request(lambda: udp.send(query),
                lambda resp: handleReqResp('SyncPlayClipOnGroup', resp))  
  
def local_action_SyncPlayClipOnAll(arg=None):
  """{"group": "Playback - All", "schema": {"type": "number"}}"""
  query = '%s*SP\r' % arg
  queue.request(lambda: udp.send(query),
                lambda resp: handleReqResp('SyncPlayClipOnAll', resp))
  
  
# ---- sync loop (page 45) ----
def local_action_SyncLoopClipOnReproducer(arg=None):
  """{"group": "Playback - Reproducer", "schema": {"type": "object", "title": "Args", "properties": {
         "fileNumber": {"type": "number", "order": 1, "title": "File number"},
         "reproducer": {"type": "number", "order": 2, "title": "Reproducer"}}}}"""
  query = '%sR%sSL\r' % (arg['fileNumber'], arg['reproducer'])
  queue.request(lambda: udp.send(query),
                  lambda resp: handleReqResp('SyncLoopClipOnReproducer', resp))
  
def local_action_SyncLoopClipOnGroup(arg=None):
  """{"group": "Playback - Group", "schema": {"type": "object", "title": "Args", "properties": {
         "fileNumber": {"type": "number", "order": 1, "title": "File number"},
         "group": {"type": "number", "order": 2, "title": "Group"}}}}"""
  query = '%sG%sSL\r' % (arg['fileNumber'], arg['group'])
  queue.request(lambda: udp.send(query),
                lambda resp: handleReqResp('SyncLoopClipOnGroup', resp))  
  
def local_action_SyncLoopClipOnAll(arg=None):
  """{"group": "Playback - All", "schema": {"type": "number"}}"""
  query = '%s*SL\r' % arg
  queue.request(lambda: udp.send(query),
                lambda resp: handleReqResp('SyncLoopClipOnAll', resp))
  
# ---- play next (page 45) ----
def local_action_PlayNextClipOnReproducer(arg=None):
  """{"group": "Playback - Reproducer", "schema": {"type": "object", "title": "Args", "properties": {
         "fileNumber": {"type": "number", "order": 1, "title": "File number"},
         "reproducer": {"type": "number", "order": 2, "title": "Reproducer"}}}}"""
  query = '%sR%sPN\r' % (arg['fileNumber'], arg['reproducer'])
  queue.request(lambda: udp.send(query),
                  lambda resp: handleReqResp('PlayNextOnReproducer', resp))
  
def local_action_PlayNextClipOnGroup(arg=None):
  """{"group": "Playback - Group", "schema": {"type": "object", "title": "Args", "properties": {
         "fileNumber": {"type": "number", "order": 1, "title": "File number"},
         "group": {"type": "number", "order": 2, "title": "Group"}}}}"""
  query = '%sG%sPN\r' % (arg['fileNumber'], arg['group'])
  queue.request(lambda: udp.send(query),
                lambda resp: handleReqResp('PlayNextClipOnGroup', resp))  
  
def local_action_PlayNextClipOnAll(arg=None):
  """{"group": "Playback - All", "schema": {"type": "number"}}"""
  query = '%s*PN\r' % arg
  queue.request(lambda: udp.send(query),
                lambda resp: handleReqResp('PlayNextClipOnAll', resp))  
  
# ---- loop next (page 46) ----
def local_action_LoopNextClipOnReproducer(arg=None):
  """{"group": "Playback - Reproducer", "schema": {"type": "object", "title": "Args", "properties": {
         "fileNumber": {"type": "number", "order": 1, "title": "File number"},
         "reproducer": {"type": "number", "order": 2, "title": "Reproducer"}}}}"""
  query = '%sR%sLN\r' % (arg['fileNumber'], arg['reproducer'])
  queue.request(lambda: udp.send(query),
                  lambda resp: handleReqResp('LoopNextOnReproducer', resp))
  
def local_action_LoopNextClipOnGroup(arg=None):
  """{"group": "Playback - Group", "schema": {"type": "object", "title": "Args", "properties": {
         "fileNumber": {"type": "number", "order": 1, "title": "File number"},
         "group": {"type": "number", "order": 2, "title": "Group"}}}}"""
  query = '%sG%sLN\r' % (arg['fileNumber'], arg['group'])
  queue.request(lambda: udp.send(query),
                lambda resp: handleReqResp('LoopNextClipOnGroup', resp))  
  
def local_action_LoopNextClipOnAll(arg=None):
  """{"group": "Playback - All", "schema": {"type": "number"}}"""
  query = '%s*LN\r' % arg
  queue.request(lambda: udp.send(query),
                lambda resp: handleReqResp('LoopNextClipOnAll', resp)) 
  
  
# ---- stop (page 47) ----
def local_action_StopOnReproducer(arg=None):
  """{"group": "Playback - Reproducer", "schema": {"type": "object", "title": "Args", "properties": {
         "reproducer": {"type": "number", "order": 2, "title": "Reproducer"}}}}"""
  query = 'R%sRJ\r' % arg['reproducer']
  queue.request(lambda: udp.send(query),
                  lambda resp: handleReqResp('StopOnReproducer', resp))
  
def local_action_StopOnGroup(arg=None):
  """{"group": "Playback - Group", "schema": {"type": "object", "title": "Args", "properties": {
         "group": {"type": "number", "order": 2, "title": "Group"}}}}"""
  query = 'G%sRJ\r' % arg['group']
  queue.request(lambda: udp.send(query),
                lambda resp: handleReqResp('StopOnGroup', resp))  
  
def local_action_StopOnAll(arg=None):
  """{"group": "Playback - All"}"""
  query = '*RJ\r'
  queue.request(lambda: udp.send(query),
                lambda resp: handleReqResp('StopOnAll', resp))
  
# ---- still (page 47) ----
def local_action_StillOnReproducer(arg=None):
  """{"group": "Playback - Reproducer", "schema": {"type": "object", "title": "Args", "properties": {
         "reproducer": {"type": "number", "order": 2, "title": "Reproducer"}}}}"""
  query = 'R%sST\r' % arg['reproducer']
  queue.request(lambda: udp.send(query),
                  lambda resp: handleReqResp('StillOnReproducer', resp))
  
def local_action_StillOnGroup(arg=None):
  """{"group": "Playback - Group", "schema": {"type": "object", "title": "Args", "properties": {
         "group": {"type": "number", "order": 2, "title": "Group"}}}}"""
  query = 'G%sST\r' % arg['group']
  queue.request(lambda: udp.send(query),
                lambda resp: handleReqResp('StillOnGroup', resp))  
  
def local_action_StillOnAll(arg=None):
  """{"group": "Playback - All"}"""
  query = '*ST\r'
  queue.request(lambda: udp.send(query),
                lambda resp: handleReqResp('StillOnAll', resp))  
  
# ---- pause (page 47) ----
def local_action_PauseOnReproducer(arg=None):
  """{"group": "Playback - Reproducer", "schema": {"type": "object", "title": "Args", "properties": {
         "reproducer": {"type": "number", "order": 2, "title": "Reproducer"}}}}"""
  query = 'R%sPA\r' % arg['reproducer']
  queue.request(lambda: udp.send(query),
                  lambda resp: handleReqResp('PauseOnReproducer', resp))
  
def local_action_PauseOnGroup(arg=None):
  """{"group": "Playback - Group", "schema": {"type": "object", "title": "Args", "properties": {
         "group": {"type": "number", "order": 2, "title": "Group"}}}}"""
  query = 'G%sPA\r' % arg['group']
  queue.request(lambda: udp.send(query),
                lambda resp: handleReqResp('PauseOnGroup', resp))  
  
def local_action_PauseOnAll(arg=None):
  """{"group": "Playback - All"}"""
  query = '*PA\r'
  queue.request(lambda: udp.send(query),
                lambda resp: handleReqResp('PauseOnAll', resp))
  
# ---- video mute/umute (page 47) ----
def local_action_VideoMuteOnReproducer(arg=None):
  """{"group": "Playback - Reproducer", "schema": {"type": "object", "title": "Args", "properties": {
         "reproducer": {"type": "number", "order": 2, "title": "Reproducer"},
         "state": {"type": "string", "order": 3, "title": "State", "enum": ["Mute", "Unmute"]}
         }}}"""
  query = '%sR%sVD\r' % (0 if arg['state']=='Mute' else 1, arg['reproducer'])
  queue.request(lambda: udp.send(query),
                  lambda resp: handleReqResp('VideoMuteOnReproducer', resp))
  
def local_action_VideoMuteOnGroup(arg=None):
  """{"group": "Playback - Group", "schema": {"type": "object", "title": "Args", "properties": {
         "group": {"type": "number", "order": 2, "title": "Group"},
         "state": {"type": "string", "order": 3, "title": "State", "enum": ["Mute", "Unmute"]}
         }}}"""
  query = '%sG%sVD\r' % (0 if arg['state']=='Mute' else 1, arg['group'])
  queue.request(lambda: udp.send(query),
                lambda resp: handleReqResp('VideoMuteOnGroup', resp))  
  
def local_action_VideoMuteOnAll(arg=None):
  """{"group": "Playback - All", "schema": {"type": "string", "enum": ["Mute", "Unmute"]}}"""
  query = '%s*VD\r' % (0 if arg=='Mute' else 1)
  queue.request(lambda: udp.send(query),
                lambda resp: handleReqResp('VideoMuteOnAll', resp)) 
  
# ---- audio mute/umute (page 47) ----
def local_action_AudioMuteOnReproducer(arg=None):
  """{"group": "Playback - Reproducer", "schema": {"type": "object", "title": "Args", "properties": {
         "reproducer": {"type": "number", "order": 2, "title": "Reproducer"},
         "state": {"type": "string", "order": 3, "title": "State", "enum": ["Mute", "Unmute"]}
         }}}"""
  query = '%sR%sAD\r' % (0 if arg['state']=='Mute' else 1, arg['reproducer'])
  queue.request(lambda: udp.send(query),
                  lambda resp: handleReqResp('AudioMuteOnReproducer', resp))
  
def local_action_AudioMuteOnGroup(arg=None):
  """{"group": "Playback - Group", "schema": {"type": "object", "title": "Args", "properties": {
         "group": {"type": "number", "order": 2, "title": "Group"},
         "state": {"type": "string", "order": 3, "title": "State", "enum": ["Mute", "Unmute"]}
         }}}"""
  query = '%sG%sAD\r' % (0 if arg['state']=='Mute' else 1, arg['group'])
  queue.request(lambda: udp.send(query),
                lambda resp: handleReqResp('AudioMuteOnGroup', resp))  
  
def local_action_AudioMuteOnAll(arg=None):
  """{"group": "Playback - All", "schema": {"type": "string", "enum": ["Mute", "Unmute"]}}"""
  query = '%s*AD\r' % (0 if arg=='Mute' else 1)
  queue.request(lambda: udp.send(query),
                lambda resp: handleReqResp('AudioMuteOnAll', resp))   

# ---- 'reproducer status' and 'filename'(page 50) ----
STATUS_CODE_TABLE= [ ('P00', 'Error'), # (resp, code)
                     ('P01', 'Stopped'),
                     ('P04', 'Playing'),
                     ('P05', 'Stilled'),
                     ('P06', 'Paused') ]
STATUS_CODES_BY_RESP = {}
for row in STATUS_CODE_TABLE:
  STATUS_CODES_BY_RESP[row[0]] = row[1]
  
STATUS_CODES = [ row[1] for row in STATUS_CODE_TABLE ]
STATUS_CODES.append('Unknown')
STATUS_CODES.append('Missing')  

def bindReproducer(reproducerNum):
  statusEvent = Event('Reproducer %s Status' % reproducerNum, {'group': 'Reproducer %s' % reproducerNum, 'schema': {'type': 'string', 'enum': STATUS_CODES}})
  
  def getReproducerStatus(arg=None):
    query = 'R%s?P\r' % reproducerNum
    queue.request(lambda: udp.send(query),
                  lambda resp: statusEvent.emit(STATUS_CODES_BY_RESP.get(resp, 'Unknown')))
    
  Action('Get Reproducer %s Status' % reproducerNum, getReproducerStatus, {'group': 'Reproducer %s' % reproducerNum})
  
  filenameEvent = Event('Reproducer %s Filename' % reproducerNum, {'group': 'Reproducer %s' % reproducerNum, 'schema': {'type': 'string'}})
  
  def getReproducerFilename(arg=None):
    query = 'R%s?C\r' % reproducerNum
    queue.request(lambda: udp.send(query),
                  lambda resp: filenameEvent.emit(resp))
    
  Action('Get Reproducer %s Filename' % reproducerNum, getReproducerFilename, {'group': 'Reproducer %s' % reproducerNum})
   
    
# for acting as a power slave
def remote_event_Power(arg):
  lookup_local_action('LoopOnAll').call() if arg == 'On' else lookup_local_action('PauseOnAll').call()
  
# for acting as a mute slave
def remote_event_Mute(arg):
  lookup_local_action('AudioMuteOnAll').call('Unmute') if arg == 'Off' else lookup_local_action('AudioMuteOnAll').call('Mute') 
