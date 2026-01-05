'''
**Pharos API** - AZ 02/01/26

`REV 1`

Notes:

* No authentication
* Using HTTP (not HTTPS)
* API version 11.0 (latest) Pharos Designer version 2.15.3 (latest)

**MANUAL**

* [Pharos API Documentation](https://pharos-designer-controller-api.readthedocs.io/en/latest/http-api/index.html)

**REVISION HISTORY**

* rev. 1: initial

'''

DEFAULT_PORT = 9999

param_disabled = Parameter({'desc': 'Disables this node', 'schema': {'type': 'boolean'}})

param_ipAddress = Parameter({'title': 'IP Address', 'schema': {'type': 'string' }})

param_port = Parameter({'title': 'Port (HTTP)', 'schema': {'type': 'integer', 'hint': DEFAULT_PORT}})

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

import sys

def main():
  console.info("Recipe has started!")

  console.info("Using API v%s" % json_decode(call('/api/api_version', method='GET')).get('version'))


### HTTP Communications

_busy = False

def call(command, method=None, post=None, query=None, forceLog=False):
    # Avoid simultaneous calls by tracking one at a time
    global _busy
    if _busy:
        return False
    _busy = True

    try:
        url = 'http://%s:%s%s' % (param_ipAddress, param_port, command)

        if forceLog: console.info('req: url%s' % url)
        else: log(1, 'req: url%s' % url)

        try:
            timestamp = system_clock()
            resp = get_url(url, connectTimeout=5, readTimeout=5, query=query, post=post, method=method)
        except:
            e = sys.exc_info()[1]   # Tuple order is excType, value, trace
            msg = 'get_url: failed (took %0.1f) with "%s"' % ((system_clock()-timestamp)/1000.0, e)

            if forceLog: console.warn(msg)
            else:       warn(1, msg)

            return False

        log(1, 'resp: %s' % resp)

        global _lastReceive
        _lastReceive = system_clock()

        return resp
    
    finally:
        _busy = False

@local_action({'title': 'Auth', 'group': 'Authenticate'})
def Trigger():
  req = {"username": "admin", "password": "password"}
  resp = call('/authenticate', method='POST', post=json_encode(req), forceLog=True)
  console.log(resp)

@local_action({'title': 'Poll', 'group': 'Project Information'})
def ProjectInformation():
  console.info("Calling!")
  resp = call('/api/project', method='GET', forceLog=True)
  
  result = json_decode(resp)
  
  local_event_ProjectName.emit(result.get('name'))
  local_event_ProjectAuthor.emit(result.get('author'))
  local_event_ProjectFileName.emit(result.get('filename'))
  local_event_ProjectUniqueID.emit(result.get('unique_id'))
  local_event_ProjectUploadDate.emit(result.get('upload_date'))
  
@local_action({'title': 'Poll', 'group': 'Controller Information'})
def ControllerInformation():
  console.info("Calling!")
  resp = call('/api/system', method='GET', forceLog=True)
  
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
  
@local_action({'title': 'Poll', 'group': 'Scenes'})
def SceneInformation():
  console.info("Calling!")
  resp = call('/api/scene', method='GET', forceLog=True)
  
  result = json_decode(resp).get('scenes')
  console.log(result)
  
  names = [item for item in result if item.get('group_num') == 2 and '(1)' in item.get('name')]
  console.log(names)

@local_action({'title': 'Scene Test', 'group': 'Scenes'})
def Scene():
   # actions: start, start_release_others, release, toggle
    console.info("Calling scene POST")
    
    req = {
        "action": "toggle",
        "num": 211
    }

    resp = call('/api/scene', method='POST', post=json_encode(req), forceLog=True)

    console.log(resp)

@local_action({'title': 'Poll', 'group': 'Trigger'})
def TriggerInformation():
  console.info("Calling!")
  resp = call('/api/trigger', method='GET', forceLog=True)
  
  result = json_decode(resp).get('triggers')
  for trig in result:
      console.log(trig)
#   console.log(result[1].get('num'))
#   req = {
#     "num": result[1].get('num')
#   }
#   resp = call('/api/trigger', method='POST', post=json_encode(req), forceLog=True)
#   console.log(resp)

@local_action({'title': '100 manual', 'group': 'Trigger'})
def Trigger():
  req = {"num": 99}
  resp = call('/api/trigger', method='POST', post=json_encode(req), forceLog=True)
  console.log(resp)

@local_action({'title': '100 from call', 'group': 'Trigger'})
def Trigger100():
  console.info("Calling!")
  resp = call('/api/trigger', method='GET', forceLog=True)
  
  result = json_decode(resp).get('triggers')
  req = {"num": result[-1].get('num')}
  resp = call('/api/trigger', method='POST', post=json_encode(req), forceLog=True)
  console.log(resp)

# @local_action({'title': 'Ping'})
# def Ping():
#    resp = call('/api/beacon', method='POST', forceLog=True)
#    console.log(resp)

### Logging

local_event_LogLevel = LocalEvent({'group': 'Debug', 'order': 10000+next_seq(), 'desc': 'Use this to ramp up the logging (with indentation)', 'schema': {'type': 'integer'}})

def warn(level, msg):
  if local_event_LogLevel.getArg() >= level:
    console.warn(('  ' * level) + msg)

def log(level, msg):
  if local_event_LogLevel.getArg() >= level:
    console.log(('  ' * level) + msg)
