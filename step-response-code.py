import RPi.GPIO as GPIO
import decimal
import numpy as np
import time
import sys

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


initial_power = 50
final_power = 100
power_setpoint = initial_power

duration = 15  # seconds
SAMPLE_TIME = 0.1  # seconds between samples of wheel RPM
step_time = 5  # time when step occurs

run = 1  # indicatior of number of runs, used for argv batch runs

args = [
    ["--duration", "-d", "duration"],
    ["--sample-time", "-s", "SAMPLE_TIME"],
    ["--step-time", "-t", "SAMPLE_TIME"],
    ["--initial-power", "-i", "initial_power"],
    ["--final-power", "-f", "final_power"],
    ["--run", "-r", "run"],
]

for n, arg in enumerate(list(sys.argv[:])):
    if arg == "--help" or arg == "-h":
        print("Full Command\tShort\tVariable")
        for arglist in args:
            print(f"'{arglist[0]}'\t'{arglist[1]}'\t'{arglist[2]}'")
        exit(0)
    for arglist in args:
        if arg == arglist[0] or arg == arglist[1]:
            exec(f"{arglist[2]} = {sys.argv[n + 1]}")

# FIXME: there's got to be a better way than 3 or statements
if initial_power < 40 or initial_power > 100 or final_power < 40 or final_power > 100:
    print("ERROR: Invalid Power Input: Power values must be between 40% and 100%")

t = 0  # time
t_prev = 0
t_start = time.time()
t_sample = SAMPLE_TIME  # time until next sample

filename = f"{initial_power:.2f}-to-{final_power:.2f}-run-{run}"  # name of csv file to be stored in the data/ directory
f = open(f"/home/pi/controls-lab/step-response-data/{filename}.csv", "w")
f.write("Time,Power Setpoint,Left RPM,Left Count,Right RPM,Right Count\n")
f.write(f"{t},{power_setpoint},{l_RPM},{l_count},{r_RPM},{r_count}\n")

while t < duration:
    t = time.time() - t_start
    Counter()

    if t >= step_time:
        power_setpoint = final_power

    if t >= t_sample:
        t_sample += SAMPLE_TIME
        RPM_function()
        PWM1.start(power_setpoint)
        PWM2.start(power_setpoint)
        print(
            f"time: {t:.02f} power_setpoint: {power_setpoint:.02f} ----- l_RPM: {l_RPM:.02f} r_RPM: {r_RPM:.02f}"
        )
        f.write(f"{t},{power_setpoint},{l_RPM},{l_count},{r_RPM},{r_count}\n")

# print(f"Total Rotations:\nLeft: {l_count/40}\nRight: {r_count/40}")
PWM1.stop()
PWM2.stop()
f.close()
