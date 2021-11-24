'''
Pure SNMP-based control of the **Servedge** PDUs.

Useful resources:

* **PDUMIB-201010105.mib** file contains the MIB file for the Serveredge PDUs (not needed for operation, for documentation only)
* sourceforge.net/projects/jmibbrowser project is a decent little MIB browser

_rev 2b_

* port labelling exposed
* less console noise
* optional IP addressing using remote binding
* enforcement period after action use
* "Power Off" Guarding to accommodate graceful / sequenced shutdown

NOTE / TODO:

  * "Power Off" Guarding requires at least one successful connection before Bindings section can be filled in.
'''

# <! -- imports

try:
  from org.nodel.snmp import NodelSnmp
except:
  console.error('SNMP dependency missing - this recipe requires Nodel r365 or later')
  raise
  
from org.snmp4j.mp import SnmpConstants
from org.snmp4j import CommunityTarget
from org.snmp4j.smi import OctetString, UdpAddress, VariableBinding, OID, Integer32
from org.snmp4j import Snmp, PDU

# --- !>


# <!-- parameters

param_disabled = Parameter({'desc': 'Disables this node', 'schema': {'type': 'boolean'}})

param_ipAddress = Parameter({'schema': {'type': 'string', 'hint': '(overrides bindings use)' }})

local_event_IPAddress = LocalEvent({ 'group': 'Addressing', 'order': next_seq(), 'schema': { 'type': 'string' }})

def remote_event_IPAddress(arg):
  if is_blank(param_ipAddress) and arg != local_event_IPAddress.getArg():
    # update IP address only if parameter is not set
    console.warn('IP address updated to "%s"; will restart node' % arg)
    local_event_IPAddress.emit(arg)
    _node.restart()

DEFAULT_PORT = SnmpConstants.DEFAULT_COMMAND_RESPONDER_PORT
param_port = Parameter({'schema': {'type': 'integer', 'hint': '%s (default)' % DEFAULT_PORT}})

DEFAULT_COMMUNITY = 'public'
param_community = Parameter({'schema': {'type': 'string', 'hint': '%s (default)' % DEFAULT_COMMUNITY}})

param_powerOffGuarding = Parameter({ 'title': '"Power Off" Guarding', 'order': next_seq(),
                                     'schema': { 'type': 'array', 'items': { 'type': 'object', 'properties': {
                                       'port': { 'tite': 'PDU port', 'type': 'integer', 'order': 1, 'desc': 'Prevents Power Off until nodes/devices are gracefully shutdown. Bindings need to be filled in after connection to device.' },
                                       'count': { 'type': 'integer', 'order': 2, 'desc': 'How many nodes to aggregate Power signals of.' }}}}})

# -->

# the community target
_target = CommunityTarget()
_target.setCommunity(OctetString('public'))
_target.setVersion(SnmpConstants.version1)
_target.setRetries(2)
_target.setTimeout(1000)

_timers = list()

def main():
  ipAddress = param_ipAddress if not is_blank(param_ipAddress) else local_event_IPAddress.getArg()
  local_event_IPAddress.emit(ipAddress)

  if param_disabled or is_blank(ipAddress):
    console.warn('Disabled or IP address not specified; nothing to do')
    return
  
  # complete the init of the target
  console.info('Using IP address "%s"' % ipAddress)
  _target.setAddress(UdpAddress('%s/%s' % (ipAddress, param_port or DEFAULT_PORT)))
  _target.setCommunity(OctetString(param_community or DEFAULT_COMMUNITY))
  
  # kick-off timer to poll the outlet status
  Timer(lambda: snmpLookupOID.call({ 'oid': OUTLETSTATUS_OID, 'signal': 'rawOutletStatus' }), 30, 2)

  # have IP address so can start timers
  for t in _timers:
    t.start()
  timer_syncer.start()
  
  # and trap the feedback
  local_event_RawOutletStatus.addEmitHandler(handleOutletStatusResult)
  
  

# <! power ---

# specific to Serveredge (from PDUMIB-201010105.mib, included with this recipe)
# 
# > pdu01OutletStatus OBJECT-TYPE
# >    SYNTAX      DisplayString (SIZE (0..32))
# >    ACCESS read-write
# >    STATUS mandatory
# >    DESCRIPTION
# >        "Indicate the outlet statuses (On or Off) from Outlet1 to Outlet8
# >         1: Outlet ON
# >         0: Outlet OFF
# >         -1: Outlet is not available
# >         -2: Outlet powr lost or Breaker triggered"
# >    ::= { pdu01Entry 13 }
OUTLETSTATUS_OID = '1.3.6.1.4.1.17420.1.2.9.1.13.0'

# e.g. "1,1,-1,-1,-1,-1,-1,-1"
local_event_RawOutletStatus = LocalEvent({'title': 'Outlet Status', 'group': 'Raw Feedback', 'order': next_seq(), 'schema': {'type': 'string'}})

def handleOutletStatusResult(result):
  # split the result
  for index, portStatus in enumerate(result.split(',')):
    if portStatus in ['-2', '0', '1']:
      tryInitPort(index+1, portStatus)
      
  prepareForGuarding()

def portStatusToName(portStatus):
  if portStatus == '0':
    return 'Off'
  
  elif portStatus == '1':
    return 'On'
  
  elif portStatus == '-2':
    return 'Lost'
  
  else:
    return 'Not Present'
    
def tryInitPort(portNum, portStatus):
  # check if signal has already been defined
  rawPortSignal = lookup_local_event('Port %s Raw Power' % portNum)
  
  if rawPortSignal != None:
    # already initialised, just emit signal
    rawPortSignal.emit(portStatusToName(portStatus))
    return

  # init labelling (uses "pdu01Outlet2Config" e.g. "COMPUTER,0,0,0,0")
  rawConfigSignalName = 'Port %s Raw Config' % portNum
  rawConfigSignal = create_local_event(rawConfigSignalName, {'group': 'Raw Feedback', 'order': next_seq(), 'schema': {'type': 'string'}})
  labelSignal = create_local_event('Port %s Label' % portNum, {'group': 'Labels', 'order': next_seq(), 'schema': {'type': 'string'}})
  
  def getPortConfig():
    return doSnmpLookupOID('1.3.6.1.4.1.17420.1.2.9.1.14.%s.0' % portNum, rawConfigSignalName)
    
  Timer(getPortConfig, 5*60, 2)
  
  rawConfigSignal.addEmitHandler(lambda arg: labelSignal.emit(arg.split(',')[0]))
  
  # retrieve labelling now
  configStr = getPortConfig()    
  
  # initialising signals...
  label = configStr.split(',')[0]
  rawSignal     = create_local_event('Port %s Raw Power' % portNum,     {'group': 'Raw Feedback', 'order': next_seq(), 'schema': {'type': 'string', 'enum': ['On', 'Off', 'Lost']}})
  powerSignal   = create_local_event('Port %s Power' % portNum,         {'group': 'Power%s' % (' ("%s")' % label if label else ''),        'order': next_seq(), 'schema': {'type': 'string', 'enum': ['On', 'Off', 'Partially On', 'Partially Off']}})
  desiredSignal = create_local_event('Port %s Desired Power' % portNum, {'group': 'Power%s' % (' ("%s")' % label if label else ''),        'order': next_seq(), 'schema': {'type': 'string', 'enum': ['On', 'Off', 'Force Off']}})
  
  def computePower(ignore):
    desiredArg = desiredSignal.getArg()
    rawArg = rawSignal.getArg()
    
    if desiredArg == None:
      powerSignal.emit(rawArg)
      return

    # strip 'Forced' if 'Forced Off', that'll be used later
    desiredArg = 'Off' if 'Off' in desiredArg else 'On'
    
    if desiredArg == rawArg:
      powerSignal.emit(desiredArg)
      
    else:
      powerSignal.emit('Partially %s' % desiredArg)
      
  desiredSignal.addEmitHandler(computePower)
  rawSignal.addEmitHandler(computePower)
  
  # and action...
  def handlePower(arg):
    console.info('Port %s Power(%s)' % (portNum, arg))
    desiredSignal.emit(arg)
    log(1, 'handlePower_port%s: setting delay to 0.1s and interval 5s' % portNum)
    timer_syncer.setDelayAndInterval(0.1, 5) # kick off immediately (100ms if batching is required), use 5s interval during enforcement period
  
  powerAction = create_local_action('Port %s Power' % portNum, handlePower, {'group': 'Power%s' % (' ("%s")' % label if label else ''), 'order': next_seq(), 'schema': {'type': 'string', 'enum': ['On', 'Off', 'Force Off']}})
  create_local_action('Port %s Power On' % portNum, lambda ignore: powerAction.call('On'), { 'group': 'Power%s' % (' ("%s")' % label if label else ''), 'order': next_seq() })
  create_local_action('Port %s Power Off' % portNum, lambda ignore: powerAction.call('Off'), { 'group': 'Power%s' % (' ("%s")' % label if label else ''), 'order': next_seq() })

def sync_outlet_states():
    # get the existing status of all the ports
    rawOutletStatus = local_event_RawOutletStatus.getArg()
    if is_blank(rawOutletStatus):
      return
    
    parts = rawOutletStatus.split(',')

    # recompose with the new states, only if they've been recently controlled using an action
    nowMillis = date_now().getMillis()

    recentAction = False

    for portNum in range(1, len(parts) + 1): # go through all known ports
      action = lookup_local_action('Port %s Power' % portNum)
      if action == None:
        break # have come to the end of ports

      timestamp = action.getTimestamp()
      if not timestamp or (nowMillis - timestamp.getMillis()) > 5*60000:
        continue # last action was more than 5 mins ago so give up on this port

      recentAction = True
      desired = lookup_local_event('Port %s Desired Power' % portNum).getArg()

      if desired == 'On':
        parts[portNum-1] = '1'

      elif desired == 'Force Off':
        parts[portNum-1] = '0'
      
      elif desired == 'Off':
        powerOffGuard = lookup_local_event('Port %s Power Off Guarded' % portNum)
        if powerOffGuard and powerOffGuard.getArg():
          console.warn('POWER: want to turn Port %s Power Off but Power Locked Out for now' % portNum)
        else:
          # is not guarded so safe to turn off
          parts[portNum-1] = '0'
      
    # set SNMP if changed from original
    newStatus = ','.join(parts)
    if newStatus != rawOutletStatus:
      log(1, 'timer_syncer: status strings changed; forcing SNMP; "%s" (orig was %s)' % (newStatus, rawOutletStatus))
      snmpSetOID.call({'oid': OUTLETSTATUS_OID, 'value': newStatus, 'signal': 'rawOutletStatus'})
    
    if not recentAction:
      log(1, 'timer_syncer: no actions within last 5 mins, setting interval to 60s')
      timer_syncer.setInterval(60) # is safe to back-off to 1 min intervals

timer_syncer = Timer(sync_outlet_states, 20, stopped=True) # every 20 seconds but mainly on action

  
# power --!>

# <!-- other values

# Current:
#
# Name   : pdu01Value    Parent : pdu01Entry
# Number : 11            Access :  read-only  
# Syntax :  INTEGER      Status :  mandatory
# Description : 
#  "Indicate the current of PDU-01detect."
# Type :0

local_event_Current = LocalEvent({'title': 'Current', 'group': 'Monitoring', 'order': next_seq(), 'schema': {'type': 'string'}})
_timers.append(Timer(lambda: snmpLookupOID.call({'oid': '.1.3.6.1.4.1.17420.1.2.9.1.11.0', 'signal': 'Current'}), 10, 2, stopped=True))


# Firmware

local_event_Firmware = LocalEvent({'title': 'Firmware', 'group': 'Device Info', 'order': next_seq(), 'schema': {'type': 'string'}})
_timers.append(Timer(lambda: snmpLookupOID.call({'oid': '.1.3.6.1.4.1.17420.1.2.4.0', 'signal': 'Firmware'}), 5*60, 2, stopped=True))


# MAC Address

local_event_MACAddress = LocalEvent({'title': 'MAC address', 'group': 'Device Info', 'order': next_seq(), 'schema': {'type': 'string'}})
_timers.append(Timer(lambda: snmpLookupOID.call({'oid': '.1.3.6.1.4.1.17420.1.2.3.0', 'signal': 'MACAddress'}), 5*60, 2, stopped=True))


# etc.

# other values -->

# <!-- raw SNMP
@local_action({ 'group': 'SNMP', 'order': 100, 'schema': { 'type': 'object', 'properties': { 
                  'oid': { 'type': 'string', 'order': 1 },
                  'signal': { 'type': 'string', 'order': 2 }}}})
def snmpLookupOID(arg):
  doSnmpLookupOID(arg['oid'], arg['signal'])

def doSnmpLookupOID(oid, signalName):  
  pdu = PDU()
  pdu.add(VariableBinding(OID(oid)))
  pdu.setType(PDU.GET)
  
  respEvent = NodelSnmp.shared().get(pdu, _target)
  
  if respEvent == None:
    console.warn('timeout')
    return
  
  respPDU = respEvent.getResponse()
  
  if respPDU == None:
    warn(1, 'response was empty')
    return
  
  lastReceive[0] = system_clock()
  
  errStatus = respPDU.getErrorStatus()
  
  if errStatus != PDU.noError:
    errIndex = respPDU.getErrorIndex()
    errText = respPDU.getErrorStatusText()
    
    console.warn('an error occurred - status:%s, index:%s, text:[%s]' % (errStatus, errIndex, errText))
    
    return
  
  result = str(respPDU.getVariableBindings()[0].getVariable())
  
  signal = lookup_local_event(signalName)
  if signal != None:
    signal.emit(result)

  return result

@local_action({ 'group': 'SNMP', 'order': 100, 'schema': { 'type': 'object', 'properties': { 
                  'oid':    {'type': 'string', 'order': 1},
                  'value':  {'type': 'string', 'order': 2},
                  'signal': {'type': 'string', 'order': 3}}}})
def snmpSetOID(arg):
  pdu = PDU()
  pdu.add(VariableBinding(OID(arg['oid']), OctetString(arg['value'])))
  pdu.setType(PDU.SET)
  
  respEvent = NodelSnmp.shared().set(pdu, _target)
  
  if respEvent == None:
    console.warn('timeout')
    return
  
  respPDU = respEvent.getResponse()
  
  if respPDU == None:
    warn(1, 'resp was empty')
    return
  
  errStatus = respPDU.getErrorStatus()
  
  if errStatus != PDU.noError:
    errIndex = respPDU.getErrorIndex()
    errText = respPDU.getErrorStatusText()
    
    console.warn('an error occurred - status:%s, index:%s, text:[%s]' % (errStatus, errIndex, errText))
    
    return
  
  result = str(respPDU.getVariableBindings()[0].getVariable())
  
  signal = lookup_local_event(arg['signal']).emit(result)  

# ---!>

# <!-- Power Off guarding

# (called once PDU polled at least once)
def prepareForGuarding():
  for i in param_powerOffGuarding or EMPTY:
    initPowerOffGuarding(i['port'], i['count'])

def initPowerOffGuarding(portNum, count):
  if not count:
    return
  
  label = lookup_local_event('Port %s Label' % portNum).getArg()
  
  poweroffGuardedName = 'Port %s Power Off Guarded' % portNum
  if lookup_local_event(poweroffGuardedName):
    return
  
  powerOffGuardedEvent = create_local_event('Port %s Power Off Guarded' % portNum, { 'group': 'Power%s' % (' ("%s")' % label if label else ''), 'order': next_seq(), 'schema': { 'type': 'boolean' }})

  events = list()

  def handler(arg):
    prev = powerOffGuardedEvent.getArg()
    
    # aggregate all remote args, True if *any* is active
    value = any([ not is_fully_off(e.getArg()) for e in events ]) 

    powerOffGuardedEvent.emit(value)

    if prev != value:
      _lastGuardOffChange = system_clock()

  console.info('%s set up for Power Off guard; ensure bindings have been set' % count)
  
  for i in range(1, (count or 0) + 1):
    events.append(create_remote_event('Port %s Guarding Power Off %s' % (portNum, i), handler))
    
def is_fully_off(value):
  return value == False or value in ['Off', 'off']    

# Power Off guarding -->

# <!-- status

local_event_Status = LocalEvent({'group': 'Status', 'order': 9990, "schema": { 'title': 'Status', 'type': 'object', 'properties': {
        'level': {'title': 'Level', 'order': next_seq(), 'type': 'integer'},
        'message': {'title': 'Message', 'order': next_seq(), 'type': 'string'}
    } } })

# for status checks
lastReceive = [0]

# roughly, the last contact  
local_event_LastContactDetect = LocalEvent({'group': 'Status', 'title': 'Last contact detect', 'schema': {'type': 'string'}})
  
def statusCheck():
  diff = (system_clock() - lastReceive[0])/1000.0 # (in secs)
  now = date_now()
  
  if diff > status_check_interval+15:
    previousContactValue = local_event_LastContactDetect.getArg()
    
    if previousContactValue == None:
      message = 'Always been missing.'
      
    else:
      previousContact = date_parse(previousContactValue)
      roughDiff = (now.getMillis() - previousContact.getMillis())/1000/60
      if roughDiff < 60:
        message = 'Missing for approx. %s mins' % roughDiff
      elif roughDiff < (60*24):
        message = 'Missing since %s' % previousContact.toString('h:mm:ss a')
      else:
        message = 'Missing since %s' % previousContact.toString('h:mm:ss a, E d-MMM')
      
    local_event_Status.emit({'level': 2, 'message': message})
    
  else:
    local_event_LastContactDetect.emit(str(now))
    local_event_Status.emit({'level': 0, 'message': 'OK'})
    
status_check_interval = 75
status_timer = Timer(statusCheck, status_check_interval)

# status --!>

# <!-- logging

local_event_LogLevel = LocalEvent({'group': 'Debug', 'order': 10000+next_seq(), 'desc': 'Use this to ramp up the logging (with indentation)',  
                                   'schema': {'type': 'integer'}})

def warn(level, msg):
  if local_event_LogLevel.getArg() >= level:
    console.warn(('  ' * level) + msg)

def log(level, msg):
  if local_event_LogLevel.getArg() >= level:
    console.log(('  ' * level) + msg)

# --!>