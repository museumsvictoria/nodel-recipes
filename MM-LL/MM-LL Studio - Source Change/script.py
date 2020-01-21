# coding=utf-8
'''
With this recipe,
you can recall Presets saved on Barco E2 device and change sources linked to layers of screen destination.
'''

import os  # working directory
from java.io import File  # reading files
from org.nodel.io import Stream  # reading files

# <!-- parameters

param_disabled = Parameter({'desc': 'Disables this node?', 'schema': {'type': 'boolean'}})
param_ipAddress = Parameter({'schema': {'type': 'string'}})

DEFAULT_PORT = 9999
param_port = Parameter({'schema': {'type': 'integer', 'hint': '(default is %s)' % DEFAULT_PORT}})

# the node's working directory
workingDir = os.getcwd()

# -->

# -------------------------------- Actions --------------------------------

local_event_pip_mode = LocalEvent(
    {
        'title': 'PIP Mode',
        'group': 'PIP Mode',
        'order': next_seq(),
        'schema': {
            'type': 'string'
        }
    }
)

_preset_id = -1  # 0-based


def reset_source_event():
    for src in SOURCES:
        evt = lookup_local_event(src['Name'])
        if evt is not None:
            evt.emit(False)


@local_action({'group': 'PIP Mode', 'title': 'Mode 1', 'order': next_seq()})
def pip_mode_1(data):
    console.log("[pip_mode_1] called")
    local_event_pip_mode.emit('Mode 1')
    local_event_pip_mode_1.emit(True)
    local_event_pip_mode_2.emit(False)
    local_event_pip_mode_3.emit(False)

    global _preset_id
    _preset_id = 0
    activate_preset(PRESETS[_preset_id]['Name'])
    reset_source_event()


local_event_pip_mode_1 = LocalEvent(
    {
        'title': 'PIP Mode 1',
        'group': 'PIP Mode',
        'order': next_seq(),
        'schema': {
            'type': 'boolean'
        }
    }
)


@local_action({'group': 'PIP Mode', 'title': 'Mode 2', 'order': next_seq()})
def pip_mode_2(data):
    console.log("[pip_mode_2] called")
    local_event_pip_mode.emit('Mode 2')
    local_event_pip_mode_1.emit(False)
    local_event_pip_mode_2.emit(True)
    local_event_pip_mode_3.emit(False)

    global _preset_id
    _preset_id = 1
    activate_preset(PRESETS[_preset_id]['Name'])
    reset_source_event()


local_event_pip_mode_2 = LocalEvent(
    {
        'title': 'PIP Mode 2',
        'group': 'PIP Mode',
        'order': next_seq(),
        'schema': {
            'type': 'boolean'
        }
    }
)


@local_action({'group': 'PIP Mode', 'title': 'Mode 3', 'order': next_seq()})
def pip_mode_3(data):
    console.log("[pip_mode_3] called")
    local_event_pip_mode.emit('Mode 3')
    local_event_pip_mode_1.emit(False)
    local_event_pip_mode_2.emit(False)
    local_event_pip_mode_3.emit(True)

    global _preset_id
    _preset_id = 2
    activate_preset(PRESETS[_preset_id]['Name'])
    reset_source_event()


local_event_pip_mode_3 = LocalEvent(
    {
        'title': 'PIP Mode 3',
        'group': 'PIP Mode',
        'order': next_seq(),
        'schema': {
            'type': 'boolean'
        }
    }
)


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


_layer_number = -1  # 0-based


def on_change_layer(layer_number):
    console.info("[on_change_layer] called: %d" % layer_number)
    global _layer_number
    _layer_number = layer_number - 1  # 0-based
    reset_source_event()


# -------------------------------- Events --------------------------------


# -------------------------------- Others --------------------------------

# <!-- main entry-point


def on_change_source(arg, src_name, event):
    console.info("[on_change_source] called: %s" % src_name)

    if _preset_id == -1 or _preset_id > 2:
        raise Exception('_preset_id is not valid')

    if _layer_number == -1:
        raise Exception('_layer_number is not valid')

    dst_id = PRESETS[_preset_id]['Layers'][_layer_number]['DestinationId']
    lyr_id = PRESETS[_preset_id]['Layers'][_layer_number]['id']

    change_source_of_normal_layer(dst_id, lyr_id, src_name)

    reset_source_event()
    event.emit(True)


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


def load_source_list(json):
    data = json_decode(json)

    global SOURCES
    SOURCES = data['result']['response']

    for src in SOURCES:
        action_order = next_seq()
        event_order = next_seq()

        local_evt = create_local_event(
            src['Name'],
            metadata={
                'title': src['Name'] + ' Selected',
                'group': 'Source List',
                'order': event_order,
                'schema': {
                    'type': 'boolean'
                }
            }
        )

        local_action = create_local_action(
            src['Name'],
            lambda arg, src_name=src['Name'], event=local_evt: on_change_source(arg, src_name, event),
            metadata={
                'title': 'Source - %s' % src['Name'],
                'group': 'Source List',
                'order': action_order,
                'schema': {
                    'type': 'string'
                }
            }
        )

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


PRESETS = list()


def load_preset_list(json):
    data = json_decode(json)

    global PRESETS
    PRESETS = data['presets']


def change_source_of_normal_layer(dst_id, layer_id, src_name):
    console.info("[change_source_of_normal_layer] Screen[%d], Layer[%d], Source to [%s]" % (dst_id, layer_id, src_name))
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


def main():
    console.info("Recipe has started!")
    remote_event = create_remote_event('OnChangeLayer', on_change_layer)

    source_list_file = os.path.join(workingDir, 'content', 'source_list.json')
    if os.path.exists(source_list_file):
        load_source_list(Stream.readFully(File(source_list_file)))
    else:
        console.warn('(no source info was present)')

    preset_list_file = os.path.join(workingDir, 'content', 'preset_list_new.json')
    if os.path.exists(preset_list_file):
        load_preset_list(Stream.readFully(File(preset_list_file)))
    else:
        console.warn('(no preset info was present)')


@after_main
def after_main():
    print('START AFTER!')


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
