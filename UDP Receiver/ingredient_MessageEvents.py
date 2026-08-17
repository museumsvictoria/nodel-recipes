# coding=utf-8
# Create a local event for each configured, expected UDP message.

from org.nodel import SimpleName


param_messageEvents = Parameter({
    'title': 'Message events',
    'desc': 'Create events for expected messages. Matching is case-sensitive and ignores trailing CR/LF characters.',
    'schema': {
        'type': 'array',
        'items': {
            'type': 'object',
            'properties': {
                'message': {
                    'title': 'Expected message',
                    'type': 'string',
                    'required': True,
                    'order': 1
                },
                'event': {
                    'title': 'Event name',
                    'type': 'string',
                    'required': True,
                    'order': 2
                },
                'value': {
                    'title': 'Event value',
                    'type': 'string',
                    'hint': '(defaults to the expected message)',
                    'order': 3
                }
            }
        }
    },
    'default': [],
    'order': 5
})


local_event_MatchedCount = LocalEvent({
    'group': 'Status',
    'order': 20,
    'schema': {'type': 'integer', 'minimum': 0}
})

local_event_UnmatchedCount = LocalEvent({
    'group': 'Status',
    'order': 21,
    'schema': {'type': 'integer', 'minimum': 0}
})

local_event_MessageEventStatus = LocalEvent({
    'group': 'Status',
    'order': 9991,
    'schema': {
        'type': 'object',
        'properties': {
            'level': {'type': 'integer'},
            'message': {'type': 'string'}
        }
    }
})


_messageMappings = {}
_matchedCount = 0
_unmatchedCount = 0


def _normalise_message(message):
    return str(message).rstrip('\r\n')


def _validate_message_events():
    specs = []
    messages = {}
    event_names = {}

    for index, item in enumerate(param_messageEvents or []):
        row = index + 1
        if not hasattr(item, 'get'):
            return None, 'Message event row %s must be an object' % row

        message = item.get('message')
        if not isinstance(message, basestring):
            return None, 'Message event row %s requires a string message' % row
        message = _normalise_message(message)
        if len(message) == 0:
            return None, 'Message event row %s has an empty message' % row
        if message in messages:
            return None, 'Message event rows %s and %s have the same message' % (
                messages[message], row)

        event_name = item.get('event')
        if not isinstance(event_name, basestring):
            return None, 'Message event row %s requires a string event name' % row
        event_name = event_name.strip()
        if len(event_name) == 0:
            return None, 'Message event row %s has an empty event name' % row

        simple_name = SimpleName(event_name).getReducedForMatchingName()
        if len(simple_name) == 0:
            return None, 'Message event row %s has an invalid event name' % row
        if simple_name in event_names:
            return None, 'Message event rows %s and %s have equivalent event names' % (
                event_names[simple_name], row)
        if lookup_local_event(event_name) is not None:
            return None, 'Message event row %s collides with existing event %s' % (
                row, event_name)

        value = item.get('value')
        if value is None or value == '':
            value = message
        elif not isinstance(value, basestring):
            return None, 'Message event row %s has a non-string event value' % row

        messages[message] = row
        event_names[simple_name] = row
        specs.append({
            'message': message,
            'eventName': event_name,
            'value': str(value),
            'order': row
        })

    return specs, None


def _route_message_event(datagram):
    global _matchedCount, _unmatchedCount

    raw_message = datagram['message']
    message = _normalise_message(raw_message)
    mapping = _messageMappings.get(message)

    if mapping is None:
        _unmatchedCount += 1
        local_event_UnmatchedCount.emit(_unmatchedCount)
        log(1, 'Unmatched UDP message from %s: %s' % (
            datagram['source'], repr(raw_message)))
        return

    _matchedCount += 1
    local_event_MatchedCount.emit(_matchedCount)
    mapping['event'].emit(mapping['value'])
    log(2, 'Matched UDP message from %s to event %s with value %s' % (
        datagram['source'], mapping['eventName'], repr(mapping['value'])))


_register_datagram_handler(_route_message_event)


@after_main
def setup_message_events():
    global _messageMappings, _matchedCount, _unmatchedCount

    _messageMappings = {}
    _matchedCount = 0
    _unmatchedCount = 0
    local_event_MatchedCount.emit(0)
    local_event_UnmatchedCount.emit(0)

    specs, error = _validate_message_events()
    if error is not None:
        message = 'Invalid message events: %s' % error
        console.error(message)
        local_event_MessageEventStatus.emit({'level': 2, 'message': message})
        return

    for spec in specs:
        event = create_local_event(spec['eventName'], {
            'group': 'Message Events',
            'order': spec['order'],
            'schema': {'type': 'string'}
        })
        _messageMappings[spec['message']] = {
            'event': event,
            'eventName': spec['eventName'],
            'value': spec['value']
        }

    if len(specs) == 0:
        message = 'No message mappings configured'
    else:
        message = '%s message mapping%s active' % (
            len(specs), '' if len(specs) == 1 else 's')

    local_event_MessageEventStatus.emit({'level': 0, 'message': message})
