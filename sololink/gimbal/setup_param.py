#!/usr/bin/env python

"""
Utility for loading firmware into the 3DR Gimbal.

"""
import time
from pymavlink.mavparm import MAVParmDict
from pymavlink.dialects.v10.ardupilotmega import MAV_PARAM_TYPE_REAL32
from pymavlink.rotmat import Vector3
import setup_mavlink

try:
    import setup_factory_private
except ImportError:
    setup_factory_private = None

def fetch_param(link, param, timeout=2):
    for i in range(timeout):
        link.param_request_read_send(link.target_sysid, link.target_compid, param, -1)
        msg = link.file.recv_match(type="PARAM_VALUE", blocking=True, timeout=1)
        if msg:
            return msg
    return None

def set_param(link, param_name, param_value):
    parameters = MAVParmDict()
    parameters.mavset(link.file, param_name, param_value, 3);

def commit_to_flash(link):
    # Commit the zeroed out calibration parameters to flash
    link.param_set_send(link.target_sysid, 0, "GMB_FLASH", 69.0, MAV_PARAM_TYPE_REAL32)
    # Sleep for two seconds as immedietly following commands will fail (while the C2000 is writing flash)
    time.sleep(2)

def load_param_file(pid, link):
    parameters = MAVParmDict()
    parameters.load(pid, 'GMB*', link.file, check=False)
    commit_to_flash(link)

def clear_comutation_params(link):
    parameters = MAVParmDict()

    # Set all commutation calibration parameters to 0
    parameters.mavset(link.file, "GMB_YAW_SLOPE", 0.0, 3)
    parameters.mavset(link.file, "GMB_YAW_ICEPT", 0.0, 3)
    parameters.mavset(link.file, "GMB_ROLL_SLOPE", 0.0, 3)
    parameters.mavset(link.file, "GMB_ROLL_ICEPT", 0.0, 3)
    parameters.mavset(link.file, "GMB_PITCH_SLOPE", 0.0, 3)
    parameters.mavset(link.file, "GMB_PITCH_ICEPT", 0.0, 3)
    commit_to_flash(link)

def set_offsets(link, kind, offsets):
    if offsets and kind:
        set_param(link, "GMB_OFF_" + kind + "_X", offsets.x)
        set_param(link, "GMB_OFF_" + kind + "_Y", offsets.y)
        set_param(link, "GMB_OFF_" + kind + "_Z", offsets.z)
        commit_to_flash(link)

def get_offsets(link, kind, timeout=2):
    x = fetch_param(link, "GMB_OFF_" + kind + "_X", timeout=timeout)
    y = fetch_param(link, "GMB_OFF_" + kind + "_Y", timeout=timeout)
    z = fetch_param(link, "GMB_OFF_" + kind + "_Z", timeout=timeout)
    if x == None or y == None or z == None:
        return None
    else:
        return Vector3(x=x.param_value, y=y.param_value, z=z.param_value)

def getAxisCalibrationParam(link, axis_enum):
    icept = fetch_param(link, "GMB_" + axis_enum + "_ICEPT")
    slope = fetch_param(link, "GMB_" + axis_enum + "_SLOPE")
    if icept == None or slope == None:
        return None
    else:
        return [icept.param_value, slope.param_value]

def get_accel_params(link):
    offsets_x = fetch_param(link, "GMB_OFF_ACC_X")
    offsets_y = fetch_param(link, "GMB_OFF_ACC_Y")
    offsets_z = fetch_param(link, "GMB_OFF_ACC_Z")
    offset = Vector3(x=offsets_x.param_value, y=offsets_y.param_value, z=offsets_z.param_value)

    gains_x = fetch_param(link, "GMB_GN_ACC_X")
    gains_y = fetch_param(link, "GMB_GN_ACC_Y")
    gains_z = fetch_param(link, "GMB_GN_ACC_Z")
    gain = Vector3(x=gains_x.param_value, y=gains_y.param_value, z=gains_z.param_value)

    alignments_x = fetch_param(link, "GMB_ALN_ACC_X")
    alignments_y = fetch_param(link, "GMB_ALN_ACC_Y")
    alignments_z = fetch_param(link, "GMB_ALN_ACC_Z")
    alignment = Vector3(x=alignments_x.param_value, y=alignments_y.param_value, z=alignments_z.param_value)

    return offset, gain, alignment

def set_accel_params(link, p, level):
    parameters = MAVParmDict()
    parameters.mavset(link.file, "GMB_OFF_ACC_X", p[0], 3)
    parameters.mavset(link.file, "GMB_OFF_ACC_Y", p[1], 3)
    parameters.mavset(link.file, "GMB_OFF_ACC_Z", p[2], 3)
    parameters.mavset(link.file, "GMB_GN_ACC_X", p[3], 3)
    parameters.mavset(link.file, "GMB_GN_ACC_Y", p[4], 3)
    parameters.mavset(link.file, "GMB_GN_ACC_Z", p[5], 3)
    parameters.mavset(link.file, "GMB_ALN_ACC_X", level[0], 3)
    parameters.mavset(link.file, "GMB_ALN_ACC_Y", level[1], 3)
    parameters.mavset(link.file, "GMB_ALN_ACC_Z", level[2], 3)
    commit_to_flash(link)

def pos_hold_enable(link):
    parameters = MAVParmDict()
    parameters.mavset(link.file, "GMB_POS_HOLD", 1, 3)

def pos_hold_disable(link):
    parameters = MAVParmDict()
    parameters.mavset(link.file, "GMB_POS_HOLD", 0, 3)

def set_use_custom_gains(link, value):
    current_param = fetch_param(link, "GMB_CUST_GAINS")
    new_value = float(value)
    if current_param:
        if current_param.param_value != new_value:
            set_param(link, "GMB_CUST_GAINS", new_value)
            commit_to_flash(link)
        else:
            print("GMB_CUST_GAINS is already set to %0.1f" % new_value)

def enable_torques_message(link, enabled=True):
    if enabled:
        value = 1.0
    else:
        value = 0.0
    set_param(link, "GMB_SND_TORQUE", value)

def low_torque_mode(link, enabled=True):
    if enabled:
        value = 5000
    else:
        value = 0.0
    set_param(link, "GMB_MAX_TORQUE", value)

def charging(link, enabled=True):
    if enabled:
        value = 1.0
    else:
        value = 0.0
    set_param(link, "GMB_GP_CHARGE", value)
    commit_to_flash(link)

def restore_params(link, params):
    parameters = MAVParmDict()

    # Accel params
    parameters.mavset(link.file, "GMB_OFF_ACC_X", params['accel']['offset']['x'], 3)
    parameters.mavset(link.file, "GMB_OFF_ACC_Y", params['accel']['offset']['y'], 3)
    parameters.mavset(link.file, "GMB_OFF_ACC_Z", params['accel']['offset']['z'], 3)
    parameters.mavset(link.file, "GMB_GN_ACC_X", params['accel']['gain']['x'], 3)
    parameters.mavset(link.file, "GMB_GN_ACC_Y", params['accel']['gain']['y'], 3)
    parameters.mavset(link.file, "GMB_GN_ACC_Z", params['accel']['gain']['z'], 3)
    parameters.mavset(link.file, "GMB_ALN_ACC_X", params['accel']['alignment']['x'], 3)
    parameters.mavset(link.file, "GMB_ALN_ACC_Y", params['accel']['alignment']['y'], 3)
    parameters.mavset(link.file, "GMB_ALN_ACC_Z", params['accel']['alignment']['z'], 3)

    # Commutation params
    parameters.mavset(link.file, "GMB_YAW_SLOPE", params['yaw']['slope'], 3)
    parameters.mavset(link.file, "GMB_YAW_ICEPT", params['yaw']['icept'], 3)
    parameters.mavset(link.file, "GMB_ROLL_SLOPE", params['roll']['slope'], 3)
    parameters.mavset(link.file, "GMB_ROLL_ICEPT", params['roll']['icept'], 3)
    parameters.mavset(link.file, "GMB_PITCH_SLOPE", params['pitch']['slope'], 3)
    parameters.mavset(link.file, "GMB_PITCH_ICEPT", params['pitch']['icept'], 3)

    # Gyro
    parameters.mavset(link.file, "GMB_OFF_GYRO_X", params['gyro']['x'], 3)
    parameters.mavset(link.file, "GMB_OFF_GYRO_Y", params['gyro']['y'], 3)
    parameters.mavset(link.file, "GMB_OFF_GYRO_Z", params['gyro']['z'], 3)

    # Joint
    parameters.mavset(link.file, "GMB_OFF_JNT_X", params['gyro']['x'], 3)
    parameters.mavset(link.file, "GMB_OFF_JNT_Y", params['gyro']['y'], 3)
    parameters.mavset(link.file, "GMB_OFF_JNT_Z", params['gyro']['z'], 3)

    # Serial Number and Assembly Time
    if setup_factory_private:
        setup_factory_private.set_serial_number(link, params['serial_number'], commit=False)
        set_param(link, "GMB_ASM_TIME", setup_factory_private.uint32_to_float(params['assembly_time']))

    # Save the values
    commit_to_flash(link)

    # Reset the gimbal
    setup_mavlink.reset_gimbal(link)
