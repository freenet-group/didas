from collections import defaultdict

from importlib_metadata import version

try:
    from ._version import __version__
except ImportError:
    try:
        __version__ = version("didas")
    except (ImportError, LookupError) as e:
        __version__ = str(e)


def dic(o):
    r = defaultdict(dict)
    for d in dir(o):
        a = getattr(o, d)
        t = type(a)
        r[t][d] = a
    return dict(r)
