#!/usr/bin/env python

from vlc import *
import sys
import os
import time
import termios
import tty

echo_position = False

def getch():  # getchar(), getc(stdin)  #PYCHOK flake
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

def toggle_echo_position():
    """Toggle echoing of media position"""
    global echo_position
    echo_position = not echo_position


if __name__ == '__main__':

    if sys.argv[1:] and sys.argv[1] not in ('-h', '--help'):

        ### Kick off background job to get Twitter messages

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
        player.play()

        # Some marquee examples.  Marquee requires '--sub-source marq' in the
        # Instance() call above.  See <http://www.videolan.org/doc/play-howto/en/ch04.html>
        player.video_set_marquee_int(VideoMarqueeOption.Enable, 1)
        player.video_set_marquee_int(VideoMarqueeOption.Size, 24)  # pixels
        player.video_set_marquee_int(VideoMarqueeOption.Position, Position.Bottom)
        if True:  # only one marquee can be specified
            player.video_set_marquee_int(VideoMarqueeOption.Timeout, 5000)  # millisec, 0==forever
            t = media.get_mrl()  # movie
        else:  # update marquee text periodically
            player.video_set_marquee_int(VideoMarqueeOption.Timeout, 0)  # millisec, 0==forever
            player.video_set_marquee_int(VideoMarqueeOption.Refresh, 1000)  # millisec (or sec?)
            t = 'Hello, World'
        player.video_set_marquee_string(VideoMarqueeOption.Text, str_to_bytes(t))
        time.sleep(8)
        player.video_set_marquee_string(VideoMarqueeOption.Text, str_to_bytes("Family Fued"))

        keybindings = {
            ' ': player.pause,
            '+': sec_forward,
            '-': sec_backward,
            '.': frame_forward,
            ',': frame_backward,
            'f': player.toggle_fullscreen,
            'i': print_info,
            'p': toggle_echo_position,
            'q': quit_app,
            '?': print_help,
            }


        print('Press q to quit, ? to get help.%s' % os.linesep)
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
