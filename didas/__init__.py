from collections import defaultdict

try:
    from ._version import __version__
except ImportError:
    from importlib.metadata import version

    __version__ = version("didas")


def dic(o):
    r = defaultdict(dict)
    for d in dir(o):
        a = getattr(o, d)
        t = type(a)
        r[t][d] = a
    return dict(r)
