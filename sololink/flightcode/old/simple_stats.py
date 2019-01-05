import math

class SimpleStats:

    def __init__(self):
        self.reset()

    def reset(self):
        self._count = 0
        self._sum_x = 0.0
        self._sum_x2 = 0.0
        self._max_x = None
        self._min_x = None

    def update(self, x):
        self._count += 1
        self._sum_x += x
        self._sum_x2 += (x * x)
        if self._max_x is None or self._max_x < x:
            self._max_x = float(x)
        if self._min_x is None or self._min_x > x:
            self._min_x = float(x)

    # always returns int
    def count(self):
        return self._count

    # always returns float
    def max(self):
        return self._max_x

    # always returns float
    def min(self):
        return self._min_x

    # always returns float
    def average(self):
        if(self._count > 0):
            return float(self._sum_x / self._count)
        else:
            return 0

    # always returns float
    def stdev(self):
        avg = self.average()
        if(self._count > 0):
            return math.sqrt(self._sum_x2 / self._count - avg * avg)
        else:
            return 0
