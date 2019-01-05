import setup_comutation
import setup_factory_pub
import setup_param
from distutils.version import LooseVersion
from pymavlink.mavparm import MAVParmDict
from pymavlink.rotmat import Vector3
import setup_mavlink
import math

EXPECTED_VERSION = '0.26.0'

EXPECTED_SERIAL_NUMBER_START = 'GB11A'
EXPETED_ASSEMBLY_DATE_MIN = 1434778800 # Sat Jun 20 02:40:00 BRT 2015

EXPECTED_PITCH_ICEPT_MAX = 0.35
EXPECTED_PITCH_ICEPT_MIN = 0.05
EXPECTED_PITCH_SLOPE_MAX = 0.14
EXPECTED_PITCH_SLOPE_MIN = 0.12
EXPECTED_ROLL_ICEPT_MIN = 0.35
EXPECTED_ROLL_ICEPT_MAX = 0.53
EXPECTED_ROLL_SLOPE_MAX = 0.15
EXPECTED_ROLL_SLOPE_MIN = 0.11
EXPECTED_YAW_ICEPT_MAX = 0.60
EXPECTED_YAW_ICEPT_MIN = 0.40
EXPECTED_YAW_SLOPE_MAX = 0.13
EXPECTED_YAW_SLOPE_MIN = 0.09

EXPECTED_JOINT_X_MAX = 0.20
EXPECTED_JOINT_X_MIN = -0.14
EXPECTED_JOINT_Y_MAX = 0.20
EXPECTED_JOINT_Y_MIN = -0.07
EXPECTED_JOINT_Z_MAX = 0.18
EXPECTED_JOINT_Z_MIN = -0.18

EXPECTED_ACC_GAIN_MIN = 0.95
EXPECTED_ACC_GAIN_MAX = 1.05

EXPECTED_ACC_ALIGN_X_MIN = math.radians(-5)
EXPECTED_ACC_ALIGN_X_MAX = math.radians(5)
EXPECTED_ACC_ALIGN_Y_MIN = math.radians(-5)
EXPECTED_ACC_ALIGN_Y_MAX = math.radians(5)
EXPECTED_ACC_ALIGN_Z_MIN = math.radians(-5)
EXPECTED_ACC_ALIGN_Z_MAX = math.radians(5)

EXPECTED_ACC_OFFSET_X_MIN = -2.0
EXPECTED_ACC_OFFSET_X_MAX = 2.0
EXPECTED_ACC_OFFSET_Y_MIN = -2.0
EXPECTED_ACC_OFFSET_Y_MAX = 2.0
EXPECTED_ACC_OFFSET_Z_MIN = -2.0
EXPECTED_ACC_OFFSET_Z_MAX = 2.0

EXPECTED_GYRO = 0.07

class Results:
    Pass, Fail, Error = 'pass', 'fail', 'error'

def show(link):
    swver = setup_factory_pub.read_software_version(link, timeout=2)
    if swver != None:
        major, minor, rev = int(swver[0]), int(swver[1]), int(swver[2])
        if (major == 0 and minor >= 18) or major > 0:
            serial_number = setup_factory_pub.get_serial_number(link)
            assembly_time = setup_factory_pub.get_assembly_time(link)
        else:
            serial_number = ''
            assembly_time = ''
    pitch_com, roll_com, yaw_com = setup_comutation.getAxisCalibrationParams(link)
    joint = setup_param.get_offsets(link, 'JNT')
    gyro = setup_param.get_offsets(link, 'GYRO')
    accel_offset, accel_gain, accel_alignment = setup_param.get_accel_params(link)
    k_rate = setup_param.fetch_param(link, "GMB_K_RATE")

    if swver != None and serial_number != None and assembly_time != None and pitch_com != None and roll_com != None and yaw_com != None and isinstance(joint, Vector3) and isinstance(gyro, Vector3) and isinstance(accel_offset, Vector3) and isinstance(accel_gain, Vector3) and isinstance(accel_alignment, Vector3) and k_rate != None:
        params = {
            'version': swver,
            'serial_number': serial_number,
            'assembly_time': assembly_time,
            'pitch': {
                'icept': pitch_com[0],
                'slope': pitch_com[1]
            },
            'roll': {
                'icept': roll_com[0],
                'slope': roll_com[1]
            },
            'yaw': {
                'icept': yaw_com[0],
                'slope': yaw_com[1]
            },
            'joint': {
                'x': joint.x,
                'y': joint.y,
                'z': joint.z
            },
            'gyro': {
                'x': gyro.x,
                'y': gyro.y,
                'z': gyro.z
            },
            'accel': {
                'offset': {
                    'x': accel_offset.x,
                    'y': accel_offset.y,
                    'z': accel_offset.z
                },
                'gain': {
                    'x': accel_gain.x,
                    'y': accel_gain.y,
                    'z': accel_gain.z
                },
                'alignment': {
                    'x': accel_alignment.x,
                    'y': accel_alignment.y,
                    'z': accel_alignment.z
                }
            },
            'k_rate': k_rate.param_value,
            'validation': {
                'version': validate_version(link, swver=swver),
                'serial': validate_serial_number(link, serial_number=serial_number),
                'date': validate_date(link, assembly_time=assembly_time),
                'commutation': {
                    'pitch': validate_comutation_axis_value('pitch', pitch_com),
                    'roll': validate_comutation_axis_value('roll', roll_com),
                    'yaw': validate_comutation_axis_value('yaw', yaw_com)
                },
                'joints': validate_joints(link, joint=joint),
                'gyros': validate_gyros(link, gyro=gyro),
                'accels': validate_accelerometers(link, gain=accel_gain, offset=accel_offset, alignment=accel_alignment)
            }
        }
        return params
    else:
        return None

def validate_version(link, swver=None):
    if not swver:
        swver = setup_factory_pub.read_software_version(link, timeout=2)
    if not swver:
        return Results.Error
    ver = LooseVersion("%i.%i.%i" % (swver[0], swver[1], swver[2]))
    ver_expected = LooseVersion(EXPECTED_VERSION)
    if ver >= ver_expected:
        return Results.Pass
    else:
        return Results.Fail

def validate_comutation_axis_value(axis, values):
    if axis == 'pitch':
        valid = validate_comutation_axis(None, values, EXPECTED_PITCH_ICEPT_MAX, EXPECTED_PITCH_ICEPT_MIN, EXPECTED_PITCH_SLOPE_MAX, EXPECTED_PITCH_SLOPE_MIN)
    elif axis == 'roll':
        valid = validate_comutation_axis(None, values, EXPECTED_ROLL_ICEPT_MAX, EXPECTED_ROLL_ICEPT_MIN, EXPECTED_ROLL_SLOPE_MAX, EXPECTED_ROLL_SLOPE_MIN)
    elif axis == 'yaw':
        valid = validate_comutation_axis(None, values, EXPECTED_YAW_ICEPT_MAX, EXPECTED_YAW_ICEPT_MIN, EXPECTED_YAW_SLOPE_MAX, EXPECTED_YAW_SLOPE_MIN)
    else:
        return Results.Error

    if valid:
        return Results.Pass
    else:
        return Results.Fail

def validate_comutation_axis(link, axis, i_max, i_min, s_max, s_min):
    icept = axis[0]
    slope = axis[1]
    if (icept == 0) or (i_min >= icept) or (i_max <= icept):
        return False
    elif (icept == 0) or (s_min >= slope) or (s_max <= slope):
        return False
    else:
        return True

def validate_comutation(link, pitch_com=None, roll_com=None, yaw_com=None):
    "The acceptable range values where collected from the batch of DVT1 gimbals"
    if pitch_com == None or roll_com == None or yaw_com == None:
        pitch_com, roll_com, yaw_com = setup_comutation.getAxisCalibrationParams(link)
    if pitch_com == None or roll_com == None or yaw_com == None:
        return Results.Error
    if (validate_comutation_axis(link, pitch_com, EXPECTED_PITCH_ICEPT_MAX, EXPECTED_PITCH_ICEPT_MIN, EXPECTED_PITCH_SLOPE_MAX, EXPECTED_PITCH_SLOPE_MIN) and 
        validate_comutation_axis(link, roll_com, EXPECTED_ROLL_ICEPT_MAX, EXPECTED_ROLL_ICEPT_MIN, EXPECTED_ROLL_SLOPE_MAX, EXPECTED_ROLL_SLOPE_MIN) and 
        validate_comutation_axis(link, yaw_com, EXPECTED_YAW_ICEPT_MAX, EXPECTED_YAW_ICEPT_MIN, EXPECTED_YAW_SLOPE_MAX, EXPECTED_YAW_SLOPE_MIN)):
        return Results.Pass
    else:
        return Results.Fail

def validate_joints(link, joint=None):
    "The acceptable range values where collected from the batch of DVT1 gimbals"
    if not isinstance(joint, Vector3):
        joint = setup_param.get_offsets(link, 'JNT')
    if not isinstance(joint, Vector3):
        return Results.Error
    if ((joint.x <= EXPECTED_JOINT_X_MAX) and (joint.x >= EXPECTED_JOINT_X_MIN) and (joint.x != 0) and
        (joint.y <= EXPECTED_JOINT_Y_MAX) and (joint.y >= EXPECTED_JOINT_Y_MIN) and (joint.y != 0) and
        (joint.z <= EXPECTED_JOINT_Z_MAX) and (joint.z >= EXPECTED_JOINT_Z_MIN) and (joint.z != 0)):
        return Results.Pass
    else:
        return Results.Fail

def validate_gyros(link, gyro=None):
    "The acceptable range values where collected from the batch of DVT1 gimbals"
    if not isinstance(gyro, Vector3):
        gyro = setup_param.get_offsets(link, 'GYRO')
    if not isinstance(gyro, Vector3):
        return Results.Error
    if ((gyro.x <= EXPECTED_GYRO) and (gyro.x >= -EXPECTED_GYRO) and (gyro.x != 0) and
        (gyro.y <= EXPECTED_GYRO) and (gyro.y >= -EXPECTED_GYRO) and (gyro.y != 0) and
        (gyro.z <= EXPECTED_GYRO) and (gyro.z >= -EXPECTED_GYRO) and (gyro.z != 0)):
        return Results.Pass
    else:
        return Results.Fail

def validate_accelerometers(link, offset=None, gain=None, alignment=None):
    "Since there is no accelerometer cal yet, just check if the values are zeroed"
    if not isinstance(offset, Vector3) or not isinstance(gain, Vector3) or not isinstance(alignment, Vector3):
        offset, gain, alignment = setup_param.get_accel_params(link)
    if not isinstance(offset, Vector3) or not isinstance(gain, Vector3) or not isinstance(alignment, Vector3):
        return Results.Error
    if ((offset.x >= EXPECTED_ACC_OFFSET_X_MIN) and (offset.x <= EXPECTED_ACC_OFFSET_X_MAX) and
        (offset.y >= EXPECTED_ACC_OFFSET_Y_MIN) and (offset.y <= EXPECTED_ACC_OFFSET_Y_MAX) and
        (offset.z >= EXPECTED_ACC_OFFSET_Z_MIN) and (offset.z <= EXPECTED_ACC_OFFSET_Z_MAX) and
        (alignment.x >= EXPECTED_ACC_ALIGN_X_MIN) and (alignment.x <= EXPECTED_ACC_ALIGN_X_MAX) and
        (alignment.y >= EXPECTED_ACC_ALIGN_Y_MIN) and (alignment.y <= EXPECTED_ACC_ALIGN_Y_MAX) and
        (alignment.z >= EXPECTED_ACC_ALIGN_Z_MIN) and (alignment.z <= EXPECTED_ACC_ALIGN_Z_MAX) and
        (gain.x >= EXPECTED_ACC_GAIN_MIN) and (gain.x <= EXPECTED_ACC_GAIN_MAX) and
        (gain.y >= EXPECTED_ACC_GAIN_MIN) and (gain.y <= EXPECTED_ACC_GAIN_MAX) and
        (gain.z >= EXPECTED_ACC_GAIN_MIN) and (gain.z <= EXPECTED_ACC_GAIN_MAX)):
        return Results.Pass
    else:
        return Results.Fail

def validate_gains(link):
    custom_gains = setup_param.fetch_param(link, "GMB_CUST_GAINS")
    if custom_gains is None:
        return Results.Error
    elif custom_gains.param_value == 0.0:
        return Results.Pass
    else:
        return Results.Fail

def validate_date(link, assembly_time=None):
    if assembly_time == None:
        assembly_time = setup_factory_pub.get_assembly_time(link)
    if assembly_time == None:
        return Results.Error
    elif assembly_time > EXPETED_ASSEMBLY_DATE_MIN:
        return Results.Pass
    else:
        return Results.Fail

def validate_serial_number(link, serial_number=None):
    if serial_number == None:
        serial_number = setup_factory_pub.get_serial_number(link)
    if serial_number == None:
        return Results.Error
    elif serial_number.startswith(EXPECTED_SERIAL_NUMBER_START):
        return Results.Pass
    else:
        return Results.Fail
        
def validate(link):
    validation = {
        'version': validate_version(link),
        'serial': validate_serial_number(link),
        'date': validate_date(link),
        'commutation': validate_comutation(link),
        'joints': validate_joints(link),
        'gyros': validate_gyros(link),
        'accels': validate_accelerometers(link),
        'gains': validate_gains(link)
    }
    return validation

def restore_defaults(link):
    parameters = MAVParmDict()
    parameters.mavset(link.file, "GMB_CUST_GAINS", 0.0); # do not use custom gains for default values   
    setup_param.commit_to_flash(link)
    setup_mavlink.reset_gimbal(link)
    return True
