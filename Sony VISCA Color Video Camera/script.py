'''
With this recipe, you can control pan/tilt and preset of Sony VISCA Color Video Camera.
'''

# You can refer to the Scripting Toolkit Reference by clicking on the
# Nodel logo twice and following the link


# <!-- parameters

param_disabled = Parameter({'desc': 'Disables this node?', 'schema': {'type': 'boolean'}})
param_ipAddress = Parameter({'schema': {'type': 'string'}})

DEFAULT_PORT = 52381
param_port = Parameter({'schema': {'type': 'integer', 'hint': '(default is %s)' % DEFAULT_PORT}})

DEFAULT_VISCA_ADDRESS = 1
param_viscaAddress = Parameter({'schema': {'type': 'integer', 'hint': '(default is %s)' % DEFAULT_VISCA_ADDRESS}})


def udp_received(src, data):
    console.log('udp RECV from %s %s' % (src, string_to_hex_arr(data)))


def udp_sent(data):
    console.log('udp SENT %s' % string_to_hex_arr(data))


def string_to_hex_arr(src_string):
    arr = [elem.encode('hex') for elem in src_string]
    return arr


udp = UDP(sent=udp_sent,  # 'dest' set in 'main'
          ready=lambda: console.info('udp READY'),
          received=udp_received)


def address_to_hex(addr_number):
    return chr(0x80 + addr_number)


def seq_to_hex(seq_number):
    hex_str = ''
    hex_str += chr(seq_number >> 24 & 0xff)
    hex_str += chr(seq_number >> 16 & 0xff)
    hex_str += chr(seq_number >> 8 & 0xff)
    hex_str += chr(seq_number & 0xff)
    return hex_str


def number_to_hex(number):
    return chr(int(number))


def get_command_string(cmd_type, visca_addr, seq_number, data=None):
    msg_header = None
    msg_payload = None

    if cmd_type == 'up':
        msg_header = '\x01\x00' + '\x00\x09' + seq_to_hex(seq_number)
        msg_payload = address_to_hex(visca_addr) + '\x01\x06\x01\x05\x05\x03\x01' + '\xff'
    elif cmd_type == 'down':
        msg_header = '\x01\x00' + '\x00\x09' + seq_to_hex(seq_number)
        msg_payload = address_to_hex(visca_addr) + '\x01\x06\x01\x05\x05\x03\x02' + '\xff'
    elif cmd_type == 'left':
        msg_header = '\x01\x00' + '\x00\x09' + seq_to_hex(seq_number)
        msg_payload = address_to_hex(visca_addr) + '\x01\x06\x01\x05\x05\x01\x03' + '\xff'
    elif cmd_type == 'right':
        msg_header = '\x01\x00' + '\x00\x09' + seq_to_hex(seq_number)
        msg_payload = address_to_hex(visca_addr) + '\x01\x06\x01\x05\x05\x02\x03' + '\xff'
    elif cmd_type == 'home':
        msg_header = '\x01\x00' + '\x00\x05' + seq_to_hex(seq_number)
        msg_payload = address_to_hex(visca_addr) + '\x01\x06\x04' + '\xff'
    elif cmd_type == 'stop':
        msg_header = '\x01\x00' + '\x00\x09' + seq_to_hex(seq_number)
        msg_payload = address_to_hex(visca_addr) + '\x01\x06\x01\x05\x05\x03\x03' + '\xff'
    elif cmd_type == 'reset_seq':
        msg_header = '\x02\x00' + '\x00\x01' + seq_to_hex(seq_number)
        msg_payload = '\x01'
    elif cmd_type == 'preset_reset':
        msg_header = '\x01\x00' + '\x00\x07' + seq_to_hex(seq_number)
        msg_payload = address_to_hex(visca_addr) + '\x01\x04\x3f\x00' + number_to_hex(data) + '\xff'
    elif cmd_type == 'preset_set':
        msg_header = '\x01\x00' + '\x00\x07' + seq_to_hex(seq_number)
        msg_payload = address_to_hex(visca_addr) + '\x01\x04\x3f\x01' + number_to_hex(data) + '\xff'
    elif cmd_type == 'preset_recall':
        msg_header = '\x01\x00' + '\x00\x07' + seq_to_hex(seq_number)
        msg_payload = address_to_hex(visca_addr) + '\x01\x04\x3f\x02' + number_to_hex(data) + '\xff'
    else:
        raise Exception('Unsupported command type')

    return msg_header + msg_payload


# save preset

# recall preset

# -->

# -------------------------------- Actions --------------------------------


def resetSequenceNo():
    console.log('[resetSequenceNo] called')
    ctrlCmd_reset_seq = get_command_string('reset_seq', param_viscaAddress, next_seq() + 20000)
    udp.send(ctrlCmd_reset_seq)


def ptz_home(data):
    console.log('[ptz_home] called')
    inquery_ptdHome = get_command_string('home', param_viscaAddress, next_seq() + 20000)
    udp.send(inquery_ptdHome)


def ptz_up(data):
    console.log('[ptz_up] called')
    inquery_ptdUp = get_command_string('up', param_viscaAddress, next_seq() + 20000)
    udp.send(inquery_ptdUp)


def ptz_down(data):
    console.log('[ptz_down] called')
    inquery_ptdDown = get_command_string('down', param_viscaAddress, next_seq() + 20000)
    udp.send(inquery_ptdDown)


def ptz_left(data):
    console.log('[ptz_left] called')
    inquery_ptdLeft = get_command_string('left', param_viscaAddress, next_seq() + 20000)
    udp.send(inquery_ptdLeft)


def ptz_right(data):
    console.log('[ptz_right] called')
    inquery_ptdRight = get_command_string('right', param_viscaAddress, next_seq() + 20000)
    udp.send(inquery_ptdRight)


def ptz_stop(data):
    console.log('[ptz_stop] called')
    inquery_ptdStop = get_command_string('stop', param_viscaAddress, next_seq() + 20000)
    udp.send(inquery_ptdStop)


def ptz_preset_reset(data):
    console.log('[ptz_preset_reset] called')
    inquery_presetReset = get_command_string('preset_reset', param_viscaAddress, next_seq() + 20000, data)
    udp.send(inquery_presetReset)


def ptz_preset_set(data):
    console.log('[ptz_preset_set] called')
    inquery_presetSet = get_command_string('preset_set', param_viscaAddress, next_seq() + 20000, data)
    udp.send(inquery_presetSet)


def ptz_preset_recall(data):
    console.log('[ptz_preset_recall] called')
    inquery_presetRecall = get_command_string('preset_recall', param_viscaAddress, next_seq() + 20000, data)
    udp.send(inquery_presetRecall)


# -------------------------------- Events --------------------------------


# -------------------------------- Others --------------------------------

# <!-- main entry-point

def main():
    console.info("Recipe has started!")


@after_main
def afterMain():
    print('START AFTER!')

    dest = "%s:%s" % (param_ipAddress, param_port or DEFAULT_PORT)
    udp.setDest(dest)

    resetSequenceNo()

    # Create Local actions
    la_PTZ_Home = create_local_action(
        'PTZ - Home',
        ptz_home,
        metadata={
            'title': 'PTZ - Home',
            'group': 'PTZ Drive',
            'order': next_seq()
        }
    )

    la_PTZ_Up = create_local_action(
        'PTZ - Up',
        ptz_up,
        metadata={
            'title': 'PTZ - Up',
            'group': 'PTZ Drive',
            'order': next_seq()
        }
    )

    la_PTZ_Down = create_local_action(
        'PTZ - Down',
        ptz_down,
        metadata={
            'title': 'PTZ - Down',
            'group': 'PTZ Drive',
            'order': next_seq()
        }
    )

    la_PTZ_Left = create_local_action(
        'PTZ - Left',
        ptz_left,
        metadata={
            'title': 'PTZ - Left',
            'group': 'PTZ Drive',
            'order': next_seq()
        }
    )

    la_PTZ_Right = create_local_action(
        'PTZ - Right',
        ptz_right,
        metadata={
            'title': 'PTZ - Right',
            'group': 'PTZ Drive',
            'order': next_seq()
        }
    )

    la_PTZ_Stop = create_local_action(
        'PTZ - Stop',
        ptz_stop,
        metadata={
            'title': 'PTZ - Stop',
            'group': 'PTZ Drive',
            'order': next_seq()
        }
    )

    la_PTZ_Preset_Reset = create_local_action(
        'PTZ Preset - Reset',
        ptz_preset_reset,
        metadata={
            'title': 'PTZ Preset - Reset',
            'group': 'PTZ Preset',
            'order': next_seq(),
            'schema': {
                'type': 'integer'
            }
        }
    )

    la_PTZ_Preset_Set = create_local_action(
        'PTZ Preset - Set',
        ptz_preset_set,
        metadata={
            'title': 'PTZ Preset - Set',
            'group': 'PTZ Preset',
            'order': next_seq(),
            'schema': {
                'type': 'integer'
            }
        }
    )

    la_PTZ_Preset_Recall = create_local_action(
        'PTZ Preset - Recall',
        ptz_preset_recall,
        metadata={
            'title': 'PTZ Preset - Recall',
            'group': 'PTZ Preset',
            'order': next_seq(),
            'schema': {
                'type': 'integer'
            }
        }
    )

    # Create Local events

    # Initialise


@before_main
def beforeMain():
    print('BEFORE MAIN')


# -->


# <!-- example local actions and events/signals and timer
# -->


# <!-- logging

local_event_LogLevel = LocalEvent({
    'group': 'Debug',
    'order': 10000 + next_seq(),
    'desc': 'Use this to ramp up the logging (with indentation)',
    'schema': {'type': 'integer'}
})


def warn(level, msg):
    if local_event_LogLevel.getArg() >= level:
        console.warn(('  ' * level) + msg)


def log(level, msg):
    if local_event_LogLevel.getArg() >= level:
        console.log(('  ' * level) + msg)

# --!>
