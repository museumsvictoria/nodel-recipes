# Exhibit Node

An extensible node, designed to bind together multiple device nodes in a common-sense fashion, while including the signal aggregation of the group node.

If your use case doesn't require custom scriptings, including timings, or responding to remote events, then the **group node** is recommended as an alternative.

## Overview

The `custom.py` file will be injected at load, and generate identical actions/events to the group node.

##### Actions
- Muting
- Power
- Status Suppression
- Power

##### Signals
- Status
- Members' Power
- Members' Status
- Status Suppression

The `script.py` is formatted to encourage user customisation through basic scripting. 

![scripting_example](https://user-images.githubusercontent.com/9277107/53773179-631e5d00-3f3d-11e9-9865-8f03fb32a81e.gif)

## `script.py` Explanation

###  Libraries required by this Node
Any supplementary libraries go here.
</br> *e.g.* `from time import sleep`.

###  Parameters used by this Node
Any extraneous variables not captured by events, or for supplementary parameters.
</br>*formatting:* `param_name = Parameter({schema})`

###  Functions used by this Node
Additional functions written by the user to be utilised alongside the Nodel toolkit functions.

### Local actions this Node provides
Two classes *(Power and Mute)* containing default functions tied to the local *Power* and *Muting* actions respectively.

``` python
class Power:
  """Control enable and disable actions"""

  # called on a Power{'On'}
  def enable(arg = None):
    print 'Action Enable requested.'
    remote_action_PowerOnRP.call()

  # called on a Power{'Off'}  
  def disable(arg = None):
    print 'Action Disable requested.'
    remote_action_PowerOffRP.call()
```

![poweron_actionenable](https://user-images.githubusercontent.com/9277107/53775203-a67cc980-3f45-11e9-8e2f-1fca8845293a.gif)

### Remote actions this Node provides
Declarations of all the *remote actions* to be used by this Node.

The format is `remote_action_Name = RemoteAction()`

```python 
### Example remote actions
remote_action_MuteOffSD = RemoteAction()
remote_action_MuteOnSD = RemoteAction()
```

The remote actions declared here will appear as bindings in the **Advanced mode** section of the node. Then the user can specify which local action, from which node, should be triggered when this remote action is called.

![binding_example](https://user-images.githubusercontent.com/9277107/53775385-7550c900-3f46-11e9-88fb-07f71988982a.jpg)

### Remote events this Node requires
Declarations of all the *remote events* to be used by this Node.

The format is:

```python
def remote_event_Example(arg = None):
  """{"title":"Example","desc":"Example"}"""
  print 'Remote event Example arrived.'
  remote_action_PlayClip01.call()
```

As above, the remote events will generate bindings for the user to declare a relationship with another node.

### Related nodes to aggregate and monitor
There are two lists `monitor_our_status` and `monitor_our_power` which are to be populated with the names of nodes (or a meaningful alias) meant to be monitored.

This replaces the *members* facility of the group node.

The items listed here will generate bindings as when directly declaring *remote events* or *remote actions*, allowing the user to specify the nodes which require status aggregation.