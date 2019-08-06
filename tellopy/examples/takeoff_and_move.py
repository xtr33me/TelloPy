import time
from time import sleep
import sys
import tellopy
import pygame
import pygame.key
import pygame.locals
import os
import datetime
from subprocess import Popen, PIPE

prev_flight_data = None
video_player = None
video_recorder = None
font = None
wid = None
date_fmt = '%Y-%m-%d_%H%M%S'

FORWARD_SPEED = 20
COUNTER_SPEED = 1
TURN_SPEED = 30
COUNTER_SLEEP = 2

controls = {
    'w': 'forward',
    's': 'backward',
    'a': 'left',
    'd': 'right',
    'space': 'up',
    'left shift': 'down',
    'right shift': 'down',
    'q': 'counter_clockwise',
    'e': 'clockwise',
    # arrow keys for fast turns and altitude adjustments
    'left': lambda drone, speed: drone.counter_clockwise(speed*2),
    'right': lambda drone, speed: drone.clockwise(speed*2),
    'up': lambda drone, speed: drone.up(speed*2),
    'down': lambda drone, speed: drone.down(speed*2),
    'tab': lambda drone, speed: drone.takeoff(),
    'backspace': lambda drone, speed: drone.land(),
    #'p': palm_land,
    #'r': toggle_recording,
    #'z': toggle_zoom,
    #'enter': take_picture,
    #'return': take_picture,
}

def handler(event, sender, data, **args):
    drone = sender
    if event is drone.EVENT_FLIGHT_DATA:
        print(data)

def MoveForward(drone, time):
    drone.forward(FORWARD_SPEED)
    sleep(time)
    drone.backward(COUNTER_SPEED)
    sleep(COUNTER_SLEEP)

def CounterClockwiseTurn(drone, time):
    drone.counter_clockwise(30)
    sleep(time)
    drone.clockwise(COUNTER_SPEED)
    sleep(COUNTER_SLEEP)


def test():
    drone = tellopy.Tello()
    try:
        drone.subscribe(drone.EVENT_FLIGHT_DATA, handler)##

        drone.connect()
        drone.wait_for_connection(60.0)
        drone.takeoff()
        sleep(5)

        MoveForward(drone, 17)
        CounterClockwiseTurn(drone, 5)
        MoveForward(drone, 8.5)
        CounterClockwiseTurn(drone, 5)
        MoveForward(drone, 17.3)
        CounterClockwiseTurn(drone, 5)
        MoveForward(drone, 8.5)
        
        drone.land()
        sleep(5)
    except Exception as ex:
        print(ex)
    finally:
        drone.quit()

def videoFrameHandler(event, sender, data):
    global video_player
    global video_recorder
    if video_player is None:
        cmd = [ 'mplayer', '-fps', '35', '-really-quiet' ]
        if wid is not None:
            cmd = cmd + [ '-wid', str(wid) ]
        video_player = Popen(cmd + ['-'], stdin=PIPE)

    try:
        video_player.stdin.write(data)
    except IOError as err:
        status_print(str(err))
        video_player = None

    try:
        if video_recorder:
            video_recorder.stdin.write(data)
    except IOError as err:
        status_print(str(err))
        video_recorder = None

def handleFileReceived(event, sender, data):
    global date_fmt
    # Create a file in ~/Pictures/ to receive image data from the drone.
    path = '%s/Pictures/tello-%s.jpeg' % (
        os.getenv('HOME'),
        datetime.datetime.now().strftime('%Y-%m-%d_%H%M%S'))
    with open(path, 'wb') as fd:
        fd.write(data)
    #status_print('Saved photo to %s' % path)

def main():
    pygame.init()
    pygame.display.init()
    pygame.display.set_mode((1280, 720))
    pygame.font.init()

    #global font
    font = pygame.font.SysFont("dejavusansmono", 32)

    #global wid
    if 'window' in pygame.display.get_wm_info():
        wid = pygame.display.get_wm_info()['window']
    print("Tello video WID:", wid)


    drone = tellopy.Tello()
    drone.connect()
    drone.start_video()
    drone.subscribe(drone.EVENT_FLIGHT_DATA, handler)
    drone.subscribe(drone.EVENT_VIDEO_FRAME, videoFrameHandler)
    #drone.subscribe(drone.EVENT_FILE_RECEIVED, handleFileReceived)
    speed = 30

    try:
        while 1:
            time.sleep(0.01)  # loop with pygame.event.get() is too mush tight w/o some sleep
            for e in pygame.event.get():
                # WASD for movement
                if e.type == pygame.locals.KEYDOWN:
                    print('+' + pygame.key.name(e.key))
                    keyname = pygame.key.name(e.key)
                    if keyname == 'escape':
                        drone.quit()
                        exit(0)
                    if keyname in controls:
                        key_handler = controls[keyname]
                        if type(key_handler) == str:
                            getattr(drone, key_handler)(speed)
                        else:
                            key_handler(drone, speed)

                elif e.type == pygame.locals.KEYUP:
                    print('-' + pygame.key.name(e.key))
                    keyname = pygame.key.name(e.key)
                    if keyname in controls:
                        key_handler = controls[keyname]
                        if type(key_handler) == str:
                            getattr(drone, key_handler)(0)
                        else:
                            key_handler(drone, 0)
    except e:
        print(str(e))
    finally:
        print('Shutting down connection to drone...')
        #if video_recorder:
        #    toggle_recording(drone, 1)
        drone.quit()
        exit(1)

if __name__ == '__main__':
    #main()
    test()


#Help on package tellopy:

#NAME
#    tellopy - DJI Tello controller

#DESCRIPTION
#    This is a python package which controlls DJI toy drone 'Tello'. The major portion of #the source
#    code was ported from the driver of GOBOT project. Please refer their blog post at
#    https://gobot.io/blog/2018/04/20/hello-tello-hacking-drones-with-go

#PACKAGE CONTENTS
#    _internal (package)
#    examples (package)

#CLASSES
#    builtins.object
#        tellopy._internal.tello.Tello
    
#    class Tello(builtins.object)
#     |  Methods defined here:
#     |  
#     |  __init__(self, port=9000)
#     |      Initialize self.  See help(type(self)) for accurate signature.
#     |  
#     |  backward(self, val)
#     |      Backward tells the drone to go in reverse. Pass in an int from 0-100.
#     |  
#     |  clockwise(self, val)
#     |      Clockwise tells the drone to rotate in a clockwise direction.
#     |      Pass in an int from 0-100.
#     |  
#     |  connect(self)
#     |      Connect is used to send the initial connection request to the drone.
#     |  
#     |  counter_clockwise(self, val)
#     |      CounterClockwise tells the drone to rotate in a counter-clockwise direction.
#     |      Pass in an int from 0-100.
#     |  
#     |  down(self, val)
#     |      Down tells the drone to descend. Pass in an int from 0-100.
#     |  
#     |  flip_back(self)
#     |      flip_back tells the drone to perform a backwards flip
#     |  
#     |  flip_backleft(self)
#     |      flip_backleft tells the drone to perform a backwards left flip
#     |  
#     |  flip_backright(self)
#     |      flip_backleft tells the drone to perform a backwards right flip
#     |  
#     |  flip_forward(self)
#     |      flip_forward tells the drone to perform a forwards flip
#     |  
#     |  flip_forwardleft(self)
#     |      flip_forwardleft tells the drone to perform a forwards left flip
#     |  
#     |  flip_forwardright(self)
#     |      flip_forwardright tells the drone to perform a forwards right flip
#     |  
#     |  flip_left(self)
#     |      flip_left tells the drone to perform a left flip
#     |  
#     |  flip_right(self)
#     |      flip_right tells the drone to perform a right flip
#     |  
#     |  forward(self, val)
#     |      Forward tells the drone to go forward. Pass in an int from 0-100.
#     |  
#     |  get_video_stream(self)
#     |      Get_video_stream is used to prepare buffer object which receive video data #from the drone.
#     |  
#     |  land(self)
#     |      Land tells the drone to come in for landing.
#     |  
#     |  left(self, val)
#     |      Left tells the drone to go left. Pass in an int from 0-100.
#     |  
#     |  palm_land(self)
#     |      Tells the drone to wait for a hand underneath it and then land.
#     |  
#     |  quit(self)
#     |      Quit stops the internal threads.
#     |  
#     |  recv_file_data(self, data)
#     |  
#     |  right(self, val)
#     |      Right tells the drone to go right. Pass in an int from 0-100.
#     |  
#     |  send_packet(self, pkt)
#     |      Send_packet is used to send a command packet to the drone.
#     |  
#     |  send_packet_data(self, command, type=104, payload=[])
#     |  
#     |  set_exposure(self, level)
#     |      Set_exposure sets the drone camera exposure level. Valid levels are 0, 1, #and 2.
#     |  
#     |  set_loglevel(self, level)
#     |      Set_loglevel controls the output messages. Valid levels are
#     |      LOG_ERROR, LOG_WARN, LOG_INFO, LOG_DEBUG and LOG_ALL.
#     |
#     |  
#     |  set_pitch(self, pitch)
#     |      Set_pitch controls the forward and backward tilt of the drone.
#     |      Pass in an int from -1.0 ~ 1.0. (positive value will make the drone move #forward)
#     |  
#     |  set_roll(self, roll)
#     |      Set_roll controls the the side to side tilt of the drone.
#     |      Pass in an int from -1.0 ~ 1.0. (positive value will make the drone move to #the right)
#     |  
#     |  set_throttle(self, throttle)
#     |      Set_throttle controls the vertical up and down motion of the drone.
#     |      Pass in an int from -1.0 ~ 1.0. (positive value means upward)
#     |  
#     |  set_video_encoder_rate(self, rate)
#     |      Set_video_encoder_rate sets the drone video encoder rate.
#     |  
#     |  set_video_mode(self, zoom=False)
#     |      Tell the drone whether to capture 960x720 4:3 video, or 1280x720 16:9 zoomed #video.
#     |      4:3 has a wider field of view (both vertically and horizontally), 16:9 is #crisper.
#     |  
#     |  set_yaw(self, yaw)
#     |      Set_yaw controls the left and right rotation of the drone.
#     |      Pass in an int from -1.0 ~ 1.0. (positive value will make the drone turn to #the right)
#     |  
#     |  start_video(self)
#     |      Start_video tells the drone to send start info (SPS/PPS) for video stream.
#     |  
#     |  subscribe(self, signal, handler)
#     |      Subscribe a event such as EVENT_CONNECTED, EVENT_FLIGHT_DATA, #EVENT_VIDEO_FRAME and so on.
#     |  
#     |  take_picture(self)
#     |  
#     |  takeoff(self)
#     |      Takeoff tells the drones to liftoff and start flying.
#     |  
#     |  up(self, val)
#     |      Up tells the drone to ascend. Pass in an int from 0-100.
#     |  
#     |  wait_for_connection(self, timeout=None)
#     |      Wait_for_connection will block until the connection is established.
#     |  
#     |  ----------------------------------------------------------------------
#     |  Data descriptors defined here:
#     |  
#     |  __dict__
#     |      dictionary for instance variables (if defined)
#     |  
#     |  __weakref__
#     |      list of weak references to the object (if defined)
#     |  ----------------------------------------------------------------------
#     |  Data and other attributes defined here:
#     |  
#     |  CONNECTED_EVENT = Event::connected
#     |  
#     |  EVENT_CONNECTED = Event::connected
#     |  
#     |  EVENT_DISCONNECTED = Event::disconnected
#     |  
#     |  EVENT_FILE_RECEIVED = Event::file received
#     |  
#     |  EVENT_FLIGHT_DATA = Event::fligt_data
#     |  
#     |  EVENT_LIGHT = Event::light
#     |  
#     |  EVENT_LOG = Event::log
#     |  
#     |  EVENT_TIME = Event::time
#     |  
#     |  EVENT_VIDEO_DATA = Event::video data
#     |  
#     |  EVENT_VIDEO_FRAME = Event::video frame
#     |  
#     |  EVENT_WIFI = Event::wifi
#     |  
#     |  FLIGHT_EVENT = Event::fligt_data
#     |  
#     |  LIGHT_EVENT = Event::light
#     |  
#     |  LOG_ALL = 99
#     |  
#     |  LOG_DEBUG = 3
#     |  
#     |  LOG_ERROR = 0
#     |  
#     |  LOG_EVENT = Event::log
#     |  
#     |  LOG_INFO = 2
#     |  
#     |  LOG_WARN = 1
#     |  
#     |  STATE_CONNECTED = State::connected
#     |  
#     |  STATE_CONNECTING = State::connecting
#     |  
#     |  STATE_DISCONNECTED = State::disconnected
#     |  
#     |  STATE_QUIT = State::quit  
