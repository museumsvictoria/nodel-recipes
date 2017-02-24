## Nodel VLC Recipe 1.5 (Jan 2017)
> Simple single instance Nodel channel using stdio.
> Integration for software-playback utilising VLC Python API: https://wiki.videolan.org/python_bindings

### Setup
- Nodel must be running on the dekstop, and not as a service, as Windows will prevent access to the GUI layer. You can utilise cmd.exe, a batch file, or task scheduler to automate the process.
- **Parameters** allow the specification of Python and the building of a playlist. On Windows the script will attempt to auto-detect Python's location.
- **Enable teaser** will loop the first video in the playlist indefinitely, returning to this clip on the completition of any other video.

### Changes
**1.4.6 - 1.5**
- General house-keeping inline for stable release.
- Removal of Museums Victoria specific clip index.

**1.4.6 - 1.4.7**
- Removed subtitle support in effort to resolve lagged playback occuring occasionally.

**1.4.5 - 1.4.6**
- Bug fix and reworked teaser/looping functionality, removing the need for a playlist callback.
- Other minor fixes, high priority mode, video always on top.

**1.4.4 - 1.4.5**
- Removed a lot of extraneous functions.

**1.4.3 - 1.4.4**
- Reduced reporting rate of elapsed time.

**1.4.2 - 1.4.3**
- Listing version and config information automated.
- Refactored 'playlist' parameter to 'content'.
- Description of PlayClip actions derived from content filenames.

**1.4.1 - 1.4.2**
- Reverted to original teaser loop behaviour ('input-repeat=-1') in an attempt to alleviate crashes.
- Previous behaviour involved videos calling themselves from a seperate thread in order to loop.
- Reversed teaser parameter to be opt-in instead of opt-out.
- Removed 'Toggle Loop' action. This is now handled in in the VLC wrapper.

**1.4 - 1.4.1**
- Fixed bug with EOF callback caused by removal of PlayMain.
- Minor clean up of console reporting.

**1.3 - 1.4**
- Removed PlayMain and reworked playlist index to run from 1 - n
- Transitioning away from (0, 1, 2, 3, 4) being Teaser, Clip01, Clip02 to a more generic index.
- Implemented elapsed time in seconds.

### Requirements
- [Nodel] v2.1.1-release196
- [VLC] 2.1.4
- [VLC Python Bindings] are provided alongside the recipe

### Todos
- GUI supported playlist creation.
- Playlist items displayed as signals.
- Selectable audio tracks.

### Known issues
- Playlist injection unable to decode non-standard UTF-8 characters: å é í ò ü
- Guarantee current Dynamic Exhibit recipe is out-of-date for these changes.
- [04372cb4] direct3d vout display error: SetThumbNailClip failed caused by running without explorer.exe

 [Nodel]: <https://github.com/museumvictoria/nodel.git>
 [VLC]: <https://www.videolan.org/vlc>
 [VLC Python Bindings]: <https://github.com/oaubert/python-vlc>