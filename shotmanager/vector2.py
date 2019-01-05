#  vector2.py
#  shotmanager
#
#  A two-dimensional vector class.
#
#  Created by Will Silva on 11/22/2015.
#  Copyright (c) 2015 3D Robotics.
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import math


class Vector2:

    def __init__(self, x, y):
        self.x = x
        self.y = y

    # normalizes self and returns the length
    def normalize(self):
        length2 = self.x * self.x + self.y * self.y
        length = math.sqrt(length2)
        if length != 0:  # if our vector is a zero vector
            self.x /= length
            self.y /= length
        return length

    def length(self):
        length2 = self.x * self.x + self.y * self.y
        return math.sqrt(length2)

    def dot(a, b):
        return a.x * b.x + a.y * b.y

    def __add__(self, vector):
        return Vector2(self.x + vector.x, self.y + vector.y)

    def __sub__(self, vector):
        return Vector2(self.x - vector.x, self.y - vector.y)

    def __mul__(self, scalar):
        return Vector2(self.x * scalar, self.y * scalar)

    def __rmul__(self, scalar):
        return Vector2(scalar * self.x, scalar * self.y)

    def __repr__(self):
        return "<%f,%f>" % (self.x, self.y)

    def __str__(self):
        return "<%f,%f>" % (self.x, self.y)

    def __iter__(self):
        return iter([self.x, self.y])
