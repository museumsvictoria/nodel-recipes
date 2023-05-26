'''
OSC Client Node

`rev 2 2023.02.07`

- Unidirectional only.
- Turn OSC messages (address pattern + optional argument) into local actions via parameters.
- Send custom OSC messages via a custom local action.

'''

'''
https://www.music.mcgill.ca/~gary/306/week9/osc.html

An OSC message has the following general format:
<address pattern>   <type tag string>   <arguments>

The address pattern is a string that starts with a '/', followed by a message routing or destination.

OSC addresses follow a URL or directory tree structure, such as /voices/synth1/osc1/modfreq.
'''

# <-- parameters

from java.io import File
from org.nodel.io import Stream

DEFAULT_IPADDRESS = "127.0.0.1"
DEFAULT_PORT = 9000

DEFAULT_PATTERN = "/foo/bar"

param_ipAddress = Parameter({'title': 'IP address', 'schema': {
                            'type': 'string', 'hint': DEFAULT_IPADDRESS}, 'order': next_seq()})
param_port = Parameter({'title': 'Port', 'schema': {
                       'type': 'integer', 'hint': DEFAULT_PORT}, 'order': next_seq()})

param_patterns = Parameter({'title': 'Patterns', 'order': next_seq(), 'schema': {'type': 'array', 'items': {
    'type': 'object', 'title': 'Pattern', 'properties': {
            'label': {'type': 'string', 'title': 'Label', 'hint': 'Foobar', 'order': next_seq()},
        'address': {'type': 'string', 'title': 'Address', 'hint': '/foo/bar', 'order': next_seq()}
    }}}})

# -->

# <-- functions

# batch local actions sending OSC messages based on parameter patterns
def create_client_action(pattern):

  def default_handler(arg):
    
    # address pattern
    oscmsg = OSC.OSCMessage()
    oscmsg.setAddress(pattern['address'])

    # optional argument
    if arg:
      if isinstance(arg, int):
        # last minute have to add this, remove from generic client
        arg = get_float(arg)
      else:
        arg = get_number(arg)
      oscmsg.append(arg)

    # send
    console.log('Sending [ %s ] to [ %s ].' % (arg, pattern['address']))
    udp.send(oscmsg.getBinary())

  create_local_action(
      name='%s' % pattern['label'],
      metadata=basic_meta('%s' % pattern['label'], '%s' % pattern['address']),
      handler=default_handler
  )

# a custom action for sending arbitrary OSC messages
def create_custom_action():

  def generic_osc_handler(message):
    if message != None:

      # address pattern
      address = (message['address'] or DEFAULT_PATTERN).strip()
      oscmsg = OSC.OSCMessage()
      oscmsg.setAddress(address)

      # optional argument
      arg = None
      if message['arg']:
        if isinstance(message['arg'], int):
          arg = get_float(message['arg'])
        else:
          arg = get_number(message['arg'])
        oscmsg.append(arg)

      # send
      console.log('Sending [ %s ] to [ %s ].' % (arg, address))
      udp.send(oscmsg.getBinary())

  custom_metadata = {'group': 'Custom', 'title': 'Send a custom message', 'schema': {'type': 'object', 'properties': {
      'address': {'type': 'string', 'title': 'Address', 'hint': DEFAULT_PATTERN, 'order': next_seq()},
      'arg': {'type': 'string', 'title': 'Argument', 'hint': '1', 'order': next_seq()}
  }}, 'order': next_seq()}
  
  create_local_action('Custom', handler=generic_osc_handler, metadata=custom_metadata)

# -->

# <-- UDP

udp = UDP(ready=lambda: console.info('UDP ready. %s' % udp.getDest()))

# -->

# <-- main

def main(arg=None):
  console.log('Nodel script started.')

  udp.setDest((param_ipAddress or DEFAULT_IPADDRESS) +
              ':' + str(param_port or DEFAULT_PORT))
  
  # Create a generic local actions for sending custom OSC messages
  create_custom_action()

  # Generate any user specified pattern-matching local actions from parameters
  if not is_empty(param_patterns):
    for pattern in param_patterns:
      create_client_action(pattern)

# -->

# <-- utilities

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

def get_float(arg):
  if arg > 1:
    arg = float(arg)
    arg = arg / 100
  return arg

def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False
    
# -->

# <-- retrieve and write OSC dependency
PYOSC_URL = 'https://raw.githubusercontent.com/ptone/pyosc/master/OSC.py'

def retrieve_osc_dependency():
  resp = get_url(PYOSC_URL, fullResponse=True)
  if resp.statusCode != 200:
    raise Exception(
        "Failed to retrieve OSC dependency, got status code: " + str(resp.statusCode))

  return resp.content

def write_osc_file(content):
  rootDir = File(_node.getRoot(), '')
  dstFile = File(rootDir, 'OSC.py')

  try:
    Stream.writeFully(dstFile, content.encode("utf-8"))
    console.info('"OSC.py" dependency retrieved, restarting node...')
    call(lambda: _node.restart(), delay = 2.5) # need a brief pause to allow the file to be written
  except Exception, e:
    console.error('Failed to write the OSC.py file: ', e)

@after_main
def check_for_osc_dependency():
  global OSC
  try:
    import OSC
  except ImportError:
    console.info('No OSC dependency found, retrieving...')
    content = retrieve_osc_dependency()
    write_osc_file(content)

# -->
