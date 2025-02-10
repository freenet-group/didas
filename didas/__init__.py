from collections import defaultdict
from typing import Any, Dict, Type

from importlib_metadata import version

try:
    from ._version import __version__
except ImportError:
    try:
        __version__ = version("didas")
    except (ImportError, LookupError) as e:
        __version__ = str(e)


def dic(o: Any) -> Dict[Type[Any], Dict[str, Any]]:
    r: Dict[Type[Any], Dict[str, Any]] = defaultdict(dict)
    for d in dir(o):
        a = getattr(o, d)
        t = type(a)
        r[t][d] = a
    return dict(r)
