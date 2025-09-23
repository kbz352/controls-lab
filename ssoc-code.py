import RPi.GPIO as GPIO
import decimal
import numpy as np
import time
# import os, sys

###############
# Definitions #
###############

GPIO_IN_R = 3
GPIO_IN_L = 5
GPIO_OUT_R = 19
GPIO_OUT_L = 21

######################
# GPIO and PWM Setup #
######################

# setup based on board pin numbers and not GPIO name
GPIO.setmode(GPIO.BOARD)

GPIO.setup(GPIO_IN_R, GPIO.IN)
GPIO.setup(GPIO_IN_L, GPIO.IN)
GPIO.setup(GPIO_OUT_R, GPIO.OUT)
GPIO.setup(GPIO_OUT_L, GPIO.OUT)

# set up Pulse Width Modulation for output pins (this allows for the digital pins to emulate analog)
# max frequency is 8000, but causes issues w/ motor driver.
frequency = 100

PWM1 = GPIO.PWM(GPIO_OUT_L, frequency)
PWM2 = GPIO.PWM(GPIO_OUT_R, frequency)

# Activate PWM at 0% power
PWM1.start(0)
PWM2.start(0)

###########################
# Variable Initialization #
###########################

# initialize variables
l_count = 0  # count of edges detected by the algorithm for the left side
r_count = 0
l_count_prev = 0  # previous edge count for left side
r_count_prev = 0
l_prev = GPIO.input(GPIO_IN_L)
r_prev = GPIO.input(GPIO_IN_R)
l_RPM = 0
r_RPM = 0
l_power = 0  # left motor power output
r_power = 0  # right motor power output

# starting array
ARRAY_SIZE_ENCODER = 6
l_array = np.full(ARRAY_SIZE_ENCODER, l_prev)
r_array = np.full(ARRAY_SIZE_ENCODER, r_prev)

# jw: this basically makes example arrays for what a "true" edge case should look like
# based on ARRAY_SIZE_ENCODER, e.g. array_edge_high = [1,1,1,0,0,0]
# edge comparison array
edge_size = round(ARRAY_SIZE_ENCODER / 2)
array_edge_high = np.full(ARRAY_SIZE_ENCODER, 1)
array_edge_high[:-edge_size] = 0
array_edge_low = np.full(ARRAY_SIZE_ENCODER, 0)
array_edge_low[:-edge_size] = 1


def Counter():  # FIXME: convert to a function which takes inputs and has a return statement
    global l_count, r_count, l_array, r_array, array_edge_high, array_edge_low

    l_input = GPIO.input(GPIO_IN_L)
    r_input = GPIO.input(GPIO_IN_R)

    # refresh the array. add the newest value to the front and subtract the oldest value from the end
    # FIXME: change to use np.roll()
    l_array = np.insert(l_array, 0, l_input)
    l_array = np.delete(l_array, -1)
    r_array = np.insert(r_array, 0, r_input)
    r_array = np.delete(r_array, -1)

    # if there is an edge according the the edge array...
    if (r_array == array_edge_high).all() or (r_array == array_edge_low).all():
        r_count += 1
    if (l_array == array_edge_high).all() or (l_array == array_edge_low).all():
        l_count += 1


# RPM array
ARRAY_SIZE_RPM = 3
l_RPM_array = np.full(ARRAY_SIZE_RPM, 0, dtype=decimal.Decimal)
r_RPM_array = np.full(ARRAY_SIZE_RPM, 0, dtype=decimal.Decimal)


def RPM_function():
    global l_count, r_count, l_count_prev, r_count_prev, l_RPM, r_RPM
    global l_RPM_array, r_RPM_array, t, t_prev, l_distance, r_distance

    # calculating how many counts have happened between the last implementation
    # 40 edges per rotation
    l_RPM_now = (l_count - l_count_prev) / 40 * 60 / (t - t_prev)
    r_RPM_now = (r_count - r_count_prev) / 40 * 60 / (t - t_prev)

    # filter for RPM using arrays
    # FIXME: change to use np.roll()
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


# f = open("/home/pi/controls-data/data.csv", "w")
# f.write("Time,Left Power,Left RPM,Left Count,Right Power,Right RPM,Right Count\n")
# f.write(f"{t},{l_power},{l_RPM},{l_count},{r_power},{r_RPM},{r_count}\n")

#for run in [1, 2, 3]:
run = 3
for power in np.linspace(0, 100, 11):
    f = open(f"/home/pi/controls-lab/ssoc-data/power-{power}-run-{run}.csv", "w")
    f.write("Time,Power,Left RPM,Right RPM\n")

    l_count = 0
    r_count = 0

    t = 0  # time
    t_prev = 0
    SAMPLE_TIME = 0.1  # seconds between samples of wheel RPM
    t_start = time.time()
    t_sample = SAMPLE_TIME  # time until next sample
    duration = 5  # seconds

    f.write(f"{t},{power},{l_RPM},{r_RPM}\n")
    PWM1.start(power)
    PWM2.start(power)

    while t < duration:
        t = time.time() - t_start
        Counter()

        if t >= t_sample:
            t_sample += SAMPLE_TIME
            RPM_function()
            PWM1.start(power)
            PWM2.start(power)
            print(f"{t} {power} {l_RPM} {r_RPM} {r_count}")
            f.write(f"{t},{power},{l_RPM},{r_RPM}\n")
    # print(f"Total Rotations:\nLeft: {l_count / 40}\nRight: {r_count / 40}")
    PWM1.stop()
    PWM2.stop()
    time.sleep(1)

    f.close()
