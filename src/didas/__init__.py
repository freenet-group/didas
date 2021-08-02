from collections import defaultdict
import pandas as pd


def dic(o):
    pd.DataFrame()
    r = defaultdict(set)
    for d in dir(o):
        a = getattr(o, d)
        t = type(a)
        r[t].add(d)
    return dict(r)
