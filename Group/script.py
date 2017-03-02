'''A node that groups members for control propagation and status monitoring.'''

def main(arg=None):
  console.info('Started!')
  
# <!--- members and status support  

@after_main
def initMembersSupport():
  for memberInfo in param_members or []:
    initMember(memberInfo)
  
param_members = Parameter({'title': 'Members', 'schema': {'type': 'array', 'items': {'type': 'object', 'properties': {
   'name': {'type': 'string', 'order': 1},
   'slave': {'type': 'boolean', 'title': 'Slave?', 'order': 2},
   'hasStatus': {'type': 'boolean', 'title': 'Status?', 'order': 3},          
   'hasPower': {'type': 'boolean', 'title': 'Power?', 'order': 4},
   'hasMuting': {'type': 'boolean', 'title': 'Muting?', 'order': 5}
 }}}})

membersBySignal = {}  

def initMember(memberInfo):
  name = mustNotBeBlank('name', memberInfo['name'])
    
  if memberInfo.get('hasMuting'):
    initSignalSupport(memberInfo, 'Muting', ['On', 'Off'])
    
  if memberInfo.get('hasPower'):
    initSignalSupport(memberInfo, 'Power', ['On', 'Off'])
    
  if memberInfo.get('hasStatus'):
    initStatusSupport(memberInfo)
    
def initSignal(signalName, states):
  resultantStates = states + ['Partially %s' % s for s in states]
  
  localDesiredSignal = Event('Desired %s' % signalName, {'group': signalName, 'order': next_seq(), 'schema': {'type': 'string', 'enum': states}})
  
  localResultantSignal = Event('%s' % signalName, {'group': signalName, 'order': next_seq(), 'schema': {'type': 'string', 'enum': resultantStates}})
  
  def adjust(state, propagate):
    localDesiredSignal.emit(state)
    
    # for convenience, just emit the state as the status if no members are configured
    if isEmpty(param_members):
      localResultantSignal.emit(state)
      
    else:
      if propagate:
        for memberName in membersBySignal[signalName]['controlled']:
          lookup_remote_action('Member %s %s' % (memberName, signalName)).call({'state': state, 'noPropagate': False})
          
  localAction = Action('%s' % signalName, lambda arg: adjust(arg, True), {'group': signalName, 'order': next_seq(), 'schema': {'type': 'string', 'enum': states}})
  
  localPropagateAction = Action('%s Propagate' % signalName, lambda arg: adjust(arg['state'], not arg.get('noPropagation')), {'group': signalName, 'order': next_seq(), 'schema': {'type': 'object', 'properties': {
          'state': {'type': 'string', 'enum': states, 'order': 1},
          'noPropagation': {'type': 'boolean', 'order': 2}}}})
  
  return localDesiredSignal, localResultantSignal

def getMembersInfoOrRegister(signalName, memberName, memberInfo):
  members = membersBySignal.get(signalName)
  if members == None:
    members = { 'slaves': list(),
                'controlled': list() }
    membersBySignal[signalName] = members
    
  if memberInfo.get('slave'):
    members['slaves'].append(memberName)
  else:
    members['controlled'].append(memberName)    
    
  return members

def initSignalSupport(memberInfo, signalName, states):
  name = memberInfo['name']
  
  members = getMembersInfoOrRegister(signalName, name, memberInfo)
  
  # establish local signals if haven't done so already
  localDesiredSignal = lookup_local_event('Desired %s' % signalName)
  
  if localDesiredSignal == None:
    localDesiredSignal, localResultantSignal = initSignal(signalName, states)
  else:
    localResultantSignal = lookup_local_event(signalName)
    
  # establish a remote action (if not a slave)
  if not memberInfo.get('slave'):
    create_remote_action('Member %s %s' % (name, signalName), {'group': 'Members (%s)' % signalName, 'schema': {'type': 'string', 'enum': states}},
                         suggestedNode=name, suggestedAction=signalName)
  
  # establish a remote signal to receive status
  # signal status states include 'Partially ...' forms
  resultantStates = states + ['Partially %s' % s for s in states]
  
  localMemberSignal = Event('Member %s %s' % (name, signalName), {'group': 'Members (%s)' % signalName, 'order': next_seq(), 'schema': {'type': 'string', 'enum': resultantStates}})
  
  def aggregateMemberSignals():
    shouldBeState = localDesiredSignal.getArg()
    partially = False
    
    for memberName in members['slaves'] + members['controlled']:
      if lookup_local_event('Member %s %s' % (memberName, signalName)).getArg() != shouldBeState:
        partially = True
        
    localResultantSignal.emit('Partially %s' % shouldBeState if partially else shouldBeState)
    
  localMemberSignal.addEmitHandler(lambda arg: aggregateMemberSignals())
  localDesiredSignal.addEmitHandler(lambda arg: aggregateMemberSignals())
  
  def handleRemoteEvent(arg):
    localMemberSignal.emit(arg)
  
  create_remote_event('Member %s %s' % (name, signalName), handleRemoteEvent, {'group': 'Members (%s)' % signalName, 'order': next_seq(), 'schema': {'type': 'string', 'enum': resultantStates}},
                     suggestedNode=name, suggestedEvent=signalName)


STATUS_SCHEMA = { 'type': 'object', 'properties': {
                    'level': { 'type': 'integer', 'order': 1 },
                    'message': {'type': 'string', 'order': 2 }
                } }

EMPTY_SET = {}
  
def initStatusSupport(memberInfo):
  name = memberInfo['name']
  
  # look up the members structure (assume
  members = getMembersInfoOrRegister('Status', name, memberInfo)
  
  # check if this node has a status yet
  selfStatusSignal = lookup_local_event('Status')
  if selfStatusSignal == None:
    selfStatusSignal = Event('Status', {'group': 'Status', 'order': next_seq(), 'schema': STATUS_SCHEMA})
    
  # create the status for the member
  memberStatusSignal = Event('Member %s Status' % name, {'group': 'Members (Status)', 'order': next_seq(), 'schema': STATUS_SCHEMA})
  
  def aggregateMemberStatus():
    aggregateLevel = 0
    aggregateMessage = 'OK'
    
    # for composing the aggegate message at the end
    msgs = []
    
    for memberName in members['slaves'] + members['controlled']:
      memberStatus = lookup_local_event('Member %s Status' % memberName).getArg() or EMPTY_SET
      
      memberLevel = memberStatus.get('level') or 99
      if memberLevel > aggregateLevel:
        # raise the level
        aggregateLevel = memberLevel
      
      memberMessage = memberStatus.get('message') or 'Has never been seen'
      if memberLevel > 0:
        if isBlank(memberMessage):
          msgs.append(memberName)
        else:
          msgs.append('%s: [%s]' % (memberName, memberMessage))
          
    if len(msgs) > 0:
      aggregateMessage = ', '.join(msgs)
      
    selfStatusSignal.emitIfDifferent({'level': aggregateLevel, 'message': aggregateMessage})
      
  memberStatusSignal.addEmitHandler(lambda arg: aggregateMemberStatus())
  
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
  
def safely(o):
  return o if o != None else ''

# convenience functions ---!>