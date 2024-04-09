import ctypes
from picosdk.ps3000a import ps3000a as ps
from picosdk.functions import adc2mV, assert_pico_ok
from picosdk.PicoDeviceEnums import picoEnum

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

# stop unit
status["stop"] = ps.ps3000aStop(chandle)
assert_pico_ok(status["stop"])

# close unit
status["close"] = ps.ps3000aCloseUnit(chandle)
assert_pico_ok(status["close"])

# print status
print(status)
