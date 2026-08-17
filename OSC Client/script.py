# coding=utf-8
'''
OSC Client Node

`rev 3 2026.08.17`

Sends OSC 1.0 messages over UDP, and can optionally listen for replies.

* Turns address patterns into local actions via parameters.
* Sends arbitrary messages via a custom local action.
* Optionally binds a receive port and emits inbound messages as events.

OSC encoding is implemented directly against the OSC 1.0 specification, so this
recipe has no external dependency, no runtime download and no self-restart.

**REVISION HISTORY**

* rev. 3: pure-Jython OSC codec, replacing the pyosc dependency that was fetched
  from GitHub at startup (the node then restarted itself). Arguments may now be
  typed, repeated, empty, or literal `0`. Optional receive port with a generic
  `Received` event and a handler hook for ingredients. Sends are reported
  through the usual `LogLevel` convention instead of unconditional
  `console.log`, so a node polling on a timer no longer fills its console.

  **Breaking change:** rev 2 divided any numeric argument greater than 1 by 100,
  so `5` went on the wire as `0.05`. Arguments are now sent exactly as written.
  Rigs that relied on the old scaling must send the already-scaled value.

* rev. 2: pattern-driven client, custom message action.

---

An OSC message is:

    <address pattern> <type tag string> <arguments>

Each part is padded to a multiple of 4 bytes. Addresses follow a directory-like
structure, e.g. `/voices/synth1/osc1/modfreq`.

See http://opensoundcontrol.org/spec-1_0
'''

import struct

# <-- parameters

DEFAULT_IPADDRESS = '127.0.0.1'
DEFAULT_PORT = 9000
DEFAULT_PATTERN = '/foo/bar'

param_ipAddress = Parameter({
    'title': 'IP address',
    'schema': {'type': 'string', 'hint': DEFAULT_IPADDRESS},
    'order': next_seq()
})

param_port = Parameter({
    'title': 'Port',
    'schema': {'type': 'integer', 'hint': DEFAULT_PORT},
    'order': next_seq()
})

param_receivePort = Parameter({
    'title': 'Receive port',
    'desc': 'Optional. Bind this local UDP port to listen for replies. Leave '
            'empty to send only. Outgoing messages also originate from this '
            'port, so devices that reply to the sender are answered here.',
    'schema': {'type': 'integer', 'hint': 'empty (send only)'},
    'order': next_seq()
})

param_patterns = Parameter({
    'title': 'Patterns',
    'desc': 'One action per entry. Leave Argument empty and the operator '
            'supplies a value when the action is called, for a fader or a '
            'level. Fill Argument in and the action becomes a plain button '
            'that always sends that value, for a preset or a cue.',
    'order': next_seq(),
    'schema': {'type': 'array', 'items': {
        'type': 'object', 'title': 'Pattern', 'properties': {
            'label': {'type': 'string', 'title': 'Label', 'hint': 'Foobar', 'order': next_seq()},
            'address': {'type': 'string', 'title': 'Address', 'hint': DEFAULT_PATTERN, 'order': next_seq()},
            'args': {'type': 'string', 'title': 'Argument', 'hint': 'optional, e.g. 12 or "cue name"', 'order': next_seq()}
        }}}
})

# -->

# <-- OSC 1.0 codec

def osc_string(value):
    'Encodes an OSC-string: null terminated, padded to a multiple of 4 bytes.'
    if isinstance(value, unicode):
        data = value.encode('utf-8')
    else:
        data = str(value)

    data += '\x00'
    return data + ('\x00' * ((4 - (len(data) % 4)) % 4))


def osc_blob(value):
    'Encodes an OSC-blob: int32 length, then data padded to a multiple of 4.'
    data = str(value)
    return struct.pack('>i', len(data)) + data + ('\x00' * ((4 - (len(data) % 4)) % 4))


def osc_message(address, args):
    '''
    Encodes an OSC message. `args` is a list of (tag, value) pairs as produced
    by `parse_arguments`. An empty list produces a message with the bare `,`
    type tag string, which is what a device expects for a no-argument command.
    '''
    tags = ','
    body = ''

    for tag, value in args:
        tags += tag
        if tag == 'i':
            body += struct.pack('>i', int(value))
        elif tag == 'f':
            body += struct.pack('>f', float(value))
        elif tag == 's':
            body += osc_string(value)
        elif tag == 'b':
            body += osc_blob(value)
        # 'T', 'F' and 'N' carry no payload

    return osc_string(address) + osc_string(tags) + body


def read_osc_string(data, offset):
    'Reads a padded OSC-string, returning (value, next offset).'
    end = data.find('\x00', offset)
    if end < 0:
        raise ValueError('unterminated OSC string')

    value = data[offset:end]
    return value, offset + (((end - offset) // 4) + 1) * 4


def decode_osc_message(data):
    '''
    Decodes an OSC message into {'address': ..., 'args': [...]}.

    Note: Nodel hands UDP payloads to scripts as text, so a datagram carrying
    bytes above 0x7F may not survive intact. Addresses and type tags are ASCII
    and are always safe; numeric arguments are decoded on a best-effort basis.
    '''
    address, offset = read_osc_string(data, 0)

    args = []
    if offset < len(data):
        tags, offset = read_osc_string(data, offset)

        for tag in tags.lstrip(','):
            if tag == 'i':
                args.append(struct.unpack('>i', data[offset:offset + 4])[0])
                offset += 4
            elif tag == 'f':
                args.append(struct.unpack('>f', data[offset:offset + 4])[0])
                offset += 4
            elif tag == 's':
                value, offset = read_osc_string(data, offset)
                args.append(value)
            elif tag == 'T':
                args.append(True)
            elif tag == 'F':
                args.append(False)
            elif tag == 'N':
                args.append(None)
            else:
                # Unknown or unsupported tag: stop rather than mis-read the rest
                break

    return {'address': address, 'args': args}

# -->

# <-- argument parsing

def split_arguments(text):
    '''
    Splits a comma separated argument list into (value, quoted) pairs.

    Quoting serves two purposes: a string argument may contain a comma, and a
    numeric looking value may be forced to be sent as a string.
    '''
    parts = []
    current = ''
    quoted = False
    quote = None

    for char in text:
        if quote is not None:
            if char == quote:
                quote = None
            else:
                current += char
        elif char in ('"', "'"):
            quote = char
            quoted = True
        elif char == ',':
            parts.append((current, quoted))
            current = ''
            quoted = False
        else:
            current += char

    parts.append((current, quoted))
    return parts


def type_argument(value):
    '''
    Maps a single value onto an (OSC type tag, value) pair.

    Bare digits become int32 and bare decimals become float32, which is what
    almost every OSC device expects. Quote a value in the action field to force
    it to be sent as a string.
    '''
    if isinstance(value, bool):
        return ('T' if value else 'F', None)

    if isinstance(value, int) or isinstance(value, long):
        return ('i', value)

    if isinstance(value, float):
        return ('f', value)

    text = value if isinstance(value, basestring) else str(value)
    stripped = text.strip()

    if len(stripped) == 0:
        return ('s', '')

    try:
        return ('i', int(stripped))
    except ValueError:
        pass

    try:
        return ('f', float(stripped))
    except ValueError:
        pass

    return ('s', text)


def parse_arguments(arg):
    '''
    Turns an action argument into a list of (tag, value) pairs.

    Accepts `None` and the empty string (no arguments), a number or boolean, a
    list, or a comma separated string such as `5, 2.0, "cue name"`.
    '''
    if arg is None:
        return []

    if isinstance(arg, list):
        return [type_argument(item) for item in arg]

    if not isinstance(arg, basestring):
        return [type_argument(arg)]

    if len(arg.strip()) == 0:
        return []

    args = []
    for value, quoted in split_arguments(arg):
        if quoted:
            # Quoted values are sent verbatim as strings, never coerced
            args.append(('s', value))
        elif len(value.strip()) > 0:
            args.append(type_argument(value))
        # An unquoted empty section (e.g. a trailing comma) sends nothing

    return args

# -->

# <-- events

local_event_Received = LocalEvent({
    'title': 'Received',
    'group': 'Monitoring',
    'order': next_seq(),
    'desc': 'The most recent inbound OSC message. Only emitted when a receive '
            'port is configured.',
    'schema': {'type': 'object', 'properties': {
        'address': {'type': 'string', 'order': 1},
        'args': {'type': 'array', 'items': {'type': 'string'}, 'order': 2},
        'source': {'type': 'string', 'order': 3}
    }}
})

# -->

# <-- UDP

# Parameter values are only bound by the time main() runs; at module scope the
# param_* names still hold their descriptors. Everything that depends on them
# is therefore resolved in start_udp(), called from main().
udp = None
_receivePort = 0

# Handlers registered by ingredient_*.py scripts, called as
# handler(address, args, source) for every decoded inbound message.
_messageHandlers = []


def register_message_handler(handler):
    'Registers a callback for decoded inbound OSC messages.'
    if handler not in _messageHandlers:
        _messageHandlers.append(handler)


def udp_received(source, data):
    try:
        message = decode_osc_message(data)
    except:
        console.warn('Received a datagram from %s that is not a valid OSC message.' % source)
        return

    local_event_Received.emit({
        'address': message['address'],
        'args': [str(value) for value in message['args']],
        'source': str(source)
    })

    for handler in list(_messageHandlers):
        try:
            handler(message['address'], message['args'], source)
        except:
            console.error('An inbound OSC message handler failed.')


def udp_ready():
    if _receivePort > 0:
        console.info('UDP ready. Sending to %s, listening on %s.' % (udp.getDest(), _receivePort))
    else:
        console.info('UDP ready. Sending to %s.' % udp.getDest())


def start_udp():
    'Resolves parameter values and opens the socket. Called from main().'
    global udp, _receivePort

    dest = '%s:%s' % (param_ipAddress or DEFAULT_IPADDRESS, param_port or DEFAULT_PORT)
    _receivePort = param_receivePort or 0

    if _receivePort > 0:
        udp = UDP(source='0.0.0.0:%s' % _receivePort, dest=dest,
                  ready=udp_ready, received=udp_received)
    else:
        udp = UDP(dest=dest, ready=udp_ready)

# -->

# <-- logging

local_event_LogLevel = LocalEvent({
    'title': 'Log level',
    'group': 'Debug',
    'order': 10000 + next_seq(),
    'desc': 'Use this to ramp up the logging (with indentation). 0 is quiet, '
            '1 shows messages sent on demand, 2 also shows periodic traffic.',
    'schema': {'type': 'integer'}
})


def log(level, msg):
    if (local_event_LogLevel.getArg() or 0) >= level:
        console.log(('  ' * level) + msg)


@local_action({'title': 'Raise log level', 'group': 'Debug', 'order': 10000 + next_seq()})
def RaiseLogLevel(arg=None):
    local_event_LogLevel.emit(min((local_event_LogLevel.getArg() or 0) + 1, 2))


@local_action({'title': 'Lower log level', 'group': 'Debug', 'order': 10000 + next_seq()})
def LowerLogLevel(arg=None):
    local_event_LogLevel.emit(max((local_event_LogLevel.getArg() or 0) - 1, 0))

# -->

# <-- functions

def send_osc(address, arg, level=1):
    '''
    Encodes and sends a single OSC message. Shared by every action.

    `level` is the log level the send is reported at, so periodic traffic such
    as a health check can sit at 2 and stay out of the console by default.
    '''
    args = parse_arguments(arg)
    udp.send(osc_message(address, args))

    if len(args) == 0:
        log(level, 'Sent [ %s ].' % address)
    else:
        log(level, 'Sent [ %s ] to [ %s ].' % (', '.join([str(value) for tag, value in args]), address))


def create_client_action(pattern):
    '''
    Creates one local action per configured pattern.

    With an argument configured the action ignores whatever it is called with
    and always sends that value, so the dashboard shows a plain button.
    '''
    preset = pattern.get('args')
    fixed = preset is not None and len(preset.strip()) > 0

    def handler(arg=None):
        send_osc(pattern['address'], preset if fixed else arg)

    create_local_action(
        name='%s' % pattern['label'],
        metadata=basic_meta(pattern['label'], pattern['address'], preset if fixed else None),
        handler=handler
    )


def create_custom_action():
    'Creates a single action for sending an arbitrary OSC message.'

    def handler(message):
        if message is None:
            return

        address = (message.get('address') or DEFAULT_PATTERN).strip()
        send_osc(address, message.get('args'))

    metadata = {
        'group': 'Custom',
        'title': 'Send a custom message',
        'order': next_seq(),
        'schema': {'type': 'object', 'properties': {
            'address': {'type': 'string', 'title': 'Address', 'hint': DEFAULT_PATTERN, 'order': next_seq()},
            'args': {'type': 'string', 'title': 'Arguments', 'hint': '5, 2.0, "cue name"', 'order': next_seq()}
        }}
    }

    create_local_action('Custom', handler=handler, metadata=metadata)


def basic_meta(label, address, preset=None):
    'Action metadata. A preset argument means a button, otherwise a text field.'
    if preset is not None:
        return {
            'title': '%s' % label,
            'group': 'Patterns',
            'order': next_seq(),
            'desc': 'Sends %s to %s.' % (preset, address)
        }

    return {
        'title': '%s' % label,
        'group': 'Patterns',
        'order': next_seq(),
        'desc': 'Sends to %s. Arguments are optional and comma separated; '
                'quote a value to send it as a string.' % address,
        'schema': {'type': 'string', 'title': '%s' % address}
    }

# -->

# <-- main

def main(arg=None):
    console.log('Nodel script started.')

    start_udp()
    create_custom_action()

    if not is_empty(param_patterns):
        for pattern in param_patterns:
            create_client_action(pattern)

# -->
