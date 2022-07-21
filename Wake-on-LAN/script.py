'''
Wake On LAN and computer monitoring node

 * _rev 2 - leakfix: uses managed UDP, allows for MAC address over remote binding (optional)_
'''

# <!-- Wake-on-LAN:

param_macAddress = Parameter({ 'title': 'MAC Address', 'schema': {'type': 'string', 'hint': '(or use MAC address binding if available)' }})

local_event_MACAddress = LocalEvent({'group': 'Addressing', 'order': next_seq(), 'schema': { 'type': 'string' }})

def remote_event_MACAddress(arg):
  if not param_macAddress: # param takes precedence, set at main()
    local_event_MACAddress.emit(arg)           

_wol = UDP(dest='255.255.255.255:9', received=lambda arg: console.info('wol: received [%s]'),
           sent=lambda arg: console.info('wol: sent packet (size %s)' % len(arg)))

def sendMagicPacket():
    macAddr = local_event_MACAddress.getArg() # will be parameter of remote event
    
    if is_blank(macAddr):
      return console.warn('No MAC address to use; cannot perform WOL operation')
    
    hw_addr = macAddr.replace('-', '').replace(':', '').decode('hex')
    macpck = '\xff' * 6 + hw_addr * 16
    _wol.send(macpck)

# -->

### Local actions this Node provides
def local_action_PowerOn(arg = None):
  """{"group": "Power"}"""
  lookup_local_action('Power').call('On')

def local_action_SendWOL(arg = None):
  """{"group": "Power"}"""
  print 'Sending WOL magic packet'
  sendMagicPacket()
  
remote_action_PowerOff = RemoteAction()

### Main
def main(arg = None):
  if param_macAddress: # parameter specified?
    local_event_MACAddress.emit(param_macAddress)
  
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
    lookup_local_action('SendWOL').call()
    
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
    
    if diff < 180000: # give it at least 3 minutes before determining it's off
      local_event_Power.emit('Partially Off')
      
    else:
      local_event_Power.emit('Off')
      local_event_Status.emit({'level': 0, 'message': 'OK (*)'})
        
# Remote events to activate actions   
def remote_event_Power(arg):
  lookup_local_action('Power').call(arg)
