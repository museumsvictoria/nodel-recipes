## Nodel Process Recipe 0.4 (Jan 2017)
> Simple process mangement tool utilising Nodel's Java toolkit.
> Intended sandboxing for Windows processes using job objects. 

### Setup
- Nodel must be running on the dekstop, and not as a service, as Windows will prevent access to the GUI layer. You can utilise cmd.exe, a batch file, or task scheduler to automate the process.
- **Do not attempt to revive** will prevent Nodel from attempting to restart a closed process.

### Changes
**0.3 - 0.4**
- Implemented exclusive and inclusive message filtering.

**0.2 - 0.3**
- Minor bug fix with lambda arguments.
- Commented out process.stop() on auto-launch.

**0.1 - 0.2**
- OS Testing.
- Basic process running with state events.
- Additional arguments.
- Keep alive disable not yet implemented.

**0.0 - 0.1**
- Basic layout forming. Non-functional.

### Requirements
- [Nodel] v2.1.1-release214

 [Nodel]: <https://github.com/museumvictoria/nodel.git>
 [VLC]: <https://www.videolan.org/vlc>
 [VLC Python Bindings]: <https://github.com/oaubert/python-vlc>

### Issues
- No support for OSX:
[Timestamp] (process) java.io.IOException: Cannot run program "/Applications/Notes.app" (in directory "./nodes/node"): error=13, Permission denied
- No support for Ubuntu:
[Timestamp] (process) java.io.IOException: Cannot run program "/usr/share/applications/libreoffice-writer.desktop" (in directory "./nodes/node"): error=13, Permission denied