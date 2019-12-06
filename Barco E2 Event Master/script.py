'''
With this recipe, you can recall Presets saved on Barco E2 device.
'''

# You can refer to the Scripting Toolkit Reference by clicking on the
# Nodel logo twice and following the link


# <!-- parameters

param_disabled = Parameter({'desc': 'Disables this node?', 'schema': {'type': 'boolean'}})
param_ipAddress = Parameter({'schema': {'type': 'string'}})

DEFAULT_PORT = 9999
param_port = Parameter({'schema': {'type': 'integer', 'hint': '(default is %s)' % DEFAULT_PORT}})

# -->

# -------------------------------- Actions --------------------------------

PRESETS = list()
PRESET_NAMES = list()


def getListPresets():
    console.info('[getListPresets] called')

    payload_listPresets = {
        "id": str(system_clock()),
        "jsonrpc": "2.0",
        "method": "listPresets",
        "params": {
            "ScreenDest": -1,
            "AuxDest": -1
        }
    }

    dest = 'http://%s:%s' % (param_ipAddress, param_port or DEFAULT_PORT)
    resp = get_url(dest, post=json_encode(payload_listPresets))
    obj = json_decode(resp)

    # id         : 0-based
    # presetSno  : 1-based
    # presetName : string

    # expected result :
    # {
    # u'jsonrpc': u'2.0',
    # u'result': {
    #   u'response': [
    #       {u'presetSno': 1, u'LockMode': 0, u'id': 0, u'Name': u'Show L1'},
    #       {u'presetSno': 2, u'LockMode': 0, u'id': 1, u'Name': u'Hide L1'}
    #   ],
    #   u'success': 0
    # },
    # u'id': u'1234'
    # }

    if obj['result']['success'] != 0:
        raise Exception('listPresets command failed!')

    global PRESETS
    PRESETS = obj['result']['response']
    for preset in PRESETS:
        global PRESET_NAMES
        PRESET_NAMES.append(preset['Name'])


def Presets(arg):
    if arg not in PRESET_NAMES:
        raise Exception('Unknown preset [%s]' % arg)

    activatePreset(arg)
    le_PresetActivated.emit(arg)


def activatePreset(presetName):
    payload_activatePreset = {
        "params": {
            "presetName": presetName,
            "type": 1
        },
        "method": "activatePreset",
        "id": str(system_clock()),
        "jsonrpc": "2.0"
    }

    dest = 'http://%s:%s' % (param_ipAddress, param_port or DEFAULT_PORT)
    resp = get_url(dest, post=json_encode(payload_activatePreset))
    obj = json_decode(resp)

    # expected result : {u'jsonrpc': u'2.0', u'result': {u'response': None, u'success': 0}, u'id': u'1234'}
    if obj['result']['success'] != 0:
        raise Exception('activatePreset command failed!')


la_ActivatePreset = None

# -------------------------------- Events --------------------------------

le_PresetActivated = None


# -------------------------------- Others --------------------------------

def checkE2Online():
    payload_powerStatus = {
        "params": {},
        "method": "powerStatus",
        "id": str(system_clock()),
        "jsonrpc": "2.0"
    }

    dest = 'http://%s:%s' % (param_ipAddress, param_port or DEFAULT_PORT)
    resp = get_url(dest, post=json_encode(payload_powerStatus), connectTimeout=5, readTimeout=10)
    obj = json_decode(resp)

    # expected result : {u'jsonrpc': u'2.0', u'result': {u'response': None, u'success': 0}, u'id': u'1234'}
    if obj['result']['success'] != 0:
        raise Exception('powerStatus command failed!')

    console.info('E2 is online!!!')


# <!-- main entry-point

def main():
    console.info("Recipe has started!")


@after_main
def afterMain():
    print('START AFTER!')

    # Check E2 is online
    try:
        checkE2Online()
    except:
        console.error('E2 not responding. Please check connection!!!')
        return

    # Get Presets list
    getListPresets()

    # Create Local actions
    global la_ActivatePreset
    la_ActivatePreset = create_local_action(
        'Activate Preset',
        Presets,
        metadata={
            'title': 'Activate Preset',
            'group': 'Presets',
            'order': next_seq(),
            'schema': {
                'type': 'string',
                'enum': PRESET_NAMES
            }
        }
    )

    # Create Local events
    global le_PresetActivated
    le_PresetActivated = create_local_event(
        'Preset Activated',
        metadata={
            'title': 'Preset Activated',
            'group': 'Presets',
            'order': next_seq(),
            'schema': {
                'type': 'string'
            }
        }
    )

    # Initialise
    le_PresetActivated.emit('')


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
