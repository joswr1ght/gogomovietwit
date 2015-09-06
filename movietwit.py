#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import time
import termios
import tty
import socket
import threading
import tweepy
import json
import string
import re
import HTMLParser
from tweepy import OAuthHandler
from tweepy import Stream
from tweepy.streaming import StreamListener
from PIL import ImageFont
from vlc import *

try:
    import config
except ImportError:
    sys.stderr.write("You need to configure the config.py file. Copy config.py.sample to config.py, then edit.\n")
    sys.exit(1)

threads = []

# Yeah, predictable world writeable filename location. Pfft. Whatevs.
sockfile = '/tmp/gogomovietwit'
FONTSIZE=18


class GogoMovieTwitListener(StreamListener):

    def __init__(self, font, fontsize, videowidth):
            self.font = ImageFont.truetype(font, fontsize)
            self.vidw = videowidth
 
    def on_data(self, data):
        try:
            #print "\n" + "-"*80
            print data

            tweet=json.loads(data)

            # HTML parse ASCII only
            text = HTMLParser.HTMLParser().unescape(tweet["text"].encode('ascii', 'ignore'))
            # Remove hashtag, case insensitive (matching Tweepy stream)
            hashtag = re.compile(re.escape(config.hashtag), re.IGNORECASE)
            text = re.sub(hashtag, "", text)
            # Remove URLs
            text = re.sub(re.compile(r'((https?://[^\s<>"]+|www\.[^\s<>"]+))',re.DOTALL), "", text)
            # Remove newlines
            text = text.replace("\n", '')

            # Skip RT's if configured to do so
            if config.skiprt:
                if tweet["retweeted"]:
                    return False
                if "RT" in re.split("(?:(?:[^a-zA-Z]+')|(?:'[^a-zA-Z]+))|(?:[^a-zA-Z']+)", text):
                    return False

            name = tweet["user"]["screen_name"]

            # Using known font and font size, wrap text to fix on screen
            #text = wrap_text(text)

            if config.anonmode:
                sendmessage("%s"%(text))
            else:
                sendmessage("%s: %s"%(name, text))
            time.sleep(5)

            return True

        except Exception, e:
            print('Error on_data: %s' % sys.exc_info()[1])

        return True
 
    def on_error(self, status):
        print "Stream error:",
        print status
        return True

    def on_disconnect(self, notice):
        """Called when twitter sends a disconnect notice
    
        Disconnect codes are listed here:
        https://dev.twitter.com/docs/streaming-apis/messages#Disconnect_messages_disconnect
        """
        return

    def wrap_text(self, text): 
       words=text.split(" ")
       start = stop = 0
       while stop < len(words):
           pass




# Sends a message to the given socket
def sendmessage(message):
    s = socket.socket(socket.AF_UNIX)
    s.settimeout(1)
    s.connect(sockfile)
    s.send(message)
    s.close()


def getch():
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
    return ch

def mspf():
    """Milliseconds per frame."""
    return int(1000 // (player.get_fps() or 25))

def print_version():
    """Print libvlc version"""
    try:
        print('Build date: %s (%#x)' % (build_date, hex_version()))
        print('LibVLC version: %s (%#x)' % (bytes_to_str(libvlc_get_version()), libvlc_hex_version()))
        print('LibVLC compiler: %s' % bytes_to_str(libvlc_get_compiler()))
        if plugin_path:
            print('Plugin path: %s' % plugin_path)
    except:
        print('Error: %s' % sys.exc_info()[1])

def print_info():
    """Print information about the media"""
    try:
        print_version()
        media = player.get_media()
        print('State: %s' % player.get_state())
        print('Media: %s' % bytes_to_str(media.get_mrl()))
        print('Track: %s/%s' % (player.video_get_track(), player.video_get_track_count()))
        print('Current time: %s/%s' % (player.get_time(), media.get_duration()))
        print('Position: %s' % player.get_position())
        print('FPS: %s (%d ms)' % (player.get_fps(), mspf()))
        print('Rate: %s' % player.get_rate())
        print('Video size: %s' % str(player.video_get_size(0)))  # num=0
        print('Scale: %s' % player.video_get_scale())
        print('Aspect ratio: %s' % player.video_get_aspect_ratio())
       #print('Window:' % player.get_hwnd()
    except Exception:
        print('Error: %s' % sys.exc_info()[1])

def sec_forward():
    """Go forward one sec"""
    player.set_time(player.get_time() + 1000)

def sec_backward():
    """Go backward one sec"""
    player.set_time(player.get_time() - 1000)

def frame_forward():
    """Go forward one frame"""
    player.set_time(player.get_time() + mspf())

def frame_backward():
    """Go backward one frame"""
    player.set_time(player.get_time() - mspf())

def print_help():
    """Print help"""
    print('Single-character commands:')
    for k, m in sorted(keybindings.items()):
        m = (m.__doc__ or m.__name__).splitlines()[0]
        print('  %s: %s.' % (k, m.rstrip('.')))
    print('0-9: go to that fraction of the movie')

def quit_app():
    """Stop and exit"""
    sys.exit(0)


def serverproc(player):
        # Remove the socket file if it already exists
        if os.path.exists(sockfile):
            os.remove(sockfile)

        #print "Opening socket..."
        server = socket.socket( socket.AF_UNIX, socket.SOCK_STREAM )
        server.bind(sockfile)
        server.listen(5)
        
        #print "Listening..."
        while True:
            conn, addr = server.accept()
            #print 'Accepted connection'

            while True:
                data = conn.recv(1024)
                if not data:
                    break
                else:
                    #print "-" * 20
                    #print data
                    # Write overlay marquee content
                    player.video_set_marquee_string(VideoMarqueeOption.Text, str_to_bytes(data))

def clientproc():
    ### Twitter parsing
    auth = OAuthHandler(config.consumer_key, config.consumer_secret)
    auth.set_access_token(config.access_token, config.access_secret)
    while True:
        vidwidth=720 # TODO: Figure out dynamic movie width
        twitter_stream = Stream(auth, GogoMovieTwitListener("FreeSans.ttf", FONTSIZE, vidwidth), timeout=60)

        try:
            twitter_stream.filter(track=[config.hashtag])
        except Exception, e:
            print "Error:"
            print e.__doc__
            print e.message
            print "Restarting stream."
        time.sleep(3)



if __name__ == '__main__':

    if sys.argv[1:] and sys.argv[1] not in ('-h', '--help'):

        movie = os.path.expanduser(sys.argv[1])
        if not os.access(movie, os.R_OK):
            print('Error: %s file not readable' % movie)
            sys.exit(1)

        instance = Instance("--sub-source marq")
        try:
            media = instance.media_new(movie)
        except NameError:
            print('NameError: %s (%s vs LibVLC %s)' % (sys.exc_info()[1],
                                                       __version__,
                                                       libvlc_get_version()))
            sys.exit(1)

        player = instance.media_player_new()
        player.set_media(media)

        ### Kick off background job to handle server messages
        t = threading.Thread(target=serverproc, args=(player,))
        threads.append(t)
        t.daemon=True
        t.start()

        ### Kick off background job to get Twitter messages
        t = threading.Thread(target=clientproc)
        threads.append(t)
        t.daemon=True
        t.start()

        player.video_set_marquee_int(VideoMarqueeOption.Enable, 1)
        player.video_set_marquee_int(VideoMarqueeOption.Size, FONTSIZE)  # pixels
        player.video_set_marquee_int(VideoMarqueeOption.Position, Position.Bottom+Position.Left)
        player.video_set_marquee_int(VideoMarqueeOption.Timeout, 5000)  # millisec, 0==forever
        player.video_set_marquee_int(VideoMarqueeOption.Refresh, 1000)  # millisec (or sec?)

        keybindings = {
            ' ': player.pause,
            '+': sec_forward,
            '-': sec_backward,
            '.': frame_forward,
            ',': frame_backward,
            'f': player.toggle_fullscreen,
            'i': print_info,
            'q': quit_app,
            '?': print_help,
            'h': print_help,
            }

        print_help()
        # Start playing the video
        player.play()
        sendmessage('gogomovietwit - watching hashtag %s'%config.hashtag)

        while True:
            k = getch()
            print('> %s' % k)
            if k in keybindings:
                keybindings[k]()
            elif k.isdigit():
                 # jump to fraction of the movie.
                player.set_position(float('0.'+k))
            ### Check IPC for messages to display next

    else:
        print('Usage: %s <movie_filename>' % sys.argv[0])
        print('Once launched, type ? for help.')
        print('')
