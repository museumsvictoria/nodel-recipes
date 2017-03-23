from java.net import URLEncoder # For generating the node's REST end-points
from org.nodel import SimpleName # For loose matching
from java.lang import Exception as JavaException # For non-Python exception details

param_ScriptTypes = Parameter({'schema': {'type': 'array', 'items': {
        'type': 'object', 'properties': {
          'type':      { 'type': 'string', 'order': 1},
          'signature': { 'type': 'string', 'order': 2}}
        }}})

scriptTypes_bySignature = {}
scripts_bySignature = {}

def main():
  for scriptTypeInfo in param_ScriptTypes or []:
    scriptTypes_bySignature[scriptTypeInfo['signature']] = scriptTypeInfo
  
  global udp
  udp = UDP(source='0.0.0.0:0', dest='224.0.0.252:5354', ready=udp_ready, received=udp_received, 
            #intf='136.154.24.165'
           )
  
def udp_ready():
  console.info('udp_ready')
  
nodeAddressesByName = {} # (by SimpleName)

NODESINFO_SCHEMA = {'type': 'object', 'properties': {
                       'httpAddress': {'type': 'string', 'order': next_seq()},
                       'scriptModified': {'type': 'string', 'order': next_seq()},
                       'scriptSignature': {'type': 'string', 'order': next_seq()}
                   }}
  
def udp_received(src, data):
  console.info('udp_recieved: src:[%s] data:[%s]' % (src, data))
  
  packet = json_decode(data)
  
  present = packet.get('present')
  if present is None:
    return
  
  for nodeName in present:
    if nodeName in nodeAddressesByName:
      # node already exists
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

def local_action_Probe(arg=None):
  udp.send(json_encode({"discovery": "*", "types": ["tcp", "http"]}))
  
  
def local_action_ProcessAll(arg=None):
  errors = list()
  
  for nodeName in nodeAddressesByName:
    try:
      queryNode(nodeName)
        
    except BaseException, exc:
      errors.append([nodeName, exc])
      
    except JavaException, exc:
      errors.append([nodeName, exc])
      
  for error in errors:
    console.warn('("%s" failed)' % error)
    
  console.info('%s nodes detected (%s with errors)' % (len(nodeAddressesByName), len(errors)))
  console.info('%s signatures' % len(signatures))
  
  types = [t for t in countByType]
  types.sort()
  
  for t in types:
    console.info('%s of type "%s"' % (countByType[t], t))
    
SCRIPT_SCHEMA = {'type': 'object', 'properties': {
                    'type':  { 'type': 'string', 'title': 'Type', 'order': 1 },
                    'signature': { 'type': 'string', 'title': 'Signature', 'order': 2 },
                    'nodes':     { 'type': 'array', 'title': 'Nodes', 'order': 3, 'items': { 
                                     'type': 'object', 'properties': {
                                       'name': {'type': 'string', 'order': 1}}}},
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
      arg = {'signature': signature, 'nodes': []}
      signatureEvent.emit(arg)
      
    arg = signatureEvent.getArg()
      
    # add another node (need to do reconstruction instead of a direct '.append' in case of a locked list (from persistence)
    newNodes = [x for x in arg['nodes'] or []]
    newNodes.append({'name': nodeName})
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
    nodes = [x['node'] for x in arg]
    
    console.info('Pushing to %s...' % nodes)
    
    for nodeName in nodes:
      address = nodeAddressesByName[SimpleName(nodeName)]
  
      scriptUrl = '%sREST/script/save' % address
    
      result = get_url(scriptUrl, post=json_encode({'script': script}))
      console.info('result: %s' % result)
  
  Action('Push script type %s' % ttype, handler, 
         {'group': 'Push', 'schema': {'caution': 'Are you sure?', 'type': 'array', 'items': {
            'type': 'object', 'properties': {
              'node': {'type': 'string'}}}}})
  

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
