# App Launcher node
This node is used to rapidly control the state of long running application (launch and kill).

## Features
1. application path, arguments and working directory can be specified
2. signals show state of application ('On' running, 'Off' not running)
3. application feedback (standard-out) is piped to node's console
4. on disruption, event is reported and application is recycled
5. OS-level functions are used to ensure *all* child processes are cleaned up
6. FUTURE UPDATE: further sandboxing restrictions of the process may be added e.g. memory or CPU restrictions

### Notes & Restrictions
- applications launched by a nodehost when *installed as a service* will not be displayed
- ensure *installed as user* instead
- not suitable for macOS applications
- requires v2.1.1-release365+
- FUTURE UPDATE: support for macOS

