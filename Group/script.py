'''A node that groups members for control propagation and status monitoring - see script.py for notes'''

# For disappearing member support:
#    (requires at least Nodel Host rev. 322 or later)
#
#    - remote "Disappearing" signals should be wired to the actual signals
#    - the usual remote signals should be wired to the respective "assumed" local signals respectively.

def main(arg=None):
  try:
    for memberInfo in lookup_parameter('members') or []:
      initMember(memberInfo)
  
    console.info('Started!')
    
  except:
    console.err("Failed it initialise structures. NOTE: if 'disappearing' member support is being used, Nodel Host rev. 322 or later is required")
    
    raise
  
# <!--- members and status support  

MODES = ['Action & Signal', 'Signal Only']

param_members = Parameter({'title': 'Members', 'schema': {'type': 'array', 'items': {'type': 'object', 'properties': {
   'name': {'type': 'string', 'order': 1},
   'hasStatus': {'type': 'boolean', 'title': 'Status?', 'order': 3},
   'disappears': {'title': 'Disappears when Power Off?', 'type': 'boolean', 'order': 3.1},
   'power': {'title': 'Power', 'type': 'object', 'order': 4, 'properties': {
     'mode': {'title': 'Mode', 'type': 'string', 'enum': MODES}
   }},
   'muting': {'title': 'Muting', 'type': 'object', 'order': 5, 'properties': {
     'mode': {'title': 'Mode', 'type': 'string', 'enum': MODES}
   }}
}}}})

def initMember(memberInfo):
  name = mustNotBeBlank('name', memberInfo['name'])
                           
  disappears = memberInfo.get('disappears')

  if (memberInfo.get('power') or {}).get('mode') in MODES:
    initSignalSupport(name, memberInfo['power']['mode'], 'Power', ['On', 'Off'], disappears)
    
  if (memberInfo.get('muting') or {}).get('mode') in MODES:
    initSignalSupport(name, memberInfo['muting']['mode'], 'Muting', ['On', 'Off'], disappears)
    
  # do status last because it depends on 'Power' when 'disappears' is in use
  if memberInfo.get('hasStatus'):
    initStatusSupport(name, disappears)

membersBySignal = {}
    
def initSignalSupport(name, mode, signalName, states, disappears):
  members = getMembersInfoOrRegister(signalName, name)
  
  # establish local signals if haven't done so already
  localDesiredSignal = lookup_local_event('Desired %s' % signalName)
  
  if localDesiredSignal == None:
    localDesiredSignal, localResultantSignal = initSignal(signalName, mode, states)
  else:
    localResultantSignal = lookup_local_event(signalName)
    
  # establish a remote action
  if mode == 'Action & Signal':
    create_remote_action('Member %s %s' % (name, signalName), {'group': 'Members (%s)' % signalName, 'schema': {'type': 'string', 'enum': states}},
                         suggestedNode=name, suggestedAction=signalName)
  
  # establish a remote signal to receive status
  # signal status states include 'Partially ...' forms
  resultantStates = states + ['Partially %s' % s for s in states]
  
  localMemberSignal = Event('Member %s %s' % (name, signalName), {'title': '"%s" %s' % (name, signalName), 'group': '(advanced)', 'order': 9999+next_seq(), 'schema': {'type': 'string', 'enum': resultantStates}})
  
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
  
  create_remote_event('Member %s %s' % (name, signalName), handleRemoteEvent, {'group': 'Members (%s)' % signalName, 'order': next_seq(), 'schema': {'type': 'string', 'enum': resultantStates}},
                      suggestedNode=name, suggestedEvent=signalName)
                           
  if disappears:
    prepareForDisappearingMemberSignal(name, signalName)

def initSignal(signalName, mode, states):
  resultantStates = states + ['Partially %s' % s for s in states]
  
  localDesiredSignal = Event('Desired %s' % signalName, {'group': signalName, 'order': next_seq(), 'schema': {'type': 'string', 'enum': states}})
  
  localResultantSignal = Event('%s' % signalName, {'group': signalName, 'order': next_seq(), 'schema': {'type': 'string', 'enum': resultantStates}})
  
  def handler(complexArg):
    state = complexArg['state']
    noPropagate = complexArg.get('noPropagate')
    
    localDesiredSignal.emit(state)
    
    # for convenience, just emit the state as the status if no members are configured
    if isEmpty(lookup_parameter('members')):
      localResultantSignal.emit(state)
    
    else:
      if noPropagate:
        return
      
      for memberName in membersBySignal[signalName]:
        remoteAction = lookup_remote_action('Member %s %s' % (memberName, signalName))
        if remoteAction != None:
          remoteAction.call(complexArg)
          
  # create normal action (propagates)
  Action('%s' % signalName, lambda arg: handler({'state': arg}), {'group': signalName, 'order': next_seq(), 'schema': {'type': 'string', 'enum': states}})
  
  # create action with options (e.g. 'noPropagate')
  Action('%s Extended' % signalName, handler, {'group': '(extended)', 'order': next_seq(), 'schema': {'type': 'object', 'properties': {
           'state': {'type': 'string', 'enum': states, 'order': 3},
           'noPropagate': {'type': 'boolean', 'order': 2}}}})
  
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
  
def initStatusSupport(name, disappears):
  # look up the members structure (assume
  members = getMembersInfoOrRegister('Status', name)
  
  # check if this node has a status yet
  selfStatusSignal = lookup_local_event('Status')
  if selfStatusSignal == None:
    selfStatusSignal = Event('Status', {'group': 'Status', 'order': next_seq(), 'schema': STATUS_SCHEMA})
    
  # status for the member
  memberStatusSignal = Event('Member %s Status' % name, {'title': '"%s" Status' % name, 'group': '(advanced)', 'order': 9999+next_seq(), 'schema': STATUS_SCHEMA})
  
  # suppression flag?
  memberStatusSuppressedSignal = Event('Member %s Status Suppressed' % name, {'title': 'Suppress "%s" Status' % name, 'group': '(advanced)', 'order': 9999+next_seq(), 'schema': {'type': 'boolean'}})
  
  Action('Member %s Status Suppressed' % name, lambda arg: memberStatusSuppressedSignal.emit(arg), {'title': 'Suppress "%s" Status' % name, 'group': '(advanced)', 'order': 9999+next_seq(), 'schema': {'type': 'boolean'}})
  
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
  
  create_remote_event('Member %s Status' % name, handleRemoteEvent, {'group': 'Members (Status)', 'order': next_seq(), 'schema': STATUS_SCHEMA},
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

