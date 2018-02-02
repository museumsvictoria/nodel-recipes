import sys # for exception info

DEFAULT_CONN_ENDPOINT = 'https://outlook.office365.com/EWS/Exchange.asmx'

param_connector = Parameter({'title': 'Connector', 'schema': {'type': 'object', 'properties': {
        'ewsEndPoint': {'title': 'EWS end-point', 'type': 'string', 'hint': DEFAULT_CONN_ENDPOINT, 'order': 1},
        'username':    {'title': 'Username', 'type': 'string', 'order': 2}, 
        'password':    {'title': 'Password', 'type': 'string', 'format': 'password', 'order': 3},
        'address':     {'title': 'Address', 'type': 'string', 'hint': 'e.g. boardroom@company.com', 'order': 4}
  }}})

param_calendars = Parameter({'title': 'Calendars', 'schema': {'type': 'array', 'items': { 'type': 'object', 'properties': {
        'name': {'type': 'string', 'order': 1},
        'folderName': {'title': 'Folder name (if not default calendar)', 'type': 'string', 'desc': 'If default calendar is not being used, the exact name of the folder holding the group of calendars.', 'order': 2}
  }}}})

local_event_RawItems = LocalEvent({'title': 'Raw Items', 'group': 'Raw', 'schema': {'type': 'array', 'items': {
        'type': 'object', 'properties': {
          'subject': {'type': 'string', 'order': 1},
          'location': {'type': 'string', 'order': 2},
          'start': {'type': 'string', 'order': 3},
          'end': {'type': 'string', 'order': 4}
  }}}})

local_event_RawFolders = LocalEvent({'title': 'Raw Folders', 'group': 'Raw', 'schema': {'type': 'array', 'items': {
        'type': 'object', 'properties': {
          'displayName': {'type': 'string', 'order': 1}
  }}}})

# Booking / raw mappings
# 'title' taken from 'subject'
# 'member' taken from 'location'
# 'signal' extracted from 'subject' (e.g. '... {signal}')
# 'state' extracted from 'subject' (e.g. '... {signal: state}')

ITEM_SCHEMA = { 'type': 'object', 'title': '...', 'properties': {
                      'title': {'type': 'string', 'order': 1},
                      'start': {'type': 'string', 'order': 2},
                      'end': {'type': 'string', 'order': 3},
                      'member': {'type': 'string', 'order': 4},
                      'signal': {'type': 'string', 'order': 5},
                      'state': {'type': 'string', 'order': 6}
  }}

import xml.etree.ElementTree as ET
import base64

# (uses a safe default)
connector = { 'ewsEndPoint': DEFAULT_CONN_ENDPOINT,
              'username': None,
              'password': None,
              'address': None }

# some pre-constructed XML elements:

# - FolderId elements (by folder name)
resolvedFolderElements = {}

# DistinguishedFolderId element (including mailbox info if relevant)
distinguishedFolderIdElement = None

def main():
  username, password = None, None

  try:
    if param_connector == None:
      raise Exception('No connector config set!')
      
    username = tryGet(param_connector, 'username')
    if isBlank(username):
      raise Exception('No username set!')
      
    password = tryGet(param_connector, 'password')
    if isBlank(password):
      raise Exception('No password set!')

    # go through calendars...

    # ... ensure at least one exists 
    if isEmpty(param_calendars):
      raise Exception('At least one calendar must be configured.')

    # ... and no more than one default calendar is configured
    # ... and the folder name is not configured twice
    calendarMap = set()

    for calendarParam in param_calendars:
      if isEmpty(calendarParam.get('name')):
        raise Exception('A calendar must have a unique name given to it')

      folderName = calendarParam.get('folderName')

      if isEmpty(folderName):
        folderName = '<DEFAULT>'

      # raise an error if the calendar is already in the set
      if folderName in calendarMap:
        raise Exception('The same calendar has been referred to more than once in the calendars config - "%s"' % folderName)
       
      # add to the set
      calendarMap.add(folderName)
      
  except Exception, exc:
    console.warn(str(exc))
    return
  
  ewsEndPoint = tryGet(param_connector, 'ewsEndPoint')
  if isBlank(ewsEndPoint):
    ewsEndPoint = DEFAULT_CONN_ENDPOINT
  
  connector['ewsEndPoint'] = ewsEndPoint
  connector['username'] = username
  connector['password'] = password
  connector['address'] = param_connector.get('address')

  # pre-construct some of the re-useable XML elements
  global distinguishedFolderIdElement
  distinguishedFolderIdElement = ET.fromstring('<DistinguishedFolderId Id="calendar" xmlns="http://schemas.microsoft.com/exchange/services/2006/types"></DistinguishedFolderId>')

  # update mailbox and inject if present
  if not isBlank(connector['address']):
    mailboxElement = ET.fromstring('<Mailbox xmlns="http://schemas.microsoft.com/exchange/services/2006/types"><EmailAddress>SMTP_ADDRESS_HERE</EmailAddress></Mailbox>')
    searchElement(mailboxElement, 'type:EmailAddress').text = connector['address']

    distinguishedFolderIdElement.append(mailboxElement)


  # create signals for each calendar
  for calendarParam in param_calendars:
    name = calendarParam['name']
    Event('Calendar %s Items' % name, {'title': '"%s"' % (name), 'group': 'Calendars', 'order': next_seq(), 'schema': {'type': 'array', 'title': '...', 'items': ITEM_SCHEMA}})

  console.info('Started! Will poll folders and items now (then items every minute)')

  # folder resolution might not even be necessary, but no harm in doing it once anyway
  call(lambda: lookup_local_action('PollFolders').call())


# timer responsible for continually polling items  
# (every min, first after 10s)
timer_poller = Timer(lambda: lookup_local_action('PollItems').call(), 60, 10)

def local_action_PollItems(arg=None):
  try:
    now = date_now()

    rawBookings = query_ews(now, now.plusDays(7))
  
    trace('Raw:')
    for raw in rawBookings:
      trace(raw)
    
    # emit raw bookings
    local_event_RawItems.emitIfDifferent(rawBookings)

  
    # go through the raw list
    bookingsByCalendar = {}

    for raw in rawBookings:
      calendarIndex = raw['calendar']
    
      subject = raw['subject']

      booking = { 'title': subject,
                  'start': str(raw['start']),
                  'end': str(raw['end']),
                  'member': raw['location'],
                  'signal': None,
                  'state': None }
    
      # extract optional fields in the subject line

      # e.g. subject': 'Peace and quiet! {Power: Off}
      fieldName, fieldValue = extractField(subject)
    
      # override the signal name if it's present
      if not isBlank(fieldName):
        booking['signal'] = fieldName

      # override the value if it's present
      if not isBlank(fieldValue):
        booking['state'] = fieldValue

      bookings = bookingsByCalendar.get(calendarIndex)
      if bookings == None:
        bookings = list()
        bookingsByCalendar[calendarIndex] = bookings

      bookings.append(booking)

    # emit clean bookings
    for index, info in enumerate(param_calendars):
      trace('index:%s, info:%s' % (index, info))
    
      lookup_local_event('Calendar %s Items' % info['name']).emitIfDifferent(bookingsByCalendar.get(index) or [])
      
    # indicate a successful poll cycle
    lastSuccess[0] = system_clock()

  except:
    eType, eValue, eTraceback = sys.exc_info()
    
    console.warn('Failed to poll items; exception was [%s]' % eValue)
  
def query_ews(start, end):
  '''Date-range query of calendar items. Returns false if calendar resolution has not been completed yet.'''

  # prepare named folder elements if in use
  folderElements = list()
  for calendar in param_calendars or '':
    folderName = calendar['folderName']
    if not isEmpty(folderName):
      # lookup the folder by display name
      folderElement = resolvedFolderElements.get(folderName)

      if folderElement == None:
        raise Exception('At least one named-calendar has not been located yet; (folder name is "%s")' % folderName)

      folderElements.append(folderElement)

    else:
      # use distinguished folder
      folderElements.append(distinguishedFolderIdElement)

  request = prepareQueryRequest(start, end, resolvedFolders=folderElements)
  xmlRequest = ET.tostring(request)
  
  trace('Requesting... request:%s' % xmlRequest)
  
  response = get_url(connector['ewsEndPoint'],
                       username=connector['username'],
                       password=connector['password'],
                       contentType='text/xml',
                       post=xmlRequest)
  
  trace('Got response. data:%s' % response)
  
  warnings = list()
  
  items = parse_query_response(response, warnings)
  return items
  
def parse_query_response(responseXML, warnHandler):
  '''Parses a response, given the full envelope (as XML string)'''
  # no way to specify string encoding using this version of Python APIs
  # so need to pre-encode UTF8. Inner parser only deals with plain ASCII.
  root = ET.fromstring(responseXML.encode('utf-8'))

  # ensure header exists
  header = getElement(root, 'env:Header')

  # ensure body exists
  body = getElement(root, 'env:Body')

  # get major response part
  if len(body) <= 0:
    raise ParseException('Expected a major response with the Body')
  
  majorResponseTag = body[0].tag
  
  calendarItems = list()

  # (tag can be {m:FindItemResponse}, etc.)
  if majorResponseTag == expandPath('message:FindItemResponse'):
    findItemResponse = body[0]

    for responseMessage in findItemResponse:
      for responseIndex, findItemResponseMessage in enumerate(responseMessage):
        if getAttrib(findItemResponseMessage, "ResponseClass") != "Success":
          raise DataException("FindItemResponseMessage response class was not 'Success' (was %s)" % ET.tostring(findItemResponseMessage))

        responseCode = getElementText(findItemResponseMessage, 'message:ResponseCode')
        if responseCode != 'NoError':
          raise DataException("Response code was not 'NoError'")
          
        rootFolder = getElement(findItemResponseMessage, 'message:RootFolder')

        # warning...
        includesLastItemInRange = rootFolder.get('IncludesLastItemInRange')
        if includesLastItemInRange == False and warnings:
          warnings.append('IncludesLastItemInRange=false but this parser does not support paged responses')
        
        rootFolderItems = getElement(rootFolder, 'type:Items')

        for item in rootFolderItems:
          itemTag = item.tag

          # interpret calendar items only
          if itemTag == expandPath('type:CalendarItem'):
            itemIDElement = getElement(item, 'type:ItemId')
            itemID = {'id': getAttrib(itemIDElement, 'Id'),
                      'changeKey': getAttrib(itemIDElement, 'ChangeKey')}
            subject = tryGetElementText(item, 'type:Subject', default='')
            sensitivity = tryGetElementText(item, 'type:Sensitivity', default='') # TODO: interpret 'Sensitivity'
            start = getElementText(item, 'type:Start')
            end = getElementText(item, 'type:End')
            location = tryGetElementText(item, 'type:Location', default='')
            
            organiserElement = tryGetElement(item, 'type:Organizer')
            if organiserElement != None:
              organiserMailboxElement = getElement(organiserElement, 'type:Mailbox')
              organiserName = tryGetElementText(organiserMailboxElement, 'type:Name', default='')
              
            else:
              organiserName = ''

            calendarItems.append({ # 'id': itemID,
                                   'calendar': responseIndex,
                                   'subject': subject,
                                   'sensitivity': sensitivity,
                                   'start': date_instant(date_parse(start).getMillis()), # trick to convert into local timezone for display convenience (instead of GMT)
                                   'end': date_instant(date_parse(end).getMillis()), # trick to convert into local timezone for display convenience (instead of GMT)
                                   'location': location,
                                   'organiser': organiserName })
  else:
    raise DataException('Unexpected major response element - got %s' % majorResponseTag)
            
  return calendarItems

def local_action_PollFolders(arg=None):
  try:
    updateFolderMap()
    
  except:
    eType, eValue, eTraceback = sys.exc_info()
    
    console.warn('Failed to poll folders (will self retry in 5 mins); exception was [%s]' % eValue)
    
    call(lambda: lookup_local_action('PollFolders').call(), 5*60)

def updateFolderMap():
  folderItems = find_folders()
  
  local_event_RawFolders.emit(folderItems)

  # set up the lookup map
  for item in folderItems:
    resolvedFolderElements[item['displayName']] = item['folderIDElement']

def find_folders():
  '''Find all general calendar folders, returns array of {folderIDElement: ___, displayName: '___'}'''
  request = prepareGetFoldersRequest(smtpAddress=connector['address'])

  xmlRequest = ET.tostring(request)
  trace('find_folders requesting... data:%s' % xmlRequest)
  
  response = get_url(connector['ewsEndPoint'], 
                       username=connector['username'],
                       password=connector['password'],
                       contentType='text/xml',
                       post=xmlRequest)
  
  trace('find_folders. got response. data:%s' % response)
  
  warnings = list()
  
  items = parse_find_folders_response(response, warnings)

  return items

def parse_find_folders_response(responseXML, warnHandler):
  '''Parses a response, given the full envelope (as XML string)'''
  # see previous comment RE UTF-8 encoding
  root = ET.fromstring(responseXML.encode('utf-8'))

  # ensure header exists
  header = getElement(root, 'env:Header')

  # ensure body exists
  body = getElement(root, 'env:Body')

  # get major response part
  if len(body) <= 0:
    raise ParseException('Expected a major response with the Body')
  
  majorResponseTag = body[0].tag
  
  calendarFolders = list()

  # (tag can be {m:FindItemResponse}, etc.)
  if majorResponseTag == expandPath('message:FindFolderResponse'):
    findItemResponse = body[0]

    for responseMessage in findItemResponse:
      for findItemResponseMessage in responseMessage:
        if getAttrib(findItemResponseMessage, "ResponseClass") != "Success":
          raise DataException("FindFolderResponseMessage response class was not 'Success' (was %s)" % ET.tostring(findItemResponseMessage))

        responseCode = getElementText(findItemResponseMessage, 'message:ResponseCode')
        if responseCode != 'NoError':
          raise DataException("Response code was not 'NoError'")

        rootFolder = getElement(findItemResponseMessage, 'message:RootFolder')

        # warning...
        includesLastItemInRange = rootFolder.get('IncludesLastItemInRange')
        if includesLastItemInRange == False and warnings:
          warnings.append('IncludesLastItemInRange=false but this parser does not support paged responses')
        
        rootFolderFolders = getElement(rootFolder, 'type:Folders')

        for folder in rootFolderFolders:
          folderTag = folder.tag

          # interpret calendar folders only
          if folderTag == expandPath('type:CalendarFolder'):
            folderIDElement = getElement(folder, 'type:FolderId')
            folderID = {'id': getAttrib(folderIDElement, 'Id'),
                        'changeKey': getAttrib(folderIDElement, 'ChangeKey')}
            displayName = getElementText(folder, 'type:DisplayName')

            calendarFolders.append({ 'folderIDElement': folderIDElement,
                                     'displayName': displayName })

  else:
    raise DataException('Unexpected major response element - got %s' % majorResponseTag)
            
  return calendarFolders

# <SOAP/XML operations ---

# XML namespace lookups
NS = { 'env': 'http://schemas.xmlsoap.org/soap/envelope/',
       'message': 'http://schemas.microsoft.com/exchange/services/2006/messages',
       'type': 'http://schemas.microsoft.com/exchange/services/2006/types' }

# %STARTDATE% example: 2017-02-02T17:09:08.967+11:00
# %ENDDATE% example: 2017-02-03T17:09:09.099+11:00

REQ_QUERY_TEMPLATE_XML = '''<?xml version="1.0" encoding="utf-8"?>
  <s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
     <s:Header>
        <h:DateTimePrecisionType xmlns:h="http://schemas.microsoft.com/exchange/services/2006/types">Seconds</h:DateTimePrecisionType>
        <h:RequestServerVersion Version="Exchange2010_SP2" xmlns:h="http://schemas.microsoft.com/exchange/services/2006/types"/>
     </s:Header>
     <s:Body>
        <FindItem Traversal="Shallow" xmlns="http://schemas.microsoft.com/exchange/services/2006/messages">
           <ItemShape>
              <BaseShape xmlns="http://schemas.microsoft.com/exchange/services/2006/types">Default</BaseShape>
              <AdditionalProperties xmlns="http://schemas.microsoft.com/exchange/services/2006/types">
                 <FieldURI FieldURI="item:Sensitivity"/>
              </AdditionalProperties>
           </ItemShape>
           <CalendarView StartDate="START_DATE_HERE" EndDate="END_DATE_HERE"/>
           <ParentFolderIds><!-- important folder options end up here --></ParentFolderIds>
        </FindItem>
     </s:Body>
  </s:Envelope>
'''

# NOTE:
#  For normal calendar folder add:
#  <FindItem ...>
#    <ParentFolderIds>
#      <DistinguishedFolderId Id="calendar" xmlns="http://schemas.microsoft.com/exchange/services/2006/types"/>
#    </ParentFolderIds>
#  ...
#
# And with different mailbox:
#  <FindItem ...>
#    <ParentFolderIds>
#      <DistinguishedFolderId Id="calendar" xmlns="http://schemas.microsoft.com/exchange/services/2006/types">
#        <Mailbox><EmailAddress>%SMTPADDRESS%</EmailAddress></Mailbox>
#      <DistinguishedFolderId />
#    </ParentFolderIds>
# ...
#
# And with specific folders
#  <FindItem ...>
#    <ParentFolderIds>
#      <FolderId xmlns="http://schemas.microsoft.com/exchange/services/2006/types"/>
#                Id="AAMkAGVkOTNmM2I5LTkzM2EtNGE2NC05N2JjLTFhOTU2ZmJkOTIzOQAuAAAAAAB6Kun2T1UaS7SeML/WWukdAQCKlTYVK0L1S4NbyOQ4sSbQAALZU7ffAAA=" 
#                ChangeKey="AgAAABQAAAD8vWH6ONfhT7eqjuZ+hFA+AAAEQA==" />
#      <FolderId Id=... />
#    </ParentFolderIds>
# ...

def prepareQueryRequest(start, end, resolvedFolders=None):
  '''(folders contain XML objects)'''
  # construct a new FindItem request
  request = ET.fromstring(REQ_QUERY_TEMPLATE_XML)
  
  # specify date range
  calendarView = searchElement(request, 'message:CalendarView')
  calendarView.set('StartDate', str(start))
  calendarView.set('EndDate', str(end))
  
  # specify folder options
  parentFolderIds = searchElement(request, 'message:ParentFolderIds')

  # use pre-constructed (resolved) folder elements
  for element in resolvedFolders:
    parentFolderIds.append(element)

  return request

REQ_GETFOLDERS_TEMPLATE_XML = '''<?xml version="1.0" encoding="utf-8"?>
  <s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
      <s:Header>
          <h:DateTimePrecisionType xmlns:h="http://schemas.microsoft.com/exchange/services/2006/types">Seconds</h:DateTimePrecisionType>
          <h:RequestServerVersion Version="Exchange2010_SP2" xmlns:h="http://schemas.microsoft.com/exchange/services/2006/types"/>
      </s:Header>
      <s:Body>
          <FindFolder Traversal="Deep" xmlns="http://schemas.microsoft.com/exchange/services/2006/messages">
              <FolderShape>
                  <BaseShape xmlns="http://schemas.microsoft.com/exchange/services/2006/types">Default</BaseShape>
              </FolderShape>
              <ParentFolderIds><!-- important folder options end up here --></ParentFolderIds>
          </FindFolder>
      </s:Body>
  </s:Envelope>'''  

def prepareGetFoldersRequest(smtpAddress=None):
  # construct a new request type
  request = ET.fromstring(REQ_GETFOLDERS_TEMPLATE_XML)
  
  # specify folder options
  parentFolderIds = searchElement(request, 'message:ParentFolderIds')

  # use pre-constructed distinguished folder element
  parentFolderIds.append(distinguishedFolderIdElement)

  return request

# SOAP/XML operations --->


# <XML parsing convenience functions ---

# NOTE: unfortunately in this version of Jython/Python, ElementTree.find(...) does not
#       support any namespace assistance so some of the missing functionality is covered 
#       by the convenience functions below.

class DataException(Exception):
  '''A specialized exception related to data parsing this XML'''
  pass

def getElement(root, path):
  '''Strictly gets an element'''
  result = root.find(expandPath(path))
  if result == None:
    raise DataException('Missing element %s' % path)
  return result

def searchElement(root, path):
  '''Recursively searches for the first matching element'''
  
  def _searchElement(root, fullPath):
    result = root.find(fullPath)
    
    if result == None:
      for sub in root:
        result = _searchElement(sub, fullPath)
        if result != None:
          break
          
    return result
  
  return _searchElement(root, expandPath(path))

def tryGetElement(root, path):
  '''Tries to get an optional element'''
  result = root.find(expandPath(path))
  return result  

def getElementText(root, path):
  '''Strictly gets the text part of an element e.g. <e>Text</e>'''
  result = root.find(expandPath(path))
  if result == None:
    raise DataException('Missing element %s' % path)

  return result.text

def tryGetElementText(root, path, default=None):
  '''Gets the text part of an element (optionally)'''
  result = root.find(expandPath(path))
  
  if result != None:
    result = result.text
    
  if result == None:
    result = default

  return result

def getElements(root, path):
    results = root.findall(expandPath(path))
    if results == None:
        raise DataException('Missing elements %s' % path)

    return results

def tryGetAttrib(root, name):
  value = root.get(name)
  if value == None:
    return

  return value

def getAttrib(root, name):
  value = root.get(name)
  if value == None:
    raise DataException('Missing attribute %s' % name)

  return value

def expandPath(path):
  if ':' not in path:
    return path

  parts = path.split(':')
  
  return '{%s}%s' % (NS[parts[0]], parts[1])

# XML parsing convenience functions --->

# <--- simple parsing


def extractField(s):
  '''e.g. "Peace and quiet! {Power: Off}" returns {'Power': 'Off'}'''
  
  if not s.endswith('}'):
    return None, None
  
  lastIndex = s.rfind('{')
  if lastIndex < 0:
    return None, None
  
  inner = s[lastIndex+1:-1]
  
  # e.g. Power: Off
  parts = inner.split(':')
  
  if len(parts) == 1:
    return parts[0].strip(), None
  
  if len(parts) == 2:
    return parts[0].strip(), parts[1].strip()


# simple parsing --->

# <--- status, errors and debug

local_event_Trace = LocalEvent({'group': 'Status, Errors & Debug', 'order': 9999+next_seq(), 'schema': {'type': 'boolean'}})

def trace(msg):
  if local_event_Trace.getArg():
    console.info(msg)
    
def traceWarn(msg):
  if local_event_Trace.getArg():
    console.warn(msg)
    
local_event_Status = LocalEvent({'group': 'Status, Errors & Debug', 'order': 9999+next_seq(), 'schema': {'type': 'object', 'properties': {
        'level': {'type': 'integer', 'order': 1},
        'message': {'type': 'string', 'order': 2}
      }}})
    
# for status checks
lastSuccess = [0]

# roughly, the last contact  
local_event_LastContactDetect = LocalEvent({'group': 'Status, Errors & Debug', 'order': 9999+next_seq(), 'schema': {'type': 'string'}})
  
def statusCheck():
  diff = (system_clock() - lastSuccess[0])/1000.0 # (in secs)
  now = date_now()
  
  if diff > status_check_interval+15:
    previousContactValue = local_event_LastContactDetect.getArg()
    
    if previousContactValue == None:
      message = 'A successful poll has never taken place.'
      
    else:
      previousContact = date_parse(previousContactValue)
      roughDiff = (now.getMillis() - previousContact.getMillis())/1000/60
      if roughDiff < 60:
        message = 'Continual failures for approx. %s mins' % roughDiff
      elif roughDiff < (60*24):
        message = 'Continual failures since %s' % previousContact.toString('h:mm:ss a')
      else:
        message = 'Continual failures since %s' % previousContact.toString('h:mm:ss a, E d-MMM')
      
    local_event_Status.emit({'level': 2, 'message': message})
    
  else:
    local_event_LastContactDetect.emit(str(now))
    local_event_Status.emit({'level': 0, 'message': 'OK'})
    
status_check_interval = 75
status_timer = Timer(statusCheck, status_check_interval)    

# status, errors and debug --->

# <--- convenience functions

def isBlank(s):
  'Safely checks whether a string is blank. False otherwise, no exceptions.'
  if s == None:
    return True
  
  if len(s) == 0:
    return True
  
  if len(s.strip()) == 0:
    return True
  
def isEmpty(o):
  if o == None or len(o) == 0:
    return True
  
def tryGet(d, key, default=None):
  'Safely get a value from a dictionary, otherwise returning a default (if specified) or None (no exceptions).'
  if d == None:
    return default
  
  result = d.get(key)
  
  if result == None:
    return default
  
  return result

# convenience functions --->

# <--- examples

# (see examples.py for XML snippets)

# examples --->
