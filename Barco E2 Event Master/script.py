# coding=utf-8
'''
Call presets saved on the Barco and change sources linked to layers of screen destination
'''


# <!-- parameters

param_ipAddress = Parameter({'schema': {'type': 'string'}})

# -->

poller_destinations = Timer(lambda: build_screen_destination_tab(), 10, 15) # every 10s, first after 15

# <!--- Protocol / API

HTTP_PORT = 9999

# (JSON RPC over HTTP layer)
def callUrl(method, params):
  req = { 'id': str(next_seq()),
          'jsonrpc': '2.0',
          'method': method,
          'params': params }
  
  log(2, 'request: /%s params:%s' % (method, json_encode(params)))
  
  rawResp = get_url('http://%s:%s' % (param_ipAddress, HTTP_PORT), post=json_encode(req))

  resp = json_decode(rawResp)
  result = resp['result']
  
  if not result or result['success'] != 0:
     raise Exception('"%s" failed!' % method)

  global _lastReceive
  _lastReceive = system_clock() # indicate successful comms for status monitoring
      
  actualResp = result['response']
  log(2, 'response: %s' % json_encode(actualResp)) # use json to display nicely
  
  return actualResp

# --!>

# ---- preset ----

PRESETS = list()
PRESET_NAMES = list()

def get_list_presets():
    console.info('[getListPresets] called')
    
    result = callUrl('listPresets', { 'ScreenDest': -1, 'AuxDest': -1 })

    # id         : 0-based
    # presetSno  : 1-based
    # presetName : string

    # expected result :
    # [ 
    #   { 'presetSno': 1, 'LockMode': 0, 'id': 0, 'Name': 'Show L1'},
    #   { 'presetSno': 2, 'LockMode': 0, 'id': 1, 'Name': 'Hide L1'} 
    # ]
    
    global PRESETS
    
    PRESETS = result
    for preset in PRESETS:
        PRESET_NAMES.append(preset['Name'])

def presets(arg):
    if arg not in PRESET_NAMES:
        raise Exception('Unknown preset [%s]' % arg)

    activate_preset(arg)
    le_PresetActivated.emit(arg)
    
    build_screen_destination_tab()

def activate_preset(preset_name):
    result = callUrl('activatePreset', { 'presetName': preset_name, 'type': 1 })

la_ActivatePreset = None

# ---- Source ----

SOURCES = list()
SOURCE_NAMES = list()
MAP_SRC_ID_TO_NAME = {}
MAP_SRC_NAME_TO_ID = {}


def src_name_to_idx(src_name):
    if src_name in MAP_SRC_NAME_TO_ID:
        return MAP_SRC_NAME_TO_ID[src_name]

    return -1


def src_idx_to_name(src_idx):
    if src_idx in MAP_SRC_ID_TO_NAME:
        return MAP_SRC_ID_TO_NAME[src_idx]

    return 'NONE'


def get_all_sources():
    console.info('[get_all_sources] called')
      
    resp = callUrl("listSources", { 'type': 0 })

    # expected result :
    #    {"id": 0, "Name": "src-1"},
    #    {"id": 1, "Name": "src-2"}

    global SOURCES
    SOURCES = resp

    for src in SOURCES:
        name = src['Name']
        
        # strip the last dash
        dashPos = name.rfind('-')
        if dashPos >= 0:
          name = name[0:dashPos]
        
        # console.info('name: %s' % name)
        # console.info('src: %s' % src)
        
        if name not in SOURCE_NAMES:
          SOURCE_NAMES.append(name)

        # if src['id'] in MAP_SRC_ID_TO_NAME:
        #     raise Exception("Src Id [%d] duplicated!" % src['id'])
        MAP_SRC_ID_TO_NAME[src['id']] = name

        # if src['Name'] in MAP_SRC_NAME_TO_ID:
        #     raise Exception("Src Name [%s] duplicated!" % src['Name'])
        MAP_SRC_NAME_TO_ID[name] = src['id']


# ---- Screen Destination ----

DESTINATIONS = list()
DESTINATION_NAMES = {}


def dst_name_by_id(dst_id):
    if dst_id in DESTINATION_NAMES:
        return DESTINATION_NAMES[dst_id]
    raise Exception("DST[%n] not found!" % dst_id)


def get_all_destinations():
    console.info('[get_all_destinations] called')
    
    resp = callUrl("listDestinations", { "type": 0 })
    
    # expected result :
    #   u'response': [
    #   ]
    
    global DESTINATIONS
    
    DESTINATIONS = resp['ScreenDestination']
    for dst in DESTINATIONS:
        DESTINATION_NAMES[dst['id']] = dst['Name']

# ---- Contents ----

def get_content(dst_id):
    console.info('[get_content] called')

    resp = callUrl("listContent", { "id": dst_id })

    # expected result :
    #   [ ],
    #   u'success': 0
    
    return resp


# -------------------------------- Events --------------------------------

le_PresetActivated = None


# -------------------------------- Others --------------------------------

def check_e2_online():
    callUrl("powerStatus", {})

    # expected result : None
    
    console.info('E2 is online!!!')

# <!-- main entry-point

def main():
    console.info("Recipe has started!")


@after_main
def after_main():
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
    la_ActivatePreset = create_local_action('Preset', presets, { 'group': 'Presets', 'order': next_seq(), 'schema': { 'type': 'string', 'enum': PRESET_NAMES } })

    global le_PresetActivated
    le_PresetActivated = create_local_event('Preset', { 'group': 'Presets', 'order': next_seq(), 'schema': { 'type': 'string' } })
    
    into_discrete_joins('Preset', PRESET_NAMES, 'Presets')

    # Initialise
    le_PresetActivated.emit('')

def change_source_of_normal_layer(dst_id, layer_id, src_name, event):
    console.info("[change_source_of_normal_layer] Screen[%s], Layer[%d], Source to [%s]" % (dst_name_by_id(dst_id), layer_id, src_name))
    
    callUrl("changeContent", { "id": dst_id,
                               "Layers": [ 
                                 { "id": layer_id, "LastSrcIdx": src_name_to_idx(src_name) }
                              ] })

    event.emit(src_name or "NONE")

def change_source_of_bglayer(dst_id, layer_id, src_name, event):
    console.info("[change_source_of_bglayer] Screen[%s], BGLayer[%d], Source to [%s]" % (dst_name_by_id(dst_id), layer_id, src_name))
    result = callUrl("changeContent", { "id": dst_id,
                                        "BGLyr": [ {
                                          "id": layer_id,
                                          "LastBGSourceIndex": src_name_to_idx(src_name)
                                       } ] })

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
            
            name = 'Screen[%d] Layer[%d] Source' % (dst_id, layer_id)
            title = 'Layer %d' % layer_id
            group = 'Screen - ' + dst_name
            
            local_evt = lookup_local_event(name)
            if not local_evt:
              local_evt = create_local_event(name, { 'title': title, 'group': group, 'order': next_seq(), 'schema': { 'type': 'string' }})

              create_local_action(name, lambda src_name, dst_idx=dst_id, layer_idx=layer_id, event=local_evt:
                  change_source_of_normal_layer(dst_idx, layer_idx, src_name, event),
                  metadata={ 'title': title, 'group': group, 'order': action_order, 'schema': { 'type': 'string', 'enum': SOURCE_NAMES } })
            
              # add all discrete options
              into_discrete_joins(name, SOURCE_NAMES, '%s Layer[%s]' % (group, layer_id))
            
            local_evt.emit(src_idx_to_name(layer['LastSrcIdx']))
            

        # Background Layer
        for bglayer in content['BGLyr']:
            bglayer_id = bglayer['id']

            action_order = next_seq()
            event_order = next_seq()
            
            name = 'Screen[%d] BGLayer[%d] Source' % (dst_id, bglayer_id)
            title = 'BGLayer %d' % bglayer_id
            group = 'Screen - ' + dst_name

            local_evt = lookup_local_event(name)
            
            if not local_evt:
              local_evt = create_local_event( name, { 'title': title, 'group': group, 'order': event_order, 'schema': { 'type': 'string' } })

              create_local_action(name, lambda src_name, dst_idx=dst_id, layer_idx=bglayer_id, event=local_evt:
                  change_source_of_bglayer(dst_idx, layer_idx, src_name, event),
                  metadata={ 'title': title, 'group': group, 'order': action_order, 'schema': { 'type': 'string', 'enum': SOURCE_NAMES } })

              # add all discrete options
              into_discrete_joins(name, SOURCE_NAMES, '%s BGLayer[%s]' % (group, bglayer_id))
              
            local_evt.emit(src_idx_to_name(bglayer['LastBGSourceIndex']))              
            
# -->

# <!-- convenience functions

# Creates discrete actions and events AND slave remote events 
# e.g. event and action name = "Input"
#      states = [ 'HDMI1', 'HDMI2', 'DP1', 'DP2' ]
def into_discrete_joins(name, states, group):
    a = lookup_local_action(name)
    e = lookup_local_event(name)

    def newDiscreteState(state):
        dName = '%s %s' % (name, state)
        dE = create_local_event(dName, { 'title': state, 'order': next_seq(), 'group': group, 'schema': { 'type': 'boolean' }})
        e.addEmitHandler(lambda arg: dE.emitIfDifferent(arg == state))
        dA = create_local_action(dName, lambda arg: a.call(state), { 'title': state, 'order': next_seq(), 'group': group })

    for state in states:
        newDiscreteState(state)

# --!>

# <!-- status

local_event_Status = LocalEvent({'title': 'Status', 'group': 'Status', 'order': 9990, "schema": { 'title': 'Status', 'type': 'object', 'properties': {
        'level': {'title': 'Level', 'order': 1, 'type': 'integer'},
        'message': {'title': 'Message', 'order': 2, 'type': 'string'}
    } } })

_lastReceive = 0 # last valid comms, system_clock() based

# roughly, the last contact  
local_event_LastContactDetect = LocalEvent({'group': 'Status', 'title': 'Last contact detect', 'schema': {'type': 'string'}})
  
def statusCheck():
  diff = (system_clock() - _lastReceive)/1000.0 # (in secs)
  now = date_now()
  
  if diff > status_check_interval+15:
    previousContactValue = local_event_LastContactDetect.getArg()
    
    if previousContactValue == None:
      message = 'Always been missing.'
      
    else:
      previousContact = date_parse(previousContactValue)
      message = 'Unmonitorable %s' % formatPeriod(previousContact)
      
    local_event_Status.emit({'level': 2, 'message': message})
    return
    
  local_event_Status.emit({'level': 0, 'message': 'OK'})
  
  local_event_LastContactDetect.emit(str(now))
  
status_check_interval = 75
status_timer = Timer(statusCheck, status_check_interval)

def formatPeriod(dateObj):
  if dateObj == None:      return 'for unknown period'
  
  now = date_now()
  diff = (now.getMillis() - dateObj.getMillis()) / 1000 / 60 # in mins
  
  if diff == 0:             return 'for <1 min'
  elif diff < 60:           return 'for <%s mins' % diff
  elif diff < 60*24:        return 'since %s' % dateObj.toString('h:mm:ss a')
  else:                     return 'since %s' % dateObj.toString('E d-MMM h:mm:ss a')
  
# status --!>

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
