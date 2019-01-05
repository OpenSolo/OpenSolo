#
# This is the entry point for MavProxy running DroneAPI on the vehicle
# Usage:
# * mavproxy.py
# * module load api
# * api start TestPerformance.py
#

import time
from pymavlink import mavutil

UPDATE_RATE = 50.0

class ShotManager():
    def __init__(self):
        # First get an instance of the API endpoint
        api = local_connect()
    
        # get our vehicle - when running with mavproxy it only knows about one vehicle (for now)
        self.vehicle = api.get_vehicles()[0]
        
        self.vehicle.wait_ready()

        while True:            
            msg = self.vehicle.message_factory.command_long_encode(
                                                                                     0, 1,    # target system, target component
                                                                                     mavutil.mavlink.MAV_CMD_DO_CHANGE_SPEED, # frame
                                                                                     0,       # confirmation
                                                                                     1, 1.0, -1, # params 1-3
                                                                                     0.0, 0.0, 0.0, 0.0 ) # params 4-7 (not used)
                

            # send command to vehicle
            self.vehicle.send_mavlink(msg)    

            msg2 = self.vehicle.message_factory.command_long_encode(
                                                        0, 1,    # target system, target component
                                                        mavutil.mavlink.MAV_CMD_DO_SET_ROI, #command
                                                        0, #confirmation
                                                        0, 0, 0, 0, #params 1-4
                                                        33.0,
                                                        100.9,
                                                        40.6
                                                        )

            self.vehicle.send_mavlink(msg2)            
            time.sleep( 1 / UPDATE_RATE )

ShotManager()