# Apply the accessibility rules to the hand-built canvas pages (design-system/Accessibility.md).
# These pages are edited by hand, not generated; this applies the same changes
# gen.accessible() makes to generated pages. Running it twice changes nothing.
import sys

from gen import OUT, accessible

HAND_BUILT = ['Marketplace', 'Aircraft', 'AddAircraft', 'ConfigSetup', 'Assessment', 'Staff',
              'OrgChart', 'Fleet', 'Reviews', 'Settings']

for name in sys.argv[1:] or HAND_BUILT:
    path = OUT + name + '.dc.html'
    before = open(path).read()
    after = accessible(before)
    if after != before:
        open(path, 'w').write(after)
        print('Changed', name)
