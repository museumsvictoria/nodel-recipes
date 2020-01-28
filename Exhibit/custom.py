# Members seasoning for status monitoring with standard exhibit node.

from nodetoolkit import *

# <!--- members and status support  

membersBySignal = {}
    
def initSignalSupport(name, mode, signalName, states, disappears = False, isGroup = False):
  members = getMembersInfoOrRegister(signalName, name)
  
  # establish local signals if haven't done so already
  localDesiredSignal = lookup_local_event('Desired %s' % signalName)
  
  if localDesiredSignal == None:
    localDesiredSignal, localResultantSignal = initSignal(signalName, mode, states)
  else:
    localResultantSignal = lookup_local_event(signalName)
      
  # establish a remote signal to receive status
  # signal status states include 'Partially ...' forms
  resultantStates = states + ['Partially %s' % s for s in states]
  
  localMemberSignal = Event('Member %s %s' % (name, signalName), {'title': '"%s" %s' % (name, signalName), 'group': 'Members\' %s' % signalName, 'order': 9999+next_seq(), 'schema': {'type': 'string', 'enum': resultantStates}})
  
  def aggregateMemberSignals():
    shouldBeState = localDesiredSignal.getArg()
    partially = False
    
    for memberName in members:
      if lookup_local_event('Member %s %s' % (memberName, signalName)).getArg() != shouldBeState:
        partially = True
        
    localResultantSignal.emit('Partially %s' % shouldBeState if partially else shouldBeState)
    
  localMemberSignal.addEmitHandler(lambda arg: aggregateMemberSignals())
  localDesiredSignal.addEmitHandler(lambda arg: aggregateMemberSignals())
  
  def handleRemoteEvent(arg):
    if arg == True or arg == 1:
      arg = 'On'
    elif arg == False or arg == 0:
      arg = 'Off'
    
    localMemberSignal.emit(arg)
  
  create_remote_event('Member %s %s' % (name, signalName), handleRemoteEvent, {'title': '"%s" %s' % (name, signalName),'group': 'Members ("%s")' % signalName, 'order': next_seq(), 'schema': {'type': 'string', 'enum': resultantStates}},
                      suggestedNode=name, suggestedEvent=signalName)
                           
  if disappears:
    prepareForDisappearingMemberSignal(name, signalName)

def initSignal(signalName, mode, states):
  resultantStates = states + ['Partially %s' % s for s in states]
  
  localDesiredSignal = Event('Desired %s' % signalName, {'group': '%s' % signalName, 'order': next_seq(), 'schema': {'type': 'string', 'enum': states}})
  
  localResultantSignal = Event('%s' % signalName, {'group': '%s' % signalName, 'order': next_seq(), 'schema': {'type': 'string', 'enum': resultantStates}})
                    
  return localDesiredSignal, localResultantSignal

def getMembersInfoOrRegister(signalName, memberName):
  members = membersBySignal.get(signalName)
  if members == None:
    members = list()
    membersBySignal[signalName] = members
    
  members.append(memberName)

  return members

STATUS_SCHEMA = { 'type': 'object', 'properties': {
                    'level': { 'type': 'integer', 'order': 1 },
                    'message': {'type': 'string', 'order': 2 }
                } }

EMPTY_SET = {}
  
def initStatusSupport(name, disappears = False):
  # look up the members structure (assume
  members = getMembersInfoOrRegister('Status', name)
  
  # check if this node has a status yet
  selfStatusSignal = lookup_local_event('Status')
  if selfStatusSignal == None:
    selfStatusSignal = Event('Status', {'group': 'Status', 'order': next_seq(), 'schema': STATUS_SCHEMA})
    
  # status for the member
  memberStatusSignal = Event('Member %s Status' % name, {'title': '"%s" Status' % name, 'group': 'Members\' Status', 'order': 9999+next_seq(), 'schema': STATUS_SCHEMA})
  
  # suppression flag?
  memberStatusSuppressedSignal = Event('Member %s Status Suppressed' % name, {'title': 'Suppress "%s" Status' % name, 'group': 'Status Suppression', 'order': 9999+next_seq(), 'schema': {'type': 'boolean'}})
  
  Action('Member %s Status Suppressed' % name, lambda arg: memberStatusSuppressedSignal.emit(arg), {'title': 'Suppress "%s" Status' % name, 'group': 'Status Suppression', 'order': 9999+next_seq(), 'schema': {'type': 'boolean'}})
  
  def aggregateMemberStatus():
    aggregateLevel = 0
    aggregateMessage = 'OK'
    
    # for composing the aggegate message at the end
    msgs = []
    
    activeSuppression = False
    
    for memberName in members:
      suppressed = lookup_local_event('Member %s Status Suppressed' % memberName).getArg()
      
      memberStatus = lookup_local_event('Member %s Status' % memberName).getArg() or EMPTY_SET
      
      memberLevel = memberStatus.get('level')
      if memberLevel == None: # as opposed to the value '0'
        if suppressed:
          activeSuppression = True
          continue
          
        memberLevel = 99

      if memberLevel > aggregateLevel:
        # raise the level (if not suppressed)
        if suppressed:
          activeSuppression = True
          continue
        
        aggregateLevel = memberLevel
      
      memberMessage = memberStatus.get('message') or 'Has never been seen'
      if memberLevel > 0:
        if isBlank(memberMessage):
          msgs.append(memberName)
        else:
          msgs.append('%s: [%s]' % (memberName, memberMessage))
          
    if len(msgs) > 0:
      aggregateMessage = ', '.join(msgs)
      
    if activeSuppression:
      aggregateMessage = '%s (*)' % aggregateMessage
      
    selfStatusSignal.emit({'level': aggregateLevel, 'message': aggregateMessage})
      
  memberStatusSignal.addEmitHandler(lambda arg: aggregateMemberStatus())
  memberStatusSuppressedSignal.addEmitHandler(lambda arg: aggregateMemberStatus())
  
  def handleRemoteEvent(arg):
    memberStatusSignal.emit(arg)
  
  create_remote_event('Member %s Status' % name, handleRemoteEvent, {'title': '"%s" Status' % name, 'group': 'Members (Status)', 'order': next_seq(), 'schema': STATUS_SCHEMA},
                       suggestedNode=name, suggestedEvent="Status")
                           
  if disappears:
    prepareForDisappearingMemberStatus(name)
  
# members and status support ---!>

# <!--- disappearing members

# (for disappearing signals)
from org.nodel.core import BindingState

def prepareForDisappearingMemberStatus(name):
  # lookup it's desired 'Power' signal
  desiredPowerSignal = lookup_local_event('DesiredPower')
  
  # create assumed status
  assumedStatus = Event('Member %s Assumed Status' % name, { 'group': '(advanced)', 'order': next_seq(), 'schema': {'type': 'object', 'properties': {
                          'level': {'type': 'integer', 'order': 1},
                          'message': {'type': 'string', 'order': 2}}}})
  
  # create volatile remote binding that just passes through the status anyway
  disappearingRemoteStatus = create_remote_event('%s Disappearing Status' % name, lambda arg: assumedStatus.emit(arg))
  
  # and when there's a wiring fault
  def checkBindingState():
    desiredPower = desiredPowerSignal.getArg()
    
    wiringStatus = disappearingRemoteStatus.getStatus()
    
    if desiredPower == 'On':
      if wiringStatus != BindingState.Wired:
        assumedStatus.emit({'level': 2, 'message': 'Power is supposed to be On - no confirmation of that.'})
        
      else:
        # wiringStatus is 'Wired', normal status can be passed through
        remoteStatusArg = disappearingRemoteStatus.getArg()
        if remoteStatusArg != None:
          assumedStatus.emit(remoteStatusArg)
      
    
    elif desiredPower == 'Off':
      if wiringStatus == BindingState.Wired:
        assumedStatus.emit({'level': 1, 'message': 'Power should be Off but appears to be alive'})
        
      else:
        # wiringStatus is not 'Wired'
        assumedStatus.emit({'level': 0, 'message': 'OK'})
        
  # check when the status binding state changes
  disappearingRemoteStatus.addBindingStateHandler(lambda arg: checkBindingState())
  
  # and when the power state changes
  desiredPowerSignal.addEmitHandler(lambda arg: checkBindingState())
  
  
def prepareForDisappearingMemberSignal(name, signalName):
  # lookup it's desired 'Power' signal
  desiredPowerSignal = lookup_local_event('DesiredPower')
  
  # create assumed signal
  assumedSignal = Event('Member %s Assumed %s' % (name, signalName), { 'group': '(advanced)', 'order': next_seq(), 'schema': {'type': 'string'}})
  
  # create volatile remote binding that just passes through the status anyway
  disappearingRemoteSignal = create_remote_event('%s Disappearing %s' % (name, signalName), lambda arg: assumedSignal.emit(arg))
  
  # and when there's a wiring fault
  def checkBindingState():
    desiredPower = desiredPowerSignal.getArg()
    
    wiringStatus = disappearingRemoteSignal.getStatus()
    
    if wiringStatus == BindingState.Wired:
      # pass on the remote signal
      remoteSignalArg = disappearingRemoteSignal.getArg()
      if remoteSignalArg != None:
        assumedSignal.emit(remoteSignalArg)
        
    else:
      # wiring status is NOT wired
      if desiredPower == 'On':
        assumedSignal.emit('Partially On')
        
      elif desiredPower == 'Off':
        assumedSignal.emit('Off')

  # check when the status binding state changes
  disappearingRemoteSignal.addBindingStateHandler(lambda arg: checkBindingState())        
        
  # and when the power state changes
  desiredPowerSignal.addEmitHandler(lambda arg: checkBindingState())

# disappearing members ---!>

# <!--- convenience functions

def mustNotBeBlank(name, s):
  if isBlank(s):
    raise Exception('%s cannot be blank')

  return s

def isBlank(s):
  if s == None or len(s) == 0 or len(s.strip()) == 0:
    return True
  
def isEmpty(o):
  if o == None or len(o) == 0:
    return True

# convenience functions ---!>

# <!--- attach power
@after_main
def attachActionSignals():

  def handlePower(arg):
    event = lookup_local_event('Desired Power')
    if event:
      event.emit(arg)

  action = lookup_local_action('Power')
  if action:
    action.addCallHandler(handlePower)

# attach power ---!>

# <!--- default power and muting actions
powerObj = Power()
def local_action_Power(arg = None):
  """{'title':'Power','schema':{'type':'string','enum':['On','Off']},'group':'Power'}"""
  if arg == 'On':
    powerObj.enable()
  elif arg == 'Off':
    powerObj.disable()

mutingObj = Mute()
def local_action_Muting(arg = None):
  """{'title':'Muting','schema':{'type':'string','enum':['On','Off']},'group':'Muting'}"""
  if arg == 'On':
    mutingObj.muteOn()
  elif arg == 'Off':
    mutingObj.muteOff()

# default power and muting actions ---!>

# <!--- composite signals from script.py
@after_main
def extend_node():

  def is_disappearing(device):
    disappearing_devices = ['PC', 'Computer']
    if any(name in device for name in disappearing_devices):
      return True

  # A list of devices requiring power monitoring
  try:
    for powered_device in monitor_our_power:
      initSignalSupport(powered_device, 'Signal Only', 'Power', ['On', 'Off'], disappears = is_disappearing(powered_device))
  except NameError:
    console.log("No power monitoring")

  # A list of devices requiring status monitoring
  try:
    for device in monitor_our_status:

      initStatusSupport(device, disappears = is_disappearing(device))
  except NameError:
    console.log("No status monitoring")

# composite signals from script.py ---!>