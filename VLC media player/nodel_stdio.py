import json
import sys
import fileinput

# lookup tables
_actionInfos_byReducedName = {}
_eventInfos_byReducedName = {}
_node_instance = None

class _NodelPointInfo:
    '''(works for Actions and Events)'''
    name = None
    reduced = None
    func = None
    metadata = None

    def __init__(self, name=None, func=None, metadata=None):
        # use the function name if the name's not provided
        self.name = name if name else func.__name__
        self.reduced = reduceName(self.name)
        self.func = func
        self.metadata = metadata

    def __repr__(self):
        return str({'name': self.name, 'reduced': self.reduced, 'metadata': self.metadata})

# (function decorator)
def nodel_action(metadata={}):
    '''Registers a Nodel action.'''

    def action_decorator(func):

        def func_wrapper(*args):
            # 'self' (instance) will be filled in here
            return func(*args)

        info = _NodelPointInfo(name=func.__name__, func=func_wrapper, metadata=metadata)
        _actionInfos_byReducedName[info.reduced] = info
        
        return func_wrapper
    
    return action_decorator

class _NodelEvent:
    
    def __init__(self, info):
        self.info = info

    def emit(self, arg=None):
        '''Emits the event arg'''
        print(json.dumps({'event': self.info.name, 'arg': arg}))

# (used as a static function)
def create_nodel_event(name, metadata={}):
    '''Registers a Nodel event'''
    info = _NodelPointInfo(name=name, metadata=metadata)
    _eventInfos_byReducedName[info.reduced] = info

    return _NodelEvent(info)

def get_reflection():
    '''Returns 'reflection' of stdio channel (actions, events)'''
    actions = list()
    actionsMetadata = list()

    for k in _actionInfos_byReducedName:
        info = _actionInfos_byReducedName[k]
        actions.append(info.name)
        actionsMetadata.append(info.metadata)

    events = list()
    eventsMetadata = list()

    for k in _eventInfos_byReducedName:
        info = _eventInfos_byReducedName[k]
        events.append(info.name)
        eventsMetadata.append(info.metadata)

    return ({ 'actions': actions, 'metadata': actionsMetadata },
            { 'events': events, 'metadata': eventsMetadata })


def _emit_reflection():
    (events, actions) = get_reflection()
    print(json.dumps(events))
    print(json.dumps(actions))

def register_instance_node(instance):
    global _node_instance
    _node_instance = instance

def start_nodel_channel():
    '''Starts the bridge and blocks (whilest processing stdin)'''
    # dump metadata first
    _emit_reflection()

    _process_stdin()


# general processing functions
    
def _process_stdin():
    print('# processing stdin')
    
    while True:
        line = sys.stdin.readline()
        
        print('# got raw line "%s"' % line)
        trimmed = line.strip()
        
        # print '# ([%s] arrived)' % trimmed
        if len(trimmed) == 0:
            continue

        if trimmed[0] == '#':
            print(trimmed)
            continue

        if trimmed[0] != '{':
            # only accept JSON objects
            continue

        try:
            message = json.loads(trimmed)
            print('# got message %s' % message)
        except Exception as exc:
            print('# error handling message - %s' % exc)
            continue
        
        _process_message(message)

# (message is an dict)
def _process_message(message):
    action = message.get('action')
    if action is not None:
        _process_action_message(action, message)
        return
        
    # (reserved for further processing)
    
    return


def _process_action_message(action, actionMessage):
    reducedName = reduceName(action)

    actionInfo = _actionInfos_byReducedName.get(reducedName)
    if actionInfo == None:
        # no matching action found
        print('# no matching action "%s"' % action)
        return

    try:
        argPart = actionMessage.get('arg') 
        if argPart != None:
            actionInfo.func.__call__(_node_instance, argPart)
        else:
            actionInfo.func.__call__(_node_instance)
        
    except Exception as exc:
        print('# error handling action message - %s' % exc)

# static convenience functions

def emit_event(event, arg=None):
    if arg:
        print(json.dumps({'event': event, 'arg': arg}))
    else:
        print(json.dumps({'event': event}))

def reduceName(name):
    '''Reduces a name for comparison purposes'''
    return ''.join([c.lower() for c in name if c.isalnum()])