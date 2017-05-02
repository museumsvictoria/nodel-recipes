'''See console and script for detailed usage instructions and detailed feedback.'''

console.warn('''



NOTE: 
        Due to the intensive CPU and memory requirements, it
        is highly recommended this node only execute within its 
        own independent process space e.g. run directly from
        the command-line of a workstation:
        
        > java -jar nodelhost.jar -p 0


STEPS:


Step 1: Place all recipe collections in the 'recipes' folder 
        of this node and their signatures will be loaded for 
        matching.
        
        Ensure there is at least one node running the versions
        of the scripts you want deployed to other nodes.
        
        
Step 2: Use the 'Probe' operation to determine which node 
        hosts are running on the network.
        
        WAIT... 
        
        (give at least 10s to allow all node hosts to answer)
        

Step 3: Use 'Begin Survey' to interrogate the nodes in one 
        sequential sweep.
        
        WAIT...
        
        (monitor the console and wait until operation completes)
        
        
Step 4: Refresh the Node page to show up additional actions and signals.

        WAIT...
        
        (the browser will take some time to render the page fully 
        depending on the speed of the browser/CPU.)
       

Step 5: Compose a list of node names (one per line) and use
        the 'Push' actions group to push scripts out to a 
        collection of nodes.



''')



# For generating the node's REST end-points
from java.net import URLEncoder 

# For loose matching
from org.nodel import SimpleName 

# To determine recipes folder for this host
from org.nodel.jyhost import NodelHost

# For non-Python exception details
from java.lang import Exception as JavaException 

# for loading files
from java.io import File 

# for reading unicode
from org.nodel.io import Stream 

# to determine working directory
import os 

CURRENT_RECIPES = NodelHost.instance().recipes().getRoot()
param_RecipesFolder = Parameter({'title': 'Recipes folder', 'schema': {'type': 'string', 'hint': CURRENT_RECIPES.getAbsolutePath()}})

param_ScriptTypes = Parameter({'title': 'Custom script types', 'schema': {'type': 'array', 'items': {
        'type': 'object', 'properties': {
          'type':      { 'type': 'string', 'order': 1},
          'signature': { 'type': 'string', 'order': 2}}
        }}})


scriptTypes_bySignature = {}
scripts_bySignature = {}

def main():
  for scriptTypeInfo in param_ScriptTypes or []:
    scriptTypes_bySignature[scriptTypeInfo['signature']] = scriptTypeInfo
    
  if len(param_RecipesFolder or '') == 0:
    recipesFolder = CURRENT_RECIPES
  else:
    recipesFolder = File(param_RecipesFolder)
  
  if not recipesFolder.exists():
    console.warn("NOTE: No 'recipes' folder exists; you might want to create and populate the folder with your recipes to help detection.")
    
  elif recipesFolder.listFiles() in [None, 0]:
    console.warn("NOTE: No recipes exist in the 'recipes' folder; you might want to populate the folder with your recipes to help detection.")
    
  items = load_existing_scripts(recipesFolder)
  console.info('loaded %s scripts' % len(items))
  for item in items:
    scriptTypes_bySignature[item['signature']] = {'type': item['path'], 'signature': item['signature']}
  
def load_existing_scripts(folder):
  items = list() # e.g. [{'path':       'recipes/pjlink', 
                 #        'scriptFile':  PATH_OF_SCRIPT,
                 #        'signature':   ___,
                 #       }]
  traverse('', folder, items)
  
  return items
  
def traverse(path, pathFile, items):
  fileList = pathFile.listFiles()
  if fileList == None:
    return
  
  for f in fileList:
    if f.isHidden():
      continue
      
    name = f.getName()
      
    if name.startswith('_') or name.startswith('.'):
      continue
      
    newPath = path + "/" + name if len(path) > 0 else name
    
    if f.isDirectory():
      traverse(newPath, f, items)
      
    if f.isFile() and name.lower() == 'script.py':
      signature = getSignature(Stream.readFully(f))
                                 
      items.append({'path': path, 
                    'scriptFile': f,
                    'signature': signature})
      return
    
    # otherwise, keep traversing
  
def udp_ready():
  console.info('udp is ready. Can probe now.')
  
nodeAddressesByName = {} # (by SimpleName)

NODESINFO_SCHEMA = {'type': 'object', 'properties': {
                       'httpAddress': {'type': 'string', 'order': next_seq()},
                       'scriptModified': {'type': 'string', 'order': next_seq()},
                       'scriptSignature': {'type': 'string', 'order': next_seq()}
                   }}
  
def udp_received(src, data):
  console.info('probe response from:[%s] data:[%s]' % (src, data))
  
  packet = json_decode(data)
  
  present = packet.get('present')
  if present is None:
    return
  
  for nodeName in present:
    if nodeName in nodeAddressesByName:
      # node already exists, so warn and continue
      
      console.warn('Node "%s" already exists' % nodeName)
      
      continue
      
    httpAddress = None
      
    for address in packet['addresses']:
      if address.startswith('http'):
        httpAddress = address
        httpAddress = httpAddress.replace('%NODE%', URLEncoder.encode(nodeName, 'UTF-8'))
      
    if httpAddress is None:
      console.warn('No HTTP address for this node')
      continue
      
    nodeAddressesByName[SimpleName(nodeName)] = httpAddress
    
# (can now use udp callbacks)
udp = UDP(source='0.0.0.0:0', dest='224.0.0.252:5354', ready=udp_ready, received=udp_received, 
          # intf='136.154.24.165' - 
          )

def local_action_Probe(arg=None):
  '''{"title": "1. Probe", "group": "Operations", "order": 1}'''
  
  udp.send(json_encode({"discovery": "*", "types": ["tcp", "http"]}))
  
surveyed = False
  
def local_action_BeginSurvey(arg=None):
  '''{"title": "2. Begin survey", "group": "Operations", "order": 2}'''
  
  errors = list()
  
  global surveyed
  if surveyed:
    console.warn('Can only survey once per session. Restart node to repeat.')
    return
  
  surveyed = True
  
  for nodeName in nodeAddressesByName:
    try:
      queryNode(nodeName)
        
    except BaseException, exc:
      errors.append([nodeName, exc])
      
    except JavaException, exc:
      errors.append([nodeName, exc])
      
  for error in errors:
    console.warn('("%s" failed)' % error)
    
  console.info('> %s nodes detected (%s with errors)' % (len(nodeAddressesByName), len(errors)))
  console.info('> %s signatures' % len(signatures))
  
  types = [t for t in countByType]
  types.sort()
  
  for t in types:
    console.info('> %s of type "%s"' % (countByType[t], t))
    
SCRIPT_SCHEMA = {'type': 'object', 'properties': {
                    'type':  { 'type': 'string', 'title': 'Type', 'order': 1 },
                    'signature': { 'type': 'string', 'title': 'Signature', 'order': 2 },
                    'nodes':     { 'type': 'string', 'title': 'Nodes', 'format': 'long', 'order': 3},
                    'notes':     { 'type': 'string', 'order': 10}
                }}

signatures = set()

countByType = {}
    
def queryNode(nodeName):
  # create an event if one isn't already set up
  key = 'Node %s' % nodeName
  event = lookup_local_event(key)
  if event is None:
    event = Event(key, {'title': '"%s"' % nodeName, 'group': 'Nodes', 'schema': NODESINFO_SCHEMA})
    
  info = {}
  
  address = nodeAddressesByName[nodeName]
  
  scriptUrl = '%sREST/script' % address
  
  try:
    scriptInfo = json_decode(get_url(scriptUrl))
    
    info['scriptModified'] = scriptInfo['modified']
    
    signature = getSignature(scriptInfo['script'])
    signatures.add(signature)
    
    info['scriptSignature'] = signature
    
    ttype = 'Unknown'
    scriptTypeInfo = scriptTypes_bySignature.get(signature)
    if scriptTypeInfo is not None:
      # is a well-known script
      ttype = scriptTypeInfo.get('type')
      
      # update the script (once) and set up a 'push' action
      if not signature in scripts_bySignature:
        script = scriptInfo['script']
        scripts_bySignature[signature] = script
        
        createPusher(ttype, script)
    
    signatureEvent = lookup_local_event('Script %s' % signature)
    if signatureEvent is None:
      signatureEvent = Event('Script %s' % signature, {'group': '"%s" scripts' % ttype, 'title': signature, 'schema': SCRIPT_SCHEMA})
      arg = {'signature': signature, 'nodes': ''}
      signatureEvent.emit(arg)
      
    arg = signatureEvent.getArg()
      
    # add another node (need to do reconstruction instead of a direct '.append' in case of a locked list (from persistence)
    newNodes = arg['nodes'] or ''
    
    if len(newNodes) == 0:
      newNodes = str(nodeName)
      
    else:
      newNodes = newNodes + "\r\n" + str(nodeName)
      
    arg['nodes'] = newNodes
    arg['type'] = ttype
    
    typeCount = countByType.get(ttype)
    if typeCount is None:
      countByType[ttype] = 1
    else:
      countByType[ttype] = typeCount + 1
    
    signatureEvent.emit(arg)
    
  except:
    info['scriptModified'] = ''
    
    raise
    
  finally:
    event.emit(info)
    
def createPusher(ttype, script):
  
  def handler(arg):
    nodes = [x.strip() for x in arg.splitlines() if len(x.strip())>0]
    
    console.info('Pushing to %s...' % nodes)
    
    for nodeName in nodes:
      address = nodeAddressesByName[SimpleName(nodeName)]
  
      scriptUrl = '%sREST/script/save' % address
    
      result = get_url(scriptUrl, post=json_encode({'script': script}))
      console.info('result: %s' % result)
  
  Action('Push script type %s' % ttype, handler, 
         {'title': 'Push "%s"' % ttype, 'group': 'Push', 'caution': 'Are you sure?', 'schema': {'type': 'string', 'format': 'long'}})
  

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - 

import hashlib

# gets a loose signature of a text-based file
def getSignature(data):
  m = hashlib.md5()
  
  totalLines = 0 # the number of lines in the file
  codeLines = 0 # the number of lines of code (comments excluded)
  totalSize = 0 # the number of characters of code (comments excluded)
  
  for line in data.splitlines():
    totalLines = totalLines + 1
    
    stripped = line.strip()
    if not stripped.startswith('#'):
      codeLines = codeLines + 1
      totalSize = totalSize + len(stripped)
      
    m.update(line.encode('utf-8')) # update the digest with comment
    
  h = m.digest().encode('hex')
    
  return 'loc:%s size:%s hash:%s' % (codeLines, totalSize, h)
