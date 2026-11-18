import sys, json, re
sys.path.insert(0, '/home/claude/scripts')
from expand import expand, HELPER
P='/home/claude/overhaul/project/'
def js_wrap(s, names_cols, retpat):
    i = s.index(retpat)
    s = s[:i] + HELPER + s[i:]
    j = s.index(retpat); k = s.index('\n', j)
    line = s[j:k]
    for n, cols in names_cols:
        line = re.sub(r'(?<![\w.:])%s(?=[,} ])(?!:)' % n, "%s: X('%s', %s, %s)" % (n, n, n, json.dumps(cols)), line, 1)
    return s[:j] + line + s[k:]

# Aircraft
s = open(P+'Aircraft.dc.html').read()
nc = []
for n, a in [('flights','l'),('programme','r'),('directives','d')]:
    s, cols = expand(s, n, a, 320); nc.append((n, [list(c) for c in cols]))
s, _ = expand(s, 'pos.history', 'h', 360, detail=False)
s = js_wrap(s, nc, '    return { t, dark, tree')
open(P+'Aircraft.dc.html','w').write(s)

# AddAircraft: one-line, keep picker
s = open(P+'AddAircraft.dc.html').read()
s, _ = expand(s, 'shown', 'r', 260, detail=False)
open(P+'AddAircraft.dc.html','w').write(s)

# ConfigSetup: one-line
s = open(P+'ConfigSetup.dc.html').read()
for n, a in [('templateRows','r'),('positions','r'),('mods','m')]:
    s, _ = expand(s, n, a, 280, detail=False)
open(P+'ConfigSetup.dc.html','w').write(s)
print('ok')
