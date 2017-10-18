'''This Nodes controls / monitors some of the low level functions of the Nodel Framework'''

from org.nodel.logging import Level
from org.nodel.logging.slf4j import SimpleLoggerFactory
from org.nodel.logging.slf4j import SimpleLogger

LEVEL_SCHEMA = ['TRACE', 'DEBUG', 'INFO', 'WARN', 'ERROR']

def main():
  for logger in SimpleLoggerFactory.shared().getLoggers():
    bindLogger(logger)
    
  bindStdErrSink()
  bindNodelSink()
  
def bindLogger(logger):
  name = logger.getName()
  event = Event('Logger %s' % name, {'title': name, 'group': 'Loggers', 'order': next_seq(), 'schema': {'type': 'string', 'enum': LEVEL_SCHEMA}})
  event.emitIfDifferent(str(logger.getLevel()))
  
  def handler(level):
    logger.setLevel(Level.valueOf(level))
    event.emit(level)
    
  action = Action('Logger %s' % name, handler, {'title': name, 'group': 'Loggers', 'order': next_seq(), 'schema': {'type': 'string', 'enum': LEVEL_SCHEMA}})
  
def bindStdErrSink():
  event = Event('Console Sink', {'title': 'Console', 'group': 'Log sinks', 'order': next_seq(), 'schema': {'type': 'string', 'enum': LEVEL_SCHEMA}})
  
  def handler(level):
    SimpleLogger.setStdErrLevel(Level.valueOf(level))
    event.emit(level)
    
  action = Action('Console Sink', handler, {'title': 'Console', 'group': 'Log sinks', 'order': next_seq(), 'schema': {'type': 'string', 'enum': LEVEL_SCHEMA}})
  
  current = str(SimpleLogger.getStdErrLevel())
  
  if current != event.getArg():
    handler(current)

def bindNodelSink():
  event = Event('Nodel Sink', {'title': 'Nodel', 'group': 'Log sinks', 'order': next_seq(), 'schema': {'type': 'string', 'enum': LEVEL_SCHEMA}})
  
  def handler(level):
    SimpleLogger.setNodelLevel(Level.valueOf(level))
    event.emit(level)
    
  action = Action('Nodel Sink', handler, {'title': 'Nodel', 'group': 'Log sinks', 'order': next_seq(), 'schema': {'type': 'string', 'enum': LEVEL_SCHEMA}})
  
  current = str(SimpleLogger.getNodelLevel())
  
  if current != event.getArg():
    handler(current)
    