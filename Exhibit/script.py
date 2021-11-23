'''Exhibit Node'''


### Libraries required by this Node
from time import time
from random import randint


### Parameters used by this Node
timeout = 0
param_duration = Parameter('{"title":"Duration (seconds)","schema":{"type":"integer"}}')


### Functions used by this Node
def play_random_clip():
  x = randint(0,1)
  if x is 1:
    local_action_PlayClip01()
  else:
    local_action_PlayClip02()


### Local actions this Node provides
class Power:
  """Control enable and disable actions"""

  def enable(arg = None):
    print 'Action Enable requested.'
    remote_action_PowerOnRP.call()

  def disable(arg = None):
    print 'Action Disable requested.'
    remote_action_PowerOffRP.call()

class Mute:
  """Control muting actions"""

  def muteOn(arg = None):
    print 'Action MuteOn requested.'
    remote_action_MuteOnSD.call()

  def muteOff(arg = None):
    print 'Action MuteOff requested.'
    remote_action_MuteOffSD.call()
  
def local_action_PlayClip01(arg = None):
  """{"title":"PlayClip01","desc":"PlayClip01","group":"Content"}"""
  print 'Action PlayClip01 requested.'
  remote_action_PlayClip01.call()
  
def local_action_PlayClip02(arg = None):
  """{"title":"PlayClip02","desc":"PlayClip02","group":"Content"}"""
  print 'Action PlayClip02 requested.'
  remote_action_PlayClip02.call()


### Remote actions this Node requires
remote_action_MuteOffSD = RemoteAction()
remote_action_MuteOnSD = RemoteAction()

remote_action_PlayClip01 = RemoteAction()
remote_action_PlayClip02 = RemoteAction()

remote_action_PowerOnRP = RemoteAction()
remote_action_PowerOffRP = RemoteAction()


### Remote events this Node requires
def remote_event_Triggered(arg = None):
  """{"title":"Triggered","desc":"Triggered"}"""
  print 'Remote event Triggered arrived.'
  global timeout
  if timeout < time():
    timeout = time() + param_duration
    play_random_clip()


### Related nodes to aggregate and monitor
monitor_our_status = ['MM-FGRP01','MM-FGIO01']
monitor_our_power = ['MM-FGRP01']


### Main
def main(arg = None):
  # Start your script here.
  print 'Nodel script started.'