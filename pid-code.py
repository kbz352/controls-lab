from typing import TextIO
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

setpoint = 0  # RPM setpoint
l_power = 0  # power to left wheel
r_power = 0  # power to right wheel
duration = 30  # seconds
SAMPLE_TIME = 0.01  # seconds between samples of wheel RPM
SAMPLE_TIME = 0.1  # seconds between samples of wheel RPM

run = 1  # indicatior of number of runs, used for argv batch runs

# PID variables
l_i = 0  # integral summation for left wheel
r_i = 0  # integral summation for right wheel
l_e_prev = 0  # previous error for left wheel
r_e_prev = 0  # previous error for right wheel
method = "ITAE-PI"

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


def Counter():
    global l_count, r_count, l_array, r_array, array_edge_high, array_edge_low

    l_input = GPIO.input(GPIO_IN_L)
    r_input = GPIO.input(GPIO_IN_R)

    # refresh the array. add the newest value to the front and subtract the oldest value from the end
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


def PID_function(RPM, Kc, tauI, tauD, bias, i, e_prev, t_prev_PID):
    t = time.time()
    dt = t - t_prev_PID
    t_prev_PID = t
    # t_run = t - t_start

    e = setpoint - RPM
    P = Kc * e
    D = Kc * tauD * (e - e_prev) / dt

    e_prev = e

    if tauI == 0:
        power = P + D + bias
    else:
        i = i + Kc * e * dt / tauI
        power = P + i + D + bias

    # FIXME: should power be kept above 40?
    power = max(0, min(100, power))  # prevent power going out of bounds.
    return power, i, e_prev, t_prev_PID


args = [
    ["--duration", "-d", "duration"],
    ["--setpoint", "-p", "setpoint"],
    ["--sample-time", "-s", "SAMPLE_TIME"],
    ["--run", "-r", "run"],
    ["--method", "-m", "method"],
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

# if setpoint < 40 or setpoint > 100:
#     print("ERROR: Invalid Power Input: Power values must be between 40% and 100%")

l_K = 1.150
l_tau = 0.189
l_t0 = 0.0768

r_K = 1.157
r_tau = 0.120
r_t0 = 0.1442

bias = 0

if method == "ITAE-PI":
    l_Kc = 0.586 / l_K * (l_t0 / l_tau) ** (-0.916)
    l_tauI = l_tau / (1.03 - 0.165 * (l_t0 / l_tau))
    l_tauD = 0
    r_Kc = 0.586 / r_K * (r_t0 / r_tau) ** (-0.916)
    r_tauI = r_tau / (1.03 - 0.165 * (r_t0 / r_tau))
    r_tauD = 0

elif method == "ITAE-PID":
    l_Kc = 0.965 / l_K * (l_t0 / l_tau) ** (-0.85)
    l_tauI = l_tau / (0.796 - 0.1465 * (l_t0 / l_tau))
    l_tauD = 0.308 * l_tau * (l_t0 / l_tau) ** (0.929)
    r_Kc = 0.965 / r_K * (r_t0 / r_tau) ** (-0.85)
    r_tauI = r_tau / (0.796 - 0.1465 * (r_t0 / r_tau))
    r_tauD = 0.308 * r_tau * (r_t0 / r_tau) ** (0.929)

elif method == "ZN":
    # l_Kc = 3
    # l_tauI = np.inf
    # l_tauD = 0
    # r_Kc = 3
    # r_tauI = np.inf
    # r_tauD = 0

    # P
    # l_Kc = 3/2
    # l_tauI = 0
    # l_tauD = 0
    # r_Kc = 3/2
    # r_tauI = 0
    # r_tauD = 0

    # PI
    l_Kc = 3/2.2
    l_tauI = 0.5/1.2
    l_tauD = 0
    r_Kc = 3/2.2
    r_tauI = 0.5/1.2
    r_tauD = 0

    # PID
    # l_Kc = 3/1.7
    # l_tauI = 0.5/2
    # l_tauD = 0.5/8
    # r_Kc = 3/1.7
    # r_tauI = 0.5/2
    # r_tauD = 0.5/8
    # bias = 50

t = 0  # time
t_prev = 0
t_start = time.time()
l_t_prev_PID = t_start
r_t_prev_PID = t_start
t_sample = SAMPLE_TIME  # time until next sample

filename = (
    f"{method}-{setpoint}-data-run-{run}"  # name of csv file to be stored in the data/ directory
)
f = open(f"/home/pi/controls-lab/pid-data/{filename}.csv", "w")
f.write("Time,RPM Setpoint,Left RPM,Right RPM,Left Power,Right Power\n")
f.write(f"{t},{setpoint},{l_RPM},{r_RPM},{l_power},{r_power}\n") #FIXME: calculate distance and record it

while t < duration:
    t = time.time() - t_start
    Counter()

    if t >= t_sample:
        t_sample += SAMPLE_TIME
        RPM_function()

        l_power, l_i, l_e_prev, l_t_prev_PID = PID_function(
            l_RPM, l_Kc, l_tauI, l_tauD, bias, l_i, l_e_prev, l_t_prev_PID
        )
        r_power, r_i, r_e_prev, r_t_prev_PID = PID_function(
            r_RPM, r_Kc, r_tauI, r_tauD, bias, r_i, r_e_prev, r_t_prev_PID
        )

        PWM1.start(l_power)
        PWM2.start(r_power)
        print(
                f"time: {t:.02f} setpoint: {setpoint:.02f} ----- l_RPM: {l_RPM:.02f} r_RPM: {r_RPM:.02f} ----- l_power: {l_power:.02f} r_power: {r_power:.02f}"
        )
        f.write(f"{t},{setpoint},{l_RPM},{r_RPM},{l_power},{r_power}\n")

PWM1.stop()
PWM2.stop()
f.close()
