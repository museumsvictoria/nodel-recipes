'''
This creates a 'X Status' signal which aggregates the statuses of existing Status signals or establishes new remotely 'wired' ones.

Use initStatusCombiner(names, statusPrefix='Members', membersPrefix='Member')

'''

from nodetoolkit import *

SCHEMA_STATUS = {'type': 'object', 'properties': {
  'level': {'type' : 'integer', 'order': 1},
  'message': {'type': 'string', 'order': 2}
}}

statusSignalsByName = {}

EMPTY_DICT = {}

def initStatusCombiner(names, statusPrefix='Members', membersPrefix='Member'):
  '''Creates a status (if not already created) and adds additional status sources.'''
  statusSignal = Event(('%s Status' % statusPrefix).strip(), {'order': next_seq(), 'schema': SCHEMA_STATUS})

  for name in names:
    _initMember(statusSignal, membersPrefix, name)

# create the local event
def _initMember(statusSignal, prefix, name):
  fullName = ('%s %s' % (prefix, name)).strip()

  # does a signal already exist?
  signal = lookup_local_event(fullName)

  if signal is None:
    # source member signal does not exist so create it and "wire" remote event as source
    signal = Event(fullName, {'group': '(advanced)', 'order': next_seq(), 'schema': SCHEMA_STATUS})

    # pass the remote event straight through to the signal
    remoteEvent = create_remote_event('%s %s Status' % (prefix, name), lambda arg: signal.emit(arg))

  # add a handle on the signal
  signal.addEmitHandler(lambda arg: _handleStatusChanges(statusSignal))

  statusSignalsByName[name] = signal

# remote event entry-point
def _handleStatusChanges(statusSignal):
  combinedLevel = 0
  combinedMessage = 'OK'

  msgs = []

  for name in statusSignalsByName:
    signal = statusSignalsByName[name]
    status = signal.getArg() or EMPTY_DICT

    level = status.get('level')

    if level == None: # as opposed to the value '0'
      level = 99

    if level > combinedLevel:
      # raise the level
      combinedLevel = level

    message = status.get('message') or 'Has never been seen'
    if level > 0:
      if isblank(message):
        msgs.append(name)
      else:
        msgs.append('%s: [%s]' % (name, message))

  if len(msgs) > 0:
    combinedMessage = ', '.join(msgs)

  statusSignal.emitIfDifferent({'level': combinedLevel, 'message': combinedMessage})
