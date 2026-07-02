# Pharos Object Group Dynamic Select
#
# Ingredient for the Pharos Designer 2 API node.
# For each object group, creates:
#   - A Select event  (SceneGroup%sSelect / TimelineGroup%sSelect / TriggerGroup%sSelect): list of objects in the group
#   - A Select action (SceneGroup%sSelect / TimelineGroup%sSelect / TriggerGroup%sSelect): calls the selected object

### Scene

@after_main
def SetupSceneSelect():
  if not param_objects.get('scene'):
    return
  
  all_scenes = json_decode(callURL('/api/scene', method='GET')).get('scenes') or []
  groups = sorted(set(s.get('group_num') for s in all_scenes if s.get('group_num') is not None))

  for group in groups:
    select_scenes = sorted([s for s in all_scenes if s.get('group_num') == group], key=lambda x: x['num'])
    select_items  = [{'key':   '%sScene%s' % (s.get('num'), CreateNodelSafeName(s.get('name'))),
                      'value': '%s: %s' % (s.get('num'), s.get('name')) if s.get('name') else str(s.get('num'))}
                      for s in select_scenes]
    
    e_select = create_local_event('SceneGroup%sSelect' % group, {
      'title': 'Scene GROUP %s: Select' % group, 'group': 'Scene Group %s' % group, 'order': next_seq(),
      'schema': {'type': 'array', 'items': {'type': 'object', 'properties': {
        'key':   {'title': 'Action', 'type': 'string', 'order': 1},
        'value': {'title': 'Label',  'type': 'string', 'order': 2}}}}})
    e_select.emit(select_items)
    
    def select_handler(arg):
      lookup_local_action(arg).call({'action': 'toggle'})
    
    create_local_action('SceneGroup%sSelect' % group, select_handler, {
      'title': 'Scene GROUP %s: Select' % group, 'group': 'Scene Group %s' % group, 'order': next_seq(),
      'schema': {'type': 'string', 'enum': [item['key'] for item in select_items]}})

### Timeline

@after_main
def SetupTimelineSelect():
  if not param_objects.get('timeline'):
    return
  
  all_timelines = json_decode(callURL('/api/timeline', method='GET')).get('timelines') or []
  groups = sorted(set(t.get('group_num') for t in all_timelines if t.get('group_num') is not None))
  
  for group in groups:
    select_timelines = sorted([t for t in all_timelines if t.get('group_num') == group], key=lambda x: x['num'])
    select_items     = [{'key':   '%sTimeline%s' % (t.get('num'), CreateNodelSafeName(t.get('name'))),
                          'value': '%s: %s' % (t.get('num'), t.get('name')) if t.get('name') else str(t.get('num'))}
                          for t in select_timelines]
    
    e_select = create_local_event('TimelineGroup%sSelect' % group, {
      'title': 'Timeline GROUP %s: Select' % group, 'group': 'Timeline Group %s' % group, 'order': next_seq(),
      'schema': {'type': 'array', 'items': {'type': 'object', 'properties': {
        'key':   {'title': 'Action', 'type': 'string', 'order': 1},
        'value': {'title': 'Label',  'type': 'string', 'order': 2}}}}})
    e_select.emit(select_items)
    
    def select_handler(arg):
      lookup_local_action(arg).call({'action': 'toggle'})
    
    create_local_action('TimelineGroup%sSelect' % group, select_handler, {
      'title': 'Timeline GROUP %s: Select' % group, 'group': 'Timeline Group %s' % group, 'order': next_seq(),
      'schema': {'type': 'string', 'enum': [item['key'] for item in select_items]}})

# Trigger

@after_main
def SetupTriggerSelect():
  if not param_objects.get('trigger'):
    return
  
  all_triggers = json_decode(callURL('/api/trigger', method='GET')).get('triggers') or []
  groups = set(t.get('group') for t in all_triggers)
  
  for group in groups:
    group_name      = TRIGGER_GROUP_COLOURS[group if group else 'none']
    select_triggers = sorted([t for t in all_triggers if t.get('group') == group], key=lambda x: x['num'])
    select_items    = [{'key':   '%sTrigger%s' % (t.get('num'), CreateNodelSafeName(t.get('name'))),
                        'value': '%s: %s' % (t.get('num'), t.get('name')) if t.get('name') else str(t.get('num'))}
                        for t in select_triggers]
    
    e_select = create_local_event('TriggerGroup%sSelect' % group_name, {
      'title': 'Trigger GROUP %s: Select' % group_name, 'group': 'Trigger Group %s' % group_name, 'order': next_seq(),
      'schema': {'type': 'array', 'items': {'type': 'object', 'properties': {
        'key':   {'title': 'Action', 'type': 'string', 'order': 1},
        'value': {'title': 'Label',  'type': 'string', 'order': 2}}}}})
    e_select.emit(select_items)
    
    def select_handler(arg):
      lookup_local_action(arg).call()
    
    create_local_action('TriggerGroup%sSelect' % group_name, select_handler, {
      'title': 'Trigger GROUP %s: Select' % group_name, 'group': 'Trigger Group %s' % group_name, 'order': next_seq(),
      'schema': {'type': 'string', 'enum': [item['key'] for item in select_items]}})
