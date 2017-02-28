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
  indexFile = File(workingDir, 'content\\index.xml')
  if not indexFile.exists():
    console.warn('No "content/index.xml" file exists; cannot continue')
    return
  
  schemasFile = File(workingDir, 'content\\schemas.json')
  if schemasFile.exists():
    loadSchemas(Stream.readFully(schemasFile))
  
  loadIndexFile(Stream.readFully(indexFile))
  
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

def loadIndexFile(xml):
  xml = ET.fromstring(xml)
  
  def explore(group, e):
    eType = e.tag
    eAction = e.get('action')
    eEvent = e.get('event')
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
  
  explore('', xml)


# customisation

