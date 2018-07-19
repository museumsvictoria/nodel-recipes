'''Pure SNMP based control of the Servedge PDUs - see script for additional resources'''

# Useful resources:
# - PDUMIB-201010105.mib (part of recipe) file contains the MIB file for the Serveredge PDUs
# - sourceforge.net/projects/jmibbrowser project is a decent little MIB browser

# TODO:
# - use SNMP to do the port labelling
# - current thresholds into status monitoring


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

param_ipAddress = Parameter({'schema': {'type': 'string' }})
                              

DEFAULT_PORT = SnmpConstants.DEFAULT_COMMAND_RESPONDER_PORT
param_port = Parameter({'schema': {'type': 'integer', 'hint': '%s (default)' % DEFAULT_PORT}})

DEFAULT_COMMUNITY = 'public'
param_community = Parameter({'schema': {'type': 'string', 'hint': '%s (default)' % DEFAULT_COMMUNITY}})

# -->

# the community target
_target = CommunityTarget()
_target.setCommunity(OctetString('public'))
_target.setVersion(SnmpConstants.version1)
_target.setRetries(2)
_target.setTimeout(1000)

def main():
  if param_disabled or not param_ipAddress:
    console.warn('Disabled or IP address not specified; nothing to do')
    return
  
  # complete the init of the target
  _target.setAddress(UdpAddress('%s/%s' % (param_ipAddress, param_port or DEFAULT_PORT)))
  _target.setCommunity(OctetString(param_community or DEFAULT_COMMUNITY))
  
  # kick-off timer to poll the outlet status
  Timer(lambda: lookup_local_action('snmpLookupOID').call({'oid': OUTLETSTATUS_OID,
                                                           'signal': 'rawOutletStatus'}), 30, 2)
  
  # and trap the feedback
  local_event_rawOutletStatus.addEmitHandler(handleOutletStatusResult)
  
  

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
local_event_rawOutletStatus = LocalEvent({'title': 'Outlet Status', 'group': 'Raw Feedback', 'order': next_seq(), 'schema': {'type': 'string'}})

def handleOutletStatusResult(result):
  # split the result
  for index, portStatus in enumerate(result.split(',')):
    if portStatus in ['-2', '0', '1']:
      tryInitPort(index+1, portStatus)

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
  
  # initialising signals...
  rawSignal     = create_local_event('Port %s Raw Power' % portNum,     {'group': 'Raw Feedback', 'order': next_seq(), 'schema': {'type': 'string', 'enum': ['On', 'Off', 'Lost']}})
  powerSignal   = create_local_event('Port %s Power' % portNum,         {'group': 'Power',        'order': next_seq(), 'schema': {'type': 'string', 'enum': ['On', 'Off', 'Partially On', 'Partially Off']}})
  desiredSignal = create_local_event('Port %s Desired Power' % portNum, {'group': 'Power',        'order': next_seq(), 'schema': {'type': 'string', 'enum': ['On', 'Off']}})
  
  def computerPower(ignore):
    desiredArg = desiredSignal.getArg()
    rawArg = rawSignal.getArg()
    
    if desiredArg == None:
      powerSignal.emit(rawArg)
    
    elif desiredArg == rawArg:
      powerSignal.emit(desiredArg)
      
    else:
      powerSignal.emit('Partially %s' % desiredArg)
      
  desiredSignal.addEmitHandler(computerPower)
  rawSignal.addEmitHandler(computerPower)
  
  # and action...
  def handlePower(arg):
    desiredSignal.emit(arg)
    
    # get the existing status of all the ports
    rawOutletStatus = lookup_local_event('rawOutletStatus').getArg()
    
    if is_blank(rawOutletStatus):
      return
    
    # recompose with the new state
    
    parts = rawOutletStatus.split(',')
    
    if arg == 'On':
      parts[portNum-1] = '1'
      
    elif arg == 'Off':
      parts[portNum-1] = '0'
      
    lookup_local_action('snmpSetOID').call({'oid': OUTLETSTATUS_OID, 'value': ','.join(parts), 'signal': 'rawOutletStatus'})
  
  powerAction = create_local_action('Port %s Power' % portNum, handlePower, {'group': 'Power', 'order': next_seq(), 'schema': {'type': 'string', 'enum': ['On', 'Off']}})
  
  
  
# power --!>

# <!-- other values

# Current:
#
# Name   : pdu01Value    Parent : pdu01Entry
# Number : 11            Access :  read-only  
# Syntax :  INTEGER      # Status :  mandatory
# Description : 
#  "Indicate the current of PDU-01detect."
# Type :0

local_event_Current = LocalEvent({'title': 'Current', 'group': 'Monitoring', 'order': next_seq(), 'schema': {'type': 'string'}})
Timer(lambda: lookup_local_action('snmpLookupOID').call({'oid': '.1.3.6.1.4.1.17420.1.2.9.1.11.0', 'signal': 'Current'}), 10, 2)


# Firmware

local_event_Firmware = LocalEvent({'title': 'Firmware', 'group': 'Device Info', 'order': next_seq(), 'schema': {'type': 'string'}})
Timer(lambda: lookup_local_action('snmpLookupOID').call({'oid': '.1.3.6.1.4.1.17420.1.2.4.0', 'signal': 'Firmware'}), 5*60, 2)


# MAC Address

local_event_MACAddress = LocalEvent({'title': 'MAC address', 'group': 'Device Info', 'order': next_seq(), 'schema': {'type': 'string'}})
Timer(lambda: lookup_local_action('snmpLookupOID').call({'oid': '.1.3.6.1.4.1.17420.1.2.3.0', 'signal': 'MACAddress'}), 5*60, 2)


# etc.

# other values -->

# <!-- raw SNMP

def local_action_snmpLookupOID(arg):
  '''{'group': 'SNMP', 'order': 100, 'schema': {'type': 'object', 'properties': { 
        'oid':    {'type': 'string', 'order': 1},
        'signal': {'type': 'string', 'order': 2}
     }}}'''
  pdu = PDU()
  pdu.add(VariableBinding(OID(arg['oid'])))
  pdu.setType(PDU.GET)
  
  respEvent = NodelSnmp.shared().get(pdu, _target)
  
  if respEvent == None:
    console.warn('timeout')
    return
  
  respPDU = respEvent.getResponse()
  
  if respPDU == None:
    console.warn('response PDU was empty')
    return
  
  lastReceive[0] = system_clock()
  
  errStatus = respPDU.getErrorStatus()
  
  if errStatus != PDU.noError:
    errIndex = respPDU.getErrorIndex()
    errText = respPDU.getErrorStatusText()
    
    console.warn('an error occurred - status:%s, index:%s, text:[%s]' % (errStatus, errIndex, errText))
    
    return
  
  result = str(respPDU.getVariableBindings()[0].getVariable())
  
  signal = lookup_local_event(arg['signal'])
  if signal != None:
    signal.emit(result)
  
def local_action_snmpSetOID(arg):
  '''{'group': 'SNMP', 'order': 100, 'schema': {'type': 'object', 'properties': { 
        'oid':    {'type': 'string', 'order': 1},
        'value':  {'type': 'string', 'order': 2},
        'signal': {'type': 'string', 'order': 3}
     }}}'''
  pdu = PDU()
  pdu.add(VariableBinding(OID(arg['oid']), OctetString(arg['value'])))
  pdu.setType(PDU.SET)
  
  respEvent = NodelSnmp.shared().set(pdu, _target)
  
  if respEvent == None:
    console.warn('timeout')
    return
  
  respPDU = respEvent.getResponse()
  
  if respPDU == None:
    console.warn('response PDU was empty')
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

# <!-- status

# status  ----

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
