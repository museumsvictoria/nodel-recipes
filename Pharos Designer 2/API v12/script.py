'''
**Pharos Designer** HTTP API v12

---

`REV 1.44 2026.05.26 azuell + dargs`

* API version 12.0 (latest) Pharos Designer version 2.16.2 (latest)
* Includes optional authentication using username/password
* Automatically generates actions/events from desired objects (Scenes, Timelines, Triggers) sorted by groups
* Updates events with state from Pharos as part of status checking, with default 2s delay for fade

**MANUAL**

* [Pharos API Documentation](https://pharos-designer-controller-api.readthedocs.io/en/latest/http-api/index.html)

**REVISION HISTORY**

* rev. 1.44: Additional action/event for objects for use with frontend dynamic select, sorted by Object Groups
    * eg *<dynamicselect class='btn-default' data='ObjectGroupNameSelect' action='ObjectGroupNameSelect'/>*
* rev. 1.43: Bug fixes - no authentication required, no status if no objects
    * Change action/event names to include Pharos name
    * Include all infomation in object events
    * Condense project/controller information to single event
* rev. 1.42: Pharos Designer update and new API - no change to script
* *full revision history available in multiline string literal below to keep Nodel summary short*

'''

'''
**FULL REVISION HISTORY**

* rev. 1.41: dargs adding back in On/Off events for scenes and timelines (Scene%sOnOff/Timeline%sOnOff) and Debug +/- actions
* rev. 1.4: Add full suite of variables to scene and timeline local action arguments
    * Rework group actions
* rev. 1.3: For scenes and timelines, allow for local action arguments to reflect possible actions, and local event arguments to reflect possible states
    * Add (default) two second delay for status checks after an action is called
    * Replace hex codes with colour names for trigger groups
* rev. 1.2: Add single button group control for objects (Scenes, Timelines, Triggers)
* rev. 1.1: <s>Add 'toggle' Pharos action to scenes and timeline actions without arg given</s> removed rev. 1.3
* rev. 1: Initial upload
'''

DEFAULT_PORT = 80

API_VERSION = 12

DEFAULT_USERNAME = 'admin'
DEFAULT_PASSWORD = 'admin'

AUTH_TIMEOUT          = 5 * 60 # seconds
STATUS_CHECK_INTERVAL = 75 # seconds
DELAY                 = 2 # seconds

_fullAddress = None

_authenticationRequired = False
_username = None
_password = None

_lastReceive = 0

param_disabled = Parameter({'title': 'Disable this node', 'schema': {'type': 'boolean'}})

param_playerConfig = Parameter({'title': 'Pharos Config', 'schema': {'type': 'object', 'properties': {
  'ipAddress': {'title': 'IP Address', 'type': 'string',  'hint': 'ip',          'order': 1},
  'port':      {'title': 'Port',       'type': 'string',  'hint': DEFAULT_PORT,  'order': 2}}}})

param_login = Parameter({'title': 'Pharos Login', 'schema': {'type': 'object', 'properties': {
  'required': {'title': 'Require Authentication?', 'type': 'boolean', 'order': 1},
  'username': {'title': 'Username',                'type': 'string',  'hint': DEFAULT_USERNAME, 'order': 2},
  'password': {'title': 'Password',                'type': 'string',  'hint': DEFAULT_PASSWORD, 'order': 3}}}})

param_objects = Parameter({'title': 'Pharos Objects', 'schema': {'type': 'object', 'properties': {
  'scene':    {'title': 'Scenes',    'type': 'boolean', 'order': 1},
  'timeline': {'title': 'Timelines', 'type': 'boolean', 'order': 2},
  'trigger':  {'title': 'Triggers',  'type': 'boolean', 'order': 3}}}})

local_event_AuthToken = LocalEvent({'group': 'Authentication', 'schema': {'type': 'string'}})

local_event_ProjectInformation = LocalEvent({'group': 'Project Information', 'order': next_seq(), 'schema': {'type': 'object', 'properties': {
  'name':        {'title': 'Name',        'type': 'string', 'order': 1},
  'author':      {'title': 'Author',      'type': 'string', 'order': 2},
  'filename':    {'title': 'File Name',   'type': 'string', 'order': 3},
  'unique_id':   {'title': 'Unique ID',   'type': 'string', 'order': 4},
  'upload_date': {'title': 'Upload Date', 'type': 'string', 'order': 5}}}})

local_event_ControllerInformation = LocalEvent({'group': 'Controller Information', 'order': next_seq(), 'schema': {'type': 'object', 'properties': {
  'hardware_type':       {'title': 'Hardware Type',       'type': 'string',  'order': 1},
  'channel_capacity':    {'title': 'Channel Capacity',    'type': 'integer', 'order': 2},
  'serial_number':       {'title': 'Serial Number',       'type': 'string',  'order': 3},
  'memory_total':        {'title': 'Memory Total',        'type': 'string',  'order': 4},
  'memory_used':         {'title': 'Memory Used',         'type': 'string',  'order': 5},
  'memory_available':    {'title': 'Memory Available',    'type': 'string',  'order': 6},
  'lua_memory_used':     {'title': 'Lua Memory Used',     'type': 'string',  'order': 7},
  'lua_memory_allowed':  {'title': 'Lua Memory Allowed',  'type': 'string',  'order': 8},
  'storage_size':        {'title': 'Storage Size',        'type': 'string',  'order': 9},
  'bootloader_version':  {'title': 'Bootloader Version',  'type': 'string',  'order': 10},
  'firmware_version':    {'title': 'Firmware Version',    'type': 'string',  'order': 11},
  'reset_reason':        {'title': 'Reset Reason',        'type': 'string',  'order': 12},
  'last_boot_time':      {'title': 'Last Boot Time',      'type': 'string',  'order': 13},
  'ip_address':          {'title': 'IP Address',          'type': 'string',  'order': 14},
  'subnet_mask':         {'title': 'Subnet Mask',         'type': 'string',  'order': 15},
  'broadcast_address':   {'title': 'Broadcast Address',   'type': 'string',  'order': 16},
  'default_gateway':     {'title': 'Default Gateway',     'type': 'string',  'order': 17},
  'host_name':           {'title': 'Host Name',           'type': 'string',  'order': 18},
  'domain_name':         {'title': 'Domain Name',         'type': 'string',  'order': 19}}}})

local_event_LastContactDetect = LocalEvent({'group': 'Status', 'order': 99999+next_seq(), 'title': 'Last contact detect', 'schema': {'type': 'string'}})
local_event_Status = LocalEvent({'group': 'Status', 'order': 99999+next_seq(), 'schema': {'type': 'object', 'properties': {
  'level':   {'type': 'integer', 'order': 1},
  'message': {'type': 'string',  'order': 2}}}})

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
  if not param_playerConfig or 'ipAddress' not in param_playerConfig:
    console.error('No Address has been specified, nothing to do!')
    return
  else:
    ipAddress = param_playerConfig.get('ipAddress')
    port = DEFAULT_PORT if 'port' not in param_playerConfig else param_playerConfig.get('port')
    _fullAddress = str(ipAddress) + ':' + str(port)

  # Authenticate if required
  global _authenticationRequired
  global _username, _password
  if param_login and param_login.get('required'):
    _authenticationRequired = True
    _username = DEFAULT_USERNAME if 'username' not in param_login else param_login.get('username')
    _password = DEFAULT_PASSWORD if 'password' not in param_login else param_login.get('password')
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
  if param_objects:
    if param_objects.get('scene'):
      SceneInformation()
    if param_objects.get('timeline'):
      TimelineInformation()
    if param_objects.get('trigger'):
      TriggerInformation()
  
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
    else: info(1, 'req: url%s' % url)

    # No access token if not required, or when authenticating
    if (not _authenticationRequired) or (command != '/authenticate'):
      if not headers:
        headers = {}
      headers['Authorization'] = 'Bearer %s' % local_event_AuthToken.getArg()
      headers['Connection'] = 'close'

    try:
      timestamp = system_clock()
      # get_url(url, method=None, query=None, username=None, password=None, headers=None, contentType=None, post=None, connectTimeout=10, readTimeout=15, fullResponse=False)
      resp = get_url(url, method=method, query=query, headers=headers, contentType=contentType, post=post, fullResponse=True)

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
    req = {'username': _username, 'password': _password}
    resp = callURL('/authenticate', method='POST', contentType='application/json', post=json_encode(req))
    result = json_decode(resp) 

    local_event_AuthToken.emit(result.get('token'))

@local_action({'title': 'Poll', 'group': 'Project Information'})
def ProjectInformation():
  result = json_decode(callURL('/api/project', method='GET'))
  local_event_ProjectInformation.emit({
    'name':        result.get('name'),
    'author':      result.get('author'),
    'filename':    result.get('filename'),
    'unique_id':   result.get('unique_id'),
    'upload_date': result.get('upload_date')})

@local_action({'title': 'Poll', 'group': 'Controller Information'})
def ControllerInformation():
  result = json_decode(callURL('/api/system', method='GET'))
  local_event_ControllerInformation.emit({
    'hardware_type':      result.get('hardware_type'),
    'channel_capacity':   result.get('channel_capacity'),
    'serial_number':      result.get('serial_number'),
    'memory_total':       result.get('memory_total'),
    'memory_used':        result.get('memory_used'),
    'memory_available':   result.get('memory_available'),
    'lua_memory_used':    result.get('lua_memory_used'),
    'lua_memory_allowed': result.get('lua_memory_available'),
    'storage_size':       result.get('storage_size'),
    'bootloader_version': result.get('bootloader_version'),
    'firmware_version':   result.get('firmware_version'),
    'reset_reason':       result.get('reset_reason'),
    'last_boot_time':     result.get('last_boot_time'),
    'ip_address':         result.get('ip_address'),
    'subnet_mask':        result.get('subnet_mask'),
    'broadcast_address':  result.get('broadcast_address'),
    'default_gateway':    result.get('default_gateway'),
    'host_name':          result.get('host_name'),
    'domain_name':        result.get('domain_name')})

### Scenes

SCENE_ACTIONS = ['start', 'start_release_others', 'release', 'toggle']
SCENE_STATES = ['none', 'started']

def SceneInformation():
  # GET /api/scene sample scene object {'num': 1, 'name': 'Name', 'group': 'Group', 'group_num': 1, 'state': 'none', 'onstage': true}
  resp = callURL('/api/scene', method='GET')
  result = json_decode(resp).get('scenes')

  for scene in sorted(result, key = lambda x: x['num']):
    InitScene(scene)
  for group in set([scene.get('group_num') for scene in result]):
    InitSceneGroup(group)

def InitSceneGroup(group):
  log(1, 'InitSceneGroup: %s' % group)
  
  def handler(arg):
    if arg:
      # In a group only need to call SceneStatus once here and not at the scene level
      arg['status'] = False
      SelectScenes(group, arg)
      call(SceneStatus, delay=DELAY if 'fade' not in arg else arg.get('fade'))
    else:
      warn(1, 'No argument given. Doing nothing')
      return
    
  a = create_local_action('SceneGroup%s' % group, handler, {'title': 'Scene GROUP: %s' % group, 'group': 'Scene Group %s' % group, 'order': next_seq(),
    'schema': {'type': 'object', 'properties': {
      'action': {'title': 'Action',                          'type': 'string', 'enum': ['start', 'release', 'toggle'], 'order': 1},
      'fade':   {'title': 'Fade Time in Seconds (Optional)', 'type': 'number', 'hint': '2.0',                         'order': 2}}}})

  ### Dynamic select action/event for frontend
  all_scenes    = json_decode(callURL('/api/scene', method='GET')).get('scenes')
  select_scenes = sorted([scene for scene in all_scenes if scene.get('group_num') == group], key=lambda x: x['num'])
  select_items  = [{'key': '%sScene%s' % (scene.get('num'), CreateNodelSafeName(scene.get('name'))),
                    'value': '%s: %s' % (scene.get('num'), scene.get('name')) if scene.get('name') else str(scene.get('num'))}
                      for scene in select_scenes]

  e_select = create_local_event('SceneGroup%sSelect' % group, {
    'title': 'Scene GROUP %s: Select' % group, 'group': 'Scene Group %s' % group, 'order': next_seq(),
    'schema': {'type': 'array', 'items': {'type': 'object', 'properties': {
      'key':   {'title': 'Action', 'type': 'string', 'order': 1},
      'value': {'title': 'Label',  'type': 'string', 'order': 2}}}}})
  e_select.emit(select_items)

  def select_handler(arg):
    lookup_local_action(arg).call({'action': 'toggle'})

  a_select = create_local_action('SceneGroup%sSelect' % group, select_handler, {
    'title': 'Scene GROUP %s: Select' % group, 'group': 'Scene Group %s' % group, 'order': next_seq(),
    'schema': {'type': 'string', 'enum': [item['key'] for item in select_items]}})

def InitScene(scene):
  log(1, 'InitScene: %s %s' % (scene.get('name'), scene.get('group_num')))
  e = create_local_event('%sScene%s' % (scene.get('num'), CreateNodelSafeName(scene.get('name'))), {'title': 'Scene: %s' % scene.get('name'), 'group': 'Scene Group %s' % scene.get('group_num'), 'order': next_seq(),
    'schema': {'type': 'object', 'properties': {
      'num':       {'title': 'Number',    'type': 'integer', 'order': 1},
      'name':      {'title': 'Name',      'type': 'string',  'order': 2},
      'group':     {'title': 'Group',     'type': 'string',  'order': 3},
      'group_num': {'title': 'Group Num', 'type': 'integer', 'order': 4},
      'state':     {'title': 'State',     'type': 'string',  'order': 5},
      'onstage':   {'title': 'On Stage',  'type': 'boolean', 'order': 6}}}})
  e = create_local_event('%sScene%sOnOff' % (scene.get('num'), CreateNodelSafeName(scene.get('name'))), {'title': 'Scene: %s On Off Status' % scene.get('name'), 'group': 'Scene Group %s' % scene.get('group_num'), 'order': next_seq(), 'schema': {'type': 'string', 'enum': ['On', 'Off']}})


  def handler(arg):
    # POST /api/scene sample payload {'action': 'start', 'num': 1, 'fade': 2.0, 'group': 1, 'same_group': false}  fade/group/same_group are optional

    if arg:
      arg['num'] = scene.get('num')

      callURL('/api/scene', method='POST', contentType='application/json', post=json_encode(arg))
      if 'status' not in arg or arg.get('status'): call(SceneStatus, delay=DELAY if 'fade' not in arg else arg.get('fade'))

    else:
      warn(1, 'No argument given. Doing nothing')
      return

  a = create_local_action('%sScene%s' % (scene.get('num'), CreateNodelSafeName(scene.get('name'))), handler, {'title': 'Scene: %s' % scene.get('name'), 'group': 'Scene Group %s' % scene.get('group_num'), 'order': next_seq(),
    'schema': {'type': 'object', 'properties': {
      'action':     {'title': 'Action',                          'type': 'string',  'enum': SCENE_ACTIONS,                                 'order': 1},
      'fade':       {'title': 'Fade Time in Seconds (Optional)', 'type': 'number',  'hint': '2.0',                                         'order': 2},
      'group':      {'title': 'Group (Optional)',                'type': 'string',  'hint': 'Scene group name or number. Use ! to exclude', 'order': 3},
      'same_group': {'title': 'Same Group (Optional)',           'type': 'boolean',                                                        'order': 4}}}})

def SceneStatus():
  # GET /api/scene sample scene object {'num': 1, 'name': 'Name', 'group': 'Group', 'group_num': 1, 'state': 'none', 'onstage': true}
  resp = callURL('/api/scene', method='GET')
  if resp:
    result = json_decode(resp).get('scenes')

    for scene in result:
      state = scene.get('state')
      lookup_local_event('%sScene%s' % (scene.get('num'), CreateNodelSafeName(scene.get('name')))).emit({
        'num':       scene.get('num'),
        'name':      scene.get('name'),
        'group':     scene.get('group'),
        'group_num': scene.get('group_num'),
        'state':     state,
        'onstage':   scene.get('onstage')})

      if state == 'none':
        onoff = 'Off'
      elif state == 'started':
        onoff = 'On'
      else:
        warn(1, 'SceneStatus: unknown state %s' % state)
        onoff = 'Off'
      lookup_local_event('%sScene%sOnOff' % (scene.get('num'), CreateNodelSafeName(scene.get('name')))).emit(onoff)

def AllScenes(arg):
  # GET /api/scene sample scene object {'num': 1, 'name': 'Name', 'group': 'Group', 'group_num': 1, 'state': 'none', 'onstage': true}
  resp = callURL('/api/scene', method='GET')
  result = json_decode(resp).get('scenes')

  for scene in result:
    lookup_local_action('%sScene%s' % (scene.get('num'), CreateNodelSafeName(scene.get('name')))).call(arg)

def SelectScenes(group, arg):
  # GET /api/scene sample scene object {'num': 1, 'name': 'Name', 'group': 'Group', 'group_num': 1, 'state': 'none', 'onstage': true}
  resp = callURL('/api/scene', method='GET')
  result = json_decode(resp).get('scenes')

  for scene in result:
    if scene.get('group_num') == group:
      lookup_local_action('%sScene%s' % (scene.get('num'), CreateNodelSafeName(scene.get('name')))).call(arg)

### Timelines

TIMELINE_ACTIONS = ['start', 'start_release_others', 'release', 'toggle', 'pause', 'resume', 'set_rate', 'set_position']
TIMELINE_STATES = ['none', 'running', 'paused', 'holding_at_end', 'released']

def TimelineInformation():
  # GET /api/timeline sample timeline object {'num': 1, 'name': 'Name', 'group': 'Group', 'group_num': 1, 'length': 10000, 'source_bus': 'internal', 'timecode_format': 'SMPTE30', 'audio_band': 0, 'audio_channel': 'combined', 'audio_peak': false, 'time_offset': 5000, 'state': 'none', 'onstage': true, 'position': 1000, 'priority': 'normal', 'custom_properties': {}}
  resp = callURL('/api/timeline', method='GET')
  result = json_decode(resp).get('timelines')

  for timeline in sorted(result, key = lambda x: x['num']):
    InitTimeline(timeline)
  for group in set([timeline.get('group_num') for timeline in result]):
    InitTimelineGroup(group)

def InitTimelineGroup(group):
  log(1, 'InitTimelineGroup: %s' % group)
  
  def handler(arg):

    if arg:
      # In a group only need to call TimelineStatus once here and not at the timeline level
      arg['status'] = False
      SelectTimelines(group, arg)
      call(TimelineStatus, delay=DELAY if 'fade' not in arg else arg.get('fade'))
    else:
      warn(1, 'No argument given. Doing nothing')
      return

  a = create_local_action('TimelineGroup%s' % group, handler, {'title': 'Timeline GROUP: %s' % group, 'group': 'Timeline Group %s' % group, 'order': next_seq(),
    'schema': {'type': 'object', 'properties': {
      'action': {'title': 'Action',                          'type': 'string', 'enum': ['start', 'release', 'toggle', 'pause', 'resume'], 'order': 1},
      'fade':   {'title': 'Fade Time in Seconds (Optional)', 'type': 'number', 'hint': '2.0',                                            'order': 2}}}})

  ### Dynamic select action/event for frontend
  all_timelines = json_decode(callURL('/api/timeline', method='GET')).get('timelines')
  select_timelines = sorted([timeline for timeline in all_timelines if timeline.get('group_num') == group], key=lambda x: x['num'])
  select_items = [{'key':   '%sTimeline%s' % (timeline.get('num'), CreateNodelSafeName(timeline.get('name'))),
                  'value': '%s: %s' % (timeline.get('num'), timeline.get('name')) if timeline.get('name') else str(timeline.get('num'))}
                    for timeline in select_timelines]
  
  e_select = create_local_event('TimelineGroup%sSelect' % group, {
    'title': 'Timeline GROUP %s: Select' % group, 'group': 'Timeline Group %s' % group, 'order': next_seq(),
    'schema': {'type': 'array', 'items': {'type': 'object', 'properties': {
      'key':   {'title': 'Action', 'type': 'string', 'order': 1},
      'value': {'title': 'Label',  'type': 'string', 'order': 2}}}}})
  e_select.emit(select_items)
  
  def select_handler(arg):
    lookup_local_action(arg).call({'action': 'toggle'})
  
  a_select = create_local_action('TimelineGroup%sSelect' % group, select_handler, {
    'title': 'Timeline GROUP %s: Select' % group, 'group': 'Timeline Group %s' % group, 'order': next_seq(),
    'schema': {'type': 'string', 'enum': [item['key'] for item in select_items]}})

def InitTimeline(timeline):
  log(1, 'InitTimeline: %s %s' % (timeline.get('name'), timeline.get('group_num')))
  e = create_local_event('%sTimeline%s' % (timeline.get('num'), CreateNodelSafeName(timeline.get('name'))), {'title': 'Timeline: %s' % timeline.get('name'), 'group': 'Timeline Group %s' % timeline.get('group_num'), 'order': next_seq(),
    'schema': {'type': 'object', 'properties': {
      'num':              {'title': 'Number',           'type': 'integer', 'order': 1},
      'name':             {'title': 'Name',             'type': 'string',  'order': 2},
      'group':            {'title': 'Group',            'type': 'string',  'order': 3},
      'group_num':        {'title': 'Group Num',        'type': 'integer', 'order': 4},
      'state':            {'title': 'State',            'type': 'string',  'order': 5},
      'onstage':          {'title': 'On Stage',         'type': 'boolean', 'order': 6},
      'position':         {'title': 'Position (ms)',    'type': 'integer', 'order': 7},
      'length':           {'title': 'Length (ms)',      'type': 'integer', 'order': 8},
      'priority':         {'title': 'Priority',         'type': 'string',  'order': 9},
      'source_bus':       {'title': 'Source Bus',       'type': 'string',  'order': 10},
      'time_offset':      {'title': 'Time Offset (ms)', 'type': 'integer', 'order': 11},
      'timecode_format':  {'title': 'Timecode Format',  'type': 'string',  'order': 12},
      'audio_band':       {'title': 'Audio Band',       'type': 'integer', 'order': 13},
      'audio_channel':    {'title': 'Audio Channel',    'type': 'string',  'order': 14},
      'audio_peak':       {'title': 'Audio Peak',       'type': 'boolean', 'order': 15},
      'custom_properties':{'title': 'Custom Properties','type': 'object',  'order': 16}}}})
  e = create_local_event('%sTimeline%sOnOff' % (timeline.get('num'), CreateNodelSafeName(timeline.get('name'))), {'title': 'Timeline: %s On Off Status' % timeline.get('name'), 'group': 'Timeline Group %s' % timeline.get('group_num'), 'order': next_seq(), 'schema': {'type': 'string', 'enum': ["On", "Off"]}})

  def handler(arg):
    # POST /api/timeline sample payload {'action': 'start', 'num': 1, 'fade': 2.0, 'group': 'Group', 'same_group': false, 'rate': '0.1'} fade/group/same_group/rate are optional
    
    if arg:
      arg['num'] = timeline.get('num')

      callURL('/api/timeline', method='POST', contentType='application/json', post=json_encode(arg))
      if 'status' not in arg or arg.get('status'): call(TimelineStatus, delay=DELAY)

    else:
      warn(1, 'No argument given. Request not sent')
      return

  a = create_local_action('%sTimeline%s' % (timeline.get('num'), CreateNodelSafeName(timeline.get('name'))), handler, {'title': 'Timeline: %s' % timeline.get('name'), 'group': 'Timeline Group %s' % timeline.get('group_num'), 'order': next_seq(),
    'schema': {'type': 'object', 'properties': {
      'action':     {'title': 'Action',                          'type': 'string',  'enum': TIMELINE_ACTIONS,                                  'order': 1},
      'fade':       {'title': 'Fade Time in Seconds (Optional)', 'type': 'number',  'hint': '2.0',                                             'order': 2},
      'group':      {'title': 'Group (Optional)',                'type': 'string',  'hint': 'Timeline group name or number. Use ! to exclude', 'order': 3},
      'same_group': {'title': 'Same Group (Optional)',           'type': 'boolean',                                                            'order': 4},
      'rate':       {'title': 'Rate (set_rate)',                 'type': 'string',  'hint': 'required for set_rate',                           'order': 5},
      'position':   {'title': 'Position (set_position)',         'type': 'string',  'hint': 'only one required for set_position',              'order': 6},
      'time':       {'title': 'Time (set_position)',             'type': 'number',  'hint': 'only one required for set_position',              'order': 7},
      'flag':       {'title': 'Flag (set_position)',             'type': 'string',  'hint': 'only one required for set_position',              'order': 8}}}})

def TimelineStatus():
  # GET /api/timeline sample timeline object {'num': 1, 'name': 'Name', 'group': 'Group', 'group_num': 1, 'length': 10000, 'source_bus': 'internal', 'timecode_format': 'SMPTE30', 'audio_band': 0, 'audio_channel': 'combined', 'audio_peak': false, 'time_offset': 5000, 'state': 'none', 'onstage': true, 'position': 1000, 'priority': 'normal', 'custom_properties': {}}
  resp = callURL('/api/timeline', method='GET')
  if resp:
    result = json_decode(resp).get('timelines')

    for timeline in result:
      state = timeline.get('state')
      lookup_local_event('%sTimeline%s' % (timeline.get('num'), CreateNodelSafeName(timeline.get('name')))).emit({
        'num':               timeline.get('num'),
        'name':              timeline.get('name'),
        'group':             timeline.get('group'),
        'group_num':         timeline.get('group_num'),
        'state':             state,
        'onstage':           timeline.get('onstage'),
        'position':          timeline.get('position'),
        'length':            timeline.get('length'),
        'priority':          timeline.get('priority'),
        'source_bus':        timeline.get('source_bus'),
        'time_offset':       timeline.get('time_offset'),
        'timecode_format':   timeline.get('timecode_format'),
        'audio_band':        timeline.get('audio_band'),
        'audio_channel':     timeline.get('audio_channel'),
        'audio_peak':        timeline.get('audio_peak'),
        'custom_properties': timeline.get('custom_properties')})

      if state == 'none' or state == 'released' or state == 'holding_at_end' or state == 'paused':
        onoff = 'Off'
      elif state == 'running':
        onoff = 'On'
      else:
        warn(1, 'TimelineStatus: unknown state %s' % state)
        onoff = 'Off'
      lookup_local_event('%sTimeline%sOnOff' % (timeline.get('num'), CreateNodelSafeName(timeline.get('name')))).emit(onoff)

def SelectTimelines(group, arg):
  # GET /api/timeline sample timeline object {'num': 1, 'name': 'Name', 'group': 'Group', 'group_num': 1, 'length': 10000, 'source_bus': 'internal', 'timecode_format': 'SMPTE30', 'audio_band': 0, 'audio_channel': 'combined', 'audio_peak': false, 'time_offset': 5000, 'state': 'none', 'onstage': true, 'position': 1000, 'priority': 'normal', 'custom_properties': {}}
  resp = callURL('/api/timeline', method='GET')
  result = json_decode(resp).get('timelines')

  for timeline in result:
    if timeline.get('group_num') == group:
      lookup_local_action('%sTimeline%s' % (timeline.get('num'), CreateNodelSafeName(timeline.get('name')))).call(arg)

### Triggers

TRIGGER_GROUP_COLOURS = {'none': 'None', '#e18383': 'Red', '#edb283': 'Orange', '#f3dd75': 'Yellow', '#80ca80': 'Green', '#83c2c3': 'Blue', '#b47cb4': 'Purple'}

def TriggerInformation():
  # GET /api/trigger sample trigger object {'type': 'Startup', 'num': 1, 'name': 'Name', 'group': '#e18383', 'description': 'This is a trigger', 'conditions': [{'text': 'condition'}], 'actions': [{'text': 'action'}]}
  resp = callURL('/api/trigger', method='GET')
  result = json_decode(resp).get('triggers')

  for trigger in sorted(result, key=lambda x: x['group_num']):
    InitTrigger(trigger)
  for group in set([trigger.get('group') for trigger in result]):
    InitTriggerGroup(group)

def InitTriggerGroup(group):
  log(1, 'InitTriggerGroup: %s' % group)

  ### Normal group action/event
  group_name = TRIGGER_GROUP_COLOURS[group if group else 'none']

  def handler(arg):
    SelectTriggers(group, arg)
    call(lambda: StatusCheck.call(), delay=DELAY)

  a = create_local_action('TriggerGroup%s' % group_name, handler, {'title': 'Trigger GROUP: %s' % group_name, 'group': 'Trigger Group %s' % group_name, 'order': next_seq()})

  ### Dynamic select action/event for frontend
  all_triggers = json_decode(callURL('/api/trigger', method='GET')).get('triggers')
  select_triggers = sorted([trigger for trigger in all_triggers if trigger.get('group') == group], key=lambda x: x['num'])
  select_items = [{'key':   '%sTrigger%s' % (trigger.get('num'), CreateNodelSafeName(trigger.get('name'))),
                  'value': '%s: %s' % (trigger.get('num'), trigger.get('name')) if trigger.get('name') else str(trigger.get('num'))}
                    for trigger in select_triggers]

  e_select = create_local_event('TriggerGroup%sSelect' % group_name, {
    'title': 'Trigger GROUP %s: Select' % group_name, 'group': 'Trigger Group %s' % group_name, 'order': next_seq(),
    'schema': {'type': 'array', 'items': {'type': 'object', 'properties': {
      'key':   {'title': 'Action', 'type': 'string', 'order': 1},
      'value': {'title': 'Label',  'type': 'string', 'order': 2}}}}})
  e_select.emit(select_items)

  def select_handler(arg):
    lookup_local_action(arg).call()

  a_select = create_local_action('TriggerGroup%sSelect' % group_name, select_handler, {
    'title': 'Trigger GROUP %s: Select' % group_name, 'group': 'Trigger Group %s' % group_name, 'order': next_seq(),
    'schema': {'type': 'string', 'enum': [item['key'] for item in select_items]}})

def InitTrigger(trigger):
  log(1, 'InitTrigger: %s %s' % (trigger.get('name'), trigger.get('group')))

  group_name = TRIGGER_GROUP_COLOURS[trigger.get('group') if trigger.get('group') else 'none']

  e = create_local_event('%sTrigger%s' % (trigger.get('num'), CreateNodelSafeName(trigger.get('name'))), {
    'title': 'Trigger: %s' % trigger.get('name'), 'group': 'Trigger Group %s' % group_name, 'order': next_seq(),
    'schema': {'type': 'object', 'properties': {
      'num':         {'title': 'Number',      'type': 'integer', 'order': 1},
      'name':        {'title': 'Name',        'type': 'string',  'order': 2},
      'type':        {'title': 'Type',        'type': 'string',  'order': 3},
      'description': {'title': 'Description', 'type': 'string',  'order': 4},
      'conditions':  {'title': 'Conditions',  'type': 'string',  'order': 5},
      'actions':     {'title': 'Actions',     'type': 'string',  'order': 6}}}})
  e.emit({
    'num':         trigger.get('num'),
    'name':        trigger.get('name'),
    'type':        trigger.get('type'),
    'description': trigger.get('description'),
    'conditions':  ', '.join([(c.get('text') or '') for c in (trigger.get('conditions') or [])]),
    'actions':     ', '.join([(a.get('text') or '') for a in (trigger.get('actions') or [])])})

  def handler(arg):
    # POST /api/trigger sample payload {'num': 1, 'var': 'string', 'conditions': true} var/conditions are optional
    req = {'num': trigger.get('num')}
    callURL('/api/trigger', method='POST', contentType='application/json', post=json_encode(req))
    call(lambda: StatusCheck.call(), delay=DELAY)

  a = create_local_action('%sTrigger%s' % (trigger.get('num'), CreateNodelSafeName(trigger.get('name'))), handler, {'title': 'Trigger: %s' % trigger.get('name'), 'group': 'Trigger Group %s' % group_name, 'order': next_seq()})

def SelectTriggers(group, arg):
  # GET /api/trigger
  resp = callURL('/api/trigger', method='GET')
  result = json_decode(resp).get('triggers')

  for trigger in result:
    if trigger.get('group') == group:
      lookup_local_action('%sTrigger%s' % (trigger.get('num'), CreateNodelSafeName(trigger.get('name')))).call(arg)

### Status

@local_action({'title': 'Poll', 'group': 'Status'})
def StatusCheck():
  # Check project generally
  callURL('/api/project', method='GET')
  # Update status of specific objects as required
  if param_objects and param_objects.get('scene'):
    SceneStatus()
  if param_objects and param_objects.get('timeline'):
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

local_event_LogLevel = LocalEvent({'group': 'Debug', 'order': 100000 + next_seq(), 'desc': 'Use this to ramp up the logging (with indentation)', 'schema': {'type': 'integer'}})

@local_action({'group': 'Debug', 'title': '+', 'order': 100000 + next_seq() })
def increaseLogLevel():
  local_event_LogLevel.emit((local_event_LogLevel.getArg() or 0) + 1)

@local_action({'group': 'Debug', 'title': '-', 'order': 100000 + next_seq() })
def decreaseLogLevel():
  local_event_LogLevel.emit((local_event_LogLevel.getArg() or 0) - 1)

def info(level, msg):
  if local_event_LogLevel.getArg() >= level:
    console.info(('  ' * level) + msg)

def error(level, msg):
  if local_event_LogLevel.getArg() >= level:
    console.error(('  ' * level) + msg)

def warn(level, msg):
  if local_event_LogLevel.getArg() >= level:
    console.warn(('  ' * level) + msg)

def log(level, msg):
  if local_event_LogLevel.getArg() >= level:
    console.log(('  ' * level) + msg)

### Helper

def CreateNodelSafeName(name):
  # Strips names of punctuaion without looing content within brackets
  return ''.join(c for c in (name or '') if c.isalnum())