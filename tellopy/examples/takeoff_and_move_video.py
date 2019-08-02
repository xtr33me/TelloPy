import time
import socket
import threading
import sys
import tellopy
import pygame
import pygame.display
import pygame.key
import pygame.locals
import pygame.font
import os
import datetime
from collections import OrderedDict
from subprocess import Popen, PIPE
import json
# from tellopy import logger

# log = tellopy.logger.Logger('TelloUI')

prev_flight_data = None
video_player = None
video_recorder = None
font = None
wid = None
date_fmt = '%Y-%m-%d_%H%M%S'
event_counter = 0
event_list = OrderedDict()
events_to_play = OrderedDict()
record_flight_log = False
clock = pygame.time.Clock()
wait_time = 0
current_ap_event = 'idle'
waiting = False
process_autopilot_events = False
FLIGHT_RECORD_FILENAME = "data.json"
TIME_BETWEEN_EVENT_CAPTURE = 0.01
SKIP_RATE_DEFAULT = 0.01
skip_rate = SKIP_RATE_DEFAULT
PAUSE_TIME = 1

def take_picture(drone, speed):
    if speed == 0:
        return
    drone.take_picture()

def process_autopilot_event():
    global events_to_play
    val = events_to_play.popitem(last=False)[1]
    #k, v = val.items()
    k = list(val)[0]
    v = (float)(val[k])
    send_event_for_time(k, v)
    print("Processing autopilot event {0} - {1}".format(k, v))

def set_record_flight_log(enabled):
    global record_flight_log
    record_flight_log = enabled
    print("Record flight log set:{0}".format(record_flight_log))

def load_flight_log():
    global process_autopilot_events
    #Check if file exists and is readable
    if os.path.isfile(FLIGHT_RECORD_FILENAME) and os.access(FLIGHT_RECORD_FILENAME, os.R_OK): 
        with open(FLIGHT_RECORD_FILENAME, 'r') as f:
            try:
                global events_to_play
                
                events_load = json.load(f)
                for i, val in enumerate(events_load):
                    events_to_play[i] = events_load[val]

                print('loaded flight log file: ',events_to_play)

                #Events loaded so lets process
                process_autopilot_events = True
                process_autopilot_event()

                #Now lets send the events to the drone
                #for i in events_to_play.keys():
                #    send_event_for_time(i, (float)(events_to_play[i]))
            except Exception as e:
                print("got %s on json.load()" % e)

def send_event_for_time(evt, dur):
    print("Sending event {0} for {1}".format(evt, dur))
    global current_ap_event
    global wait_time
    global waiting

    current_ap_event = evt
    wait_time = dur
    waiting = True

def pause(drone, speed):
    print("PAUSING")
    time.sleep(1.0)

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
    'left': lambda drone, speed: drone.counter_clockwise(speed*2),
    'right': lambda drone, speed: drone.clockwise(speed*2),
    'up': lambda drone, speed: drone.up(speed*2),
    'down': lambda drone, speed: drone.down(speed*2),
    'tab': lambda drone, speed: drone.takeoff(),
    'backspace': lambda drone, speed: drone.land(),
    'enter': take_picture,
    'return': take_picture,
    'l': lambda enabled: set_record_flight_log(enabled),
    'k': lambda drone, speed: load_flight_log(),
    'z': pause,
}

class FlightDataDisplay(object):
    # previous flight data value and surface to overlay
    _value = None
    _surface = None
    # function (drone, data) => new value
    # default is lambda drone,data: getattr(data, self._key)
    _update = None
    def __init__(self, key, format, colour=(255,255,255), update=None):
        self._key = key
        self._format = format
        self._colour = colour

        if update:
            self._update = update
        else:
            self._update = lambda drone,data: getattr(data, self._key)

    def update(self, drone, data):
        new_value = self._update(drone, data)
        if self._value != new_value:
            self._value = new_value
            self._surface = font.render(self._format % (new_value,), True, self._colour)
        return self._surface

def update_hud(hud, drone, flight_data):
    (w,h) = (158,0) # width available on side of screen in 4:3 mode
    blits = []
    for element in hud:
        surface = element.update(drone, flight_data)
        if surface is None:
            continue
        blits += [(surface, (0, h))]
        # w = max(w, surface.get_width())
        h += surface.get_height()
    h += 64  # add some padding
    overlay = pygame.Surface((w, h), pygame.SRCALPHA)
    overlay.fill((0,0,0)) # remove for mplayer overlay mode
    for blit in blits:
        overlay.blit(*blit)
    pygame.display.get_surface().blit(overlay, (0,0))
    pygame.display.update(overlay.get_rect())

def status_print(text):
    pygame.display.set_caption(text)

hud = [
    FlightDataDisplay('height', 'ALT %3d'),
    FlightDataDisplay('ground_speed', 'SPD %3d'),
    FlightDataDisplay('battery_percentage', 'BAT %3d%%'),
    FlightDataDisplay('wifi_strength', 'NET %3d%%'),
]

def flightDataHandler(event, sender, data):
    global prev_flight_data
    text = str(data)
    if prev_flight_data != text:
        update_hud(hud, sender, data)
        prev_flight_data = text
        print("---- Flight Data: {0}".format(data))

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
    status_print('Saved photo to %s' % path)

#This is just to allow us to slow the events getting fired to drone
def addPause():
    try:
        global event_list
        global event_counter
        event_list[event_counter] = {'z' : PAUSE_TIME}
        event_counter = event_counter + 1
        print("ADDING PAUSET LIST")
    except:
        print(str("ERROR"))

def main():
    pygame.init()
    pygame.display.init()
    pygame.display.set_mode((1280, 720))
    pygame.font.init()


    global event_list
    global event_counter

    global font
    font = pygame.font.SysFont("dejavusansmono", 32)

    global wid
    if 'window' in pygame.display.get_wm_info():
        wid = pygame.display.get_wm_info()['window']
    print("Tello video WID:", wid)

    drone = tellopy.Tello()
    drone.connect()
    drone.start_video()
    drone.subscribe(drone.EVENT_FLIGHT_DATA, flightDataHandler)
    drone.subscribe(drone.EVENT_VIDEO_FRAME, videoFrameHandler)
    drone.subscribe(drone.EVENT_FILE_RECEIVED, handleFileReceived)
    speed = 30
    last_key = None
    start_time = None

    try:
        while 1:
            
            time.sleep(TIME_BETWEEN_EVENT_CAPTURE)  # loop with pygame.event.get()
            #Get the time since last loop
            dt = clock.tick()

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
                        
                        if keyname == 'l':
                            val = not record_flight_log
                            key_handler(val)
                        elif type(key_handler) == str:
                            getattr(drone, key_handler)(speed)
                        else:
                            key_handler(drone, speed)

                        if record_flight_log == True:
                            last_key = keyname
                            start_time = pygame.time.get_ticks()#datetime.datetime.now()
                            print("START_TIME SET: {0}".format(start_time))

                elif e.type == pygame.locals.KEYUP:
                    print('-' + pygame.key.name(e.key))
                    keyname = pygame.key.name(e.key)
                    
                    #We dont want our logging enabled load events to replay
                    #Will have to create a list of elements to allow writing after this is working
                    if record_flight_log == True and keyname != 'l' and keyname != 'k':
                        #Right now just going to log keydown and see hwo it works
                        #Casting below to int just to cut down on size stored. This is in ms so lower preceision
                        #should be fine
                        curr_time = pygame.time.get_ticks()
                        print("KEY_UP TIME SET: {0}".format(curr_time))
                        event_list[event_counter] = {keyname: (curr_time - start_time)}
                        event_counter = event_counter + 1
                        print("DIFF IN TIME IS: {0}".format(curr_time - start_time))
                        last_key = None
                        start_time = None
                        addPause()

                    if keyname in controls:
                        key_handler = controls[keyname]
                        if type(key_handler) == str:
                            getattr(drone, key_handler)(0)
                        elif keyname == 'l' or keyname == 'k':
                            continue
                        else:
                            key_handler(drone, 0)
                    
                    #Going to write out log when landinginstead of finally block
                    if keyname == 'backspace':
                        if record_flight_log == True:
                            with open(FLIGHT_RECORD_FILENAME, 'w') as f:
                                json.dump(event_list, f)

                        print("Saved JSON")        
                        print(event_list)

            global process_autopilot_events
            global waiting
            global wait_time

            global skip_rate
            
            #if 0 < skip_rate:
            #    skip_rate = skip_rate - 1
            #else:
            #    skip_rate = SKIP_RATE_DEFAULT
            if waiting:
                #wait_time -= dt
                #print("---- CURRENT WAIT TIME: {0} - deltatime {1} ".format(wait_time, dt))
                
                if current_ap_event in controls:
                    if 0 < skip_rate:
                        skip_rate = skip_rate - dt
                    else:
                        wait_time -= dt
                        #print("---- CURRENT WAIT TIME: {0} - deltatime {1} ".format(wait_time, dt))
                
                        skip_rate = SKIP_RATE_DEFAULT
                        key_handler = controls[current_ap_event]
                        if type(key_handler) == str:
                            getattr(drone, key_handler)(speed)
                        elif current_ap_event == 'l' or current_ap_event == 'k':
                            continue
                        else:
                            key_handler(drone, speed)

                if wait_time <= 0:
                    waiting = False
                    #process next autopilot event
                    process_autopilot_event()
    except e:
        print(str(e))
    finally:
        print('Shutting down connection to drone...')
        #if video_recorder:
        #    toggle_recording(drone, 1)
        drone.quit()

        # if record_flight_log == True:
        #     with open(FLIGHT_RECORD_FILENAME, 'w') as f:
        #         json.dump(event_list, f)

        # print("Saved JSON")        
        # print(event_list)
        exit(1)

if __name__ == '__main__':
    main()
