import xml.etree.ElementTree as ET # XML parsing
import os                          # working directory
from java.io import File           # reading files
from org.nodel.io import Stream    # reading files
from org.nodel import SimpleName   # for Node names

param_suggestedNode = Parameter({'title': 'Suggested Node', 
                                 'desc': 'A suggestion can be made when remote bindings are created. The then need to be confirm and saved',
                                 'schema': {'type': 'string', 'format': 'node'}})

param_localOnlySignals = Parameter({'title': 'Local only signals',
                                    'desc': 'No remote bindings are configured for these. Comma-separated list of signals',
                                    'schema': {'type': 'string'}})

param_localOnlyActions = Parameter({'title': 'Local only actions',
                                    'desc': 'No remote bindings are configured for these. Comma-separated list of signals',
                                    'schema': {'type': 'string'}})

local_event_Clock = LocalEvent({"title": "Clock", "group": "General", "schema": {"type": "string" }})
timer_clock = Timer(lambda: local_event_Clock.emit(date_now()), 1)

localOnlySignals = set()
localOnlyActions = set()

# the node's working directory
workingDir = os.getcwd()

schemaMap = {} # taken from 'schema.json'
               # For example:
               #
               # { 'status_signal': {'type': 'object', 'properties': ... },
               #   'meter': {'type': 'number'},
               #   ...
               # }

def main():
  # split the local only actions and signals
  [localOnlySignals.add(SimpleName(name)) for name in (param_localOnlySignals or '').split(',')]
  [localOnlyActions.add(SimpleName(name)) for name in (param_localOnlyActions or '').split(',')]
  
  # parse the index
  indexFile = os.path.join(workingDir, 'content', 'index.xml')
  if not os.path.exists(indexFile):
    console.warn('No "%s" file exists; cannot continue' % indexFile)
    return
  
  schemasFile = os.path.join(workingDir, 'content', 'schemas.json')
  if os.path.exists(schemasFile):
    loadSchemas(Stream.readFully(File(schemasFile)))
  
  loadIndexFile(indexFile)
  
def loadSchemas(json):
  schemas = json_decode(json)
  
  keys = list()
  for key in schemas:
    schemaMap[key] = schemas[key]
    keys.append(key)
    
  if len(keys) > 0:
    print 'Loaded schemas: %s' % ', '.join(keys)

  else:
    console.warn('(no schema mapping info was present)')

def loadIndexFile(xmlFile):
  xml = ET.parse(xmlFile)
  
  def explore(group, e):
    eType = e.tag
    join = e.get('join')             # shorthand for <... action=... event=...">
    eActionNormal = e.get('action') or join
    eActionOn = e.get('action-on')   # these are for
    eActionOff = e.get('action-off') # momentary buttons
    eEvent = e.get('event') or join
    title = e.get('title')
    
    # compose a group name (if possible)
    if title == None and eType == 'title':
      title = e.text
      
    if title in ['row', 'column']:
      title = None
    
    if title == None:
      thisGroup = group
    
    elif group == '':
      thisGroup = title
      
    else:
      thisGroup = '%s - %s' % (group, title)
      
    # the default schema to use if '_action' or '_signal' is not used
    defaultSchema = schemaMap.get(eType)

    def tryAction(eAction):
      if eAction != None and lookup_local_action(eAction) == None:
        # an action is specified
        
        # is it local only?
        if SimpleName(eAction) in localOnlyActions:
          handler = lambda arg: None
          
        else:
          remoteAction = create_remote_action(eAction, suggestedNode=param_suggestedNode)
          handler = lambda arg: remoteAction.call(arg)
        
        action = Action(eAction, handler, 
                        {'group': thisGroup, 'order': next_seq(), 'schema': schemaMap.get('%s_action' % eType, defaultSchema)})
      
    tryAction(eActionNormal)
    tryAction(eActionOn)
    tryAction(eActionOff)

    if eEvent != None and lookup_local_event(eEvent) == None:
      # an event is specified
      
      event = Event(eEvent, 
                    {'group': thisGroup, 'order': next_seq(), 'schema': schemaMap.get('%s_signal' % eType, defaultSchema)})
      
      # is it local only?
      if not SimpleName(eEvent) in localOnlySignals:
        def remoteEventHandler(arg=None):
          event.emit(arg)
      
        remoteEvent = create_remote_event(eEvent, remoteEventHandler, suggestedNode=param_suggestedNode)
    
    for i in e:
      explore(thisGroup, i)
  
  explore('', xml.getroot())


# customisation

