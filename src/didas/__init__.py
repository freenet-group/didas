from collections import defaultdict

def dic(o):
    r = defaultdict(set)
    for d in dir(o):
        a = getattr(o, d)
        t = type(a)
        r[t].add(d)
    return dict(r)
