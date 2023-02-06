'''OSC Client Node'''

'''
https://www.music.mcgill.ca/~gary/306/week9/osc.html

An OSC message has the following general format:
<address pattern>   <type tag string>   <arguments>

The address pattern is a string that starts with a '/', followed by a message routing or destination.

OSC addresses follow a URL or directory tree structure, such as /voices/synth1/osc1/modfreq.
'''

### Libraries required by this Node
import OSC


### Parameters used by this Node
DEFAULT_IPADDRESS = "127.0.0.1"
DEFAULT_PORT = 9000

param_ipAddress = Parameter({'title': 'IP address', 'schema': {'type': 'string', 'hint': DEFAULT_IPADDRESS}, 'order':next_seq()})
param_port = Parameter({'title': 'Port', 'schema': {'type': 'integer', 'hint': DEFAULT_PORT}, 'order':next_seq()})

param_patterns = Parameter({'title': 'Patterns', 'order': next_seq(), 'schema': {'type': 'array', 'items': {
        'type': 'object', 'title': 'Pattern', 'properties': {
          'label': {'type': 'string', 'title': 'Label', 'hint': 'Foobar', 'order': next_seq()},
          'address': {'type': 'string', 'title': 'Address', 'hint': '/foo/bar', 'order': next_seq()}                                                             
        } } } })


### Functions used by this Node
def get_float(arg):
  # cust to reduce integers to decimal
  if arg > 1:
    arg = float(arg)
    arg = arg / 100
  return arg

def create_client_action(pattern):

  def default_handler(arg):
    oscmsg = OSC.OSCMessage()
    oscmsg.setAddress(pattern['address'])
    if arg:
      if isinstance(arg, int):
        arg = get_float(arg) # last minute have to add this, remove from generic client
      else:
        arg = get_number(arg)
      oscmsg.append(arg)

    console.log('Sending [ %s ] to [ %s ].' % (arg, pattern['address']))
    udp.send(oscmsg.getBinary())

  create_local_action(
    name='%s' % pattern['label'],
    metadata=basic_meta('%s' % pattern['label'], '%s' % pattern['address']),
    handler=default_handler
  )


### UDP utility utilised by this Node
udp = UDP(ready = lambda: console.info('UDP ready. %s' % udp.getDest()))


### Main
def main(arg = None):
  print 'Nodel script started.'

  udp.setDest((param_ipAddress or DEFAULT_IPADDRESS) + ':' + str(param_port or DEFAULT_PORT))

  # Generate pattern-matching local actions
  if not is_empty(param_patterns):
    for pattern in param_patterns:
      create_client_action(pattern)

### Utilities
def basic_meta(label, address):
  return {
    'title': '%s' % label,
    'group': 'Patterns',
    'order': next_seq(),
    'schema': {
      'type': 'string',
      'title': '%s' % address
    }
  }

def get_number(s):
  if is_number(s):
    return int(s) if s.isdecimal() else float(s)
  else:
    return s

def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False
      
# Customisation
def meta(name):
  console.log('Creating %s action.' % name.lower())
  return {
      'title': name,
      'schema': {
          'type': 'string',
          'enum': ['On', 'Off']
      },
      'order': next_seq(),
      'group': name
  }
  
def handlePower(arg):
  if arg =='On':
    lookup_local_action('Play').call()
    lookup_local_event('Power').emit('On')
  elif arg =='Off':
    lookup_local_action('Pause').call()
    lookup_local_event('Power').emit('Off')
      
create_local_action('Power', handlePower, meta('Power'))

def handleMuting(arg):
  if arg =='On':
    lookup_local_action('Power').call('Off')
  elif arg =='Off':
    lookup_local_action('Power').call('On')
      
create_local_action('Muting', handleMuting, meta('Muting'))

local_event_Power = LocalEvent({"title":"Power","schema":{"type":"string", "enum":['On','Off']},"group":"Power","order": next_seq()})

# vol cust
local_event_Volume = LocalEvent({"title":"Volume","schema":{"type":"integer"},"group":"Volume","order": next_seq()})
  

