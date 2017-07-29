#!/usr/bin/env python

"""
Utility for loading firmware into the 3DR Gimbal.

"""
import setup_mavlink, setup_param

axis_enum = ['PITCH', 'ROLL', 'YAW']
status_enum = ['in progress', 'succeeded', 'failed']

class Results:
    Success, ParamFetchFailed, CalibrationExists, CommsFailed, PitchFailed, RollFailed, YawFailed = 'Success', 'ParamFetchFailed', 'CalibrationExists', 'CommsFailed', 'PitchFailed', 'RollFailed', 'YawFailed'

def getAxisCalibrationValues(link):
    values = {
        'pitch': {'slope': 0, 'intercept': 0},
        'roll': {'slope': 0, 'intercept': 0},
        'yaw': {'slope': 0, 'intercept': 0},
    }
    for i in range(len(axis_enum)):
        result = setup_param.getAxisCalibrationParam(link, axis_enum[i])
        if result == None:
            return None
        values[axis_enum[i].lower()]['slope'] = result[0]
        values[axis_enum[i].lower()]['intercept'] = result[1]
    return values

def getAxisCalibrationParams(link):
    pitch = setup_param.getAxisCalibrationParam(link, axis_enum[0])
    roll = setup_param.getAxisCalibrationParam(link, axis_enum[1])
    yaw = setup_param.getAxisCalibrationParam(link, axis_enum[2])
    if pitch == None or roll == None or yaw == None:
        return None
    else:
        return pitch, roll, yaw

def resetCalibration(link):
    setup_param.clear_comutation_params(link)
    setup_mavlink.reset_gimbal(link)
    return True

def calibrate(link, progressCallback=None):
    # Check if a calibration exists, exit if it does
    pitch, roll, yaw = getAxisCalibrationParams(link)
    if pitch == None or roll == None or yaw == None:
        return Results.ParamFetchFailed
    elif (pitch[0] != 0 or pitch[1] != 0) and (roll[0] != 0 or roll[1] != 0) and (yaw[0] != 0 or yaw[1] != 0):
        # Check if a calibration is in progress
        result = setup_mavlink.getCalibrationProgress(link)
        if result == None:
            return Results.CalibrationExists
        elif result[2] != status_enum[0]:
            return Results.CalibrationExists
    
    calibratied_axes = 0
    axis_statuses = {'pitch': 'not started', 'roll': 'not started', 'yaw': 'not started'}
    retries = 0
    lastProgress = None
    while(calibratied_axes < 3):
        setup_mavlink.requestCalibration(link)
        result = setup_mavlink.getCalibrationProgress(link)
        if result:
            axis, progress, status = result[0], result[1], result[2]
        elif retries > 10:
            return Results.CommsFailed
        else:
            retries += 1
            continue
        retries = 0

        # Adjust number of calibrated axes if a previous calibration is already in progress
        if calibratied_axes == 0 and axis == axis_enum[1]:
            calibratied_axes == 1
        elif calibratied_axes == 0 and axis == axis_enum[2]:
            calibratied_axes == 2
        
        # Only run callback when progress has changed
        if int(progress) != lastProgress:
            progressCallback(axis, int(progress), status)
            lastProgress = int(progress)

        if status != 'in progress':
            axis_statuses[axis.lower()] = status

            # Don't continue calibration if an axis fails
            if status == 'failed':
                if axis == 'PITCH':
                    return Results.PitchFailed
                elif axis == 'ROLL':
                    return Results.RollFailed
                elif axis == 'YAW':
                    return Results.YawFailed
                break

            calibratied_axes += 1
    return Results.Success
