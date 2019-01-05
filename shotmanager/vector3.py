#!/usr/bin/env python

# Vector3 class - super minimal; just adding things as I need them
import math

class Vector3:
	def __init__(self, x=0, y=0, z=0):
		self.x = x
		self.y = y
		self.z = z

	# normalizes self and returns the length
	def normalize(self):
		length2 = self.x * self.x + self.y * self.y + self.z * self.z
		length = math.sqrt(length2)
		if length != 0: #if our vector is a zero vector
			self.x /= length
			self.y /= length
			self.z /= length
		return length

	def length(self):
		length2 = self.x * self.x + self.y * self.y + self.z * self.z
		return math.sqrt(length2)

	def cross(a,b):
		return Vector3(a.y*b.z - a.z*b.y, a.z*b.x - a.x*b.z, a.x*b.y-a.y*b.x)

	def dot(a,b):
		return a.x*b.x + a.y*b.y + a.z*b.z

	def __eq__(self,vector):
		return (self.x == vector.x and self.y == vector.y and self.z == vector.z)

	def __ne__(self,vector):
		return (self.x != vector.x or self.y != vector.y or self.z != vector.z)

	def __add__(self, vector):
		return Vector3(self.x + vector.x, self.y + vector.y, self.z + vector.z)

	def __sub__(self, vector):
		return Vector3(self.x - vector.x, self.y - vector.y, self.z - vector.z)

	def __neg__(self):
		return Vector3(-self.x, -self.y, -self.z)

	def __mul__(self, scalar):
		return Vector3(self.x * scalar, self.y * scalar, self.z * scalar)

	def __rmul__(self, scalar):
		return Vector3(scalar * self.x, scalar * self.y, scalar * self.z)

	def __div__(self, scalar):
		return Vector3(self.x/scalar, self.y/scalar, self.z/scalar)

	def __repr__(self):
		return "<%f,%f,%f>" % (self.x,self.y,self.z)

	def __str__(self):
		return "<%f,%f,%f>" % (self.x,self.y,self.z)

	def __iter__(self):
		return iter([self.x,self.y,self.z])