# coding=utf-8
'''
**UDP datagram receiver** with source filtering, message routing and tiered diagnostics.

`REV 2.20260817`

Includes:

* configurable bind address and UDP port
* optional IPv4 source allowlist
* message length and basic payload validation
* receive and rejection counters with operational status
* adjustable console logging for packet diagnostics
* message-to-event routing through `ingredient_MessageEvents.py`

**REVISION HISTORY**

* rev. 2: add tiered logging and the message-handler ingredient contract
* rev. 1: initial release

'''

import sys


# May be overridden by an ingredient_*.py or custom_*.py script.
_receiverName = 'UDP Receiver'


param_bindAddress = Parameter({
    'title': 'Bind address',
    'desc': 'Local interface to listen on. Use 0.0.0.0 for all IPv4 interfaces.',
    'schema': {'type': 'string', 'hint': '0.0.0.0 (default)'},
    'default': '0.0.0.0',
    'order': 1
})

param_port = Parameter({
    'title': 'UDP port',
    'schema': {
        'type': 'integer',
        'minimum': 1,
        'maximum': 65535,
        'hint': '12345 (default)'
    },
    'default': 12345,
    'order': 2
})

param_allowedSources = Parameter({
    'title': 'Allowed source addresses',
    'desc': 'Exact IPv4 addresses allowed to emit events. An empty list accepts any source.',
    'schema': {'type': 'array', 'items': {'type': 'string'}},
    'default': [],
    'order': 3
})

param_maximumMessageLength = Parameter({
    'title': 'Maximum message length',
    'desc': 'Longer datagrams are rejected before their content is emitted.',
    'schema': {
        'type': 'integer',
        'minimum': 1,
        'maximum': 65535,
        'hint': '1024 bytes (default)'
    },
    'default': 1024,
    'order': 4
})


local_event_ReceivedCount = LocalEvent({
    'group': 'Status',
    'order': 10,
    'schema': {'type': 'integer', 'minimum': 0}
})

local_event_RejectedCount = LocalEvent({
    'group': 'Status',
    'order': 11,
    'schema': {'type': 'integer', 'minimum': 0}
})

local_event_LastRejected = LocalEvent({
    'group': 'Status',
    'order': 12,
    'schema': {
        'type': 'object',
        'properties': {
            'source': {'type': 'string'},
            'reason': {'type': 'string'},
            'receivedAt': {'type': 'string'}
        }
    }
})

local_event_Status = LocalEvent({
    'group': 'Status',
    'order': 9990,
    'schema': {
        'type': 'object',
        'properties': {
            'level': {'type': 'integer'},
            'message': {'type': 'string'}
        }
    }
})

local_event_LogLevel = LocalEvent({
    'group': 'Debug',
    'order': 10000,
    'desc': 'Raise this to show progressively more UDP packet detail in the console.',
    'schema': {'type': 'integer', 'minimum': 0, 'maximum': 2}
})


@local_action({'group': 'Debug', 'order': 10001})
def RaiseLogLevel(arg=None):
    level = local_event_LogLevel.getArg() or 0
    local_event_LogLevel.emit(min(level + 1, 2))


@local_action({'group': 'Debug', 'order': 10002})
def LowerLogLevel(arg=None):
    level = local_event_LogLevel.getArg() or 0
    local_event_LogLevel.emit(max(level - 1, 0))


def log(level, message):
    if (local_event_LogLevel.getArg() or 0) >= level:
        console.log(('  ' * level) + message)


_receiver = None
_allowedSources = []
_maximumMessageLength = 1024
_receivedCount = 0
_rejectedCount = 0
_datagramHandlers = []


def _register_datagram_handler(handler):
    if handler not in _datagramHandlers:
        _datagramHandlers.append(handler)


def _dispatch_datagram(datagram):
    for handler in list(_datagramHandlers):
        try:
            handler(datagram)
        except:
            error = sys.exc_info()[1]
            console.error('UDP datagram handler failed: %s' % error)


def _source_address(source):
    value = str(source).strip()
    if value.startswith('/'):
        value = value[1:]

    split = value.rfind(':')
    if split > 0:
        value = value[:split]

    if value.startswith('[') and value.endswith(']'):
        value = value[1:-1]

    return value


def _reject(source, reason):
    global _rejectedCount
    _rejectedCount += 1
    received_at = str(date_now())
    local_event_RejectedCount.emit(_rejectedCount)
    local_event_LastRejected.emit({
        'source': str(source),
        'reason': reason,
        'receivedAt': received_at
    })
    log(2, 'Rejected UDP datagram from %s: %s' % (source, reason))


def _received(source, data):
    global _receivedCount

    source_address = _source_address(source)
    if len(_allowedSources) > 0 and source_address not in _allowedSources:
        _reject(source, 'Source address is not allowed')
        return

    if data is None or len(data) == 0:
        _reject(source, 'Message is empty')
        return

    if len(data) > _maximumMessageLength:
        _reject(source, 'Message exceeds the configured maximum length')
        return

    if '\x00' in data:
        _reject(source, 'Message contains a null character')
        return

    _receivedCount += 1
    received_at = str(date_now())
    source_text = str(source)

    datagram = {
        'sequence': _receivedCount,
        'source': source_text,
        'message': data,
        'receivedAt': received_at
    }

    local_event_ReceivedCount.emit(_receivedCount)
    log(2, 'Accepted UDP datagram from %s: %s' % (source_text, repr(data)))
    _dispatch_datagram(datagram)


def _ready():
    bind_address = (param_bindAddress or '0.0.0.0').strip()
    source_policy = 'any source'
    if len(_allowedSources) > 0:
        source_policy = ', '.join(_allowedSources)
    message = 'Listening on %s:%s; allowed: %s' % (
        bind_address, param_port or 12345, source_policy)
    console.info(message)
    local_event_ReceivedCount.emit(0)
    local_event_RejectedCount.emit(0)
    local_event_Status.emit({'level': 0, 'message': message})


def main(arg=None):
    console.info('%s loading' % _receiverName)


@after_main
def start_receiver():
    global _receiver, _allowedSources, _maximumMessageLength

    bind_address = (param_bindAddress or '0.0.0.0').strip()
    port = int(12345 if param_port is None else param_port)
    maximum_length = int(1024 if param_maximumMessageLength is None else param_maximumMessageLength)

    if local_event_LogLevel.getArg() is None:
        local_event_LogLevel.emit(0)

    if len(bind_address) == 0:
        bind_address = '0.0.0.0'
    if port < 1 or port > 65535:
        local_event_Status.emit({'level': 2, 'message': 'UDP port must be between 1 and 65535'})
        return
    if maximum_length < 1 or maximum_length > 65535:
        local_event_Status.emit({'level': 2, 'message': 'Maximum message length must be between 1 and 65535'})
        return

    _allowedSources = []
    for source in param_allowedSources or []:
        source = str(source).strip()
        if len(source) > 0 and source not in _allowedSources:
            _allowedSources.append(source)
    _maximumMessageLength = maximum_length

    try:
        _receiver = UDP(
            source='%s:%s' % (bind_address, port),
            dest=None,
            ready=_ready,
            received=_received)
    except:
        error = sys.exc_info()[1]
        message = 'Could not start UDP receiver on %s:%s: %s' % (
            bind_address, port, error)
        console.error(message)
        local_event_Status.emit({'level': 2, 'message': message})


@at_cleanup
def stop_receiver():
    global _receiver
    if _receiver is not None:
        _receiver.close()
        _receiver = None
    console.info('%s stopped' % _receiverName)
