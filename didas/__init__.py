from collections import defaultdict

try:
    from ._version import __version__
except ImportError:
    __version__ = "UNKNOWN"


def dic(o):
    r = defaultdict(dict)
    for d in dir(o):
        a = getattr(o, d)
        t = type(a)
        r[t][d] = a
    return dict(r)
