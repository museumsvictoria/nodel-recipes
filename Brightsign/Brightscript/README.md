# Nodel Brightsign Script and Plugin
This script works as a Brightsign Plugin, which integrates with any existing Presentation created with BA:Connected.

Go to any presentation file (or create a new one).
In Presentation Settings, under the Support Content tab, add a Script Plugin. 
Link the Nodel.BRS file and make sure its titled ‘Nodel’.

In Nodel, create a node with the provided recipe. in the config, enter the ip address.
As for the port, the Nodel.BRS script defaults to 8081, so only set the port in the node if you have changed it in the brs script.

The plugin creates a local webserver on the player with endpoints tied to functions.
| Endpoint  | Argument | Description |
| ------------- | ------------- | ------------- |
| /status  |   |  Returns json list of current state of player |
| /playback  | ?playback=play  | Plays current zone |
|  | ?playback=pause  | Pauses current Zone |
|  | ?sleep=true  | Enables power save mode, stops video and audio |
|  | ?sleep=false  | Disables power save mode |
| /mute  | ?mute=true  | Disables audio output |
|  | ?mute=false  | Enables audio output |
| /volume  | ?{number between 0 and 100}  | Sets volume to number |
| /defaults  |  | Sets player state to default, in case something gets mangled |

