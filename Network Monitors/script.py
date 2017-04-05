DEFAULT_MINTHRESHOLD = 30
DEFAULT_LONGGAP_SECS = 30

param_monitors = Parameter({'title': 'Monitors', 'schema': {'type': 'array', 'items': {'type': 'object', 'properties': {
        'name': {'title': 'Name', 'type': 'string', 'order': next_seq()},
        'url': {'title': 'URL', 'type': 'string', 'order': next_seq()},
        'minThreshold': {'title': 'Min. threshold (ms)', 'type': 'integer', 'order': next_seq(), 'hint': str(DEFAULT_MINTHRESHOLD)},
        'longGap': {'title': 'Long gap (s)', 'type': 'integer', 'order': next_seq(), 'hint': str(DEFAULT_LONGGAP_SECS)},
        'hideLatency': {'title': 'Hide latency?', 'type': 'boolean', 'order': next_seq()}
    }}}})

def main():
  if len(param_monitors or '') == 0:
    console.warn('No monitors are configured!')
    return
  
  for param in param_monitors or '':
      initMonitorParam(param)
      
  console.info('Started %s monitors' % len(param_monitors))

def initMonitorParam(param):
  initPoller(param['name'], 
             lambda complete: beginCheckURL(param['url'], complete),
             repeats=3,
             minThreshold=param.get('minThreshold') or DEFAULT_MINTHRESHOLD,
             longGapInSec=param.get('longGap') or DEFAULT_LONGGAP_SECS,
             hideLatency=param.get('hideLatency')
            )
  
  
class Stats:
  def __init__(self):
    self.reset()
    
  def reset(self):
    self.lastSent = 0
    self.lastID = 0
    self.max = 0
    self.min = 10000
    self.total = 0
    self.count = 0
    self.errors = 0
    
  def record(self, elapsed):
    self.count += 1
    if elapsed > self.max:
      self.max = elapsed
      
    if elapsed < self.min:
      self.min = elapsed
      
    self.total += elapsed
    
def initPoller(name, poller, minThreshold=DEFAULT_MINTHRESHOLD, repeats=3, gapInSec=2.5, longGapInSec=30, hideLatency=False):
  status = Event('%s Status' % name, {'title': 'Status', 'group': name, 'schema': {
                                        'type': 'object', 'title': 'Status', 'properties': {
                                          'level': {'type': 'integer', 'title': 'Level', 'order': 1},
                                          'message': {'type': 'string', 'title': 'Message', 'order': 2}
                                        }}})
  
  statsSchema = {'type': 'object', 'title': 'Latency', 'properties': {
                   'min': {'type': 'integer', 'title': 'Min.', 'order': 1}, 
                   'max': {'type': 'integer', 'title': 'Max.', 'order': 2}, 
                   'average': {'type': 'integer', 'title': 'Ave.', 'order': 3}, 
                   'errors': {'type': 'integer', 'title': 'Errors', 'order': 4}
                }}
  
  stats = Stats()
  
  def poll():
    log('%s: polling...' % name)
    started = system_clock()
    
    def onComplete(result, error):
      diff = system_clock() - started
      
      log('%s: poll complete in %s ms' % (name, diff))
      
      if error != None:
        stats.errors += 1
      
      stats.record(diff)
      
      if stats.count >= repeats:
        total = stats.total
        
        if repeats > 2:
          # remove max and min
          total -= stats.max
          total -= stats.min
          ave = total/(stats.count-2)
        else:
          ave = total/stats.count
        
        log('%s: count:%s min:%s max:%s adjusted_avg:%s errors:%s' %
                     (name, stats.count, stats.min, stats.max, ave, stats.errors))
        
        if ave > minThreshold:
          if stats.errors == 0:
            status.emit({'level': 2, 'message': '%sms latency is above %s threshold.' % (ave, minThreshold)})
          else:
            status.emit({'level': 2, 'message': 'Errors occurred and %sms latency is above %s threshold.' % (ave, minThreshold)})
          
        elif stats.errors > 0:
          status.emit({'level': 2, 'message': 'Errors occurred during poll.'})
          
        else:
          status.emit({'level': 0, 'message': 'OK%s' % ('' if hideLatency else ' (%sms latency)' % ave) })
        
        stats.reset()
        
        # wait long gap
        call_safe(poll, longGapInSec)
      else:
        # wait small gap
        call_safe(poll, gapInSec)
    
    poller(onComplete)
    
  # stagger the pollers
  call_safe(poll, (next_seq() % 8)*1.1)
        
def beginCheckURL(url, complete):
  if url == None:
    complete(None, Exception('URL is empty or missing'))
    return
    
  def get_unsafe():
    try:
      result = get_url(url)
      
      call_safe(lambda: complete(result, None))
      
    except IOError, exc:
      call_safe(lambda: complete(None, exc))
      
    except:
      call_safe(lambda: complete(None, Exception('Non-IO exception')))
      
  call(get_unsafe)
  
  
# DNS poller ----

class DNSPoller:
  # DNS request (minus first byte)
  DNS_REQ = '\x1a\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00\x03\x77\x77\x77\x06\x67\x6f\x6f\x67\x6c\x65\x03\x63\x6f\x6d\x00\x00\x01\x00\x01'

  def __init__(self, dnsServer):
    self.lastSent = 0
    self.currentID = 9 # modulo 10
    self.complete = None # on complete callback
    self.udp = UDP(dest='%s:53' % dnsServer, ready=ready, received=received)

  def ready(self):
    console.info('udp ready!')
    
  def beginPing(self, complete):
    if self.complete != None:
      raise Exception('Current operation has not finished')
      
    self.complete = complete
    newID = (self.currentID + 1) % 10
    self.currentID = newID
    
    self.lastSent = system_clock()
    udp.send('%s%s' % (chr(newID), REQ))
    
    call_safe(timeoutCheck, 10)

  def received(self, src, data):
    console.log('udp recv: %s %s' % (src, data.encode('hex')))
  
    if len(src) == 0 or src[0] != self.currentID:
      # unexpected ID
      console.log('ignoring unexpected response')
      return
    
    callback = self.complete
    self.complete = None
    callback(True, None)
    
  def timeoutCheck(self):
    if self.complete == None:
      return
    
    diff = system_clock() - self.lastSent
    if diff>10000:
      callback = self.complete
      self.complete = None
      callback(None, Exception('Timeout! (took >10s)'))
  
# convenience functions
  
def log(msg):
  pass
  print msg
  
  
  