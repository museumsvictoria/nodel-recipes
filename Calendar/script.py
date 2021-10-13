# -*- coding: utf-8 -*-
# (utf-8 for agenda mark-down)

'''
A Calendar / Scheduling node that takes in multiple sources (e.g. see *Microsoft Exchange Schedule Retriever* recipe)

* rev. 2
    * support for "momentary" events (not stateful) when "start time" strictly equals "end time" e.g. "{ Power: Off }"
    * "Agenda" signal for usable, MARKDOWN formatted, future agenda (use `<panel>` element in Frontend)
    * minor: polling every 2.5 mins now (was incorrectly 5 mins)
'''

param_members = Parameter({'title': 'Member hierarchy', 'schema': {'type': 'array', 'items': {
        'type': 'object', 'properties': {
          'name': {'type': 'string', 'order': 1},
          'members': {'type': 'array', 'order': 3, 'items': {'type': 'object', 'properties': {
            'name': {'title': 'Name', 'type': 'string', 'order': 1},
            'members': {'type': 'array', 'order': 3, 'items': {'type': 'object', 'properties': {
              'name': {'title': 'Name', 'type': 'string', 'order': 1},
              'members': {'type': 'array', 'order': 3, 'items': {'type': 'object', 'properties': {    
                'name': {'title': 'Name', 'type': 'string', 'order': 1},
                'members': {'type': 'array', 'order': 3, 'items': {'type': 'object', 'properties': {    
                  'name': {'title': 'Name', 'type': 'string', 'order': 1}
    }}}}}}}}}}}}}}}})

param_signalTypes = Parameter({'title': 'Signal types', 'schema': {'type': 'array', 'items': { 'type': 'object', 'properties': {
        'name': {'type': 'string', 'order': 1},
        'activeState': {'type': 'string', 'order': 2},
        'nonactiveState': {'type': 'string', 'order': 3}
    }}}})

param_scheduleSources = Parameter({'title': 'Schedule sources', 'schema': {'type': 'array', 'items': {'type': 'object', 'properties': {
        'name': {'type': 'string', 'order': 1},
        'defaultMember': {'type': 'string', 'order': 2},
        'defaultSignal': {'type': 'string', 'order': 3}
  }}}})

local_event_ActiveNow = LocalEvent({'title': 'Active now', 'schema': {'type': 'array', 'items': {
        'type': 'object', 'properties': {
          'title': {'type': 'string', 'order': 1},
          'member': {'type': 'string', 'order': 2},
          'signal': {'type': 'string', 'order': 3},
          'state': {'type': 'string', 'order': 4},
          'warning': {'type': 'string', 'order': 5}
  }}}})

local_event_ActiveFuture = LocalEvent({'title': 'Active Future', 'schema': {'type': 'array', 'items': {
        'type': 'object', 'properties': {
          'instant': {'type': 'string', 'order': 1},
          'items': {'order': 2, 'type': 'array', 'items': { 'type': 'object', 'properties': {
            'title': {'type': 'string', 'order': 1},
            'member': {'type': 'string', 'order': 2},
            'signal': {'type': 'string', 'order': 3},
            'state': {'type': 'string', 'order': 4},
            'warning': {'type': 'string', 'order': 5}
        }}}}}}})

# loose, text-based agent using MARKDOWN
local_event_Agenda = LocalEvent({'group': 'Info', 'schema': {'type': 'string', 'format': 'long'}})

local_event_Debug = LocalEvent({'title': 'Debug level', 'group': 'Debug', 'schema': {'type': 'integer'}})

# signal types by name
signalTypes = {}

# last trees by signal name
lastTrees = {}

# members by member name
members = {}

# The trees holds the data-structure to help with state propagation:
#
# e.g. {
#        'M':
#          { 'state': 'On', 
#            'locked': True,
#            'members': [ #REF_TO_X, #REF_TO_Y ] 
#          },
#
#        'X':
#          { 'state': 'On',
#            'locked': False,
#            'members': [ #REF_TO_A, #REF_TO_B, #REF_TO_C ]
#          }
#
#        'A':
#          { ... 
#          }
#       .
#       .
#       .
#      }

# 'states' e.g.:
#
# [ {member:M  signal:Power  state:On     warning:...},
#   {member:C  signal:Power  state:Off} ] 
#
# All keys in items must already be resolved and sanitised.
# States with warnings will be skipped

def applyStateList(states, force=False):
  stateTrees = {}
  
  def lockAndTraverse(state, member, momentary, traverseOnly=False):
    # set the state if not locked
    if not member['locked']:
      member['state'] = state
      
    # lock if not only traversing
    if not traverseOnly:
      member['locked'] = True
      
    member['momentary'] = momentary
      
    for subMember in member['members']:
      # only traverse from here
      lockAndTraverse(state, subMember, momentary, True)
      
  # create a tree for each signal type
  for signalType in param_signalTypes:
    signalName = signalType['name']
    stateTrees[signalName] = createNewTree()
      
  # for each state entry, traverse its branch (on its signal tree)
  for stateInfo in states:
    # skip those with warnings
    if not isBlank(stateInfo.get('warning')):
      continue

    memberName = stateInfo['member']
    signal = stateInfo['signal']
    state = stateInfo['state']
    momentary = stateInfo.get('momentary')
    
    member = stateTrees[signal][memberName]
      
    lockAndTraverse(state, member, momentary)
    
  for signalType in param_signalTypes:
    signalName = signalType['name']
    
    stateTree = stateTrees[signalName]
    
    # DEBUG: dump the all the trees
    dumpTree(stateTree)
    
    # state tree is ready, now go through all affected members and call the actions
    # taking into account what their previous state information was
  
    for name in stateTree:
      memberInfo = stateTree[name]
      state = memberInfo['state']
      
      if memberInfo.get('momentary'):
        # clear state entry immediately so its non-active state is called
        memberInfo['state'] = None
    
      reverting = False
      
      lastState = lastTrees[signalName][name]['state']
      
      # wasMomentary = lastTrees[signalName][name]['momentary']
      
      if not force and state == lastState:
        continue
      
      # skip if member is unaffected and last state was also none, otherwise use default inactive state
      if state == None:
        if lastState == None:
          print ('Skipping "%s"' % name)
          continue
          
        else:
          # if wasMomentary:
          #   print ('Skipping "%s", was momentary' % name)
          #   continue
          
          state = signalType['nonactiveState']
          reverting = True
      
      # if member is an edge, propagation is safe, otherwise request no propagation
    
      actionName = '%s Propagate %s' % (name, signalName)
      arg = {'state': state, 'noPropagate': not memberInfo['isEdge']}
      
      print '%s... "%s": %s' % ('Reverting' if reverting else 'Forcing', actionName, arg)

      lookup_remote_action(actionName).call(arg)
      
      lookup_local_event('%s %s' % (name, signalName)).emit(state)
    
    lastTrees[signalName] = stateTree
      
def dumpTree(tree):
  if local_event_Debug.getArg() > 0:
    for name in tree:
      value = tree[name]
      console.log('[%s]: state:[%s] locked:[%s] momentary:[%s]' % (name, value['state'], value['locked'], value['momentary']))
  
def createNewTree():
  stateTree = {}
  
  def traverse(memberInfo):
    name = memberInfo['name']
    
    if name not in stateTree:
      member = { 'state': None,
                 'locked': False,
                 'isEdge': False,
                 'momentary': False, # if a momentary event was last involved
                 'members': [] }
      stateTree[name] = member
    else:
      member = stateTree[name]
      
    if safeLen(memberInfo['members']) == 0:
      member['isEdge'] = True
      
    else:
      for subMemberInfo in memberInfo['members']:
        traverse(subMemberInfo)
      
        # set the member references
        member['members'].append(stateTree[subMemberInfo['name']])
  
  # traverse the roots
  for memberInfo in param_members:
    traverse(memberInfo)
    
  return stateTree

def main():
  # set up the schedule sources
  if isEmpty(param_scheduleSources):
    console.warn('No schedule sources are configured; nothing to do.')
    return

  for scheduleSource in param_scheduleSources:
    initScheduleSource(scheduleSource)

  if isEmpty(param_members):
    console.warn('No members have been configured; nothing to do.')
    return
  
  if isEmpty(param_signalTypes):
    console.warn('At least one signal type needs to be declared, e.g. Power; nothing to do.')
    return
  
  for signalTypeInfo in param_signalTypes:
    signalTypes[signalTypeInfo['name']] = signalTypeInfo
  
  # deal with each root
  for memberInfo in param_members:
    initMember(memberInfo)
    
  # TODO: ideally unpersist this data but not a big deal if done outside of booking windows
  
  # initialise last trees
  # create a tree for each signal type
  for signalType in param_signalTypes:
    signalName = signalType['name']
    lastTrees[signalName] = createNewTree()
    
  delay = quantisePollNow()
  
  console.info('Scheduler started! (polling on half-minute boundaries first one in %.1f seconds)' % delay)
  
  # check the active future ones every 5 mins (after 30s at first)
  Timer(lambda: lookup_local_action('ProcessActiveFuture').call(), 2.5*60, 30)
  
# schedules the next poll on sharp 30s wall-clock edges
def quantisePollNow():
  halfMinRemainder = 30 - (date_now().getMillis() % 30000) / 1000.0   # is in secs
  timer_poller.setDelay(halfMinRemainder)

  # return what is the delay
  return halfMinRemainder

# establish a timer that will be manually quantised on 30s edges
def handlePollTimer():
  if local_event_Debug.getArg() > 0:
    console.log('handlePollTimer called')

  # when this timer fires, we should be on sharp 30s intervals 
  # of the wall clock
  
  lookup_local_action('ProcessActiveNow').call()
  quantisePollNow()
  
timer_poller = Timer(handlePollTimer, 99999, 99999) # NOTE: 'delay' is continually set on-the-fly
                                                    #       and 'interval' control is not used

def initMember(memberInfo):
  name = memberInfo.get('name')
  if isBlank(name):
    raise Exception('At least one node was missing a name')

  members[name] = memberInfo
    
  # go through each signal type
  for signalInfo in param_signalTypes:
    signalName = signalInfo['name']
    
    # A remote action to perform the operations when active...
    create_remote_action('%s Propagate %s' % (name, signalName))
  
    # An event indicating the current state...
    e = Event('%s %s' % (name, signalName), {'title': '"%s"' % name, 'group': '%s Signals' % signalName, 'order': next_seq(), 'schema': {'type': 'string'}})
  
  for subMemberInfo in safely(memberInfo.get('members')):
    initMember(subMemberInfo)

def initScheduleSource(sourceInfo):
  name = sourceInfo.get('name')
  if isBlank(name):
    raise Exception('A source name must be provided')

  if isBlank(sourceInfo.get('defaultSignal')):
    raise Exception('A default signal type must be provided')
  
  # set up the remote signal that the feed is received from
  create_remote_event('Source %s Items' % name, lambda arg: handleScheduleSourceFeed(sourceInfo, arg))

  # set up the local signal that the resolve feed will be used
  Event('Source %s Items' % name, {'title': '"%s"' % name, 'group': 'Sources', 'order': next_seq(), 'schema': {'type': 'array', 'items': 
                    { 'type': 'object', 'title': '...', 'properties': {
                      'title': {'type': 'string', 'order': 1},
                      'start': {'type': 'string', 'order': 2},
                      'end': {'type': 'string', 'order': 3},
                      'member': {'type': 'string', 'order': 4},
                      'signal': {'type': 'string', 'order': 5},
                      'state': {'type': 'string', 'order': 6}
    }}}})

def handleScheduleSourceFeed(sourceInfo, items):
  lookup_local_event('Source %s Items' % sourceInfo['name']).emit(items)
  
  lookup_local_action('ProcessActiveNow').call()

def local_action_ProcessActiveNow(arg=None):
  warnings = []
  
  items = processAllActiveItems(date_now(), warnings)

  local_event_ActiveNow.emit(items)

  applyStateList(items)
  
  quantisePollNow()
  
def local_action_ForceActiveNow(arg=None):
  warnings = []
  
  items = processAllActiveItems(date_now(), warnings)

  local_event_ActiveNow.emit(items)

  applyStateList(items, force=True)

def local_action_ProcessActiveFuture(arg=None):
  instantsSet = set()
  instantsList = list()

  for sourceInfo in param_scheduleSources:
    items = lookup_local_event('Source %s Items' % sourceInfo['name']).getArg()

    for item in safely(items):
      start = item['start']

      if start not in instantsSet:
        instantsList.append(date_parse(start))
        instantsSet.add(start)

  # sort by date
  instantsList.sort()

  result = list()
  
  warnings = list()

  for instant in instantsList:
    result.append({ 'instant': str(instant), 
                    'items': processAllActiveItems(instant, warnings) })

  if len(warnings) > 0:
    message = ', '.join(['["%s" when:%s, title:"%s", calendar:%s]' % (warning['message'], 
                                                                warning['start'].toString('d-MMM HH:mm'),
                                                                warning['title'],
                                                                warning['calendar']) for warning in warnings])
    
    local_event_Status.emit({'level': 2, 'message': "%s booking%s could not be properly interpreted: %s" % ((len(warnings), '', message) if len(warnings)==1 else (len(warnings), 's', message))})
    
  else:
    local_event_Status.emit({'level': 0, 'message': 'OK'})
  
  local_event_ActiveFuture.emit(result)
  
  emitAgenda(result)
  
def emitAgenda(fullList):
  "Where 'fullList' contains {'instant': '...', 'items' : [ ... ]}"
  lines = list()
  
  now = date_now()
  
  currentDay = ''
  
  for instantItem in fullList:
    instant = date_parse(instantItem['instant'])
    items = instantItem['items']
    
    for item in items:
      # only include instants where they're the start time
      start = date_parse(item['start'])
      if start != instant:
        continue
      
      day = instant.toString('E d-MMM')
      
      momentary = item.get('momentary')
      
      # group by day
      if day != currentDay:
        if len(lines) > 0:
          lines.append('')
          
        lines.append('**%s**\r\n' % day)
        
        currentDay = day
            
      end = date_parse(item['end'])
      
      inThePast = now.isAfter(end)
      
      isActive = now.isAfter(start) and now.isBefore(end)
            
      if not momentary:
        # include the end part (with day part if it's a different day)
        endPart = 'until **%s**' % (end.toString('h:mm a') if instant.toString('yyyyMMdd') == end.toString('yyyyMMdd') else end.toString('E d-MMM h:mm a'))
      else:
        endPart = ''
        
      # strip out brackets, e.g. "... { ... }" TODO: use regex
      title = item['title'] or ''
      bracketPos = title.rfind('{')
      if bracketPos >= 0:
        bracketEnd = title.rfind('}')
        if bracketEnd > bracketPos:
          title = title[:bracketPos]
      title = title.strip()
      
      titlePart = '' if not title else '("%s")' % title
        
      # example:
      # At 3:30 PM, Power On in ASDF "longer title" 
      # INVALID: At 3:30 PM Power On in ASDF "longer title" 
      
      line = u'%s%s **%s** %s %s in %s %s %s' % ('<span style="color:red">**INVALID**</span> ' if item.get('warning') else '',
                                       'From' if not momentary else 'At',
                                       instant.toString('h:mm a'),
                                       item['signal'],
                                       item.get('state') if 'state' in item else '<undefined_state>',
                                       item['member'],
                                       titlePart,
                                       endPart)
      if inThePast:
        # wrap in strike out
        line = ' * <s style="color:#444444;">%s</s>' % line
      elif isActive:
        # wrap in purple #ff00ff, actually green
        line = ' * <span style="color:#00ff00">%s</span>' % line
      else:
        # future, lighter #444444, actually leave as is
        line = ' * %s' % line
      
      lines.append(line)
  
  local_event_Agenda.emit('\r\n'.join(lines))
  
# the last time a poll was done (used to assist with zero-length items i.e. startTime == endTime)
_lastInstantMillis = None # (date time millis based)

def processAllActiveItems(instant, warnings):
  global _lastInstantMillis

  instantMillis = instant.getMillis()

  activeItems = list()
 
  if _lastInstantMillis != None:
    console.info('Polling between: %s  and: %s' % (date_instant(_lastInstantMillis), date_instant(instantMillis)))
    
  # consolidates all available calendar sources
  for sourceInfo in param_scheduleSources:
    items = lookup_local_event('Source %s Items' % sourceInfo['name']).getArg()

    for item in safely(items):
      start = item['start']
      end = item['end']

      startMillis = date_parse(start).getMillis()
      endMillis = date_parse(end).getMillis()
      
      momentary = False
      
      if _lastInstantMillis != None and startMillis == endMillis: # check if it's a momentary event
        # check if active
        if not (startMillis > _lastInstantMillis and startMillis <= instantMillis):
          # is not within poll period i.e. start is not between current instant and end of last instant
          continue
          
        # is an active momentary event
        console.info('Is Active Momentary! %s' % start)
        
        momentary = True
        
      elif instantMillis < startMillis or instantMillis >= endMillis:
        continue

      activeItem = {}
      
      warning = None
      
      for key in item:
        activeItem[key] = item[key]
        
      if momentary:
        activeItem['momentary'] = True

      # resolve member
      if isBlank(item['member']):
        activeItem['member'] = sourceInfo['defaultMember']

      # validate member
      if members.get(activeItem['member']) == None:
        warning = 'Unknown member: %s' % activeItem['member']

      # resolve signal type
      signal = item['signal']
      if isBlank(signal):
        signal = sourceInfo['defaultSignal']
      activeItem['signal'] = signal

      # validate signal type
      if signal not in signalTypes:
        warning = 'Ignoring unmanaged signal type: %s' % signal

      # resolve signal state
      elif item['state'] == None:
        # safe to look up signal type to get active state
        activeItem['state'] = signalTypes[activeItem['signal']]['activeState']
        
      if warning != None:
        activeItem['warning'] = warning
        warnings.append({'start': instant,
                         'calendar': sourceInfo['name'], 
                         'title': item['title'],
                         'message': warning})

      activeItems.append(activeItem)
      
  _lastInstantMillis = instantMillis
  
  return activeItems


# <!--- status

local_event_Status = LocalEvent({'group': 'Status', 'schema': {'type': 'object', 'properties': {
        'level': {'type': 'integer', 'order': 1},
        'message': {'type': 'string', 'format': 'long', 'order': 2}}}})

# -->

# <!--- convenience functions    
    
def trySplit(text, delim):
  '''Splits a string by a delim, trimming and discarding blanks'''
  if isBlank(text):
    return []
  
  parts = text.split(delim)
  
  result = list()
  
  for part in parts:
    if not isBlank(part):
      result.append(part.strip())
      
  return result

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

def safeLen(o):
  return len(o) if o != None else 0

# convenience functions ---!>
