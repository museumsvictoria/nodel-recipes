'''Extron IPL, S2, S4, etc. driver'''

# reference:
#
#    http://media.extron.com/download/files/userman/68-1715-01_IPL_250_A_080509.pdf

import xml.etree.ElementTree as ET

# aborts after parse failure. Used for scrict testing; should be False in production
strictParse = True

param_ipAddress = Parameter({'title': 'IP address', "desc": "The IP address of the Extron G2 series unit.", "schema": {"type": "string"} })

# the standard file which should contain the list of configured devices
DEFAULT_CONTROLSUMMARYPATH = 'gc2/gv-ctlsum_1.xml' 
controlSummaryPath = DEFAULT_CONTROLSUMMARYPATH

param_controlSummaryFile = Parameter({'title': 'Control summary file (XML)', 'desc': 'This file changes dynamically depending on the GC3 software. Make sure it exists using a web-browser', 
                                      'schema': {'type': 'string', 'hint': DEFAULT_CONTROLSUMMARYPATH + ' (this needs to be confirmed)'}})

param_reservedPorts = Parameter({'title': 'Reserved ports', 'schema': {'type': 'array', 'items': {
        'type': 'object', 'properties': {
          'port': {'type': 'string', 'desc': 'A port number/ID e.g. "1", "2", etc.', 'order': 1},
          'nodeName': {'title': 'Node name', 'type': 'string', 'desc': 'A node name e.g. "My Site Projector 1"', 'order': 2},
        }}}})

urlBase = ""

# initialised in main
reservedNamesByPortNum = {}

ports = set()

# Receiving state
# 'Normal' (or None)
# 'Listing files'
# 'Listing IR commands'
local_event_ParseMode = LocalEvent({ 'title': 'Parse mode', 'desc': 'The parsing mode when received eedback.', 'group': 'Comms', 
                                    'schema': {'type': 'string'}})

def main(arg = None):
    if param_ipAddress == None:
        console.warn('Driver not started: No IP address has been specified.')
        return
        
    print 'Extron G2 series driver started.'
    
    # use the control summary file
    if len(param_controlSummaryFile or '') > 0:
      global controlSummaryPath
      controlSummaryPath = param_controlSummaryFile      
      
    # use the reserved port info
    if len(param_reservedPorts or '') == 0:
      console.warn('No reserved ports have been configured (ignore this message if intentional)')
    
    for reservedPortInfo in param_reservedPorts or '':
      reservedNamesByPortNum[reservedPortInfo['port']] = reservedPortInfo['nodeName']
    
    # reset parse mode
    local_event_ParseMode.emit('Normal')
    
    global urlBase
    urlBase = 'http://' + str(param_ipAddress)
    
    # (can only set the destination when 'param_ipAddress' has been injected)
    tcp.setDest('%s:23' % param_ipAddress)
    
    print 'Driver binding will occur on intial TCP connection...'
    
def bindEverything():
    print 'Extracted IR commands'
    bindIRCommands()
  
    urls = extractPortURLs(urlBase, controlSummaryPath)
    
    print 'Extracted device URLs:', urls

    for url in urls:
        bindPort(url)
        
def unbindEverything():
    for port in ports:
        if port.subnode:
          print 'Releasing node "%s"' % port.name
          releaseNode(port.subnode)
        
    ports.clear()
    _uniqueNames.clear()
        
local_event_TCPConnected = LocalEvent({ 'desc': 'When a TCP connection occurs.', 'group': 'Comms' })
local_event_TCPDisconnected = LocalEvent({ 'desc': 'When a TCP disconnection occurs.', 'group': 'Comms' })
local_event_TCPSent = LocalEvent({ 'desc': 'When TCP data is sent.', 'group': 'Comms' })
local_event_TCPReceived = LocalEvent({ 'desc': 'When TCP data is received.', 'group': 'Comms' })
local_event_TCPTimeout = LocalEvent({ 'desc': 'When TCP timeout connection or read timeout occurs.', 'group': 'Comms' })

local_event_IntroGreeting = LocalEvent()
local_event_IntroDate = LocalEvent()
local_event_Firmware = LocalEvent()

local_event_UnknownFeedback = LocalEvent({ 'desc': 'When unknown feedback is received.', 'group': 'Protocol' })

def local_action_RequestFirmware(arg = None):
    '{"title": "Request firmware" }'
    tcp.request('q', lambda resp: local_event_Firmware.emit(resp))

def tcp_connected():
    local_event_TCPConnected.emit()
    ping_timer.setInterval(60)
    ping_timer.start()
    
    # slurp the introduction and firmware date first
    tcp.receive(lambda resp: local_event_IntroGreeting.emit(resp))
    tcp.receive(lambda resp: local_event_IntroDate.emit(resp))
    
    # receive the files
    # listFiles()
    
    bindEverything()
    
def tcp_disconnected():
    local_event_TCPDisconnected.emit()
    ping_timer.stop()
    
    unbindEverything()

def tcp_sent(data):
    local_event_TCPSent.emit(data)
  
def tcp_timeout():
    local_event_TCPTimeout.emit()
  
def tcp_received(data):
    local_event_TCPReceived.emit(data)
    
    lastReceive[0] = system_clock()
    
    parseState = local_event_ParseMode.getArg()
    if parseState == 'Listing files':
        parseFileListResp(data)
        return
      
    elif parseState == 'Listing IR commands':
        if currentIRfile is not None:
            currentIRfile.parseLine(data)
    
    feedback = parseFeedback(data)

    if feedback is None or len(feedback) != 4:
        return
  
    # try match discrete state feedback
    key = '%s,%s,%s,%s' % (feedback[0], feedback[1], feedback[2], feedback[3])
    eventInfo = eventCallbacks.get(key)
    if eventInfo:
        eventInfo.event.emit()
        return

    # otherwise match variable state feedback (sliding values, etc.)
    key = '%s,%s,%s' % (feedback[0], feedback[1], feedback[2])
    eventInfo = eventCallbacks.get(key)
    if eventInfo:
        eventInfo.event.emit(int(feedback[3]))
        return
      
    local_event_UnknownFeedback.emit({'key' : key })
  
# TCP has to be set up after callback functions are defined 
tcp = TCP(connected = tcp_connected, received = tcp_received, sent = tcp_sent, disconnected = tcp_disconnected, timeout = tcp_timeout)

# 'ping' every 60s
ping_timer = Timer(lambda: local_action_RequestFirmware(), 60, stopped=True)

# holds the global EventInfos by event key
# key might be '1,2,3' or '1,2,3,4'
eventCallbacks = {}

def bindPort(url):
    console.info('Binding port against URL "%s"' % url)
    port = ExtronPort(url)
    name = url

    try:
      port.parse()
      
      name = port.name

      if len(port.warnings) > 0:
          for warn in port.warnings:
              # log to both host and subnodes
              if port.subnode:
                  port.subnode.injectInfo(warn)

              console.warn(name + ': ' + warn)
              
      if len(port.infos) > 0:
          for info in port.infos:
              # log to both host and subnodes
              if port.subnode:
                  port.subnode.injectInfo(info)

              console.log(name + ': ' + info)

    except Exception, e:
        console.error('%s: ERROR - %s' % (name, e))
        
        if strictParse:
            raise
        else:
            # allow script to continue
            pass
    
    return port

class EventInfo:
    def __init__(self, code, event, state, retrieve_cmd = None, cmd_down = None):
        self.code = code
        self.event = event
        self.state = state
        self.retrieve_cmd = retrieve_cmd
        self.cmd_down = cmd_down

class ExtronPort:
    def __init__(self, url):
        self.url = url
        self.warnings = [] # any warnings that occur during parsing
        self.infos = [] # info a user of the driver might find useful
        self.eventLookups = {} # event callback lookups
        self.subnode = None # will be created when at least one command exists
        ports.add(self)

    def parse(self):
        configXML = getURL(self.url)
        
        content = ET.fromstring(configXML)
        
        # ...
        # <group device="0" heading="Integra DTR-5.8" dev_type_id="27" driver_info="Integra DTR-5.8">
        # ...

        # only prepare a subnode if we have at least one command
        group = content.find('group')
        if group is None:
            self.warnings.append('Group element does not exist; no bindable port information.')
            return
          
        commands = group.findall('command') or []
        
        portNumber = extractPortNumber(content) or 'X'
        
        heading = group.attrib.get('heading')
        driver_info = group.attrib.get('driver_info')
        
        fields = list()
        
        if heading is None:
          self.warnings.append("'heading' was not found in <group>")
        else:
            fields.append('heading:"%s"' % heading)

        if driver_info is None:
            self.warnings.append("'driver_info' was not found in <group>")
        else:
            fields.append('driver info:"%s"' % heading)
            
        device = heading or driver_info
        
        autoName = 'Port ' + portNumber + ' ' + device if device else 'Port ' + portNumber
        
        reservedName = reservedNamesByPortNum.get(str(portNumber))
        
        uniqueName = getUniqueName(autoName if reservedName is None else reservedName)
        
        self.name = uniqueName
        self.subnode = Node(self.name)            
          
        desc = "An Extron subnode generated-on-the-fly. (%s)" % ", ".join(fields)
        self.subnode.setDesc(desc)
        
        self.subnode.injectInfo('(bound from %s)' % self.url)
          
        # 'level' or 'buildinglevel'
        level = content.attrib.get('level') or content.attrib.get('buildinglevel')
        if level is None:
            self.warnings.append("'level' or 'buildinglevel' was missing from <content>")
            level = '(not present)'

        self.subnode.injectInfo('level:%s' % level)

        deviceInfo = '(not present)'
        config = content.find('config')
        if config is not None:
            device = config.find('device')

            if device is not None:
               deviceInfo = device.attrib

        self.subnode.injectInfo('deviceInfo: %s' % deviceInfo)

        for command in commands:
            items = command.findall('item') or {}

            # the retriever action should be set up once per command
            # but it's not known until deeper

            # the retriever action for this command group
            retriever = None
            
            # the node events (by compare code) for this command group
            events = {}

            for item in items:
                itemType = item.attrib.get('type')

                if itemType == 'info':
                    self.bindInfoItem(command, item)
                    if len(items) != 1:
                        self.warnings.append("<item type='item'> was meant to be one and only within command '" + command.attrib['label'])

                elif itemType == 'set':
                    retriever = self.bindSetItem(command, item, retriever, events)

                elif itemType == 'textselect':
                    retriever = self.bindTextSelectItem(command, item, retriever)

                elif itemType == 'slider':
                    retriever = self.bindSliderItem(command, item, retriever)
                    
                elif itemType == 'text':
                    self.bindTextItem(command, item)                 

                else:
                    self.warnings.append("unknown type '%s' within command '%s'" % (itemType, command.attrib.get('label') or 'missing'))


    # ...
    # <command label="Connection Status" control-rowlimit="3" command-priority="1" id="7" show="1">
    #   <item type="info" current="W1,2,100LE|">
    #     <subitem current="W1,2,100LE|" type="info" compare="137" item-priority="1">Connected</subitem>
    #     <subitem current="W1,2,100LE|" type="info" compare="138" item-priority="2">Disconnected</subitem>
    #   </item>
    # </command>
    # ...
    def bindInfoItem(self, command, item):
        subitems = item.findall('subitem') or {}

        commandLabel = command.attrib.get('label')
        if commandLabel is None:
            self.warnings.append('A command was unlabeled (ignoring).');
            return

        # events (by compare codes)
        events = {}
        
        # set up the events first
        for subitem in subitems:
            state = subitem.text

            # 'info' items only need events
            retrieve_cmd = subitem.attrib.get('current')
            if retrieve_cmd is None:
                # try using its item
                retrieve_cmd = item.attrib.get('current')

            if retrieve_cmd is None:
                self.warnings.append("'info' command had no 'current' lookup; ignoring")
                return

            name = commandLabel + ' ' + state
            
            event = self.subnode.addEvent(name, { 'title': state,
                                                  'desc': "When '%s' is in '%s' state." % (commandLabel, state),
                                                  'group': commandLabel,
                                                  'order': nextSeqNum() })
            
            code = subitem.attrib['compare']
            events[code] = (event, state)
            eventInfo = EventInfo(code, event, state, retrieve_cmd)
            self.eventLookups[code] = eventInfo
            registerGlobalEvent(eventInfo)

        # only one action to get the state
        retrieve_cmd = item.attrib['current']
        
        def actionHandler(arg = None):
            tcp.request(retrieve_cmd, lambda data: handleFeedback(data, events))

        name = 'Refresh ' + commandLabel
        action = self.subnode.addAction(name, actionHandler, { 'title': 'Refresh', 
                                                               'desc': "Refreshes '%s' state." % commandLabel, 
                                                               'group': commandLabel,
                                                               'order': nextSeqNum() })

    # <command label="Power" control-rowlimit="3" command-priority="2" id="1" show="1">
    #   <item cmddown="W1,2,76,1LE|" current="W1,2,104LE|" type="set" compare="1" item-priority="1">On</item>
    #   <item cmddown="W1,2,76,3LE|" current="W1,2,104LE|" type="set" compare="3" item-priority="2">Off</item>
    # </command>
    # 'events' - events (by compare code)
    def bindSetItem(self, command, item, retrieverArg, events):
        state = item.text
        commandLabel = command.attrib['label']

        retriever = retrieverArg
        
        retrieve_cmd = item.attrib.get('current')
        cmd_down = item.attrib['cmddown']
        
        # prepare event first
        code = item.attrib.get('compare')
        if code is not None:
            name = commandLabel + ' ' + state
            
            event = self.subnode.addEvent(name, { 'title': state,
                                                  'desc': "When '%s' is in '%s' state" % (commandLabel, state),
                                                  'group':  commandLabel,
                                                  'order': nextSeqNum() })
            
            events[code] = (event, state)
            eventInfo = EventInfo(code, event, state, retrieve_cmd, cmd_down)
            self.eventLookups[code] = eventInfo
            registerGlobalEvent(eventInfo)

        # retrieve action (if provided or not already been set up)
        if retrieverArg is None and retrieve_cmd is not None:
              
            def actionHandler(arg = None):
                tcp.request(retrieve_cmd, lambda data: handleFeedback(data, events))
                
            name = 'Refresh ' + commandLabel
            
            try:
                retriever = self.subnode.addAction(name, actionHandler, { 'title': 'Refresh', 
                                                                          'desc': "Refreshes '%s' state." % commandLabel, 
                                                                          'group': commandLabel,
                                                                          'order': nextSeqNum() })
            except:
                # TODO: better error feedback for multiple duplicates (beyond ' (2)' suffix)
                console.warn('Action "%s.%s" could not be created. Trying different name...' % (self.name, name))
                
                retriever = self.subnode.addAction(name + " (2)", actionHandler, { 'title': 'Refresh', 
                                                                          'desc': "Refreshes '%s' state." % commandLabel, 
                                                                          'group': commandLabel,
                                                                          'order': nextSeqNum() })

        # action
        
        def actionHandler(arg = None):
            tcp.send(cmd_down)
            
        name = commandLabel + ' ' + state
        action = self.subnode.addAction(name, actionHandler, { 'title': state, 
                                                               'desc': "Calls action '%s'." % name, 
                                                               'group': commandLabel, 
                                                               'caution': cautionNeeded(commandLabel),
                                                               'order': nextSeqNum() })

        return retriever

    # <command label="Preset Recall" control-rowlimit="3" command-priority="7" id="218" show="1">
    #   <item type="textselect" current="W1,2,120LE|">
    #     <subitem cmddown="W1,2,96,3741LE|" current="W1,2,120LE|" type="textselect" compare="3741" item-priority="1">1</subitem>
    #     <subitem cmddown="W1,2,96,3742LE|" current="W1,2,120LE|" type="textselect" compare="3742" item-priority="2">2</subitem>
    #     <subitem cmddown="W1,2,96,3743LE|" current="W1,2,120LE|" type="textselect" compare="3743" item-priority="3">3</subitem>
    # ...
    def bindTextSelectItem(self, command, item, retrieverArg):
        subitems = item.findall('subitem') or {}

        retriever = retrieverArg
        
        commandLabel = command.attrib['label']
        
        # node events (by compare code)
        events = {}
        
        # event (holds state)
        event = self.subnode.addEvent(commandLabel, { 'title': commandLabel,
                                                      'desc': "When '%s' changes state" % commandLabel,
                                                      'group': commandLabel,
                                                      'order': nextSeqNum(),
                                                      'schema': STRING_SCHEMA })
        
        # retrieve action (if provided or not already been set up)
        if retrieverArg is None:
            retrieve_cmd = item.attrib.get('current')
            if retrieve_cmd is not None:
              
                def actionHandler(arg = None):
                    tcp.send(retrieve_cmd)
                    
                name = command.attrib['label'] + ' Refresh'
                retriever = self.subnode.addAction(name, actionHandler, { 'title': 'Refresh',
                                                                          'desc': "Refreshes '%s' state" % commandLabel, 
                                                                          'group': commandLabel,
                                                                          'order': nextSeqNum() })

        # need to do this out of the loop below to ensure variable capture takes place
        def createActionHandler(cmd, state):
          
            def actionHandler(arg = None):
                tcp.request(cmd, lambda data: handleFeedback(data, events, state))
                
            return actionHandler
        
        for subitem in subitems:
            # register event state
            state = subitem.text
            cmd_down = subitem.attrib['cmddown']
            retrieveCurrent = subitem.attrib['current']
            code = subitem.attrib['compare']
            events[code] = (event, state)
            eventInfo = EventInfo(code, event, state, retrieveCurrent, cmd_down)
            self.eventLookups[code] = eventInfo
            registerGlobalEvent(eventInfo)

            actionHandler = createActionHandler(cmd_down, state)

            name = commandLabel + ' ' + state
            action = self.subnode.addAction(name, actionHandler, { 'title': state,
                                                                   'desc': "Requests '%s' changes state to '%s'." % (commandLabel, state), 
                                                                   'group': commandLabel,
                                                                   'order': nextSeqNum(),
                                                                   'caution': cautionNeeded(commandLabel) })

        return retriever
      
    # <command label="Volume" control-rowlimit="3" command-priority="5" id="158" show="1">
    #   <item type="slider" current="W1,2,116LE|" pre="W1,2,88," suf="LE|" start="0" stop="100" increment="1" item-priority="1"/>
    # </command>
    def bindSliderItem(self, command, item, retrieverArg):
        # retrieve action (if provided or not already been set up)
        
        commandLabel = command.attrib['label']
        
        start = item.attrib.get('start') or "'unsure'"
        stop = item.attrib.get('stop') or "'unsure'"
        
        cmd_pre = item.attrib['pre']
        cmd_suf = item.attrib['suf']

        retriever = retrieverArg
        
        # event state
        event = self.subnode.addEvent(commandLabel, { 'title': commandLabel, 
                                                      'desc': "When '%s' changes." % commandLabel,
                                                      'group': commandLabel, 
                                                      'order': nextSeqNum(),
                                                      'schema' : integerSchema(commandLabel, commandLabel) })

        retrieve_cmd = item.attrib.get('current')
        code = item.attrib.get('compare')
        dummy_cmd_down = '%s%s%s' % (cmd_pre, 0, cmd_suf)
        eventInfo = EventInfo(code, event, None, retrieve_cmd, dummy_cmd_down)
        self.eventLookups[code] = eventInfo
        registerGlobalEvent(eventInfo, continuous=True)
        
        if retrieverArg is None and retrieve_cmd is not None: 
            def actionHandler(arg = None):
                tcp.request(retrieve_cmd, lambda data: handleVariableStateFeedback(data, event))

            name = 'Refresh ' + commandLabel
            retriever = self.subnode.addAction(name, actionHandler, { 'title': 'Refresh',
                                                                      'desc': "Retrieves '%s' value." % commandLabel, 
                                                                      'group': commandLabel,
                                                                      'order': nextSeqNum(),
                                                                      'caution': cautionNeeded(commandLabel) })

        # action

        def actionHandler(arg = None):
            if arg is None:
                print '("%s": no arg provided; nothing to send)' % commandLabel
            else:
                tcp.request("%s%s%s" % (cmd_pre, arg, cmd_suf), lambda data: handleVariableStateFeedback(data, event))

        name = 'Slide ' + commandLabel
        action = self.subnode.addAction(name, actionHandler, { 'title': 'Adjust',
                                                               'desc':  "Slides '%s' value (range is from %s to %s)." % (commandLabel, start, stop), 
                                                               'group': commandLabel, 
                                                               'caution': cautionNeeded(commandLabel), 
                                                               'schema': integerSchema(commandLabel, commandLabel, start, stop) })

        return retriever

    # <command label="Lamp Usage" control-rowlimit="3" command-priority="5" id="3" show="1">
    #   <item current="W16,2,625LE|" type="text" compare="14" item-priority="1" maxlamp="2000">Value</item>
    # </command>
    # (or)
    # <command label="Filter Usage" control-rowlimit="3" command-priority="6" id="127" show="1">
    #   <item current="W16,2,633LE|" type="text" compare="14" item-priority="1">Value</item>
    # </command>
    def bindTextItem(self, command, item):
        commandLabel = command.attrib.get('label')
        if commandLabel is None:
            self.warnings.append('A command was unlabeled (ignoring).');
            return
        
        # event state
        event = self.subnode.addEvent(commandLabel, { 'title': commandLabel, 
                                                      'desc': "When '%s' changes." % commandLabel,
                                                      'group': commandLabel, 
                                                      'order': nextSeqNum(),
                                                      'schema' : STRING_SCHEMA })
        retrieve_cmd = item.attrib['current']
        
        # don't need to register any global feedback because it comes back synchronously and can
        # be emitted straight away
        
        def actionHandler(arg = None):
            tcp.request(retrieve_cmd, lambda data: event.emit(data))

        name = 'Refresh ' + commandLabel
        retriever = self.subnode.addAction(name, actionHandler, { 'title': 'Refresh',
                                                                 'desc': "Retrieves '%s' value." % commandLabel, 
                                                                 'group': commandLabel,
                                                                 'order': nextSeqNum(),
                                                                 'caution': cautionNeeded(commandLabel) })


# 'W1,2,76,1LE|'
def parseEventKeyFromRequest(cmd, continuous = False):
    if cmd is None: return
    
    parts = cmd.split(',')
    
    if len(parts) >= 4:
        port = int(parts[0][1:]) # drop 'W'
        category = int(parts[1])
        eventId = int(parts[2])
        if continuous:
            # ignore the state part
            key = '%s,%s,%s' % (port, category, eventId)
            return key
        else:
            state = int(parts[3][0:-3]) # drop '1LE|'
            key = '%s,%s,%s,%s' % (port, category, eventId, state)
            return key
      
    else:
        return None

def registerGlobalEvent(eventInfo, continuous = False):
    "Registers a callback in the callback map"
    key = parseEventKeyFromRequest(eventInfo.cmd_down, continuous)
    
    if key:
        eventCallbacks[key] = eventInfo      
        

def parseFeedback(data):
    '''Returns a single string array (feedback with no context)
       or [evt, port, cat, value] array of integers (feedback with context)
    
    
       Example feedback:
    
       "137" 
           - volume feedback (has no context)
       
       "Evt00001,2,0000000092,330" 
           - volume down feedback (has context)
           
'''
    
    parts = data.split(',')

    count = len(parts)

    if count == 1:
        # return as a single item array
        return [parts[0]]

    elif count == 4:
        return [ int(parts[0][3:]),
                 int(parts[1]),
                 int(parts[2]),
                 int(parts[3]) ]
    
    local_event_UnknownFeedback.emit(data)
      
def handleFeedback(data, events, state = None):
    feedback = parseFeedback(data)
    
    if feedback is None:
      return
    
    if len(feedback) == 1:
        eventLookup = events.get(feedback[0])
        
    elif len(feedback) == 4:
        # leave to contextual feedback handler
        # eventLookup = events.get(feedback[FB_VALUE])
        return
        
    if eventLookup is not None:
        # arg not needed; state implied in name
        if state is None:
            eventLookup[0].emit()
        else:
            eventLookup[0].emit(state)
      

def handleVariableStateFeedback(data, event):
    feedback = parseFeedback(data)
    
    if feedback is None:
      return
    
    value = None
    
    if len(feedback) == 1:
        value = int(feedback[0])
        
    elif len(feedback) == 4:
        # leave to contextual feedback handle
        # value = int(feedback[FB_VALUE])
        return
        
    event.emit(value)
    
#holds the files list    
files = list()

def fileListTimeout():
    local_event_ParseMode.emit('Normal')
    console.warn('File listing mode timed out; disabling any special parse modes.')


timer_fileListTimeout = Timer(fileListTimeout, 0, 15, stopped=True)

def listFiles():
    console.log('Listing files...')
    
    # flush the list
    del files[:]
    
    local_event_ParseMode.emit('Listing files')
    
    timer_fileListTimeout.start()
    
    # send the file listing command
    tcp.send('\x1BDF')

def parseFileListResp(data):
    # sample response
    # [filename 1] [day, date time of upload] GMT [file size 1 in bytes]]
    # ...
    # [space remaining (to 7-digits)] Bytes Left
    if data.endswith('Bytes Left'):
        # changes modes, and return
        local_event_ParseMode.emit('Normal')
        
        timer_fileListTimeout.stop()
        
        return
      
    # filename will be first part, not interested in the rest
    parts = data.split(' ')
    filename = parts[0]
    
    files.append(filename)
    
# holds the current IR file being parsed
currentIRfile = None

def bindIRCommands():
    # check the file list for '0.eir'
    for filename in files:
        parts = filename.split('.')
        if len(parts) != 2:
            continue
            
        fileNum = parts[0]
        
        global currentIRfile
        
        currentIRfile = IRFile(fileNum)
        
        # request all the commands
        console.log('Requesting command set for IR file %s' % fileNum)
        tcp.send('w %s 0 ir' % fileNum)
        
        # send this straight afterwards to emulate an end-of-transaction
        tcp.send('w -1 0 ir')    

class IRFile:
    "Holds the command-set related to an IR file."
    def __init__(self, fileNum):
        MISSING_LABEL = '(missing)'
        self.fileNum = fileNum
        self.manufacturer = MISSING_LABEL
        self.model = MISSING_LABEL
        self.clazz = MISSING_LABEL
        self.remote = MISSING_LABEL
        self.creationDate = MISSING_LABEL
        self.comments = MISSING_LABEL
        self.userFileName = MISSING_LABEL
        
        # e.g. {  "POWER": "1", 
        #         "DVD_PLAY", "71",
        #  ...
        #         "135": "1.00",
        #         "136": "1.8.1",
        #         "137": "LG V271 VCR-DVD Combined Commands.eir
        #      }
        self.commandsByName = {}
        
        
    # parses lines like:
    # 1,POWER
    # 9,R_SRCH
    # 10,F_SRCH
    # 13,R_CHAP
    #
    # from manual:
    # 0 = return all data
    # 129 = manufacturer
    # 130 = model
    # 131 = class
    # 132 = remote
    # 133 = creation date
    # 134 = comments
    # 137 = user file name (a descriptive name the user/installer gave the file)    
    def parseLine(self, line):
        parts = line.split(',')
        
        if len(parts) != 2:
            console.warn('an IR command response was not in 2 parts, ignoring')
            return
          
        code = parts[0]
        name = parts[1]
        
        if code == '129':
            self.manufacturer = name
        elif code == '130':
            self.model = name
        elif code == '131':
            self.clazz = name
        elif code == '132':
            self.remote = name
        elif code == '133':
            self.creationDate = name
        elif code == '134':
            self.comments = name
        elif code == '137':
            self.userFileName = name
        else:
            self.commandsByName[name] = code        
                    
def cautionNeeded(label):
    "Returns a caution message if 'power' is in the label, or None otherwise"
    
    if label is None:
        return False
    else:
        return "This action relates to power control. Use with caution." if 'power' in label.lower() else None
      
def integerSchema(name, desc, start=None, stop=None):
    schema = { "name" : name,
               "title" : name,
               "desc" : desc,
               "description" : desc,
               "type" : "integer" }
    
    if start is not None:
        schema['min'] = start
    if stop is not None:
        schema['max'] = stop
    
    return schema

def extractPortNumber(xmlElement):
    "Extract port number: Explores an XML tree looking for the first 'cmddown' or 'current' attribute."

    def testFor(text):
        if text:
            parts = text.split(',')
            if len(parts) > 2 and parts[0][0] == 'W':
                return parts[0][1:]

    def extractCmddownOrCurrent(xmlElement):
        # check both attributes
        for attr in [ 'cmddown', 'current' ]:
            value = testFor(xmlElement.attrib.get(attr))
            if value:
                return value

        # check all children
        for child in xmlElement:
            value = extractCmddownOrCurrent(child)
            if value:
               return value

        return None

    return extractCmddownOrCurrent(xmlElement)
  

# $ curl http://192.168.178.205/gc2/gv-ctlsum_1_user.xml
#
# <?xml version="1.0"?>
# <?xml-stylesheet type="text/xsl" href="gv-sumctlmonsch.xsl" ?>
# <summary type="gv-control.xsl">
#    <summarygroup>
#        <device id="0">
#            <iplip>192.168.178.205</iplip>
#            <filename>gc2/gv-portserial2ctl.xml</filename>
#        </device>
#        <device id="0">
#            <iplip>192.168.178.205</iplip>
#            <filename>gc2/gv-portserial1ctl.xml</filename>
#        </device>
#    </summarygroup>
# </summary>
# 
def extractPortURLs(baseURL, filename):
    '''
    Returns a list of full URLs by exploring a 'gv-ctlsum_1_user' list file.
    baseURL: http://192.168.178.205
    filename: gc2/gv-ctlsum_1_user.xml
    '''
    dest = baseURL + '/' + filename
    console.info('Retrieving %s' % dest)
    rootXML = getURL(dest)
        
    root = ET.fromstring(rootXML)
    
    # don't care where they exist, just extract all the <device> elements
    devices = list()
    
    def explore(element):
        for child in element:
            if child.tag == 'device':
                devices.append(child)
            else:
                explore(child)
    
    explore(root)
    
    baseURLs = list()
    
    for device in devices:
        try:
            filename = device.find('filename').text
            
            if filename:
                baseURLs.append(baseURL + '/' + filename)
        except:
            pass
          
    return baseURLs
  
_seqCounter = [0L]

def nextSeqNum():
    'Returns a unique sequencing number for set ordering.'
    _seqCounter[0] += 1
    return _seqCounter[0]
  
_uniqueNames = set()
  
def getUniqueName(name):
    'Generates a unique name, e.g. NEC, NEC1, NEC2, etc.'
    key = name
    counter = 0
    while key in _uniqueNames:
        key = '%s_%s' % (key, counter)
        counter += 1
    _uniqueNames.add(key)
    return key

STRING_SCHEMA = { "name" : "A name", 
                  "desc" : "A desc", 
                  "description": "A description", 
                  "title" : "Value", 
                  "type" : "string" }

# status ---

local_event_Status = LocalEvent({'title': 'Status', 'group': 'Status', 'order': 9990, "schema": { 'title': 'Status', 'type': 'object', 'properties': {
        'level': {'title': 'Level', 'order': next_seq(), 'type': 'integer'},
        'message': {'title': 'Message', 'order': next_seq(), 'type': 'string'}
    } } })

# for status checks

lastReceive = [0]

# roughly, the last contact  
local_event_LastContactDetect = LocalEvent({'group': 'Status', 'title': 'Last contact detect', 'schema': {'type': 'string'}})
  
def statusCheck():
  diff = (system_clock() - lastReceive[0])/1000.0 # (in secs)
  now = date_now()
  
  if diff > status_check_interval+15:
    previousContactValue = local_event_LastContactDetect.getArg()
    
    if previousContactValue == None:
      message = 'Always been missing.'
      
    else:
      previousContact = date_parse(previousContactValue)
      roughDiff = (now.getMillis() - previousContact.getMillis())/1000/60
      if roughDiff < 60:
        message = 'Missing for approx. %s mins' % roughDiff
      elif roughDiff < (60*24):
        message = 'Missing since %s' % previousContact.toString('h:mm:ss a')
      else:
        message = 'Missing since %s' % previousContact.toString('h:mm:ss a, E d-MMM')
      
    local_event_Status.emit({'level': 2, 'message': message})
    
  else:
    local_event_LastContactDetect.emit(str(now))
    local_event_Status.emit({'level': 0, 'message': 'OK'}) 
  
status_check_interval = 75
status_timer = Timer(statusCheck, status_check_interval)

