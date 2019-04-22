
![Nodel Recipe Logo](http://nodel.io/media/1045/nodel-recipes.png)

Mochubecip4Lyfe!

## About
A collection of recipes for [Nodel](https://github.com/museumsvictoria/nodel), the digital control system designed for museums and galleries.

Written in Python (Jython) with the Nodel API, these recipes are used to integrate a wide variety of _nodes_ (actionable agents) into the platform, ranging from device control and content management, to monitoring and scheduling.

## Examples

#### Generated Nodes

###### Device Control
A *device node* generated from a recipe, and designed to integrate commonly used switched rack PDU devices for remote power control.

![APC Recipe Example](http://nodel.io/media/1046/apc_slim_new.png)

###### Application Wrappers
An *application node*, generated from a recipe utilising the process wrapper in Nodel's toolkit to drive a popular open-source media player.

![VLC Recipe Example](http://nodel.io/media/1047/vlc_slimexample_15.png)

###### Schedulers and Calendars ######
A snippet of a *calendar node*, generated from a recipe which retrieves and propagates events in the platform from a popular online mail and calendaring service.

![Calendar Example](http://nodel.io/media/1048/calendar_slim_preview.png)

#### Recipe Script

```Python
### Remote actions this Node requires
remote_action_PowerOnRP = RemoteAction()
remote_action_PowerOffRP = RemoteAction()

remote_action_PowerOnPC = RemoteAction()
remote_action_PowerOffPC = RemoteAction()

remote_action_PowerOnSD = RemoteAction()
remote_action_PowerOffSD = RemoteAction()

### Local actions this Node provides
def local_action_Enable(arg = None):
  """{"title":"Enable","desc":"Enable"}"""
  print 'Action Enable requested.'
  remote_action_PowerOnRP.call()
  remote_action_PowerOnPC.call()
  remote_action_PowerOnSD.call()

### Remote events this Node requires
def remote_event_Enable(arg = None):
  """{"title":"Enable","desc":"Enable","group":"General"}"""
  print 'Remote event Enable arrived.'
  local_action_Enable()
```

## Installation
Recipes are the blueprints for a node. These exist as script files contained within the node structure `../nodel/nodes/[nodename]/script.py`, and contain the node logic. They are scripted accordingly to the node type intended to be generated, with pre-made recipes available on this repository.

![Recipe Guide](http://nodel.io/media/1049/recipeplacement.jpg)

The folders created in the nodes directory will instantiate *nodes* on the Nodel platform. The folder name corresponds to the name as it appears on the web client.

There are example files generated automatically on the creation of a new folder in the nodes directory. You can access the recipes through the inline editor built into Nodel, or use your preferred text-editor.

![Editor Preview](http://nodel.io/media/1050/inlineeditor.png)

## License
* Platform - [Mozilla Public License, version 2.0](http://www.mozilla.org/MPL/2.0)
* Recipes - [MIT License](http://opensource.org/licenses/MIT)

## Credits

* [Museums Victoria](http://museumvictoria.com.au)
* [Lumicom](http://lumicom.com.au)
