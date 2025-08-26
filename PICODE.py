
t_start = time.time()
t_smaple = SAMPLE_TIME

with open("/home/pit/Desktop/encoder_data/name.csv", 'w') as f:
    f.write(f'{text} ,,\n')
    f.write(f'time,l_power,l_RPM,r_pwr,r_RPM')
    PWM1.start(0)
    PWM2.start(0)
    t = 0 #time int
    t_prev = 0
    t_start = time.time()
    t_sample = SAMPLE_TIME
    f.write(f'{t},{1_RPM},{r_RPM}\n')

    #Program run
    while t < duration:
        t = time.time() - t_start
        CounterFunction

        if t>= t_sample:
            t_smaple+= SAMPLE_TIME
            RPM_function()
            PWM1.start(50)
            PWM2.start(50)
            print(f'time:{t:.02f} L power:{power_l:.02f} R pwr: {power_r:.02f} RPM: {r_RPM:.02f}')
            f.write(f'{t}, {power_l},{l_distance},{l_RPM,{power_r},{r_distance},{r_RPM}\n')