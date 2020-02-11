# coding=utf-8
'''
With this recipe,
you can recall Presets saved on Barco E2 device and change sources linked to layers of screen destination.
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

# ---- preset ----

PRESETS = list()
PRESET_NAMES = list()


def get_list_presets():
    console.info('[getListPresets] called')

    payload_list_presets = {
        "id": str(system_clock()),
        "jsonrpc": "2.0",
        "method": "listPresets",
        "params": {
            "ScreenDest": -1,
            "AuxDest": -1
        }
    }

    dest = 'http://%s:%s' % (param_ipAddress, param_port or DEFAULT_PORT)
    resp = get_url(dest, post=json_encode(payload_list_presets))
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


def presets(arg):
    if arg not in PRESET_NAMES:
        raise Exception('Unknown preset [%s]' % arg)

    activate_preset(arg)
    le_PresetActivated.emit(arg)


def activate_preset(preset_name):
    payload_activate_preset = {
        "params": {
            "presetName": preset_name,
            "type": 1
        },
        "method": "activatePreset",
        "id": str(system_clock()),
        "jsonrpc": "2.0"
    }

    dest = 'http://%s:%s' % (param_ipAddress, param_port or DEFAULT_PORT)
    resp = get_url(dest, post=json_encode(payload_activate_preset))
    obj = json_decode(resp)

    # expected result : {u'jsonrpc': u'2.0', u'result': {u'response': None, u'success': 0}, u'id': u'1234'}
    if obj['result']['success'] != 0:
        raise Exception('activatePreset command failed!')


la_ActivatePreset = None

# ---- Source ----

SOURCES = list()
SOURCE_NAMES = list()
MAP_SRC_ID_TO_NAME = {}
MAP_SRC_NAME_TO_ID = {}


def src_name_to_idx(src_name):
    global MAP_SRC_NAME_TO_ID
    if src_name in MAP_SRC_NAME_TO_ID:
        return MAP_SRC_NAME_TO_ID[src_name]
    return -1


def src_idx_to_name(src_idx):
    global MAP_SRC_ID_TO_NAME
    if src_idx in MAP_SRC_ID_TO_NAME:
        return MAP_SRC_ID_TO_NAME[src_idx]
    return 'NONE'


def get_all_sources():
    console.info('[get_all_sources] called')

    payload_list_sources = {
        "id": str(system_clock()),
        "jsonrpc": "2.0",
        "method": "listSources",
        "params": {
            "type": 0
        }
    }

    dest = 'http://%s:%s' % (param_ipAddress, param_port or DEFAULT_PORT)
    resp = get_url(dest, post=json_encode(payload_list_sources))
    obj = json_decode(resp)

    # id         : 0-based
    # presetSno  : 1-based
    # presetName : string

    # expected result :
    # {
    # u'jsonrpc': u'2.0',
    # u'result': {
    #   u'response': [
    #    {"id": 0, "Name": "src-1"},
    #    {"id": 1, "Name": "src-2"}
    #   ],
    #   u'success': 0
    # },
    # u'id': u'1234'
    # }

    if obj['result']['success'] != 0:
        raise Exception('listSources command failed!')

    global SOURCES
    SOURCES = obj['result']['response']
    for src in SOURCES:
        global SOURCE_NAMES
        SOURCE_NAMES.append(src['Name'])

        global MAP_SRC_ID_TO_NAME
        if src['id'] in MAP_SRC_ID_TO_NAME:
            raise Exception("Src Id [%d] duplicated!" % src['id'])
        MAP_SRC_ID_TO_NAME[src['id']] = src['Name']

        global MAP_SRC_NAME_TO_ID
        if src['Name'] in MAP_SRC_NAME_TO_ID:
            raise Exception("Src Name [%s] duplicated!" % src['Name'])
        MAP_SRC_NAME_TO_ID[src['Name']] = src['id']


# ---- Screen Destination ----

DESTINATIONS = list()
DESTINATION_NAMES = {}


def dst_name_by_id(dst_id):
    if dst_id in DESTINATION_NAMES:
        return DESTINATION_NAMES[dst_id]
    raise Exception("DST[%n] not found!" % dst_id)


def get_all_destinations():
    console.info('[get_all_destinations] called')

    payload_list_destinations = {
        "id": str(system_clock()),
        "jsonrpc": "2.0",
        "method": "listDestinations",
        "params": {
            "type": 0
        }
    }

    dest = 'http://%s:%s' % (param_ipAddress, param_port or DEFAULT_PORT)
    resp = get_url(dest, post=json_encode(payload_list_destinations))
    obj = json_decode(resp)

    # id         : 0-based
    # presetSno  : 1-based
    # presetName : string

    # expected result :
    # {
    # u'jsonrpc': u'2.0',
    # u'result': {
    #   u'response': [
    #   ],
    #   u'success': 0
    # },
    # u'id': u'1234'
    # }

    if obj['result']['success'] != 0:
        raise Exception('listDestinations command failed!')

    global DESTINATIONS
    DESTINATIONS = obj['result']['response']['ScreenDestination']
    for dst in DESTINATIONS:
        global DESTINATION_NAMES
        DESTINATION_NAMES[dst['id']] = dst['Name']


# ---- Contents ----

def get_content(dst_id):
    console.info('[get_content] called')

    payload_list_content = {
        "id": str(system_clock()),
        "jsonrpc": "2.0",
        "method": "listContent",
        "params": {
            "id": dst_id
        }
    }

    dest = 'http://%s:%s' % (param_ipAddress, param_port or DEFAULT_PORT)
    resp = get_url(dest, post=json_encode(payload_list_content))
    obj = json_decode(resp)

    # id         : 0-based
    # presetSno  : 1-based
    # presetName : string

    # expected result :
    # {
    # u'jsonrpc': u'2.0',
    # u'result': {
    #   u'response': [
    #   ],
    #   u'success': 0
    # },
    # u'id': u'1234'
    # }

    if obj['result']['success'] != 0:
        raise Exception('listContent command failed!')

    return obj['result']['response']


# -------------------------------- Events --------------------------------

le_PresetActivated = None


# -------------------------------- Others --------------------------------

def check_e2_online():
    payload_power_status = {
        "params": {},
        "method": "powerStatus",
        "id": str(system_clock()),
        "jsonrpc": "2.0"
    }

    dest = 'http://%s:%s' % (param_ipAddress, param_port or DEFAULT_PORT)
    resp = get_url(dest, post=json_encode(payload_power_status), connectTimeout=5, readTimeout=10)
    obj = json_decode(resp)

    # expected result : {u'jsonrpc': u'2.0', u'result': {u'response': None, u'success': 0}, u'id': u'1234'}
    if obj['result']['success'] != 0:
        raise Exception('powerStatus command failed!')

    console.info('E2 is online!!!')


# <!-- main entry-point

def main():
    console.info("Recipe has started!")


@after_main
def after_main():
    print('START AFTER!')

    # Check E2 is online
    try:
        check_e2_online()
    except:
        console.error('E2 not responding. Please check connection!!!')
        return

    build_preset_tab()

    build_screen_destination_tab()


def build_preset_tab():
    get_list_presets()

    global la_ActivatePreset
    la_ActivatePreset = create_local_action(
        'Activate Preset',
        presets,
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


def change_source_of_normal_layer(dst_id, layer_id, src_name, event):
    console.info("[change_source_of_normal_layer] Screen[%s], Layer[%d], Source to [%s]" % (dst_name_by_id(dst_id), layer_id, src_name))
    payload_change_content = {
        "params": {
            "id": dst_id,
            "Layers": [
                {
                    "id": layer_id,
                    "LastSrcIdx": src_name_to_idx(src_name)
                }
            ]
        },
        "method": "changeContent",
        "id": str(system_clock()),
        "jsonrpc": "2.0"
    }

    dest = 'http://%s:%s' % (param_ipAddress, param_port or DEFAULT_PORT)
    resp = get_url(dest, post=json_encode(payload_change_content))
    obj = json_decode(resp)

    # expected result : {u'jsonrpc': u'2.0', u'result': {u'response': None, u'success': 0}, u'id': u'1234'}
    if obj['result']['success'] != 0:
        raise Exception('change_source_of_normal_layer command failed!')

    event.emit(src_name or "NONE")


def change_source_of_bglayer(dst_id, layer_id, src_name, event):
    console.info("[change_source_of_bglayer] Screen[%s], BGLayer[%d], Source to [%s]" % (dst_name_by_id(dst_id), layer_id, src_name))
    payload_change_content = {
        "params": {
            "id": dst_id,
            "BGLyr": [
                {
                    "id": layer_id,
                    "LastBGSourceIndex": src_name_to_idx(src_name)
                }
            ]
        },
        "method": "changeContent",
        "id": str(system_clock()),
        "jsonrpc": "2.0"
    }

    dest = 'http://%s:%s' % (param_ipAddress, param_port or DEFAULT_PORT)
    resp = get_url(dest, post=json_encode(payload_change_content))
    obj = json_decode(resp)

    # expected result : {u'jsonrpc': u'2.0', u'result': {u'response': None, u'success': 0}, u'id': u'1234'}
    if obj['result']['success'] != 0:
        raise Exception('change_source_of_bglayer command failed!')

    event.emit(src_name or "NONE")


def build_screen_destination_tab():
    get_all_sources()
    get_all_destinations()

    global DESTINATIONS
    for dst in DESTINATIONS:
        dst_id = dst['id']
        dst_name = dst['Name']

        content = get_content(dst_id)

        # Normal Layer
        for layer in content['Layers']:
            layer_id = layer['id']

            action_order = next_seq()
            event_order = next_seq()

            local_evt = create_local_event(
                'Screen[%d] Layer[%d] source set' % (dst_id, layer_id),
                metadata={
                    'title': 'Screen[%s] Layer[%d] source set' % (dst_name, layer_id),
                    'group': 'Screen - ' + dst_name,
                    'order': event_order,
                    'schema': {
                        'type': 'string'
                    }
                }
            )

            create_local_action(
                'Screen[%s] Layer[%d]' % (dst_name, layer_id),
                lambda src_name, dst_idx=dst_id, layer_idx=layer_id, event=local_evt:
                change_source_of_normal_layer(dst_idx, layer_idx, src_name, event),
                metadata={
                    'title': 'Layer[%d]' % layer_id + ' : ' + 'Change Source',
                    'group': 'Screen - ' + dst_name,
                    'order': action_order,
                    'schema': {
                        'type': 'string',
                        'enum': SOURCE_NAMES
                    }
                }
            )

            local_evt.emit(src_idx_to_name(layer['LastSrcIdx']))

        # Background Layer
        for bglayer in content['BGLyr']:
            bglayer_id = bglayer['id']

            action_order = next_seq()
            event_order = next_seq()

            local_evt = create_local_event(
                'Screen[%d] BGLayer[%d] source set' % (dst_id, bglayer_id),
                metadata={
                    'title': 'Screen[%s] BGLayer[%d] source set' % (dst_name, bglayer_id),
                    'group': 'Screen - ' + dst_name,
                    'order': event_order,
                    'schema': {
                        'type': 'string'
                    }
                }
            )

            create_local_action(
                'Screen[%s] BGLayer[%d]' % (dst_name, bglayer_id),
                lambda src_name, dst_idx=dst_id, layer_idx=bglayer_id, event=local_evt:
                change_source_of_bglayer(dst_idx, layer_idx, src_name, event),
                metadata={
                    'title': 'BGLayer[%d]' % bglayer_id + ' : ' + 'Change Source',
                    'group': 'Screen - ' + dst_name,
                    'order': action_order,
                    'schema': {
                        'type': 'string',
                        'enum': SOURCE_NAMES
                    }
                }
            )

            local_evt.emit(src_idx_to_name(bglayer['LastBGSourceIndex']))


@before_main
def before_main():
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
