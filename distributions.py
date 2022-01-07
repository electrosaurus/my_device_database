import random
import scipy.stats as stats
from datetime import *


class DateTimeDistribution:
    def __init__(self, a, b=datetime.now()):
        self.a = a
        self.b = b

    def rvs(self, size=None):
        if size is None:
            a = int(self.a.timestamp())
            b = int(self.b.timestamp())
            return datetime.fromtimestamp(random.randint(a, b))
        return [self.rvs() for _ in range(size)]


class TimeDeltaDistribution:
    def __init__(self, m, std):
        self.m = m
        self.std = std
        l = m.total_seconds() / std.total_seconds() ** 2
        k = m.total_seconds() * l
        self.distr = stats.gamma(k, scale=1/l)
    
    def rvs(self, size=None):
        if size is None:
            return timedelta(seconds=self.distr.rvs())
        else:
            return (timedelta(seconds=s) for s in self.distr.rvs(size))


class PriceDistribution:
    def __init__(self, m, std):
        self.m = m
        self.std = std
        l = m / std ** 2
        k = m * l
        self.distr = stats.gamma(k, scale=1/l)

    def rvs(self, size=None):
        if size is None:
            p = self.distr.rvs(size)
            if p < 1000:
                return int(p / 10) * 10
            elif p < 5000:
                return int(p / 100) * 100
            elif p < 30000:
                return int(p / 500) * 500
            else:
                return int(p / 1000) * 1000
        else:
            return [self.rvs() for _ in range(size)]
