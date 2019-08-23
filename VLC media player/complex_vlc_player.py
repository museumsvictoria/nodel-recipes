import os
import sys
import json
import threading
from time import sleep
from vlc import *
from nodel_stdio import *


VLC_ARGS = []

class Main:
    current_position = 0
    currentClip = create_nodel_event('Current Clip', {'schema': {'type': 'string'}, 'group': 'Playing', 'order': 2})
    numClip = create_nodel_event('Clip Number', {'schema': {'type': 'number'}, 'group': 'Playing', 'order': 4})
    # Callback on loading of a new video
    def openClip_callback(self, event, player):
        media = self.player.get_media()
        name = media.get_meta(0)
        self.currentClip.emit(name)

        playlist_size = self.medialist.count()

        # Announce new video
        for item in range(0, playlist_size):
            index_item = self.medialist.item_at_index(item)
            if index_item.get_meta(0) == name:
                # Announce index number in playlist
                self.numClip.emit(item + 1)

    endReached = create_nodel_event('End Reached', {'group': 'Playlist'})
    def endReached_callback(self, event):
        print 'End Reached!'
        t = threading.Thread(target=self.play_clip, args=[1])
        t.daemon = True
        t.start()

    position = create_nodel_event('Position', {'schema': {'type': 'number'}, 'order': 98})
    def pos_callback(self, event, player):
        new_position = event.u.new_position * 100
        new_position = int(new_position)
        # Emit complete whole integer changes only
        if ((new_position > self.current_position) or (new_position is 0)):
            self.current_position = new_position
            self.position.emit(self.current_position)

    prev_elapsed = -1
    elapsed = create_nodel_event('Elapsed', {'schema': {'type': 'number'}, 'order': 99})
    def time_callback(self, event, player):
        elapsed = self.player.get_time() / 1000
        if (elapsed != self.prev_elapsed):
            self.elapsed.emit(elapsed)
            self.prev_elapsed = elapsed

    def __init__(self):

        # Create instance
        self.instance = Instance(['--video-on-top', '--high-priority'])

        # Create playlist
        self.medialist = self.instance.media_list_new()

        # Create alphabetically ordered playlist from specific location
        # tmp = 0
        # location = 'c:/content/playlist/'
        # for file in os.listdir(location):   
        #     print str(tmp) + ': ' + str(file)
        #     self.medialist.insert_media(self.instance.media_new(location + file), tmp)
        #     tmp += 1

        file = open('nodeConfig.json', 'r')
        config = json.loads(file.read())
        file.close()

        # Add the items from our Nodel parameters into our VLC medialist.
        tmp = 0
        if 'playlist' in config["paramValues"]:
            items = config["paramValues"]["playlist"]
            for item in items:
                self.medialist.insert_media(self.instance.media_new(item['arg']), tmp)
                tmp += 1

        # If the user specified as such in Nodel, we'll repeat the first clip in the playlist more-or-less indefinitely. 
        # VLC 3.0+ removed the support for a negative value, i.e. 'input-repeat=-1'
        teaser_behaviour = False
        if 'teaser' in config["paramValues"]:
            teaser = config["paramValues"]["teaser"]
            if self.medialist.count() is 1 or teaser is True:
                self.medialist.item_at_index(0).add_option('input-repeat=65535')
                teaser_behaviour = True

        # If the user specified as such in Nodel, we'll toggle all clips to pause on the final frame using an exisiting flag.
        if 'hold' in config["paramValues"]:
            hold_behaviour = config["paramValues"]["hold"]
            if hold_behaviour == True:
                print 'Hold Enabled.'
                starting_value = 1 if teaser_behaviour == True else 0
                for x in range(starting_value, self.medialist.count()):
                    self.medialist.item_at_index(x).add_option('play-and-pause')


        # Create two players
        # The playlist player manages multiple videos
        # The regular player is going to have specific events attached to it
        self.playlist = self.instance.media_list_player_new()
        self.player = self.instance.media_player_new()

        # Assign the regular player (event handler) to our playlist player
        self.playlist.set_media_player(self.player)
        self.playlist.set_media_list(self.medialist)

        # Attach EOF and position events to our player. These events do not exist for the playlist player.
        self.player_event_manager = self.player.event_manager()

        self.player_event_manager.event_attach(EventType.MediaPlayerPositionChanged, self.pos_callback, self.player)
        self.player_event_manager.event_attach(EventType.MediaPlayerTimeChanged, self.time_callback, self.player)
        self.player_event_manager.event_attach(EventType.MediaPlayerOpening, self.openClip_callback, self.player)

        if teaser_behaviour:
            print 'Teaser Enabled.'
            self.player_event_manager.event_attach(EventType.MediaPlayerEndReached, self.endReached_callback)

        # Prepare the player for action
        self.playlist.set_playback_mode(1)
        self.player.toggle_fullscreen()
        self.play_clip(1)

    # Request playback of specific video in playlist
    @nodel_action({'schema': {'type': 'integer'},"title":"PlayClip","group":"Playlist","order":9})
    def play_clip(self, num):
        print 'Playclip: %s' % (num)
        self.playlist.play_item_at_index(num - 1)
        #self.player.video_set_spu(self.subtitle_track)
        self.current_position = 0

    @nodel_action({"title":"Stop","group":"Playback","Caution":"Are you sure?","order":1})
    def stop(self):
        self.player.stop()

    @nodel_action({"title":"Pause","group":"Playback","order":1})
    def pause(self):
        print 'Pause!'
        self.player.pause()

    @nodel_action({"title":"Resume","group":"Playback","order":1})
    def resume(self):
        self.player.play()

    @nodel_action({"title":"SetPosition","schema":{"title":"Drag slider to adjust position.","type":"integer","format":"range","min": 0, "max": 100,"required":"true"},"group":"Playback","order":0})
    def set_position(self, num):
        pos = float(num) / 100
        self.player.set_position(pos)
        self.current_position = pos

    # Populate events with information about playback engine
    @nodel_action({"title":"Config","group":"Information","order":5})
    def pop_config(self):
        self.get_config()

    @nodel_action({"title":"Version","group":"Information","order":5})
    def pop_version(self):
        self.get_version()
        #self.get_playlist()

    config_meta = {'group': 'Info', 'order': 8, 'schema': {'type': 'object', 'title': 'Config', 'properties': {
      'rate': {'type': 'string', 'order': 1, 'title': 'Rate'},
      'size': {'type': 'string', 'order': 2, 'title': 'Video size'},
      'scale': {'type': 'string', 'order': 3, 'title': 'Scale'},
      'aspect': {'type': 'string', 'order': 4, 'title': 'Aspect ratio'}, }}}
    config = create_nodel_event('Config', config_meta)
    def get_config(self):
        """Print information about the media"""
        player = self.player
        try:
            player = self.player
            arg = {'rate': '%s' % player.get_rate(),
                   'size': '%s' % str(player.video_get_size(0)),
                   'scale': '%s' % player.video_get_scale(),
                   'aspect': '%s' % player.video_get_aspect_ratio() }
            self.config.emit(arg)
        except Exception:
            print('Error: %s' % sys.exc_info()[1])

    version_meta = {'group': 'Info', 'order': 9, 'schema': {'type': 'object', 'title': 'Version', 'properties': {
      'build': {'type': 'string', 'order': 1, 'title': 'Build date'},
      'version': {'type': 'string', 'order': 2, 'title': 'LibVLC version'}, }}}
    version = create_nodel_event('Version', version_meta)
    def get_version(self):
        """Print version of this vlc.py and of the libvlc"""
        try:
            arg = {'build': '%s' % build_date,
                   'version': '%s' % '%s' % bytes_to_str(libvlc_get_version()) }
            self.version.emit(arg)
        except Exception:
            print('Error: %s' % sys.exc_info()[1])

    # PENDING: Playlist information announcement
    #playlist_meta = {'group': 'Info', 'order': 9, 'schema': {'type': 'object', 'title': 'Playlist', 'properties': {}, }}
    #playlist = create_nodel_event('Playlist', playlist_meta)
    #def get_playlist(self):
    #    """Print current playlist information"""
    #    try:
    #        print self.medialist.count()
    #        self.playlist.emit()
    #    except Exception:
    #        print('Error: %s' % sys.exc_info()[1])

    def quit_app(self):
        """Stop and exit"""
        sys.exit(0)

main = Main()
register_instance_node(main)

if __name__ == '__main__':
    start_nodel_channel()
