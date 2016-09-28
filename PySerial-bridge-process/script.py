# See https://github.com/pyserial/pyserial

DEFAULT_WORKINGDIR = '/opt/git/pyserial/examples'
DEFAULT_TCPPORT = 2001
DEFAULT_SERIALPORT = '/dev/ttyUSB0'
DEFAULT_BAUD = 9600

param_working = Parameter({'title': 'Working directory', 'schema': {'type': 'string', 'hint': DEFAULT_WORKINGDIR}})
param_tcpPort = Parameter({'title': 'TCP port', 'desc': 'Choose a fixed TCP port.', 'schema': {'type': 'integer', 'hint': DEFAULT_TCPPORT}})
param_serialPort = Parameter({'title': 'Serial port', 'desc': 'A serial port path', 'schema': {'type': 'string', 'hint': DEFAULT_SERIALPORT}})
param_baud = Parameter({'title': 'Baud rate', 'desc': '9600, etc.', 'schema': {'type': 'integer', 'hint': DEFAULT_BAUD}})


local_event_Disabled = LocalEvent({'schema': {'type': 'boolean'}})

process = None # (init. in main)

def main():
  console.info('Started!')
  
  if param_baud == None or local_event_Disabled.getArg() == True:
    console.warn('Process launch disabled (Baud not set or disabled is true)')
    return
  
  working = param_working if param_working != None and len(param_working.strip())>0 else DEFAULT_WORKINGDIR
  serialPort = param_serialPort if param_serialPort != None and len(param_serialPort.strip())>0 else DEFAULT_SERIALPORT
  tcpPort = param_tcpPort if param_tcpPort != None else DEFAULT_TCPPORT
  baud = param_baud if param_baud != None else DEFAULT_BAUD
  
  params = ['python', 'tcp_serial_redirect.py', '-P', str(tcpPort), serialPort, str(baud)]
  
  global process
  process = Process(params,
                    stderr=lambda line: console.warn('err: %s' % line),
                    stdout=lambda line: console.info('out: %s' % line),
                    working=working)
  
  console.info('Starting TCP/serial redirector... params:%s workingDir:%s) ' % (params, working))
  process.start()
    
def local_action_Disable(arg=None):
  """{"schema": {"type": "boolean"}}"""
  local_event_Disabled.emit(True)
  process.close()  
