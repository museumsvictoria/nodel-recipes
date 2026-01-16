'''
**Pharos Designer** HTTP API v11

---

`REV 1 2026.01.16 azuell`

* API version 11.0 (latest) Pharos Designer version 2.15.3 (latest)
* Includes optional authentication using username/password
* Automatically generates actions/events from desired objects (Scenes, Triggers, Timelines) sorted by groups
* Updates events with state from Pharos as part of status checking

**MANUAL**

* [Pharos API Documentation](https://pharos-designer-controller-api.readthedocs.io/en/latest/http-api/index.html)

**REVISION HISTORY**

* rev. 1: initial

**TO DO**

* Call a group of objects at once. Currently gets a little overwhelmed with multiple API calls at once

'''

DEFAULT_PORT = 80

API_VERSION = 11

DEFAULT_USERNAME = 'admin'
DEFAULT_PASSWORD = 'admin'

AUTH_TIMEOUT = 5 * 60 # seconds

STATUS_CHECK_INTERVAL = 75  # seconds

_fullAddress = None

_authenticationRequired = False

_lastReceive = 0

param_disabled = Parameter({'title': 'Disable this node', 'schema': {'type': 'boolean'}})

param_playerConfig = Parameter({'title': 'Pharos Config', 'schema': {'type': 'object', 'properties': {
  'ipAddress': {'title': 'IP Address', 'type': 'string', 'hint': 'ip', 'order': 1},
  'port': {'title': 'Port', 'type': 'string', 'hint': DEFAULT_PORT, 'order': 2}}}})

param_login = Parameter({'title': 'Pharos Login', 'schema': {'type': 'object', 'properties': {
  'required': {'title': 'Require authentication?', 'type': 'boolean', 'order': 1},
  'username': {'title': 'Username', 'type': 'string', 'hint': DEFAULT_USERNAME, 'order': 2},
  'password': {'title': 'Password', 'type': 'string', 'hint': DEFAULT_PASSWORD, 'order': 3}}}})

param_objects = Parameter({'title': 'Pharos Objects', 'schema': {'type': 'object', 'properties': {
  'scene': {'title': 'Scenes', 'type': 'boolean', 'order': 1},
  'timeline': {'title': 'Timelines', 'type': 'boolean', 'order': 2},
  'trigger': {'title': 'Triggers', 'type': 'boolean', 'order': 3}}}})

local_event_AuthToken = LocalEvent({'group': 'Authentication', 'schema': {'type': 'string'}})

local_event_ProjectName = LocalEvent({'group': 'Project Information', 'schema': {'type': 'string', 'order': next_seq()}})
local_event_ProjectAuthor = LocalEvent({'group': 'Project Information', 'schema': {'type': 'string', 'order': next_seq()}})
local_event_ProjectFileName = LocalEvent({'group': 'Project Information', 'schema': {'type': 'string', 'order': next_seq()}})
local_event_ProjectUniqueID = LocalEvent({'group': 'Project Information', 'schema': {'type': 'string', 'order': next_seq()}})
local_event_ProjectUploadDate = LocalEvent({'group': 'Project Information', 'schema': {'type': 'string', 'order': next_seq()}})

local_event_ControllerHardwareType = LocalEvent({'group': 'Controller Information', 'schema': {'type': 'string', 'order': next_seq()}})
local_event_ControllerChannelCapacity = LocalEvent({'group': 'Controller Information', 'schema': {'type': 'int', 'order': next_seq()}})
local_event_ControllerSerialNumber = LocalEvent({'group': 'Controller Information', 'schema': {'type': 'string', 'order': next_seq()}})
local_event_ControllerMemoryTotal = LocalEvent({'group': 'Controller Information', 'schema': {'type': 'string', 'order': next_seq()}})
local_event_ControllerMemoryUsed = LocalEvent({'group': 'Controller Information', 'schema': {'type': 'string', 'order': next_seq()}})
local_event_ControllerMemoryAvailable = LocalEvent({'group': 'Controller Information', 'schema': {'type': 'string', 'order': next_seq()}})
local_event_ControllerLuaMemoryUsed = LocalEvent({'group': 'Controller Information', 'schema': {'type': 'string', 'order': next_seq()}})
local_event_ControllerLuaMemoryAllowed = LocalEvent({'group': 'Controller Information', 'schema': {'type': 'string', 'order': next_seq()}})
local_event_ControllerStorageSize = LocalEvent({'group': 'Controller Information', 'schema': {'type': 'string', 'order': next_seq()}})
local_event_ControllerBootloaderVersion = LocalEvent({'group': 'Controller Information', 'schema': {'type': 'string', 'order': next_seq()}})
local_event_ControllerFirmwareVersion = LocalEvent({'group': 'Controller Information', 'schema': {'type': 'string', 'order': next_seq()}})
local_event_ControllerResetReason = LocalEvent({'group': 'Controller Information', 'schema': {'type': 'string', 'order': next_seq()}})
local_event_ControllerLastBootTime = LocalEvent({'group': 'Controller Information', 'schema': {'type': 'string', 'order': next_seq()}})
local_event_ControllerIPAddress = LocalEvent({'group': 'Controller Information', 'schema': {'type': 'string', 'order': next_seq()}})
local_event_ControllerSubnetMask = LocalEvent({'group': 'Controller Information', 'schema': {'type': 'string', 'order': next_seq()}})
local_event_ControllerBroadcastAddress = LocalEvent({'group': 'Controller Information', 'schema': {'type': 'string', 'order': next_seq()}})
local_event_ControllerDefaultGateway = LocalEvent({'group': 'Controller Information', 'schema': {'type': 'string', 'order': next_seq()}})
local_event_ControllerHostName = LocalEvent({'group': 'Controller Information', 'schema': {'type': 'string', 'order': next_seq()}})
local_event_ControllerDomainName = LocalEvent({'group': 'Controller Information', 'schema': {'type': 'string', 'order': next_seq()}})

local_event_LastContactDetect = LocalEvent({'group': 'Status', 'order': 99999+next_seq(), 'title': 'Last contact detect', 'schema': {'type': 'string'}})
local_event_Status = LocalEvent({'group': 'Status', 'order': 99999+next_seq(), 'schema': {'type': 'object', 'properties': {
        'level': {'type': 'integer', 'order': 1},
        'message': {'type': 'string', 'order': 2}}}})

def main():
  console.info('Recipe has started!')

@after_main
def start():
  # Disable node
  if param_disabled:
    console.error('Node is disabled. Doing nothing.')
    return

  # Get ip address
  global _fullAddress
  if is_blank((param_playerConfig or {}).get('ipAddress')):
    console.error('No Address has been specified, nothing to do!')
    return
  else:
    ipAddress = param_playerConfig.get('ipAddress')
    port = param_playerConfig.get('port') if not is_blank((param_playerConfig or {}).get('port')) else DEFAULT_PORT
    _fullAddress = str(ipAddress) + ':' + str(port)

  # Authenticate if required
  global _authenticationRequired
  if param_login.get('required'):
    _authenticationRequired = True
    GetAuthToken.call()
    console.info('Authentication timer starting now')
    _timer_auth.start()
  else:
    _authenticationRequired = False
    console.warn('Authentication not required. Please add log in information if access issues arise')

  # Confirm Pharos API version
  api = json_decode(callURL('/api/api_version', method='GET')).get('version')
  if api != API_VERSION:
    console.error('Check the API version of your Pharos device. This node requires %s, you are currently using %s' % (API_VERSION, api))
    return
  else:
    console.info('Using API v%s' % api)

  # Get Basic Information
  ProjectInformation.call()
  ControllerInformation.call()

  # Generate scene, trigger and timeline actions and events
  if (param_objects or {}).get('scene'):
    SceneInformation()
  if (param_objects or {}).get('trigger'):
    TriggerInformation()
  if (param_objects or {}).get('timeline'):
    TimelineInformation()

  # Start status polling
  _timer_status.start()

_timer_auth = Timer(lambda: GetAuthToken.call(), AUTH_TIMEOUT - 30, 10, stopped=True)
_timer_status = Timer(lambda: StatusCheck.call(), STATUS_CHECK_INTERVAL, 10, stopped=True) 

### HTTP Communications

_busy = False

def callURL(command, forceLog=False, method=None, query=None, headers=None, contentType=None, post=None):
    # Avoid simultaneous calls by tracking one at a time
    global _busy
    if _busy:
        return False
    _busy = True

    try:
        url = 'http://%s%s' % (_fullAddress, command)

        if forceLog: console.info('req: url%s' % url)
        else: log(1, 'req: url%s' % url)

        # No access token if not required, or when authenticating
        if (not _authenticationRequired) or (command != '/authenticate'):
          if not headers:
            headers = {}
          headers['Authorization'] = 'Bearer %s' % local_event_AuthToken.getArg()

        try:
            timestamp = system_clock()
            # get_url(url, method=None, query=None, username=None, password=None, headers=None, contentType=None, post=None, connectTimeout=10, readTimeout=15, fullResponse=False)
            resp = get_url(url, method=method, query=query, headers=headers, contentType=contentType, post=post, connectTimeout=5, readTimeout=5, fullResponse=True)

            if not(resp.statusCode >= 200 and resp.statusCode < 300):  # 200 codes are success
              raise Exception(str(resp.statusCode) + " Error: " + str(resp.reasonPhrase))

        except Exception, e:
            msg = 'get_url: failed (took %0.1f) with "%s"' % ((system_clock() - timestamp) / 1000.0, e)

            if forceLog: console.warn(msg)
            else:        warn(1, msg)

            return False

        log(1, 'resp: %s' % resp.content)

        global _lastReceive
        _lastReceive = system_clock()

        return resp.content
    
    finally:
      _busy = False

### Information and Authentication

@local_action({'title': 'Auth', 'group': 'Authentication'})
def GetAuthToken():
  # Only try to authenticate if it is required!
  if _authenticationRequired:
    req =  {'username': param_login.get('username') if not is_blank((param_login or {}).get('username')) else DEFAULT_USERNAME, 
            'password': param_login.get('password') if not is_blank((param_login or {}).get('password')) else DEFAULT_PASSWORD}
    resp = callURL('/authenticate', method='POST', contentType='application/json', post=json_encode(req))
    result = json_decode(resp) 

    local_event_AuthToken.emit(result.get('token'))

@local_action({'title': 'Poll', 'group': 'Project Information'})
def ProjectInformation():
  resp = callURL('/api/project', method='GET')
  result = json_decode(resp)
  
  local_event_ProjectName.emit(result.get('name'))
  local_event_ProjectAuthor.emit(result.get('author'))
  local_event_ProjectFileName.emit(result.get('filename'))
  local_event_ProjectUniqueID.emit(result.get('unique_id'))
  local_event_ProjectUploadDate.emit(result.get('upload_date'))

@local_action({'title': 'Poll', 'group': 'Controller Information'})
def ControllerInformation():
  resp = callURL('/api/system', method='GET')
  result = json_decode(resp)
  
  local_event_ControllerHardwareType.emit(result.get('hardware_type'))
  local_event_ControllerChannelCapacity.emit(result.get('channel_capacity'))
  local_event_ControllerSerialNumber.emit(result.get('serial_number'))
  local_event_ControllerMemoryTotal.emit(result.get('memory_total'))
  local_event_ControllerMemoryUsed.emit(result.get('memory_used'))
  local_event_ControllerMemoryAvailable.emit(result.get('memory_available'))
  local_event_ControllerLuaMemoryUsed.emit(result.get('lua_memory_used'))
  local_event_ControllerLuaMemoryAllowed.emit(result.get('lua_memory_available'))
  local_event_ControllerStorageSize.emit(result.get('storage_size'))
  local_event_ControllerBootloaderVersion.emit(result.get('bootloader_version'))
  local_event_ControllerFirmwareVersion.emit(result.get('firmware_version'))
  local_event_ControllerResetReason.emit(result.get('reset_reason'))
  local_event_ControllerLastBootTime.emit(result.get('last_boot_time'))
  local_event_ControllerIPAddress.emit(result.get('ip_address'))
  local_event_ControllerSubnetMask.emit(result.get('subnet_mask'))
  local_event_ControllerBroadcastAddress.emit(result.get('broadcast_address'))
  local_event_ControllerDefaultGateway.emit(result.get('default_gateway'))
  local_event_ControllerHostName.emit(result.get('host_name'))
  local_event_ControllerDomainName.emit(result.get('domain_name'))

### Scenes

def SceneInformation():
  # GET /api/scene sample scene object {'num': 1, 'name': 'Name', 'group': 'Group', 'group_num': 1, 'state': 'none', 'onstage': true}
  resp = callURL('/api/scene', method='GET')
  result = json_decode(resp).get('scenes')

  for scene in sorted(result, key = lambda x: x['group_num']):
    InitScene(scene)
  # for group in set([scene.get('group_num') for scene in result]):
  #   InitSceneGroup(group)

def InitSceneGroup(group):
  log(1, 'InitSceneGroup: %s' % group)
  e = create_local_event('SceneGroup%s' % group, {'title': 'Scene Group: %s' % group, 'group': 'Scene Group %s' % group, 'schema': {'type': 'string', 'enum': ['On', 'Off']}})

  def handler(arg):
    SelectScenes(group, arg)
    e.emit(arg)

  a = create_local_action('SceneGroup%s' % group, handler, {'title': 'Scene Group: %s' % group, 'group': 'Scene Group %s' % group, 'schema': {'type': 'string', 'enum': ['On', 'Off']}})

def InitScene(scene):
  log(1, 'InitScene: %s %s' % (scene.get('name'), scene.get('group_num')))
  e = create_local_event('Scene%s' % scene.get('num'), {'title': 'Scene: %s' % scene.get('name'), 'group': 'Scene Group %s' % scene.get('group_num'), 'schema': {'type': 'string', 'enum': ['On', 'Off']}})

  def handler(arg):
    # POST /api/scene sample payload {'action': 'start', 'num': 1, 'fade': 2.0, 'group': 1, 'same_group': false}  fade/group/same_group are optional
    req = {'num': scene.get('num')}
    if arg == 'On':
      req['action'] = 'start'
      e.emit('On')
      log(1, 'On. Starting %s' % req.get('num'))

    if arg == 'Off':
      req['action'] = 'release'
      e.emit('Off')
      log(1, 'Off. Releasing %s' % req.get('num'))
    
    callURL('/api/scene', headers={'Content-Type': 'application/json'}, post=json_encode(req))

  a = create_local_action('Scene%s' % scene.get('num'), handler, {'title': 'Scene: %s' % scene.get('name'), 'group': 'Scene Group %s' % scene.get('group_num'), 'schema': {'type': 'string', 'enum': ['On', 'Off']}})

def SceneStatus():
  # GET /api/scene sample scene object {'num': 1, 'name': 'Name', 'group': 'Group', 'group_num': 1, 'state': 'none', 'onstage': true}
  resp = callURL('/api/scene', method='GET')
  result = json_decode(resp).get('scenes')

  for scene in result:
    state = scene.get('state')
    if state == 'none' or state == 'released':
      arg = 'Off'
    elif state == 'started':
      arg = 'On'
    else:
      warn(1, 'SceneStatus: unknown state %s' % state)
      arg = 'Off'
    lookup_local_event('Scene%s' % scene.get('num')).emit(arg)

def AllScenes(arg):
  # GET /api/scene sample scene object {'num': 1, 'name': 'Name', 'group': 'Group', 'group_num': 1, 'state': 'none', 'onstage': true}
  resp = callURL('/api/scene', method='GET')
  result = json_decode(resp).get('scenes')

  for scene in result:
    lookup_local_action('Scene%s' % scene.get('num')).call(arg)

def SelectScenes(group, arg):
  # GET /api/scene sample scene object {'num': 1, 'name': 'Name', 'group': 'Group', 'group_num': 1, 'state': 'none', 'onstage': true}
  resp = callURL('/api/scene', method='GET')
  result = json_decode(resp).get('scenes')

  for scene in result:
    if scene.get('group_num') == group:
      lookup_local_action('Scene%s' % scene.get('num')).call(arg)

### Timelines

def TimelineInformation():
  # GET /api/timeline sample timeline object {'num': 1, 'name': 'Name', 'group': 'Group', 'group_num': 1, 'length': 10000, 'source_bus': 'internal', 'timecode_format': 'SMPTE30', 'audio_band': 0, 'audio_channel': 'combined', 'audio_peak': false, 'time_offset': 5000, 'state': 'none', 'onstage': true, 'position': 1000, 'priority': 'normal', 'custom_properties': {}}
  resp = callURL('/api/timeline', method='GET')
  result = json_decode(resp).get('timelines')

  for timeline in sorted(result, key = lambda x: x['group_num']):
    InitTimeline(timeline)
  # for group in set([timeline.get('group_num') for timeline in result]):
  #   InitTimelineGroup(group)

def InitTimelineGroup(group):
  log(1, 'InitTimelineGroup: %s' % group)
  e = create_local_event('TimelineGroup%s' % group, {'title': 'Timeline Group: %s' % group, 'group': 'Timeline Group %s' % group, 'schema': {'type': 'string', 'enum': ['On', 'Off']}})

  def handler(arg):
    SelectTimelines(group, arg)
    e.emit(arg)

  a = create_local_action('TimelineGroup%s' % group, handler, {'title': 'Timeline Group: %s' % group, 'group': 'Timeline Group %s' % group, 'schema': {'type': 'string', 'enum': ['On', 'Off']}})

def InitTimeline(timeline):
  log(1, 'InitTimeline: %s %s' % (timeline.get('name'), timeline.get('group_num')))
  e = create_local_event('Timeline%s' % timeline.get('num'), {'title': 'Timeline: %s' % timeline.get('name'), 'group': 'Timeline Group %s' % timeline.get('group_num'), 'schema': {'type': 'string', 'enum': ['On', 'Off']}})

  def handler(arg):
    # POST /api/timeline sample payload {'action': 'start', 'num': 1, 'fade': 2.0, 'group': 'Group', 'same_group': false, 'rate': '0.1'} fade/group/same_group/rate are optional
    req = {'num': timeline.get('num')}
    if arg == 'On':
      req['action'] = 'start'
      e.emit('On')
      log(1, 'On. Starting %s' % req.get('num'))

    if arg == 'Off':
      req['action'] = 'release'
      e.emit('Off')
      log(1, 'Off. Releasing %s' % req.get('num'))
    
    callURL('/api/timeline', headers={'Content-Type': 'application/json'}, post=json_encode(req))

  a = create_local_action('Timeline%s' % timeline.get('num'), handler, {'title': 'Timeline: %s' % timeline.get('name'), 'group': 'Timeline Group %s' % timeline.get('group_num'), 'schema': {'type': 'string', 'enum': ['On', 'Off']}})

def TimelineStatus():
  # GET /api/timeline sample timeline object {'num': 1, 'name': 'Name', 'group': 'Group', 'group_num': 1, 'length': 10000, 'source_bus': 'internal', 'timecode_format': 'SMPTE30', 'audio_band': 0, 'audio_channel': 'combined', 'audio_peak': false, 'time_offset': 5000, 'state': 'none', 'onstage': true, 'position': 1000, 'priority': 'normal', 'custom_properties': {}}
  resp = callURL('/api/timeline', method='GET')
  result = json_decode(resp).get('timelines')

  for timeline in result:
    state = timeline.get('state')
    if state == 'none' or state == 'released' or state == 'holding_at_end' or state == 'paused':
      arg = 'Off'
    elif state == 'running':
      arg = 'On'
    else:
      warn(1, 'TimelineStatus: unknown state %s' % state)
      arg = 'Off'
    lookup_local_event('Timeline%s' % timeline.get('num')).emit(arg)

def SelectTimelines(group, arg):
  # GET /api/timeline sample timeline object {'num': 1, 'name': 'Name', 'group': 'Group', 'group_num': 1, 'length': 10000, 'source_bus': 'internal', 'timecode_format': 'SMPTE30', 'audio_band': 0, 'audio_channel': 'combined', 'audio_peak': false, 'time_offset': 5000, 'state': 'none', 'onstage': true, 'position': 1000, 'priority': 'normal', 'custom_properties': {}}
  resp = callURL('/api/timeline', method='GET')
  result = json_decode(resp).get('timelines')

  for timeline in result:
    if timeline.get('group_num') == group:
      lookup_local_action('Timeline%s' % timeline.get('num')).call(arg)

### Triggers

def TriggerInformation():
  # GET /api/trigger sample trigger object {'type': 'Startup', 'num': 1, 'name': 'Name', 'group': '#e18383', 'description': 'This is a trigger', 'conditions': [{'text': 'condition'}], 'actions': [{'text': 'action'}]}
  resp = callURL('/api/trigger', method='GET')
  result = json_decode(resp).get('triggers')

  for trigger in sorted(result, key=lambda x: x['group_num']):
    InitTrigger(trigger)

def InitTrigger(trigger):
  log(1, 'InitTrigger: %s %s' % (trigger.get('name'), trigger.get('group')))
  
  def handler(arg):
    # POST /api/trigger sample payload {'num': 1, 'var': 'string', 'conditions': true} var/conditions are optional
    req = {'num': trigger.get('num')}
    callURL('/api/trigger', headers={'Content-Type': 'application/json'}, post=json_encode(req))

  a = create_local_action('Trigger%s' % trigger.get('num'), handler, {'title': 'Trigger %s' % trigger.get('name'), 'group': 'Trigger Group %s' % trigger.get('group'), 'schema': {'type': 'string', 'enum': ['On', 'Off']}})

### Status

@local_action({'title': 'Poll', 'group': 'Status'})
def StatusCheck():
  if param_objects.get('scene'):
    SceneStatus()
  if param_objects.get('timeline'):
    TimelineStatus()

  diff = (system_clock() - _lastReceive) / 1000.0 # in secs

  if diff > STATUS_CHECK_INTERVAL:
    previous_contact_value = local_event_LastContactDetect.getArg()
    
    if previous_contact_value == None:
      message = 'Never seen'
    else:
      previous_contact = date_parse(previous_contact_value)
      message = 'Missing %s' % FormatPeriod(previous_contact)
    local_event_Status.emit({'level': 2, 'message': message})
    
  else:
    local_event_LastContactDetect.emit(str(date_now()))
    local_event_Status.emit({'level': 0, 'message': 'OK'})

def FormatPeriod(date, as_instant=False):
  """Takes in a date object and returns the phrase to be displayed in the dashboard"""

  if date == None:
    return 'for unknown period'
    
  time_difference = (date_now().getMillis() - date.getMillis()) / 1000 / 60 # in mins

  if time_difference < 0:
    return 'never ever'
  elif time_difference == 0:
    return 'for <1 min' if not as_instant else '<1 min ago'
  elif time_difference < 60:
    return ('for <%s mins' if not as_instant else '<%s mins ago') % time_difference
  elif time_difference < 60*24:
    return ('since %s' if not as_instant else 'at %s') % date.toString('h:mm:ss a')
  else:
    return ('since %s' if not as_instant else 'at %s') % date.toString('E d-MMM h:mm:ss a')

### Logging

local_event_LogLevel = LocalEvent({'group': 'Debug', 'order': 10000+next_seq(), 'desc': 'Use this to ramp up the logging (with indentation)', 'schema': {'type': 'integer'}})

def warn(level, msg):
  if local_event_LogLevel.getArg() >= level:
    console.warn(('  ' * level) + msg)

def log(level, msg):
  if local_event_LogLevel.getArg() >= level:
    console.log(('  ' * level) + msg)