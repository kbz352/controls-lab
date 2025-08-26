# Front part of code from pdf

#####################################
# TEMPORARY VALUES NOT GIVEN IN PDF #
#####################################

ARRAY_SIZE_ENCODER = 1
ARRAY_SIZE_RPM = 1

#####################################

import time
import RPi.GPIO as GPIO
import numpy as np
import decimal
import os, sys

# setup based on board pin numbers and not GPIO name
GPIO.setmode(GPIO.BOARD)

# set up the input pins
GPIO.setup(3, GPIO.IN)
GPIO.setup(5, GPIO.IN)

# set up the output pins (to drive the motor)
GPIO.setup(19, GPIO.OUT)
GPIO.setup(21, GPIO.OUT)

# set up Pulse Width Modulation for output pins
# (this allows for the digital pins to emulate analog)

# max frequency is 8000, but causes issues w/ motor driver.
frequency = 100

PWM1 = GPIO.PWM(19, frequency)  # right wheel
PWM2 = GPIO.PWM(21, frequency)  # left wheel

# the activation of propotional volate to the pins
# In this case it is 60% power
PWM1.start(60)
PWM2.start(60)

# initialize variables
l_count = 0
r_count = 0
l_count_prev = 0
r_count_prev = 0
l_prev = GPIO.input(5)
r_prev = GPIO.input(5)
l_RPM = 0
r_RPM = 0
t = 0  # time
t_prev = 0

# starting array
l_array = np.full(ARRAY_SIZE_ENCODER, l_prev)
r_array = np.full(ARRAY_SIZE_ENCODER, r_prev)

# edge comparison array
edge_size = round(ARRAY_SIZE_ENCODER / 2)
array_edge_high = np.full(ARRAY_SIZE_ENCODER, 1)
array_edge_high[:-edge_size] = 0
array_edge_low = np.full(ARRAY_SIZE_ENCODER, 0)
array_edge_low[:-edge_size] = 1

def Counter():
    global l, r, l_count, r_count, l_array, r_array, array_edge_high, array_edge_low

    l = GPIO.input(5)
    r = GPIO.input(3)

    # refresh the array - add the newest value to the front
    # and subtract the oldest value from the end
    l_array = np.insert(l_array, 0, l)
    l_array = np.delete(l_array,-1)
    r_array = np.insert(r_array, 0, r)
    r_array = np.delete(r_array,-1)

    # if there is an edge according the the edge array...
    if (r_array==array_edge_high).all() or (r_array==array_edge_low).all():
        r_count += 1
    if (l_array==array_edge_high).all() or (l_array==array_edge_low).all():
        l_count += 1

# RPM array
l_RPM_array = np.full(ARRAY_SIZE_RPM, 0, dtype=decimal.Decimal)
r_RPM_array = np.full(ARRAY_SIZE_RPM, 0, dtype=decimal.Decimal)

def RPM_function():
    global l_count, r_count, l_count_prev, r_count_prev, l_RPM, r_RPM
    global l_RPM_array, r_RPM_array, t, t_prev, l_distance, r_distance

    # calculating how many counts have happened between the last implementation
    l_RPM_now = (l_count - l_count_prev)/40*60/(t-t_prev)
    r_RPM_now = (r_count - r_count_prev)/40*60/(t-t_prev)

    # filter for RPM using arrays
    l_RPM_array = np.insert(l_RPM_array, 0, l_RPM_now)
    l_RPM_array = np.delete(l_RPM_array, -1)
    r_RPM_array = np.insert(r_RPM_array, 0, r_RPM_now)
    r_RPM_array = np.delete(r_RPM_array, -1)

    # averaging the results of the arrays for a single value
    l_RPM = np.mean(l_RPM_array)
    r_RPM = np.mean(r_RPM_array)

    # replacing the previous values
    l_count_prev = l_count
    r_count_prev = r_count
    t_prev = t
