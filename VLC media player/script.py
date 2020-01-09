'''VLC Software Playback Node'''

### Libraries required by this Node
import os


### Parameters used by this Node
python_args = ['-u', 'complex_vlc_player.py']
param_command = Parameter({ 'title': 'Python',
                'desc': 'The list of command line arguments as JSON',
                'order': next_seq(),
                'schema': { 'type': 'array', 'items': {
                'type': 'object',
                  'properties': { 'arg': {'type': 'string'} } } } })

# example command:
# command = ['C:\\Python27\\python.exe', '-u', 'simple_vlc_player.py']
# NOTE: the '-u' flag (unbuffered) is important for interactive stdin/out

param_playlist = Parameter({'title': 'Content',
                            'desc': 'The list of playlist items as full paths.',
                            'order': next_seq(),
                            'schema': {'type': 'array', 'items': {
                                'type': 'object',
                                'properties': {'arg': {'type': 'string', 'title':'Filepath', 'hint': 'C:\\Content\\Video.mp4', 'order': next_seq()},
                                               'hold': {'type': 'boolean', 'title': 'Enable holding on final frame', 'order': next_seq()}}}}})

param_teaser = Parameter({ 'title': 'Enable teaser.',
                'desc': 'Continually loop through first video in the playlist.',
                'schema': {'type': 'boolean'},
                'order': next_seq() })


### Functions used by this Node
def search_python(): # attempt to auto find python.exe
  if (os.environ.get('OS', '') == 'Windows_NT'):
    python = find_specific('python.exe', 'C:\\Python27\\')
    if python:
      return python
    else:
      python = find_broad('python.exe', 'C:\\')
      if python:
        return python
  return False

def find_specific(name, path): # default path
  for root, dirs, files in os.walk(path):
    if name in files:
      return os.path.join(root, name)

def find_broad(name, path): # general search
  exclude = ['$Recycle.Bin', 'Windows']
  for root, dirs, files in os.walk(path, topdown=True):
    dirs[:] = [d for d in dirs if d not in exclude]
    if name in files:
      return os.path.join(root, name)

def init_vlc():
  console.info('VLC loaded.')
  if param_playlist:
    announce_playlist()
  else:
    console.warn('Playlist is empty.')
    process.close()

def announce_playlist():
  for num in range(0, len(param_playlist)):
    filename = param_playlist[num]['arg']
    console.info(filename)
    num = str((num + 1)).zfill(2)
    createAction(num, filename)

def handle_stdout(line):
  if not line.startswith('{'):
    print 'got line "%s"' % line
  
  json_message = line.strip()
  if json_message.startswith('#'):
    # ignore comments
    return
  
  if not json_message.startswith('{'):
    return
  
  message = json_decode(json_message)
  handle_message(message)

def handle_message(message):
  # lazily examine arguments (events most likely)
  
  event = message.get('event')
  if event:
      handle_event(event, message.get('arg'))
      return
  
  # next is metadata
  actions = message.get('actions')
  metadata = message.get('metadata')
  events = message.get('events')
  
  if actions:
    process_actions_reflection(actions, metadata)
    
  elif events:
    process_events_reflection(events, metadata)
    
  # (reserved for future processing)

def process_actions_reflection(actions, metadata):
  for i in range(len(actions)):
    process_action_reflection(actions[i], metadata[i])
    
def process_action_reflection(name, metadata):
  def handler(arg):
    message_json = json_encode({'action': name, 'arg': arg})
    print '# sending %s' % message_json
    process.sendNow(message_json)
    
  Action(name, handler, metadata)

def process_events_reflection(events, metadata):
  for i in range(len(events)):
    process_event_reflection(events[i], metadata[i])
  
def process_event_reflection(name, metadata):
  Event(name, metadata)
  
def handle_event(name, arg):
  event = lookup_local_event(name)
  if event:
    event.emit(arg)

# Auto create PlayClip actions based on playlist size.
def createAction(num, filename):
  event = Event('PlayClip%s' % num, {'group': 'Playlist'});

  meta = {"title":"PlayClip%s" % num,"desc":filename,"group":"Playlist","order":next_seq()}

  def handler(arg):
      print 'Action PlayClip%s requested' % num
      event.emit('Playing')
      action = lookup_local_action('playclip')
      if action:
        action.call(int(num))

  action = Action('Play Clip%s' % num, handler, metadata=meta)



### Process managed by this Node
process = Process([],
                  started=init_vlc,
                  stdout=handle_stdout,
                  stdin=None,
                  stderr=lambda data: console.info('got stderr "%s"' % data), # stderr handler
                  stopped=lambda exitCode: console.info('Process stopped (exit code %s)' % exitCode), # when the process is stops / stopped
                  timeout=lambda: console.warn('Request timeout'))  


def main(arg = None):
  # Start your script here.
  print 'Nodel script started.'

  # Retrieve Python location from arguments.
  if param_command:
    reducedCommand = [x['arg'] for x in param_command]
    reducedCommand = reducedCommand + python_args
    process.setCommand(reducedCommand)
    console.info('Using command %s' % reducedCommand)
  # Without arguments provided, attempt to search for Python.
  elif search_python():
    python_app = search_python()
    python_args.insert(0, python_app)
    process.setCommand(python_args)
    console.info('Using command %s' % python_args)
  # Exit on failure to locate Python.
  else:
    console.error('Missing Python parameters.')
    process.close()