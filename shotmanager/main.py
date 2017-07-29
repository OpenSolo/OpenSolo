#!/usr/bin/env python

# Main entry point for shot manager

import os
from os import sys, path
sys.path.append(os.path.realpath(''))
import shotManager

from dronekit import connect
from dronekit_solo import SoloVehicle
from dronekit.mavlink import MAVConnection

# First get an instance of the API endpoint
vehicle = connect(sys.argv[1], wait_ready=False, vehicle_class=SoloVehicle, source_system=255, use_native=True, heartbeat_timeout=-1)

if 'SOLOLINK_SANDBOX' in os.environ:
	from sim import rc_ipc_shim
	rc_ipc_shim.pixrc_start()

out = MAVConnection(sys.argv[2], source_system=254)
vehicle._handler.pipe(out)
out.start()

mgr = shotManager.ShotManager()
mgr.Start(vehicle)
mgr.Run()
