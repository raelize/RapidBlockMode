#!/usr/bin/env python3
import ctypes
from picosdk.ps3000a import ps3000a as ps
import numpy as np
import matplotlib.pyplot as plt
from picosdk.functions import adc2mV, assert_pico_ok
from picosdk.PicoDeviceEnums import picoEnum
import time
import serial
import os
import struct
import binascii
import datetime

from decimal import Decimal

from trsfile import trs_open, Trace, SampleCoding, TracePadding, Header
from trsfile.parametermap import TraceParameterMap, TraceParameterDefinitionMap
from trsfile.traceparameter import ByteArrayParameter, ParameterType, TraceParameterDefinition

COM_PORT = 'COM4'
ITERATIONS = 100
NR_OF_ENCRYPTIONS = 10_000
KEY = b'\x41' * 16
TRACE_NAME = 'script_1_rbm_averaged.trs'

PRE_TRIGGER_SAMPLES = 0
POST_TRIGGER_SAMPLES = 200
DELAY = 700

status = {}
chandle = ctypes.c_int16()

# open unit
status["openunit"] = ps.ps3000aOpenUnit(ctypes.byref(chandle), None)

# configure channel A
chARange = ps.PS3000A_RANGE['PS3000A_20MV']
status["setChA"] = ps.ps3000aSetChannel(chandle, picoEnum.PICO_CHANNEL["PICO_CHANNEL_A"], 1, 1, chARange, 0)
assert_pico_ok(status["setChA"])

# configure channel B
chBRange = ps.PS3000A_RANGE['PS3000A_5V']
status["setChB"] = ps.ps3000aSetChannel(chandle, picoEnum.PICO_CHANNEL["PICO_CHANNEL_B"], 1, 1, chBRange, 0)
assert_pico_ok(status["setChB"])

# configure trigger
enabled = 1
channel = picoEnum.PICO_CHANNEL["PICO_CHANNEL_B"]
threshold = 1500
direction = picoEnum.PICO_THRESHOLD_DIRECTION["PICO_RISING"]
delay = DELAY
autotrigger = 100
status["trigger"] = ps.ps3000aSetSimpleTrigger(chandle, enabled, channel, threshold, direction, delay, autotrigger)
assert_pico_ok(status["trigger"])

iterations = ITERATIONS

preTriggerSamples = PRE_TRIGGER_SAMPLES
postTriggerSamples = POST_TRIGGER_SAMPLES
maxsamples = preTriggerSamples + postTriggerSamples

timebase = 1 # 0: 1 Gs, 1: 500 Ms, 2: 250 Ms, 3: 125 Ms
timeIntervalns = ctypes.c_float()
returnedMaxSamples = ctypes.c_int16()
status["GetTimebase"] = ps.ps3000aGetTimebase2(chandle, timebase, maxsamples, ctypes.byref(timeIntervalns), 1, ctypes.byref(returnedMaxSamples), 0)
assert_pico_ok(status["GetTimebase"])

overflow = (ctypes.c_int16 * iterations)()
cmaxSamples = ctypes.c_int32(maxsamples)

status["MemorySegments"] = ps.ps3000aMemorySegments(chandle, iterations, ctypes.byref(cmaxSamples))
assert_pico_ok(status["MemorySegments"])

status["SetNoOfCaptures"] = ps.ps3000aSetNoOfCaptures(chandle, iterations)
assert_pico_ok(status["SetNoOfCaptures"])

# connect
ser = serial.Serial(port=COM_PORT, baudrate=115200, timeout=10)

# set key
ser.write(b'K' + KEY)
print(ser.readline().strip())

trace_name = TRACE_NAME

# open trace set
tracefile = trs_open(trace_name, 'w')

# set buffers
buffers = []
for i in range(0, iterations):
    buffers.append((ctypes.c_int16 * maxsamples)())

channel =  picoEnum.PICO_CHANNEL["PICO_CHANNEL_A"]
for i in range(0, iterations):
    status["SetDataBuffers"] = ps.ps3000aSetDataBuffer(chandle, channel, ctypes.byref(buffers[i]), maxsamples, i, 0)
    assert_pico_ok(status["SetDataBuffers"])   

count = 0

start = time.time_ns()

for i in range(0, NR_OF_ENCRYPTIONS):
    status["runblock"] = ps.ps3000aRunBlock(chandle, preTriggerSamples, postTriggerSamples, timebase, 1, None, 0, None, None)
    assert_pico_ok(status["runblock"])

    input_data = os.urandom(16)
    ser.write(b'L' + struct.pack(">H", iterations) + input_data)

    ready = ctypes.c_int16(0)
    check = ctypes.c_int16(0)

    # wait for scope to be ready
    while ready.value == check.value:
        status["isReady"] = ps.ps3000aIsReady(chandle, ctypes.byref(ready))

    status["GetValuesBulk"] = ps.ps3000aGetValuesBulk(chandle, ctypes.byref(cmaxSamples), 0, iterations-1, 0, 0, ctypes.byref(overflow))
    assert_pico_ok(status["GetValuesBulk"])

    response = ser.readline()
    
    # average traces
    output_data = binascii.unhexlify(response[:-2])
    encoding = SampleCoding.FLOAT
    tp = TraceParameterMap(
        {
            'INPUT': ByteArrayParameter(input_data),
            'OUTPUT': ByteArrayParameter(output_data),
        }
    )

    result = [np.mean(k) for k in zip(*buffers)]
    trace = Trace(encoding, result, tp)
    tracefile.append(trace)

    # increase total count
    count += iterations

    # get elapsed time
    elapsed_time = time.time_ns() - start

    # get time in ns per experiment
    ns_it_takes_for_one = elapsed_time / count

    # get speed per day
    total_ns_per_day = 24 * 60 * 60 * 1000 * 1000 * 1000
    speed_per_day = total_ns_per_day / ns_it_takes_for_one
    tt = datetime.timedelta(seconds=(elapsed_time//1e9))
    print("Speed per day = %.2E (time: %s; traces: %d)" % (speed_per_day,tt,count))

    # get speed per hour
    # total_ns_per_hour = 60 * 60 * 1000 * 1000 * 1000
    # speed_per_hour = total_ns_per_hour / ns_it_takes_for_one
    # print("Speed per hour = %.2E (time: %d)" % (speed_per_hour,elapsed_time))

    # get speed per second
    # total_ns_per_second = 1000 * 1000 * 1000
    # speed_per_second = total_ns_per_second / ns_it_takes_for_one
    # print("Speed per second = %d (time: %d)" % (speed_per_second,elapsed_time))

    # get speed per second
    # speed_per_nanosecond = 1 / ns_it_takes_for_one
    # print("Speed per nanosecond = %f (time: %d)" % (speed_per_nanosecond,elapsed_time))

# stop unit
status["stop"] = ps.ps3000aStop(chandle)
assert_pico_ok(status["stop"])

# close unit
status["close"] = ps.ps3000aCloseUnit(chandle)
assert_pico_ok(status["close"])

# close trace
tracefile.close()
