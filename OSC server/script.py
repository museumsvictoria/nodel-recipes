'''OSC Server Node'''

'''
https://www.music.mcgill.ca/~gary/306/week9/osc.html

An OSC message has the following general format:
<address pattern>   <type tag string>   <arguments>

The address pattern is a string that starts with a '/', followed by a message routing or destination.

OSC addresses follow a URL or directory tree structure, such as /voices/synth1/osc1/modfreq.
'''

### Libraries required by this Node
import OSC
import socket
import threading


### Parameters used by this Node
DEFAULT_IPADDRESS = "127.0.0.1"
DEFAULT_PORT = 9000

param_disabled = Parameter({ 'title': 'Disabled', 'order': next_seq(), 'schema': {'type': 'boolean'}})
param_port = Parameter({ "order": next_seq(), "name": "port", "title": "Port", "schema": {"type": "integer", "hint": DEFAULT_PORT}})

param_patterns = Parameter({'title': 'Patterns', 'order': next_seq(), 'schema': {'type': 'array', 'items': {
        'type': 'object', 'title': 'Pattern', 'properties': {
          'label': {'type': 'string', 'title': 'Label', 'hint': 'Foobar', 'order': next_seq()},
          'address': {'type': 'string', 'title': 'Address', 'hint': '/foo/bar', 'order': next_seq()}                                                              
        } } } })
param_filter = Parameter({ 'title': 'Display non-parameterised messages', 'order': next_seq(), 'schema': {'type': 'boolean'}})

### Functions used by this Node
def default_handler(addr, tags, args, source):
  if param_filter:
    for pattern in param_patterns:
      if (addr == pattern['address']):
        return
    print addr, args

# A list of OSC messages and their respective callbacks
handlers = {
  'default': default_handler
}

def add_handler(pattern):
  event = lookup_local_event(pattern['label'])
  if event:
    s.addMsgHandler(pattern['address'], lambda addr, tags, args, source: event.emit(args))


### OSC utilities utilised by this Node
def initalise_osc(dest):
  global s
  try:
    s = OSC.OSCServer(dest)
  except socket.error, msg:
    console.warn('Server failed to launch: [%s]' % msg) 
    return False

  return True

def add_osc_handlers():
  for code in handlers:
    s.addMsgHandler(code, handlers[code])


### Main
def main(arg = None):
  print 'Nodel script started.'

  if param_disabled:
    console.warn("Disabled! Nothing to do...")
    return

  dest = (socket.gethostbyname(socket.gethostname()), (param_port or DEFAULT_PORT))
  console.info('Address [ %s:%d ]' % (dest[0], dest[1]))

  # Initalise OSC server.
  if initalise_osc(dest):
    add_osc_handlers()

  # Generate pattern-matching local events
  if not is_empty(param_patterns):
    for pattern in param_patterns:
      create_local_event(
        name='%s' % pattern['label'],
        metadata=basic_meta('%s' % pattern['label'])
      )
      add_handler(pattern)

### Utilities
def basic_meta(label):
  return {
    'title': '%s' % label,
    'group': 'Patterns',
    'order': next_seq(),
    'schema': {
      'type': 'string',
      'title': '%s' % label
    }
  }

@after_main
def report_handlers():
  if 's' in globals():
    callbacks = ''
    for addr in s.getOSCAddressSpace():
      callbacks += (addr + ' ')
    console.info('Patterns [ %s]' % callbacks)

@after_main
def thread_osc_server():
  if 's' in globals():
    console.info("Starting OSCServer.")
    global st
    st = threading.Thread(target = s.serve_forever)
    st.start()

@at_cleanup
def shutdown_server():
  if 's' in globals():
    print "Closing OSCServer."
    s.close()
    print "Waiting for thread to finish."
    st.join()



