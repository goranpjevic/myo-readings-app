#!/usr/bin/env python3

#
# Original work Copyright (c) 2014 Danny Zhu
# Modified work Copyright (c) 2017 Alvaro Villoslada
# Modified work Copyright (c) 2017 Fernando Cosentino
# Modified work Copyright (c) 2022 Goran Pjević
# 
# Licensed under the MIT license. See the LICENSE file for details.
#

import sys
import time
import csv
import math
from myo_raw import MyoRaw, DataCategory
try:
    import pygame
    from pygame.locals import *
    HAVE_PYGAME = True
except ImportError:
    HAVE_PYGAME = False

pose_to_classify = 0

all_window_vals = []
previous_rms = None

if HAVE_PYGAME:
    w, h = 800, 600
    scr = pygame.display.set_mode((w, h))
    last_vals = None

    pygame.init()
    font = pygame.font.SysFont(None, 24)

    def plot(scr, vals, current_pose, time_diff, DRAW_LINES=True):
        global last_vals
        global previous_rms
        if last_vals is None:
            last_vals = vals
            return
        D = 5
        scr.scroll(-D)
        scr.fill((0, 0, 0), (w - D, 0, w, h))

        all_window_vals.append(vals)
        if len(all_window_vals) > 50:
            all_window_vals.pop(0)

        for i, (u, v) in enumerate(zip(last_vals, vals)):
            window_vals = [row[i] for row in all_window_vals]

            def get_rms(vals):
                squares = [x*x for x in vals]
                square_sum=0
                for x in squares:
                    square_sum += x
                return math.sqrt((1/len(vals))*square_sum)
            rms = get_rms(window_vals)
            if previous_rms == None:
                previous_rms = rms

            if DRAW_LINES:
                pygame.draw.line(scr, (0, 255, 0),
                                 (w - D, int(h/9 * (i+1 - u))),
                                 (w, int(h/9 * (i+1 - v))))
                pygame.draw.line(scr, (0, 0, 255),
                                 (w - D, int(h/9 * (i+1 - previous_rms))),
                                 (w, int(h/9 * (i+1 - rms))))
                pygame.draw.line(scr, (255, 255, 255),
                                 (w - D, int(h/9 * (i+1))),
                                 (w, int(h/9 * (i+1))))
            else:
                c = int(255 * max(0, min(1, v)))
                scr.fill((c, c, c), (w - D, i * h / 8, D, (i + 1) * h / 8 - i * h / 8))

        # draw rectangles for text
        pygame.draw.rect(scr, (0,0,0), pygame.Rect(0,20,400,20))

        img = font.render('pose: ' + str(current_pose) + '    time: ' + str(time_diff),True,(255,255,255))
        scr.blit(img, (20,20))

        pygame.display.flip()
        last_vals = vals
        previous_rms = rms

def proc_emg(timestamp, emg, moving, characteristic_num, category=None, times=[]):
    global pose_to_classify

    time_diff = time.time() - init_time
    if WRITE_TO_FILE:
        if time_diff >= 60:
            raise KeyboardInterrupt()
    if (time_diff % 10) >= 5:
        current_pose = pose_to_classify
    else:
        current_pose = 0

    if category != None:
        pose_to_classify = category
        current_pose = category

    if HAVE_PYGAME:
        # update pygame display
        plot(scr, [e / 500. for e in emg], current_pose, time_diff)
        # write the values to the output file
        if WRITE_TO_FILE:
            writer.writerow(emg + (current_pose,))
    else:
        print(emg)

    times.append(time.time())
    if len(times) > 20:
        times.pop(0)

def proc_battery(timestamp, battery_level):
    print("Battery level: %d" % battery_level)
    if battery_level < 5:
        m.set_leds([255, 0, 0], [255, 0, 0])
    else:
        m.set_leds([128, 128, 255], [128, 128, 255])

m = MyoRaw(sys.argv[1] if len(sys.argv) >= 2 else None)
m.add_handler(DataCategory.EMG, proc_emg)
m.add_handler(DataCategory.BATTERY, proc_battery)
m.subscribe()

m.add_handler(DataCategory.ARM, lambda arm, xdir: print('arm', arm, 'xdir', xdir))
m.add_handler(DataCategory.POSE, lambda p: print('pose', p))
m.set_sleep_mode(1)
m.set_leds([128, 128, 255], [128, 128, 255])  # purple logo and bar LEDs
m.vibrate(1)

WRITE_TO_FILE = False
load_or_record = input("(R)ecord or (l)oad a recording?: ")
if load_or_record == 'l':
    input_filename = input("input file: ")
    with open(input_filename,'r') as csv_file:
        reader = csv.reader(csv_file)
        init_time = time.time()
        MYO_FREQUENCY = 200
        interval = 1/MYO_FREQUENCY
        for i, row in enumerate(reader):
            last_element_index = len(row) - 1
            proc_emg(time.time(),tuple(int(num) for num in row[:last_element_index]),0,0,int(row[last_element_index]))
            time_to_sleep = init_time + i*interval - time.time()
            if time_to_sleep < 0:
                time_to_sleep = 0
            time.sleep(time_to_sleep)
    exit()

WRITE_TO_FILE = True
# write the data to a file
pose_to_classify = input("which pose to classify?: ")
output_filename = pose_to_classify + '.csv'
f = open(output_filename,'w')
writer=csv.writer(f)

init_time = time.time()

try:
    while True:
        m.run(1)

        if HAVE_PYGAME:
            for ev in pygame.event.get():
                if ev.type == QUIT or (ev.type == KEYDOWN and ev.unicode == 'q'):
                    raise KeyboardInterrupt()
                elif ev.type == KEYDOWN:
                    if K_1 <= ev.key <= K_3:
                        m.vibrate(ev.key - K_0)
                    if K_KP1 <= ev.key <= K_KP3:
                        m.vibrate(ev.key - K_KP0)

except KeyboardInterrupt:
    pass
finally:
    m.disconnect()
    print("Disconnected")
    f.close
