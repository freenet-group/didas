from collections import defaultdict
from ._version import __version__


def dic(o):
    r = defaultdict(dict)
    for d in dir(o):
        a = getattr(o, d)
        t = type(a)
        r[t][d] = a
    return dict(r)
