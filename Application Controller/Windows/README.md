# Application Node - Windows
> Long-term application mangement utilising `Process` from the nodetoolkit.

## Setup
- For security reasons interactive services were [removed with Windows Vista](https://docs.microsoft.com/en-us/previous-versions/windows/hardware/design/dn653293(v=vs.85)). 
- Any applications launched by a nodehost *installed as a service* will not be displayed.
- You can alternatively utilise the CLI, a `.bat` file or Windows Task Scheduler to launch Nodel in a regularly logged in desktop session.

## Features
- Launch and manage an application
- Bundle child processes with the `ProcessSandbox.exe`
- Standard streams
	- stdin
	- stdout
	- stederr
- Interruption detection
- Message filtering
- CPU monitoring


## Requirements
- The `Process` feature has been available since `v2.1.1-release214`