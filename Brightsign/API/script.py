'''
BrightSign monitoring only using its built-in API.

* includes snapshots on demand

ISSUES

* work needs to be done on this if authentication is required

`rev 3`

'''

param_IPAddress = Parameter({ 'schema': { 'type': 'string' }})


local_event_Uptime = LocalEvent({ 'order': next_seq(), 'schema': { 'type': 'string' }})

local_event_Name = LocalEvent({ 'order': next_seq(), 'schema': { 'type': 'string' }})

local_event_Desc = LocalEvent({ 'order': next_seq(), 'schema': { 'type': 'string' }})


local_event_Serial = LocalEvent({ 'group': 'Information', 'schema': { 'type': 'string', 'order': next_seq() }})
local_event_Model = LocalEvent({ 'group': 'Information', 'schema': { 'type': 'string', 'order': next_seq() }})
local_event_FW = LocalEvent({ 'group': 'Information', 'schema': { 'type': 'string', 'order': next_seq() }})
local_event_BootVersion = LocalEvent({ 'group': 'Information', 'schema': { 'type': 'string', 'order': next_seq() }})


local_event_Snapshot = LocalEvent({ 'schema': { 'type': 'string' }})

# e.g. > curl "http://192.168.110.11/api/v1/snapshot" -X "POST" -H "x-api-key: cf70"
@local_action({ 'title': 'Generate Snapshot' })
def Snapshot():
  resp = get_url('http://%s/api/v1/snapshot' % param_IPAddress, method='POST')
  
  # e.g. >> { "data":{"result":{"remoteSnapshotThumbnail":"data:image/jpeg;base64,/9j ...", 
  #           "filename":"/sd/remote_snapshots/img-2022-04-29-01-47-57.jpg","timestamp":"2022-04-29 13:47:59 AEST","devicename":"RG SC R"}}}
  
  result = json_decode(resp)['data']['result']
  local_event_Snapshot.emit(result['remoteSnapshotThumbnail'])
  
@local_action({ 'title': 'Poll', 'group': 'Information' })
def Information():
  resp = get_url('http://%s/api/v1/info' % param_IPAddress)
  
  global _lastReceive
  _lastReceive = system_clock()
  
  # e.g. >> {"data":{"result":{"serial":"D1E927000148","upTime":"297 days 1 hours 40 minutes","upTimeSeconds":25666854,"model":"XD234","FWVersion":"8.2.75","bootVersion":"7.1.53","family":"malibu","isPlayer":true,
  #         "power":{"result":{"battery":"absent","source":"AC","switch_mode":"hard"}},"poe":{"result":
  
  result = json_decode(resp)['data']['result']
  
  
  local_event_Uptime.emit(result['upTime'])
  local_event_Name.emit(result['networking']['result']['name'])
  local_event_Desc.emit(result['networking']['result']['description'])
  
  
  local_event_Serial.emit(result['serial'])
  local_event_Model.emit(result['model'])
  local_event_FW.emit(result['FWVersion'])
  local_event_BootVersion.emit(result['bootVersion'])
  local_event_IPAddress.emit([paramIPAddress])
  
Timer(lambda: Information.call(), 60, 5) # every minute, first after 5



# <!-- logging and status

local_event_Status = LocalEvent({ 'group': 'Status', 'order': 1, 'schema': { 'type': 'object', 'properties': {
  'level': { 'type': 'integer', 'order': 1 },
  'message': { 'type': 'string', 'order': 2 }}}})

_lastReceive = 0

# roughly, the last contact  
local_event_LastContactDetect = LocalEvent({'group': 'Status', 'title': 'Last contact detect', 'schema': {'type': 'string'}})
  
def statusCheck():
  diff = (system_clock() - _lastReceive)/1000.0 # (in secs)
  now = date_now()
  
  if diff > status_check_interval+15:
    previousContactValue = local_event_LastContactDetect.getArg()
    
    if previousContactValue == None: 
      message = 'Never been monitored'
    else:
      message = 'Unmonitorable %s' % formatPeriod(date_parse(previousContactValue))
      
    local_event_Status.emit({ 'level': 2, 'message': message })
    return
  
  local_event_Status.emit({'level': 0, 'message': 'OK'})
  
  local_event_LastContactDetect.emit(str(now))
  
status_check_interval = 60 # was 75

status_timer = Timer(statusCheck, status_check_interval)

def formatPeriod(dateObj, asInstant=False):
  if dateObj == None:       return 'for unknown period'

  now = date_now()
  diff = (now.getMillis() - dateObj.getMillis()) / 1000 / 60 # in mins
  
  if diff < 0:              return 'never ever'
  elif diff == 0:           return 'for <1 min' if not asInstant else '<1 min ago'
  elif diff < 60:           return ('for <%s mins' if not asInstant else '<%s mins ago') % diff
  elif diff < 60*24:        return ('since %s' if not asInstant else 'at %s') % dateObj.toString('h:mm a')
  else:                     return ('since %s' if not asInstant else 'on %s') % dateObj.toString('E d-MMM h:mm a')

local_event_LogLevel = LocalEvent({ 'group': 'Debug', 'order': 10000+next_seq(), 'desc': 'Use this to ramp up the logging (with indentation)',
                                    'schema': { 'type': 'integer' }})

@local_action({ 'group': 'Debug', 'order': 10000+next_seq() })
def RaiseLogLevel():
  local_event_LogLevel.emit((local_event_LogLevel.getArg() or 0) + 1)

@local_action({ 'group': 'Debug', 'order': 10000+next_seq() })
def LowerLogLevel():
  local_event_LogLevel.emit(max((local_event_LogLevel.getArg() or 0) - 1, 0))

def warn(level, msg):
  if (local_event_LogLevel.getArg() or 0) >= level:
    console.warn(('  ' * level) + msg)

def log(level, msg):
  if (local_event_LogLevel.getArg() or 0) >= level:
    console.log(('  ' * level) + msg)

# --!>
