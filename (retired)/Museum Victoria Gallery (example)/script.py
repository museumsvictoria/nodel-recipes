'''Gallery Node'''

# This node's events / signal

local_event_AllOn = LocalEvent({"title":"All On"})
local_event_AllOff = LocalEvent({"title":"All Off", "Caution": "Are you sure you want signal this gallery to turn off?"})
local_event_MuteOn = LocalEvent({"title":"Mute On"})
local_event_MuteOff = LocalEvent({"title":"Mute Off"})


# This node's actions

def local_action_AllOn(arg = None):
  """{"title":"All On", "order": 1}"""
  print 'Action AllOn requested.'
  local_event_AllOn.emit()

def local_action_AllOff(arg = None):
  """{"title": "All Off", "Caution": "Are you sure you want signal this gallery to turn off?", "order": 2}"""
  print 'Action AllOff requested.'
  local_event_AllOff.emit()

def local_action_MuteOn(arg = None):
  """{"title":"Mute On", "order": 3}"""
  print 'Action MuteOn requested.'
  local_event_MuteOn.emit()

def local_action_MuteOff(arg = None):
  """{"title":"Mute Off", "order": 4}"""
  print 'Action MuteOff requested.'
  local_event_MuteOff.emit()

  
# Remote events this node is interested in

def remote_event_AllOn(arg = None):
  '{"title":"All On"}'
  print 'Remote event AllOn arrived.'
  local_event_AllOn.emit()

def remote_event_AllOff(arg = None):
  '{"title": "AllOff"}'
  print 'Remote event AllOff arrived.'
  local_event_AllOff.emit()

def remote_event_MuteOn(arg = None):
  '{"title": "MuteOn"}'
  print 'Remote event MuteOn arrived.'
  local_event_MuteOn.emit()

def remote_event_MuteOff(arg = None):
  '{"title": "MuteOff"}'
  print 'Remote event MuteOff arrived.'
  local_event_MuteOff.emit()


# entry-point
def main(arg = None):
  print 'Node started!'
