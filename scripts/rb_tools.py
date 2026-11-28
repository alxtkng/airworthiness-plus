from gen import *
import gen, json

# Logistics: Tools and Equipment (145.A.40 and AMC, CAO.A.050, CAO.A.060(d) and (i), CAO.A.105).
TR = 'Logistics=PartsReceived.dc.html|Tools and Equipment=Tools.dc.html'
S = lambda text, c, sub=None: {'text': text, 'dot': c, 'status': True, 'sub': sub}
WP = lambda r: {'text': r, 'href': 'WorkPackages.dc.html', 'mono': True}
MONO = lambda r: {'text': r, 'mono': True}
TOOL = lambda name, n, href=None: {'text': name + ' ' + n, 'href': href}


# ---------- Register: a filtered table, so its rows carry a filter key ----------
def ftable(cols, rows, minw=1040):
    """gen.table with each row (and its detail) shown only while its filter group is on."""
    th = ''.join(f'<th scope="col" style="padding: 12px 16px; font-weight: 500; white-space: nowrap; border-bottom: 1px solid {{{{t.border}}}}; text-align: {a}{"; width: " + w if w else ""}">{E(l)}</th>' for l, w, a in cols)
    th = '<th scope="col" style="width: 40px; padding: 12px 0 12px 12px; border-bottom: 1px solid {{t.border}}"><span style="position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0)">Details</span></th>' + th
    body, groups = '', []
    for key, r, extra in rows:
        rid = 'r%d' % (len(gen.ROWS) + 1)
        gen.ROWS.append(rid)
        groups.append([rid, key])
        line = '{{line.%s}}' % rid
        b = (f'<td style="width: 40px; padding: 10px 0 10px 12px; border-bottom: 1px solid {line}; vertical-align: middle">'
             f'<button type="button" aria-expanded="{{{{exp.{rid}}}}}" aria-label="Show Details" onClick="{{{{tog.{rid}}}}}" style="font: inherit; width: 28px; height: 28px; border: 0; border-radius: 6px; background: transparent; cursor: pointer; display: inline-flex; align-items: center; justify-content: center">{gen.CHEV % rid}</button></td>')
        tds = ''.join(
            f'<td style="padding: 12px 16px; border-bottom: 1px solid {line}; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: {(w if w else "360px")}; text-align: {cols[i][2]}">{cell(plain(v), i == 0)}</td>'
            for i, (v, (l, w, a)) in enumerate(zip(r, cols)))
        facts = [(cols[i][0], v) for i, v in enumerate(r) if has_text(v)] + extra
        fx = ''.join(
            f'<div style="display: flex; flex-direction: column; gap: 4px; min-width: 0"><span style="font-size: 13px; line-height: 16px; color: {{{{t.muted}}}}">{E(l)}</span><span style="font-size: 14px; line-height: 20px">{cell(v)}</span></div>'
            for l, v in facts)
        detail = (f'<sc-if value="{{{{open.{rid}}}}}" hint-placeholder-val="{{{{false}}}}"><tr><td colspan="{len(cols) + 1}" style="padding: 4px 16px 16px 52px; border-bottom: 1px solid {{{{t.row}}}}">'
                  f'<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); column-gap: 32px; row-gap: 14px">{fx}</div></td></tr></sc-if>')
        body += f'<sc-if value="{{{{vis.{rid}}}}}" hint-placeholder-val="{{{{true}}}}"><tr style="background: {{{{bg.{rid}}}}}">{b}{tds}</tr>{detail}</sc-if>\n'
    html_ = f'''<div style="overflow-x: auto; border: 1px solid {{{{t.border}}}}; border-radius: 6px">
<table style="width: 100%; min-width: {minw}px; border-collapse: collapse; font-size: 14px; line-height: 20px">
<thead><tr style="background: {{{{t.sidebar}}}}; color: {{{{t.muted}}}}; font-size: 13px; text-align: left">{th}</tr></thead>
<tbody>
{body}</tbody>
</table>
</div>
'''
    return html_, groups


SEG = '''    <div role="group" aria-label="Control" style="align-self: flex-start; display: inline-flex; flex-wrap: wrap; padding: 3px; border-radius: 6px; background: {{t.empty}}; gap: 2px">
      <sc-for list="{{segs}}" as="f" hint-placeholder-count="5">
        <button type="button" aria-pressed="{{f.pressed}}" onClick="{{f.pick}}" style="font: inherit; font-size: 13px; font-weight: 500; height: 32px; padding: 0 12px; border-radius: 6px; border: 0; cursor: pointer; color: {{t.text}}; background: {{f.bg}}; box-shadow: {{f.shadow}}">{{f.label}} <span style="color: {{t.muted}}">{{f.count}}</span></button>
      </sc-for>
    </div>
'''


def filtered_page(name, title, active, height, parts, groups, segs):
    """gen.page, plus a segmented control state that hides rows outside the chosen group."""
    js = ('''    t.empty = dark ? '#1A1A1A' : '#F2F2F2'; t.raised = dark ? '#2E2E2E' : '#FFFFFF';
    const groups = __GROUPS__, segDefs = __SEGS__, seg = this.state.seg || 'all';
    const vis = {};
    groups.forEach(g => { vis[g[0]] = seg === 'all' || g[1] === seg; });
    const segs = segDefs.map(s => { const on = seg === s[0]; const n = groups.filter(g => s[0] === 'all' || g[1] === s[0]).length;
      return { label: s[1], count: String(n), pressed: on ? 'true' : 'false', bg: on ? t.raised : 'transparent', shadow: on ? '0 1px 2px rgba(0,0,0,0.12)' : 'none', pick: () => this.setState({ seg: s[0] }) }; });
    return { t, dark, open, exp, rot, tog, line, bg, vis, segs };''').replace('__GROUPS__', json.dumps(groups)).replace('__SEGS__', json.dumps(segs))
    tail = (gen.TAIL % height).replace('__IDS__', json.dumps(gen.ROWS))
    tail = tail.replace('this.state = { open: {} }', "this.state = { open: {}, seg: 'all' }")
    tail = tail.replace('    return { t, dark, open, exp, rot, tog, line, bg };', js)
    s = gen.HEAD % (E(title), active, height) + ''.join(parts) + tail
    del gen.ROWS[:]
    open(gen.OUT + name, 'w').write(gen.named_tables(s))


CAL, SRV, INS = 'cal', 'srv', 'ins'
REG_COLS = [('Tool', '300px', 'left'), ('Control', '240px', 'left'), ('Location', '', 'left'), ('Next Due', '200px', 'left'), ('Status', '190px', 'left')]
OWN = ('Owned By', 'Organisation')
reg_rows = [
    (CAL, [TOOL('Torque Wrench', '0142', 'Tool.dc.html'), {'text': 'Calibration, Every 6 Months', 'sub': 'Reduced From 12 Months After Results'}, {'text': 'Issued, WP-2026-046', 'sub': 'Chris Moore, B1.2'}, '14 March 2027', S('Serviceable', 'g')],
     [('Range', '20–100 Newton Metres'), ('Serial Number', '[Serial Number]'), OWN, ('Last Calibrated', '14 September 2026, [Calibration Laboratory]'), ('Classification', 'Standard Tool')]),
    (CAL, [TOOL('Torque Wrench', '0143'), 'Calibration, Every 12 Months', {'text': '[Calibration Laboratory]', 'sub': 'Order 2026-C07'}, {'text': 'Back by 28 November 2026', 'sub': 'Calibration Due 20 November 2026'}, S('At Calibration', 'o')],
     [('Range', '4–20 Newton Metres'), ('Serial Number', '[Serial Number]'), OWN, ('Sent', '14 November 2026'), ('Classification', 'Standard Tool')]),
    (CAL, [TOOL('Tyre Pressure Gauge', '0151'), 'Calibration, Every 12 Months', 'Line Kit, Home Airfield', {'text': '1 December 2026', 'dot': 'a', 'sub': '13 Days Left'}, S('Serviceable', 'g')],
     [('Range', '0–100 Pounds per Square Inch'), ('Serial Number', '[Serial Number]'), OWN, ('Method', 'Tool Manufacturer’s Instructions'), ('Last Calibrated', '1 December 2025, [Calibration Laboratory]'), ('Next Step', 'Raise Calibration Order, Stand-In Gauge From Hangar Stock')]),
    (CAL, [TOOL('Digital Multimeter', '0160'), 'Calibration, Every 24 Months', 'Quarantine Shelf, Stores', 'Held', S('Quarantined', 'r', 'Certificate Without Traceability')],
     [('Serial Number', '[Serial Number]'), OWN, ('Method', 'Tool Manufacturer’s Instructions'), ('Returned', '27 October 2026, Order 2026-C06'), ('Acceptance', 'Rejected, No Traceability to the Standard Used'), ('Next Step', 'Corrected Certificate Requested 29 October 2026')]),
    (CAL, [TOOL('Differential Compression Tester', '0170'), 'Calibration, Every 12 Months', 'Hangar, Tool Board 1', '9 June 2027', S('Serviceable', 'g')],
     [('Serial Number', '[Serial Number]'), OWN, ('Method', 'Tool Manufacturer’s Instructions'), ('Last Calibrated', '9 June 2026, [Calibration Laboratory]')]),
    (CAL, [TOOL('Cable Tensiometer', '0175'), 'Calibration, Every 12 Months', {'text': 'Issued, WP-2026-046', 'sub': 'Chris Moore, B1.2'}, '22 April 2027', S('Serviceable', 'g')],
     [('Range', '30–150 Pounds Tension'), ('Serial Number', '[Serial Number]'), OWN, ('Method', 'Tool Manufacturer’s Instructions'), ('Last Calibrated', '22 April 2026, [Calibration Laboratory]')]),
    (CAL, [TOOL('Pitot-Static Test Set', '0180'), 'Calibration, Every 12 Months', 'Avionics Bench', '2 April 2027', S('Serviceable', 'g')],
     [('Serial Number', '[Serial Number]'), OWN, ('Method', 'Tool Manufacturer’s Instructions'), ('Last Calibrated', '2 April 2026, [Calibration Laboratory]')]),
    (CAL, [TOOL('Micrometer', '0190'), 'Calibration, Every 12 Months', 'Engine Bench', '20 August 2027', S('Serviceable', 'g')],
     [('Range', '0–25 Millimetres'), ('Serial Number', '[Serial Number]'), OWN, ('Last Calibrated', '20 August 2026, [Calibration Laboratory]')]),
    (CAL, [TOOL('Torque Screwdriver', '0405'), 'Calibration, Every 12 Months', 'Personal Toolbox, Sam Patel', '9 July 2027', S('Serviceable', 'g')],
     [('Range', '1–6 Newton Metres'), ('Serial Number', '[Serial Number]'), ('Owned By', 'Sam Patel, Personal Tool'), ('Last Calibrated', '9 July 2026, [Calibration Laboratory]')]),
    (SRV, [TOOL('Grease Gun', '0201'), 'Servicing, Every 6 Months', 'Hangar, Tool Board 1', '3 February 2027', S('Serviceable', 'g')],
     [OWN, ('Method', 'Tool Manufacturer’s Instructions'), ('Last Serviced', '3 August 2026')]),
    (SRV, [TOOL('Hydraulic Aircraft Jack', '0210'), 'Servicing, Every 12 Months', 'Segregated, Hangar Bay 2', {'text': 'Repair', 'sub': 'Seal Kit Due 25 November 2026'}, S('Unserviceable', 'r', 'Seal Leaking')],
     [('Capacity', '3 Tonnes'), ('Serial Number', '[Serial Number]'), OWN, ('Label', 'Unserviceable, 10 November 2026'), ('Repair', 'Seal Replaced In-House to the Tool Manufacturer’s Instructions'), ('Seal Kit', '[Parts Distributor]')]),
    (SRV, [TOOL('Aircraft Battery Charger', '0220'), 'Servicing, Every 12 Months', 'Hangar, Battery Room', '18 May 2027', S('Serviceable', 'g')],
     [OWN, ('Method', 'Tool Manufacturer’s Instructions'), ('Last Serviced', '18 May 2026')]),
    (INS, [TOOL('Jack Point Adapter', '0301'), 'Inspection Before Use', 'Hangar, Tool Board 2', 'Before Each Use', S('Serviceable', 'g')],
     [('Part Number', '[Part Number]'), ('For', 'Piper PA-28 Series (Lycoming)'), ('Classification', 'Task-Specific Tool, Named in the Maintenance Data'), OWN]),
    (INS, [TOOL('Propeller Protractor', '0302'), 'Inspection Before Use', 'Hangar, Tool Board 2', 'Before Each Use', S('Serviceable', 'g')],
     [('Classification', 'Standard Tool'), OWN]),
    (INS, [{'text': 'Wheel Bearing Puller 0303', 'href': 'AltTool.dc.html'}, 'Inspection Before Use', 'Hangar, Tool Board 2', 'Before Each Use', S('Serviceable', 'g')],
     [('In Place Of', '[Part Number], Named in the Maintenance Data'), ('Classification', 'Alternative Tool'), ('Equivalence Statement', '2026-A02, Released 6 June 2026'), OWN]),
    (INS, [{'text': 'Magneto Timing Indicator 0304', 'href': 'AltTool.dc.html'}, 'Inspection Before Use', 'Stores, Not Issued', 'Before Each Use', S('Not Released', 'a', 'Validation 20 November 2026')],
     [('In Place Of', '[Part Number], Named in the Engine Maintenance Manual'), ('Classification', 'Alternative Tool'), ('Assessment', '2026-A03, in Progress'), OWN]),
    ('wd', [TOOL('Torque Wrench', '0099'), 'Calibration, Every 12 Months', 'Withdrawn 4 March 2025', '—', 'Withdrawn'],
     [('Range', '5–25 Newton Metres'), ('Reason', 'Failed Calibration, Beyond Repair'), ('Record', 'Kept with the Calibration Records')]),
]
reg_table, reg_groups = ftable(REG_COLS, reg_rows)

issued = table(
    [('Tool', '260px', 'left'), ('Issued To', '200px', 'left'), ('Work Package', '160px', 'left'), ('Aircraft Registration', '170px', 'left'), ('Issued', '190px', 'left'), ('Returned', '', 'left')],
    [[TOOL('Torque Wrench', '0142', 'Tool.dc.html'), 'Chris Moore, B1.2', WP('WP-2026-046'), 'G-DGHI', '17 November 2026', {'text': 'Not Returned', 'sub': 'Before Release to Service'}],
     [TOOL('Cable Tensiometer', '0175'), 'Chris Moore, B1.2', WP('WP-2026-046'), 'G-DGHI', '17 November 2026', {'text': 'Not Returned', 'sub': 'Before Release to Service'}],
     [TOOL('Torque Wrench', '0142', 'Tool.dc.html'), 'Sam Patel, B1.2', WP('WP-2026-043'), 'G-CDEF', '2 November 2026', '4 November 2026'],
     [TOOL('Grease Gun', '0201'), 'Sam Patel, B1.2', WP('WP-2026-043'), 'G-CDEF', '2 November 2026', '4 November 2026']], minw=1080)

filtered_page('Tools.dc.html', 'Tools and Equipment', 'tools', 1950, [
    header('Logistics', 'Tool and Equipment Register', '', [btn('Raise a Calibration Order', href='Providers.dc.html'), btn('Receive a Tool', primary=True)],
           tabs=('tools', 'tools'), trail=TR + '|Register'),
    section('att-h', 'Needs Attention', checklist([
        ('r', 'Digital Multimeter 0160 Quarantined', 'Calibration Certificate Without Traceability, Corrected Certificate Requested 29 October 2026'),
        ('r', 'Hydraulic Aircraft Jack 0210 Unserviceable', 'Seal Leaking, Seal Kit From [Parts Distributor] Due 25 November 2026'),
        ('a', 'Tyre Pressure Gauge 0151 Calibration Due 1 December 2026', 'Raise a Calibration Order, 13 Days Left'),
        ('a', 'Magneto Timing Indicator 0304 Not Released', 'Alternative Tool Validation Booked 20 November 2026'),
    ])),
    f'''    <section aria-labelledby="reg-h" style="display: flex; flex-direction: column; gap: 16px">
      <h2 id="reg-h" style="margin: 0; font-size: 16px; line-height: 24px; font-weight: 600; letter-spacing: -0.32px">Register</h2>
      <p style="margin: 0; font-size: 13px; line-height: 18px; color: {{{{t.muted}}}}">Calibrated to an Officially Recognised Standard, Label Shows the Next Due Date</p>
{SEG}{reg_table}    </section>
''',
    section('iss-h', 'Issued Tools', issued, intro='All Tools Accounted for Before the Certificate of Release to Service'),
], reg_groups, [['all', 'All'], [CAL, 'Calibration'], [SRV, 'Servicing'], [INS, 'Inspection Before Use'], ['wd', 'Withdrawn']])


# ---------- Tool record: Torque Wrench 0142 ----------
def fact(label, value, note='', c=None):
    d = dot(c) if c else ''
    n = f'<span style="font-size: 13px; line-height: 18px; color: {{{{t.muted}}}}">{E(L(note))}</span>' if note else ''
    return (f'<div style="display: flex; flex-direction: column; gap: 4px"><span style="font-size: 13px; line-height: 18px; color: {{{{t.muted}}}}">{E(label)}</span>'
            f'<span style="display: inline-flex; align-items: center; gap: 8px; font-size: 14px; line-height: 20px; font-weight: 500">{d}{E(L(value))}</span>{n}</div>')

tool_head = f'''    <dc-import name="TopBar" trail="{E(TR)}" dark="{{{{dark}}}}" hint-size="1100px,56px"></dc-import>
    <div style="display: flex; flex-wrap: wrap; justify-content: space-between; align-items: flex-end; gap: 16px; margin-top: -12px">
      <div style="display: flex; flex-direction: column; gap: 4px">
        <h1 style="margin: 0; font-size: 24px; line-height: 32px; font-weight: 600; letter-spacing: -0.96px">Torque Wrench 0142</h1>
        <span style="font-size: 14px; line-height: 20px; color: {{{{t.muted}}}}">Calibrated Tool, 20–100 Newton Metres</span>
      </div>
      <div style="display: flex; flex-wrap: wrap; gap: 8px">{btn('Quarantine')}{btn('Send for Calibration', primary=True, href='Providers.dc.html')}</div>
    </div>
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); column-gap: 32px; row-gap: 16px; padding: 16px 20px; border-radius: 6px; border: 1px solid {{{{t.border}}}}">
      {fact('Status', 'Serviceable', 'Label Checked 16 September 2026', 'g')}
      {fact('Control', 'Calibration, Every 6 Months', 'Reduced From 12 Months, 14 September 2026')}
      {fact('Next Calibration Due', '14 March 2027', '116 Days Left')}
      {fact('Accuracy Required', 'Within 4 Percent', 'Tool Manufacturer’s Instructions')}
      {fact('Location', 'Issued, WP-2026-046', 'Chris Moore, B1.2, G-DGHI')}
      {fact('Serial Number', '[Serial Number]', 'Owned by the Organisation')}
    </div>
'''

label_box = f'''<div style="display: flex; flex-wrap: wrap; gap: 40px; align-items: flex-start">
      <div style="flex: 0 1 300px; box-sizing: border-box; border: 1px solid {{{{t.border}}}}; border-radius: 6px; padding: 14px 16px; display: grid; grid-template-columns: 96px minmax(0, 1fr); row-gap: 8px; font-size: 14px; line-height: 20px">
        <span style="grid-column: 1 / -1; display: inline-flex; align-items: center; gap: 8px; font-weight: 600">{dot('g')}Serviceable</span>
        <span style="color: {{{{t.muted}}}}">Tool</span><span style="font-family: 'Geist Mono Embedded', 'Geist Mono', monospace; font-size: 13px">0142</span>
        <span style="color: {{{{t.muted}}}}">Calibrated</span><span>14 September 2026</span>
        <span style="color: {{{{t.muted}}}}">Next Due</span><span style="font-weight: 500">14 March 2027</span>
        <span style="color: {{{{t.muted}}}}">Accepted By</span><span>Chris Moore, B1.2</span>
        <span style="color: {{{{t.muted}}}}">Organisation</span><span>[Your Organisation]</span>
      </div>
      <div style="flex: 1 1 360px; min-width: 0">
{checklist([
    ('g', 'Laboratory Accreditation Valid on the Day', '[Calibration Laboratory], United Kingdom Accreditation Service [Number]'),
    ('g', 'Standard Used Stated', 'ISO 6789-2'),
    ('g', 'Traceability to National Standards Shown', 'Reference Given on the Certificate'),
    ('g', 'Results As Found and As Left', 'As Left Within 2 Percent'),
    ('g', 'Within the Limits on Order 2026-C05', 'Accepted 16 September 2026, Chris Moore, B1.2'),
])}      </div>
    </div>
'''

page('Tool.dc.html', 'Torque Wrench 0142', 'tool', 1650, [
    tool_head,
    section('lab-h', 'Label and Acceptance', label_box),
    section('hist-h', 'Calibration History', table(
        [('Calibrated', '190px', 'left'), ('Laboratory', '230px', 'left'), ('Standard Used', '150px', 'left'), ('As Found', '', 'left'), ('As Left', '200px', 'left'), ('Interval After', '170px', 'left')],
        [['14 September 2026', {'text': '[Calibration Laboratory]', 'sub': 'Certificate [Number], Order 2026-C05'}, 'ISO 6789-2', {'text': '5.2 Percent High at 100 Newton Metres', 'dot': 'r'}, 'Adjusted, Within 2 Percent', {'text': '6 Months', 'sub': 'Reduced Because of the Result'}],
         ['12 September 2025', {'text': '[Calibration Laboratory]', 'sub': 'Certificate [Number]'}, 'ISO 6789-2', 'Within Limits', 'No Adjustment', '12 Months'],
         ['10 September 2024', {'text': '[Calibration Laboratory]', 'sub': 'Certificate [Number]'}, 'ISO 6789-2', 'Within Limits', 'No Adjustment', {'text': '12 Months', 'sub': 'Entered the Register'}]], minw=1100)),
    section('imp-h', 'Work Since the Previous Calibration', table(
        [('Used On', '220px', 'left'), ('Aircraft Registration', '170px', 'left'), ('Task', '', 'left'), ('Outcome', '', 'left')],
        [['12 September 2026', 'G-ABCD', 'Cylinder Base Nuts', {'text': 'Re-Checked with Torque Wrench 0143', 'sub': 'Within Limits, No Action'}],
         ['2 August 2026', 'G-BXYZ', 'Propeller Bolts After Removal', {'text': 'Re-Torqued 20 September 2026', 'sub': 'Recorded in the Propeller Logbook'}],
         ['14 May 2026', 'G-FMNO', 'Wheel Axle Nut', {'text': 'No Effect', 'sub': 'Low Torque Value, Error Found at 100 Newton Metres Only'}]], minw=1000),
        intro='Found Out of Limits on 14 September 2026, Every Use Since 12 September 2025 Reviewed'),
    section('chk-h', 'Checks Between Calibrations', table(
        [('Checked', '220px', 'left'), ('Against', '', 'left'), ('Reading', '300px', 'left'), ('Result', '160px', 'left')],
        [['13 November 2026', 'Torque Tester 0145', '100.8 Newton Metres at 100', 'Passed'],
         ['14 October 2026', 'Torque Tester 0145', '99.6 Newton Metres at 100', 'Passed']], minw=900),
        intro='Monthly, Supports the Interval, Never Replaces Calibration'),
])


# ---------- Service Providers ----------
page('Providers.dc.html', 'Service Providers', 'providers', 1300, [
    header('Logistics', 'Service Providers', '', [btn('Suppliers', href='Suppliers.dc.html'), btn('Raise a Calibration Order', primary=True)],
           tabs=('tools', 'providers'), trail=TR + '|Service Providers'),
    section('ord-h', 'Calibration Orders', table(
        [('Order', '130px', 'left'), ('Tool', '260px', 'left'), ('Provider', '230px', 'left'), ('Sent', '180px', 'left'), ('Acceptance', '', 'left')],
        [[MONO('2026-C07'), TOOL('Torque Wrench', '0143'), '[Calibration Laboratory]', '14 November 2026', S('At Laboratory', 'o', 'Expected 28 November 2026')],
         [MONO('2026-C06'), TOOL('Digital Multimeter', '0160'), '[Calibration Laboratory]', '13 October 2026', S('Rejected', 'r', 'No Traceability on the Certificate, Corrected Certificate Requested')],
         [MONO('2026-C05'), TOOL('Torque Wrench', '0142', 'Tool.dc.html'), '[Calibration Laboratory]', '1 September 2026', S('Accepted', 'g', 'Found 5.2 Percent High, Adjusted, Interval Reduced to 6 Months')]], minw=1040)),
    section('prov-h', 'Providers', table(
        [('Provider', '240px', 'left'), ('Service', '', 'left'), ('Basis', '280px', 'left'), ('Next Evaluation', '190px', 'left'), ('Status', '150px', 'left')],
        [[{'text': '[Calibration Laboratory]', 'href': 'Suppliers.dc.html'}, 'Calibration of Torque, Pressure, Tension, Electrical and Dimensional Tools', {'text': 'Accredited Laboratory', 'sub': 'United Kingdom Accreditation Service [Number], Valid to 30 June 2027'}, '11 January 2027', S('Approved', 'g')],
         [{'text': '[Propeller Organisation]', 'href': 'Suppliers.dc.html'}, 'Loan of Propeller Dynamic Balancing Kit', {'text': 'Access Procedure for Occasional Tools', 'sub': 'Calibration Certificate Checked on Each Loan'}, {'text': '30 November 2026', 'dot': 'a', 'sub': '12 Days Left'}, S('Approved', 'g')],
         [{'text': '[Parts Distributor]', 'href': 'Suppliers.dc.html'}, 'Purchase of Tools and Seal Kits', {'text': 'Accepted on Receipt', 'sub': 'Certificate of Conformity'}, '3 March 2027', S('Approved', 'g')]], minw=1100),
        intro='Evaluated and Approved in Suppliers'),
    section('req-h', 'What Each Calibration Order Sets', table(
        [('Item', '220px', 'left'), ('Requirement', '', 'left'), ('Point', '220px', 'left')],
        [['Standard', 'Officially Recognised Standard, Traceable to National Standards', '145.A.40(b), CAO.A.050(b)'],
         ['Method and Interval', 'Tool Manufacturer’s Instructions, Unless Results Justify a Different Interval', 'AMC 145.A.40'],
         ['Accuracy', 'From the Maintenance Data or the Tool Manufacturer', '145.A.40(b)'],
         ['Certificate', 'Standard Used, Results As Found and As Left, Traceability', 'CAO.A.050(b), CAO.A.090'],
         ['Acceptance', 'Certificate Checked on Return, New Label with the Next Due Date', 'AMC 145.A.40']], minw=900)),
])


# ---------- Alternative Tooling ----------
page('AltTool.dc.html', 'Alternative Tooling', 'alt', 1400, [
    header('Logistics', 'Alternative Tooling', '', [btn('Start an Assessment', primary=True)],
           tabs=('tools', 'alt'), trail=TR + '|Alternative Tooling'),
    section('as-h', 'Assessments', table(
        [('Reference', '130px', 'left'), ('Alternative Tool', '280px', 'left'), ('In Place Of', '', 'left'), ('Assessed By', '200px', 'left'), ('Status', '200px', 'left')],
        [[MONO('2026-A03'), {'text': 'Magneto Timing Indicator 0304', 'sub': 'Technical Specification 2026-TS-03'}, '[Part Number], Engine Maintenance Manual', 'Chris Moore, B1.2', S('In Progress', 'a', 'Validation 20 November 2026')],
         [MONO('2026-A02'), {'text': 'Wheel Bearing Puller 0303', 'sub': 'Technical Specification 2026-TS-02'}, '[Part Number], Aircraft Maintenance Manual', 'Chris Moore, B1.2', S('Released', 'g', '6 June 2026')],
         [MONO('2025-A01'), 'Brake Lining Riveting Tool', '[Part Number], Aircraft Maintenance Manual', '[Name]', {'text': 'Rejected at Validation', 'sub': 'Named Tool Bought Instead'}]], minw=1100)),
    section('a3-h', '2026-A03 Magneto Timing Indicator', checklist([
        ('g', 'Technical Specification', 'Dimensions, Function and Accuracy From the Engine Manufacturer’s Data, 2026-TS-03'),
        ('g', 'Acquisition', 'Bought From [Parts Distributor], 3 November 2026'),
        ('g', 'Acceptance', 'Inspected Against the Specification, 10 November 2026, Entered as Tool 0304'),
        ('a', 'Validation', 'Side by Side with the Named Tool on G-BXYZ, Booked 20 November 2026'),
        ('o', 'Equivalence Statement', 'Signed by the Assessor After Validation'),
        ('o', 'Listed in the Exposition', 'Verified Equivalent Added to the Tool List, Civil Aviation Authority Notified Within 15 Days'),
        ('o', 'Task Card Updated', 'Names the Tool That Replaces the One in the Maintenance Data'),
    ])),
    section('rule-h', 'Rules', table(
        [('Approval', '150px', 'left'), ('Rule', '', 'left'), ('Point', '200px', 'left')],
        [['Part-CAO', 'Hold the Tools in the Maintenance Data or Verified Equivalents Listed in the Exposition', 'CAO.A.050(a)'],
         ['Part-CAO', 'Exposition Change Notified Within 15 Days', 'CAO.A.105'],
         ['Part 145', 'Tools Named by the Manufacturer Unless an Alternative Is Agreed Through an Exposition Procedure', '145.A.40(a)'],
         ['Part 145', 'Change to the Alternative Tooling Procedure Needs Prior Approval', 'GM1 145.A.85(b)'],
         ['Part 145', 'Instructions Changed for an Alternative Tool: Practical Demonstration, Compliance Monitoring Approval, Author Informed', 'AMC 145.A.45']], minw=960)),
])


# ---------- Tooling Need Evaluations ----------
PA28 = 'Piper PA-28 Series (Lycoming)'
HELD = lambda n: {'text': 'Held', 'sub': n}
page('ToolNeed.dc.html', 'Tooling Need Evaluations', 'need', 1450, [
    header('Logistics', 'Tooling Need Evaluations', '', [btn('Add a Task'), btn('Start an Evaluation', primary=True)],
           tabs=('tools', 'need'), trail=TR + '|Tooling Need Evaluations'),
    section('ev-h', 'Evaluations by Type Rating', table(
        [('Type Rating', '', 'left'), ('Last Evaluated', '190px', 'left'), ('Tasks', '90px', 'right'), ('Held', '90px', 'right'), ('Access Procedure', '150px', 'right'), ('Not Yet Available', '160px', 'right'), ('Status', '220px', 'left')],
        [[PA28, '10 November 2026', '9', '7', '1', '1', S('Gap', 'a', 'Magneto Timing Indicator')],
         ['Cessna/Reims-Cessna 152/F152 Series (Lycoming)', '10 November 2026', '6', '5', '0', '1', S('Gap', 'a', 'Wing Jack Point Adapter Due 2 December 2026')],
         ['Cessna/Reims-Cessna 172/F172 Series (Lycoming)', '10 November 2026', '6', '5', '0', '1', S('Gap', 'a', 'Wing Jack Point Adapter Due 2 December 2026')],
         ['Robin DR 400 series (Lycoming)', '12 November 2026', '5', '5', '0', '0', S('Complete', 'g')],
         ['Grob G115/120 Series (Lycoming)', '12 November 2026', '5', '5', '0', '0', S('Complete', 'g')],
         ['Piper PA-38 Series (Lycoming)', 'Not Evaluated', '—', '—', '—', '—', S('Due by 24 November 2026', 'a', 'Scope Change Notified by Then')]], minw=1180),
        intro='Day-to-Day Tools Held up to the Annual or 100-Hour Inspection, Occasional Tools Through the Access Procedure'),
    section('pa-h', PA28, table(
        [('Task', '260px', 'left'), ('Tool in the Maintenance Data', '', 'left'), ('Control', '200px', 'left'), ('Available As', '260px', 'left')],
        [[{'text': 'Cylinder Compression Check', 'sub': 'Engine Maintenance Manual, [Reference]'}, 'Differential Compression Tester', 'Calibration', HELD('Tool 0170')],
         [{'text': 'Fastener Torque, General', 'sub': 'Aircraft Maintenance Manual, [Reference]'}, 'Torque Wrenches, 4–100 Newton Metres', 'Calibration', {'text': 'Held', 'sub': 'Tools 0142 and 0143', 'href': 'Tool.dc.html'}],
         [{'text': 'Control Cable Tension', 'sub': 'Aircraft Maintenance Manual, [Reference]'}, 'Cable Tensiometer', 'Calibration', HELD('Tool 0175')],
         [{'text': 'Jacking', 'sub': 'Aircraft Maintenance Manual, [Reference]'}, 'Jack Point Adapter, [Part Number]', 'Inspection Before Use', HELD('Tool 0301')],
         [{'text': 'Jacking', 'sub': 'Aircraft Maintenance Manual, [Reference]'}, 'Hydraulic Aircraft Jack, 3 Tonnes', 'Servicing', {'text': 'Held, Unserviceable', 'dot': 'a', 'sub': 'Tool 0210, Seal Kit Due 25 November 2026'}],
         [{'text': 'Main Wheel Bearing Removal', 'sub': 'Aircraft Maintenance Manual, [Reference]'}, 'Wheel Bearing Puller, [Part Number]', 'Inspection Before Use', {'text': 'Alternative Tool', 'sub': 'Tool 0303, 2026-A02', 'href': 'AltTool.dc.html'}],
         [{'text': 'Magneto Timing', 'sub': 'Engine Maintenance Manual, [Reference]'}, 'Timing Indicator, [Part Number]', 'Inspection Before Use', {'text': 'Not Yet Available', 'dot': 'a', 'sub': 'Alternative Tool 2026-A03 Awaiting Validation', 'href': 'AltTool.dc.html'}],
         [{'text': 'Propeller Dynamic Balance', 'sub': 'Propeller Manufacturer’s Instructions, [Reference]'}, 'Propeller Dynamic Balancing Kit', 'Calibration', {'text': 'Access Procedure', 'sub': 'Loan From [Propeller Organisation]', 'href': 'Providers.dc.html'}],
         [{'text': 'Tyre Pressure Check', 'sub': 'Aircraft Maintenance Manual, [Reference]'}, 'Tyre Pressure Gauge', 'Calibration', HELD('Tool 0151')]], minw=1100)),
    section('new-h', 'New Tool Types Awaiting a Control Decision', table(
        [('Tool', '280px', 'left'), ('Arrived', '200px', 'left'), ('Proposed Control', '220px', 'left'), ('Basis', '', 'left')],
        [['Propeller Dynamic Balancing Kit', {'text': 'On Loan When Needed', 'sub': '[Propeller Organisation]'}, {'text': 'Calibration', 'dot': 'a', 'sub': 'Decision Due'}, 'Measures Vibration, Tool Manufacturer’s Instructions to Be Checked'],
         ['Engine Preheater', '12 November 2026', {'text': 'Servicing, Every 6 Months', 'dot': 'a', 'sub': 'Decision Due'}, 'Measures Nothing, Tool Manufacturer Asks for a Filter Clean Every 6 Months']], minw=1000),
        intro='Inspection Before Use, Servicing or Calibration, From the Tool Manufacturer’s Instructions'),
])
print('done')
