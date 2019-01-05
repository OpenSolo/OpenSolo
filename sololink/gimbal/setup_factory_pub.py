import struct
import setup_param

def float_to_uint32(f):
    return struct.unpack('I',struct.pack('<f',f))[0]

def float_to_bytes4(f):
    return struct.unpack('4b', struct.pack('>f', f))

def float3_to_string12(f1, f2, f3):
    return struct.unpack('12s',struct.pack('<3f', f1, f2, f3))[0]

def get_assembly_time(link):
    value = setup_param.fetch_param(link, "GMB_ASM_TIME", timeout=1)
    if value:
        return float_to_uint32(value.param_value)
    return None

def read_software_version(link, timeout=1):
    msg = setup_param.fetch_param(link, "GMB_SWVER", timeout=timeout)
    if not msg:
        return None
    else:
        return float_to_bytes4(msg.param_value)[:-1]

def get_serial_number(link):
    ser_num_1 = setup_param.fetch_param(link, "GMB_SER_NUM_1", timeout=1)
    ser_num_2 = setup_param.fetch_param(link, "GMB_SER_NUM_2", timeout=1)
    ser_num_3 = setup_param.fetch_param(link, "GMB_SER_NUM_3", timeout=1)
    if ser_num_1 != None and ser_num_2 != None and ser_num_3 != None:
        serial_str = float3_to_string12(ser_num_1.param_value, ser_num_2.param_value, ser_num_3.param_value)
        if serial_str.startswith('GB'):
            return serial_str
        else:
            return ''
    return None
