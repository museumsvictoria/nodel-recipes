'''Wake On LAN and computer monitoring node'''

### Libraries this Node requires
import struct, socket, re



### Parameters used by this Node
param_macAddress = Parameter('{"title":"MAC Address","schema":{"type":"string"}}')



### Functions used by this Node
def sendMagicPacket(dst_mac_addr):
    if not re.match("[0-9a-f]{2}([:])[0-9a-f]{2}(\\1[0-9a-f]{2}){4}$", dst_mac_addr.lower()):
      raise ValueError('Incorrect MAC address format')
    addr_byte = dst_mac_addr.upper().split(':')
    hw_addr = struct.pack('BBBBBB', int(addr_byte[0], 16), int(addr_byte[1], 16), int(addr_byte[2], 16), int(addr_byte[3], 16), int(addr_byte[4], 16), int(addr_byte[5], 16))
    macpck = '\xff' * 6 + hw_addr * 16
    scks = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    scks.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    scks.sendto(macpck, ('<broadcast>', 9))



### Local actions this Node provides
def local_action_PowerOn(arg = None):
  """{"title":"PowerOn","desc":"PowerOn","group":"Power"}"""
  print 'Action PowerOn requested'
  sendMagicPacket(param_macAddress)
  
remote_action_PowerOff = RemoteAction()

### Main
def main(arg = None):
  # Start your script here.
  print 'Nodel script started.'
  
  
local_event_Status = LocalEvent({'group': 'Status', 'order': next_seq(), 'schema': {'type': 'object', 'properties': {
        'level': {'type': 'integer', 'order': 1},
        'message': {'type': 'string', 'order': 2}}}})

local_event_ComputerStatus = LocalEvent({'group': '(advanced)', 'order': 9999+next_seq(), 'schema': {'type': 'object', 'properties': {
        'level': {'type': 'integer', 'order': 1},
        'message': {'type': 'string', 'order': 2}}}})

def remote_event_ComputerStatus(arg=None):
  local_event_ComputerStatus.emit(arg)
  
  # this alway implies the computer is on, so set the on flag
  local_event_Power.emit('On')
  
  updateStatus()
  
# power on and power off
POWER_SCHEMA = {'type': 'string', 'enum': ['On', 'Off']}

local_event_DesiredPower = LocalEvent({'group': 'Power', 'order': next_seq(), 'schema': {'type': 'string', 'enum': ['On', 'Off']}})
local_event_Power = LocalEvent({'group': 'Power', 'order': next_seq(), 'schema': {'type': 'string', 'enum': ['Partially On', 'Partially Off', 'On', 'Off']}})

def local_action_Power(arg=None):
  '''{"group": "Power", "schema": {"type": "string", "enum": ["On", "Off"]}}'''
  local_event_DesiredPower.emit(arg)
  
  if arg == 'On':
    lookup_local_action('PowerOn').call()
    
  elif arg == 'Off':
    lookup_remote_action('PowerOff').call()
    
  updateStatus()

local_event_WiringStatus = LocalEvent({'group': 'Status', 'order': next_seq(), 'schema': {'type': 'string'}})

def checkWiringStatus():
  bindingState = lookup_remote_action('PowerOff').getBindingState()
  local_event_WiringStatus.emit(str(bindingState))
  
  updateStatus()

Timer(checkWiringStatus, 60, 7)

# performs the status aggregation
def updateStatus():
  now = date_now().getMillis()
  
  desiredPower = lookup_local_event('DesiredPower').getArg()
  if desiredPower is None:
    local_event_Status.emit({'level': 1, 'message': 'No desired status has been set yet.'})
    return
  
  elif desiredPower == 'On':
    # computer is supposed to be on so check wiring status
    wiringStatus = local_event_WiringStatus.getArg()
    
    if wiringStatus != 'Wired':
      last = local_event_ComputerStatus.getTimestamp()
      when = last.toString('E dd-MMM h:mm a') if last != None else "<never>"
      
      diff = now - (last.getMillis() if last != None else 0)
      if diff > 150000: # give it two and half minutes to boot up
        local_event_Status.emit({'level': 2, 'message': 'No connection from computer (last heard from %s)' % (when)})
      
      local_event_Power.emit('Partially On')
      
      return
    
    else:
      # wiring status is 'Wired', so pass through last computer status and power state
      lastStatus = local_event_ComputerStatus.getArg()
      local_event_Power.emit('On')
      
      if lastStatus == None:
        local_event_Status.emit({'level': 1, 'message': 'No status information from computer yet.'})
        
      else:
        # pass on last status
        local_event_Status.emit(lastStatus)
    
  else:
    # (desired power is Off, ensure off)
    timestamp = local_event_ComputerStatus.getTimestamp()
    last = 0 if timestamp == None else timestamp.getMillis()
    diff = now - last
    
    if diff < 30000:
      local_event_Power.emit('Partially Off')
      
    else:
      local_event_Power.emit('Off')
      local_event_Status.emit({'level': 0, 'message': 'OK (*)'})
