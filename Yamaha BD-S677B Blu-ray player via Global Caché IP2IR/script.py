# coding=utf-8
u"Intended to be used with a Global Caché iTachIP2IR node and ILearn application. See scripy.py for data format expected "

# example 'command' structure expected, as taken from example "Yamaha BD-S677B Blu-ray player via Global Caché IP2IR" node
# (ends up in nodeConfig.json)
#   { 
#      "group": "Power", 
#      "name": "PowerToggle",
#      "data": "1,38109,1,1,343,171,22,21,22,21,22,64,22,64,22,64,22,64,22,64,22,21,22,64,22,64,22,21,22,21,22,21,22,21,22,21,22,64,22,21,22,21,22,21,22,21,22,21,22,21,22,21,22,64,22,64,22,64,22,64,22,64,22,64,22,64,22,64,22,21,22,1523,343,86,22,3668,343,86,22,3800"
#   }, etc.

remote_action_portSend = RemoteAction()

local_event_CommandSet = LocalEvent()

param_commands = Parameter(
  { "title": "Commands", 
    "schema": { "type": "array", "title": "Inputs", 
                "items": {
                  "type": "object", "title": "Input",        
                  "properties": {
                    "group": { "type": "string", "title": "Group", "order": 1 },
                    "name": { "type": "string", "title": "Name", "order": 2 },
                    "data": { "type": "string", "title": u"Global Caché iTach IP2IR data", 'order': 3 }
  } } } } )

commandSet = list()

def handle_timer():
  local_event_CommandSet.emit(commandSet)

# periodically emit the command set
timer_timer = Timer(handle_timer, 5 * 60)

def main():
  bindCommands()
  
  local_event_CommandSet.emit(commandSet)
  
def bindCommands():
  for command in param_commands:
    bindCommand(command)
    
def bindCommand(command):
  commandName = command['name']

  name = 'Send "%s"' % commandName
  group = command['group']
  data = command['data']
  title = '"%s"' % commandName
    
  schema = {'title': title, 'group': group, 'order': next_seq() }
    
  event = Event(name, schema)
    
  def handler(arg=None):
    remote_action_portSend.call(data)
    event.emit()
    
  action = Action(name, handler, schema)
  
  commandSet.append({'name': name, 'group': group, 'title': title})