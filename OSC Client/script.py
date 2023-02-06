'''
OSC Client Node

`rev 2 2023.02.07`
'''

'''
https://www.music.mcgill.ca/~gary/306/week9/osc.html

An OSC message has the following general format:
<address pattern>   <type tag string>   <arguments>

The address pattern is a string that starts with a '/', followed by a message routing or destination.

OSC addresses follow a URL or directory tree structure, such as /voices/synth1/osc1/modfreq.
'''

# <-- parameters

import os                          # working directory
from java.io import File           # reading files
from org.nodel.io import Stream    # reading files
from org.nodel.core import Nodel   # for host path
DEFAULT_IPADDRESS = "127.0.0.1"
DEFAULT_PORT = 9000

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

def create_client_action(pattern):

  def default_handler(arg):
    oscmsg = OSC.OSCMessage()
    oscmsg.setAddress(pattern['address'])
    if arg:
      if isinstance(arg, int):
        # last minute have to add this, remove from generic client
        arg = get_float(arg)
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

# -->


# <-- UDP

udp = UDP(ready=lambda: console.info('UDP ready. %s' % udp.getDest()))

# -->

# <-- main

def main(arg=None):
  print 'Nodel script started.'

  udp.setDest((param_ipAddress or DEFAULT_IPADDRESS) +
              ':' + str(param_port or DEFAULT_PORT))

  # Generate pattern-matching local actions
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
  # cust to reduce integers to decimal
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

# <-- customisation

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
  if arg == 'On':
    lookup_local_action('Play').call()
    lookup_local_event('Power').emit('On')
  elif arg == 'Off':
    lookup_local_action('Pause').call()
    lookup_local_event('Power').emit('Off')


create_local_action('Power', handlePower, meta('Power'))


def handleMuting(arg):
  if arg == 'On':
    lookup_local_action('Power').call('Off')
  elif arg == 'Off':
    lookup_local_action('Power').call('On')


create_local_action('Muting', handleMuting, meta('Muting'))

local_event_Power = LocalEvent({"title": "Power", "schema": {
                               "type": "string", "enum": ['On', 'Off']}, "group": "Power", "order": next_seq()})

# vol cust
local_event_Volume = LocalEvent({"title": "Volume", "schema": {
                                "type": "integer"}, "group": "Volume", "order": next_seq()})

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
    _node.restart()
  except Exception, e:
    console.error('Failed to write the OSC.py file: ', e)


@after_main
def check_for_osc_dependency():
  try:
    import OSC
  except ImportError:
    console.info('No OSC dependency found, retrieving...')
    content = retrieve_osc_dependency()
    write_osc_file(content)

# -->
