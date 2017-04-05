'''A node that groups members for control propagation and status monitoring.'''

def main(arg=None):
  console.info('Started!')
  
# <!--- members and status support  

@after_main
def initMembersSupport():
  for memberInfo in lookup_parameter('members') or []:
    initMember(memberInfo)

MODES = ['Action & Signal', 'Signal Only']

param_members = Parameter({'title': 'Members', 'schema': {'type': 'array', 'items': {'type': 'object', 'properties': {
   'name': {'type': 'string', 'order': 1},
   'hasStatus': {'type': 'boolean', 'title': 'Status?', 'order': 3},
   'power': {'title': 'Power', 'type': 'object', 'order': 4, 'properties': {
     'mode': {'title': 'Mode', 'type': 'string', 'enum': MODES}}
   },
   'muting': {'title': 'Muting', 'type': 'object', 'order': 5, 'properties': {
     'mode': {'title': 'Mode', 'type': 'string', 'enum': MODES}
   }
}}}}})

def initMember(memberInfo):
  name = mustNotBeBlank('name', memberInfo['name'])

  if memberInfo.get('hasStatus'):
    initStatusSupport(name)

  if (memberInfo.get('power') or {}).get('mode') in MODES:
    initSignalSupport(name, memberInfo['power']['mode'], 'Power', ['On', 'Off'])
    
  if (memberInfo.get('muting') or {}).get('mode') in MODES:
    initSignalSupport(name, memberInfo['muting']['mode'], 'Muting', ['On', 'Off'])

membersBySignal = {}
    
def initSignalSupport(name, mode, signalName, states):
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
          remoteAction.call(state)
          
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
  
def initStatusSupport(name):
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
      
    selfStatusSignal.emitIfDifferent({'level': aggregateLevel, 'message': aggregateMessage})
      
  memberStatusSignal.addEmitHandler(lambda arg: aggregateMemberStatus())
  memberStatusSuppressedSignal.addEmitHandler(lambda arg: aggregateMemberStatus())
  
  def handleRemoteEvent(arg):
    memberStatusSignal.emit(arg)
  
  create_remote_event('Member %s Status' % name, handleRemoteEvent, {'group': 'Members (Status)', 'order': next_seq(), 'schema': STATUS_SCHEMA},
                       suggestedNode=name, suggestedEvent="Status")
  
# members and status support ---!>


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
