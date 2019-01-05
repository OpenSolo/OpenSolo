import shots
import selfie
import orbit
import cable_cam
import zipline
import follow
import pano
import rewind
import multipoint
import transect
import returnHome

class ShotFactory(object):
	__shot_classes = {
		shots.APP_SHOT_SELFIE : selfie.SelfieShot,
		shots.APP_SHOT_ORBIT: orbit.OrbitShot,
		shots.APP_SHOT_CABLECAM : cable_cam.CableCamShot,
		shots.APP_SHOT_ZIPLINE : zipline.ZiplineShot,
		shots.APP_SHOT_FOLLOW : follow.FollowShot,
		shots.APP_SHOT_MULTIPOINT : multipoint.MultipointShot,
		shots.APP_SHOT_PANO : pano.PanoShot,
		shots.APP_SHOT_REWIND : rewind.RewindShot,
		shots.APP_SHOT_TRANSECT : transect.TransectShot,
		shots.APP_SHOT_RTL : returnHome.returnHomeShot,
	}

	@staticmethod
	def get_shot_obj(shot, *args, **kwargs):
		shot_class = ShotFactory.__shot_classes.get(shot, None)
		if shot_class:
			return shot_class(args[0], args[1])
		raise NotImplementedError("[shot]: ShotFactory failed to generate the requested shot.")