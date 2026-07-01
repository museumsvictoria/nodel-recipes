# Pharos On/Off status
#
# Ingredient for the Pharos Designer 2 API node.
# For each scene and timeline, creates:
#   - An On/Off event  (%sSceneOnOff / %sTimelineOnOff): reflects whether the object is active
#   - An On/Off action (%sSceneOnOff / %sTimelineOnOff): starts or releases the object

### Scene

@after_main
def SetupSceneOnOff():
  if not param_objects.get('scene'):
    return

  def MakeAction(name):
    def onoff_handler(arg):
      if arg == 'On':
        lookup_local_action(name).call({'action': 'start'})
      elif arg == 'Off':
        lookup_local_action(name).call({'action': 'release'})
    return onoff_handler

  def MakeEmit(onoff_name):
    def emit_handler(arg):
      e = lookup_local_event(onoff_name)
      if e is None:
        return
      state = arg.get('state') if arg else None
      e.emit('On' if state == 'started' else 'Off')
    return emit_handler

  scenes = json_decode(callURL('/api/scene', method='GET')).get('scenes') or []
  for scene in scenes:
    scene_name = '%sScene%s' % (scene.get('num'), CreateNodelSafeName(scene.get('name')))
    scene_onoff_name = '%sOnOff' % scene_name

    e_main = lookup_local_event(scene_name)
    if e_main is None:
      continue

    create_local_event(scene_onoff_name,
      {'title': 'Scene: %s On Off' % scene.get('name'),
        'group': 'Scene Group %s' % scene.get('group_num'),
        'order': next_seq(),
        'schema': {'type': 'string', 'enum': ['On', 'Off']}})

    create_local_action(scene_onoff_name, MakeAction(scene_name),
      {'title': 'Scene: %s On Off' % scene.get('name'),
        'group': 'Scene Group %s' % scene.get('group_num'),
        'order': next_seq(),
        'schema': {'type': 'string', 'enum': ['On', 'Off']}})

    e_main.addEmitHandler(MakeEmit(scene_onoff_name))


### Timeline

@after_main
def SetupTimelineOnOff():
  if not param_objects.get('timeline'):
    return

  def MakeAction(name):
    def onoff_handler(arg):
      if arg == 'On':
        lookup_local_action(name).call({'action': 'start'})
      elif arg == 'Off':
        lookup_local_action(name).call({'action': 'release'})
    return onoff_handler

  def MakeEmit(onoff_name):
    def emit_handler(arg):
      e = lookup_local_event(onoff_name)
      if e is None:
        return
      state = arg.get('state') if arg else None
      e.emit('On' if state == 'running' else 'Off')
    return emit_handler

  timelines = json_decode(callURL('/api/timeline', method='GET')).get('timelines') or []
  for timeline in timelines:
    timeline_name      = '%sTimeline%s' % (timeline.get('num'), CreateNodelSafeName(timeline.get('name')))
    timeline_onoff_name = '%sOnOff' % timeline_name
    
    e_main = lookup_local_event(timeline_name)
    if e_main is None:
      continue

    create_local_event(
      timeline_onoff_name,
      {'title': 'Timeline: %s On Off' % timeline.get('name'),
        'group': 'Timeline Group %s' % timeline.get('group_num'),
        'order': next_seq(),
        'schema': {'type': 'string', 'enum': ['On', 'Off']}})

    create_local_action(
      timeline_onoff_name,
      MakeAction(timeline_name),
      {'title': 'Timeline: %s On Off' % timeline.get('name'),
        'group': 'Timeline Group %s' % timeline.get('group_num'),
        'order': next_seq(),
        'schema': {'type': 'string', 'enum': ['On', 'Off']}})

    e_main.addEmitHandler(MakeEmit(timeline_onoff_name))
