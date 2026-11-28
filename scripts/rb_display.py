# Settings, Display: the person's own display settings (design-system/Accessibility.md, Display Settings).
# Both themes are on the canvas: this page, and DisplayDark showing it with dark set.
# Both densities are shown by the two tables at the foot of the page.
from gen import *

ST = lambda text, c, sub=None: {'text': text, 'dot': c, 'status': True, 'sub': sub}

SETTINGS = [
    ['Appearance', 'System', 'System, Light, Dark', 'Follows the Device Colour Scheme'],
    ['Contrast', 'System', 'System, Standard, High', {'text': 'Follows the Device Contrast Setting', 'sub': 'High: Muted Text and Lines at 7:1 or More, SC 1.4.6'}],
    ['Text Size', 'Default', 'Default, Large, Larger', {'text': 'From the Root Size', 'sub': 'Independent of Browser Zoom'}],
    ['Density', 'Compact', 'Compact, Comfortable', {'text': 'Comfortable: 44 Pixel Targets', 'sub': 'For Gloves and Tablets, SC 2.5.5'}],
    ['Reduce Motion', 'System', 'System, On, Off', 'Follows the Device Motion Setting'],
]

FLEET = [
    [{'text': 'G-DGHI', 'href': 'Aircraft.dc.html'}, ST('Unserviceable', 'r'), 'Rectify Defect'],
    [{'text': 'G-EJKL', 'href': 'Aircraft.dc.html'}, ST('Serviceable', 'g'), {'text': '18 Days', 'dot': 'a'}],
]
COLS = [('Aircraft Registration', '220px', 'left'), ('Status', '220px', 'left'), ('Remaining', '', 'left')]


def comfortable(markup):
    """The same table at the Comfortable density: 44 pixel targets and taller rows."""
    return (markup.replace('padding: 12px 16px', 'padding: 16px 16px')
            .replace('padding: 10px 0 10px 12px', 'padding: 8px 0 8px 12px')
            .replace('width: 28px; height: 28px', 'width: 44px; height: 44px'))


page('Display.dc.html', 'Display Settings', 'display', 1500, [
    header('Settings', 'Display Settings', '', [btn('Edit Settings', primary=True)],
           tabs=('settings', 'display'), trail='Settings=Settings.dc.html|Display'),
    section('disp-h', 'Your Display', table(
        [('Setting', '220px', 'left'), ('Chosen', '160px', 'left'), ('Options', '260px', 'left'), ('Behaviour', '', 'left')],
        SETTINGS, minw=900)),
    section('compact-h', 'Compact', table(COLS, FLEET, minw=720)),
    section('comfortable-h', 'Comfortable', comfortable(table(COLS, FLEET, minw=720))),
])

open(OUT + 'DisplayDark.dc.html', 'w').write('''<!doctype html>
<html lang="en-GB">
<head>
<meta charset="utf-8">
<title>Display Settings, Dark</title>
<script src="./support.js"></script>
</head>
<body>
<x-dc>
<helmet>
<style>
body{margin:0;background:#0A0A0A}
</style>
</helmet>
<div style="background: #0A0A0A; min-height: 100vh">
  <dc-import name="Display" dark="{{true}}" hint-size="100%,1500px"></dc-import>
</div>
</x-dc>
<script type="text/x-dc" data-dc-script data-props='{"$preview":{"width":1440,"height":1500}}'>
class Component extends DCLogic {
  renderVals() {
    return {};
  }
}
</script>
</body>
</html>
''')
print('wrote Display.dc.html, DisplayDark.dc.html')
