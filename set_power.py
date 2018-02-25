import subprocess
import time
import sys

# Define your static power configuration options here
GPU_PWR_LIMITS = {
    'GTX 1060': {'high': 140, 'normal': 120, 'low': 100},
    'GTX 1070': {'high': 160, 'normal': 150, 'low': 120},
    'GTX 1080': {'high': 180, 'normal': 160, 'low': 140},
}

# Define the min/max power for each card type
MAX_PWR = {
    'GTX 1060' : 140,
    'GTX 1070' : 180,
    'GTX 1080' : 210,
}
MIN_PWR = {
    'GTX 1060' : 80,
    'GTX 1070' : 75,
    'GTX 1080' : 115,
}

GPU_DATA_ROWS = 3

def fix_truncation(gpu_type):
    if gpu_type == 'GTX 106...':
        return 'GTX 1060'
    return gpu_type

def detect_gpu_info():
    process = subprocess.Popen(['nvidia-smi'], stdout=subprocess.PIPE)
    out, err = process.communicate()
    out_data = out.split('\n')

    start_line = -1
    stop_line = -1
    for i in xrange(0, len(out_data)):
        if 'Pwr:Usage/Cap' in out_data[i]:
            start_line = i
        elif '+-------------------------------+' in out_data[i]:
            stop_line = i

    num_gpus = (stop_line - start_line) / GPU_DATA_ROWS
    gpu_list = []
    for i in xrange(0, num_gpus):
        gpu_data = {}
        line1 = start_line + 2 + i * GPU_DATA_ROWS
        gpu_index = int((out_data[line1])[1:5])
        gpu_type = (out_data[line1])[14:25].strip(' ')
        gpu_type = fix_truncation(gpu_type)

        line2 = start_line + 3 + i * GPU_DATA_ROWS
        gpu_temp = int((out_data[line2])[7:10])
        gpu_power = int((out_data[line2])[20:23])

        gpu_data['index'] = gpu_index
        gpu_data['type'] = gpu_type
        gpu_data['temp'] = gpu_temp
        gpu_data['power'] = gpu_power
        gpu_list.append(gpu_data)

    return gpu_list

def check_available_config(type, level):
    if type not in GPU_PWR_LIMITS:
        print 'No power limits are defined for GPU type %s' % type
        return 0
    else:
        if level not in GPU_PWR_LIMITS[type]:
            print 'The power configuration %s is not defined for GPU type %s' % (level, type)
            return 0
    return 1

def set_gpu_power(index, power):
    process = subprocess.Popen(['nvidia-smi', '-i', str(index), '-pl', str(power)], stdout=subprocess.PIPE)
    out, err = process.communicate()
    if 'All done' not in out:
        print 'Power configuration unsuccessful\nError: %s' % out
        return 0
    else:
        print 'Success setting gpu: %s' % index
        return 1


def set_gpu_power_levels(level):
    gpu_info = detect_gpu_info()
    for gpu in gpu_info:
        if check_available_config(gpu['type'], level):
            index = gpu['index']
            power = GPU_PWR_LIMITS[gpu['type']][level]
            set_gpu_power(index, power)


def adjust_temp_limit(ambient, temperature_limit):
    # Adjust power limit either up or down based on temperature
    gpu_info = detect_gpu_info()
    for gpu in gpu_info:
        ThetaJ = float(gpu['temp'] - ambient) / gpu['power']
        if gpu['temp'] < temperature_limit:
            # Increase the power limit
            deltaP = int((temperature_limit - gpu['temp']) / ThetaJ)
            power = gpu['power'] + deltaP

            if power > MAX_PWR[gpu['type']]:
                power = MAX_PWR[gpu['type']]
            if set_gpu_power(gpu['index'], power):
                print 'Increase Power for gpu %s - %s W' % (gpu['index'], power)
        else:
            # Reduce power by specified limit
            deltaP = int((gpu['temp'] - temperature_limit) / ThetaJ)
            power = gpu['power'] - deltaP
            if power < MIN_PWR[gpu['type']]:
                power = MIN_PWR[gpu['type']]
            if set_gpu_power(gpu['index'], power):
                print 'Running gpu %s at reduced power - %s W' % (gpu['index'], power)


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print 'Insufficient parameters, Usage: set_power.py static normal'
        print 'or "set_power.py continous 70" to limit the temperature to 70C'
        exit(1)

    # Define your ambient temperature in degrees C
    ambient = 25

    command = sys.argv[1].lower()
    parameter = sys.argv[2].lower()

    if command == 'continuous':
        temperature = int(parameter)
        while True:
            print 'Starting continuous temperature management target = %s C' % temperature
            time.sleep(20)
            adjust_temp_limit(ambient, temperature)
    else:
        # static setting
        set_gpu_power_levels(parameter)