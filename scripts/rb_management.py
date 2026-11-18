# Management System pages: Hazard Log (Main), Dark wrapper, Safety Reports, Report a Safety Issue,
# Compliance Monitoring (Audit) and Actions. Hand-built interactive DC pages in the shared layout.
# Run: cd /home/claude/scripts && python3 rb_management.py
import json
OUT = '/home/claude/overhaul/project/'

HEAD = '''<!doctype html>
<html lang="en-GB">
<head>
<meta charset="utf-8">
<title>@TITLE</title>
<script src="./support.js"></script>
</head>
<body>
<x-dc>
<helmet>
<style>
@font-face{font-family:"Geist Sans Embedded";src:url("/_blob/d039f9457dfa163de154da5ccb5ef1ce") format("woff2");font-weight:100 900;font-style:normal;font-display:block}
@font-face{font-family:"Geist Mono Embedded";src:url("/_blob/cbad824f95366da895c21559ece6cd03") format("woff2");font-weight:100 900;font-style:normal;font-display:block}
body{margin:0}
a{text-decoration:none}
tbody tr:last-child > td{border-bottom-color:transparent !important}
ol > li:last-child{border-bottom-color:transparent !important}
</style>
</helmet>
<div style="font-family: 'Geist Sans Embedded', Geist, sans-serif; color: {{t.text}}; background: {{t.bg}}; color-scheme: {{t.scheme}}; font-feature-settings: 'tnum' 1; display: flex; flex-wrap: wrap; align-items: stretch; min-height: 100vh">
  <div style="flex: 1 1 248px; max-width: 100%; display: flex">
    <dc-import name="Sidebar" active="@ACTIVE" dark="{{dark}}" hint-size="248px,@Hpx"></dc-import>
  </div>
  <main style="flex: 999 1 640px; min-width: 0; box-sizing: border-box; padding: 32px 40px 64px; display: flex; flex-direction: column; gap: 40px">
    <dc-import name="TopBar" trail="@TRAIL" line="true" dark="{{dark}}" hint-size="1100px,56px"></dc-import>
'''

TAIL = '''  </main>
</div>
</x-dc>
<script type="text/x-dc" data-dc-script data-props='{"dark":{"editor":"boolean","default":false},"$preview":{"width":1440,"height":@H}}'>
class Component extends DCLogic {
  constructor(props) { super(props); this.state = @STATE; }
  renderVals() {
    const dark = this.props.dark === true || this.props.dark === 'true';
    const t = dark
      ? { scheme: 'dark', bg: '#0A0A0A', sidebar: '#000000', border: '#2E2E2E', row: '#2E2E2E', text: '#EDEDED', muted: '#A1A1A1', body: '#EDEDED', pBg: '#EDEDED', pFg: '#0A0A0A', sBorder: '#2E2E2E', empty: '#1A1A1A', raised: '#2E2E2E', note: '#000000', error: '#FF6166' }
      : { scheme: 'light', bg: '#FFFFFF', sidebar: '#FAFAFA', border: '#EBEBEB', row: '#EBEBEB', text: '#171717', muted: '#666666', body: '#171717', pBg: '#171717', pFg: '#FFFFFF', sBorder: '#EBEBEB', empty: '#F2F2F2', raised: '#FFFFFF', note: '#FAFAFA', error: '#CB2A2F' };
    const M = { r: '#FF5A4E', a: '#FFB224', g: '#1FCB6E' };
    const mark = k => k === 'o' ? { mc: 'transparent', mr: 'inset 0 0 0 1.5px ' + t.muted, md: 'inline-block' } : (k ? { mc: M[k], mr: 'none', md: 'inline-block' } : { mc: 'transparent', mr: 'none', md: 'none' });
    const ui = id => { const on = !!(this.state.open || {})[id]; return { open: on, exp: on ? 'true' : 'false', rot: on ? '90deg' : '0deg', line: on ? 'transparent' : t.row, bg: on ? t.sidebar : 'transparent',
      tog: () => { const n = Object.assign({}, this.state.open); n[id] = !n[id]; this.setState({ open: n }); } }; };
    const seg = (key, opts) => opts.map(([k, label, n]) => { const on = this.state[key] === k; return { label, count: n === undefined ? '' : String(n), pressed: on ? 'true' : 'false', bg: on ? t.raised : 'transparent', shadow: on ? '0 1px 2px rgba(0,0,0,0.12)' : 'none', pick: () => this.setState({ [key]: k }) }; });
    const fact = (label, value) => ({ label, value });
@BODY
  }
}
</script>
</body>
</html>
'''

SR = 'position: absolute; width: 1px; height: 1px; margin: -1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap'
MONO = "font-family: 'Geist Mono Embedded', 'Geist Mono', monospace; font-size: 13px"
LINK = 'color: {{t.text}}; text-decoration: underline; text-underline-offset: 3px; text-decoration-color: {{t.sBorder}}'
INPUT = 'font: inherit; font-size: 14px; height: 40px; box-sizing: border-box; padding: 0 12px; border-radius: 6px; border: 1px solid {{t.sBorder}}; background: {{t.bg}}; color: {{t.text}}; width: 100%'
LABEL = 'display: flex; flex-direction: column; gap: 6px; font-size: 13px; line-height: 16px; color: {{t.muted}}; min-width: 0'
CHEV = '<svg aria-hidden="true" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="transform: rotate({{r.rot}}); color: {{t.muted}}"><path d="M9 6l6 6-6 6"></path></svg>'


def btn(label, primary=False, href=None, onclick=None, submit=False):
    st = ('border: 0; background: {{t.pBg}}; color: {{t.pFg}}' if primary
          else 'border: 1px solid {{t.sBorder}}; background: {{t.bg}}; color: {{t.text}}')
    if href:
        return f'<a href="{href}" style="font-size: 14px; font-weight: 500; height: 40px; line-height: 38px; box-sizing: border-box; padding: 0 16px; border-radius: 6px; {st}; display: inline-block">{label}</a>'
    oc = f' onClick="{onclick}"' if onclick else ''
    ty = 'submit' if submit else 'button'
    return f'<button type="{ty}"{oc} style="font: inherit; font-size: 14px; font-weight: 500; height: 40px; padding: 0 16px; border-radius: 6px; {st}; cursor: pointer">{label}</button>'


def buttons(*b):
    return f'    <div style="display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 8px; margin-top: -16px">{"".join(b)}</div>\n'


def h1(text):
    return f'    <h1 style="{SR}">{text}</h1>\n'


def strip(items):
    # items: (value, words); value may be a {{hole}}
    s = ''.join(f'<span><span style="color: {{{{t.text}}}}; font-weight: 500">{v}</span> {w}</span>' for v, w in items)
    return f'    <div style="display: flex; flex-wrap: wrap; column-gap: 40px; row-gap: 8px; padding: 14px 16px; border-radius: 6px; border: 1px solid {{{{t.border}}}}; font-size: 14px; line-height: 20px; font-weight: 400; color: {{{{t.muted}}}}">{s}</div>\n'


def segmented(lst, label):
    return (f'<div role="group" aria-label="{label}" style="display: inline-flex; flex-wrap: wrap; padding: 3px; border-radius: 6px; background: {{{{t.empty}}}}; gap: 2px">'
            f'<sc-for list="{{{{{lst}}}}}" as="f" hint-placeholder-count="4"><button type="button" aria-pressed="{{{{f.pressed}}}}" onClick="{{{{f.pick}}}}" style="font: inherit; font-size: 13px; font-weight: 500; height: 32px; padding: 0 12px; border-radius: 6px; border: 0; cursor: pointer; color: {{{{t.text}}}}; background: {{{{f.bg}}}}; box-shadow: {{{{f.shadow}}}}">{{{{f.label}}}} <span style="color: {{{{t.muted}}}}">{{{{f.count}}}}</span></button></sc-for></div>')


def section(hid, heading, inner, intro='', right=''):
    i = f'      <p style="margin: 0; font-size: 13px; line-height: 18px; font-weight: 400; color: {{{{t.muted}}}}">{intro}</p>\n' if intro else ''
    return f'''    <section aria-labelledby="{hid}" style="display: flex; flex-direction: column; gap: 16px">
      <div style="display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 12px"><h2 id="{hid}" style="margin: 0; font-size: 16px; line-height: 24px; font-weight: 600; letter-spacing: -0.32px">{heading}</h2>{right}</div>
{i}{inner}    </section>
'''


def dot(path):
    return (f'<span aria-hidden="true" style="width: 10px; height: 10px; border-radius: 9999px; background: {{{{{path}.mc}}}}; box-shadow: {{{{{path}.mr}}}}; display: {{{{{path}.md}}}}; flex: none"></span>')


def status(path, text):
    return f'<span style="display: inline-flex; align-items: center; gap: 8px">{dot(path)}<span>{{{{{text}}}}}</span></span>'


def txt(k, strong=False, mono=False):
    st = 'font-weight: 500' if strong else 'font-weight: 400'
    if mono:
        st += '; ' + MONO
    return f'<span style="{st}">{{{{r.{k}}}}}</span>'


def link(k, hk, mono=False):
    m = '; ' + MONO if mono else ''
    return f'<a href="{{{{r.{hk}}}}}" style="{LINK}{m}">{{{{r.{k}}}}}</a>'


def table(lst, cols, minw=1040, count=6):
    """cols: (label, width, align, cell html). Rows carry ui() fields and facts."""
    th = ('<th scope="col" style="width: 40px; padding: 12px 0 12px 12px; border-bottom: 1px solid {{t.border}}"><span style="position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0)">Details</span></th>'
          + ''.join(f'<th scope="col" style="padding: 12px 16px; font-weight: 500; white-space: nowrap; border-bottom: 1px solid {{{{t.border}}}}; text-align: {a}{"; width: " + w if w else ""}">{l}</th>' for l, w, a, c in cols))
    tds = ''.join(f'<td style="padding: 12px 16px; border-bottom: 1px solid {{{{r.line}}}}; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: {w or "360px"}; text-align: {a}">{c}</td>' for l, w, a, c in cols)
    return f'''      <div style="overflow-x: auto; border: 1px solid {{{{t.border}}}}; border-radius: 6px">
        <table style="width: 100%; min-width: {minw}px; border-collapse: collapse; font-size: 14px; line-height: 20px">
          <thead><tr style="background: {{{{t.sidebar}}}}; color: {{{{t.muted}}}}; font-size: 13px; text-align: left">{th}</tr></thead>
          <tbody>
            <sc-for list="{{{{{lst}}}}}" as="r" hint-placeholder-count="{count}">
              <tr style="background: {{{{r.bg}}}}"><td style="width: 40px; padding: 10px 0 10px 12px; border-bottom: 1px solid {{{{r.line}}}}; vertical-align: middle"><button type="button" aria-expanded="{{{{r.exp}}}}" aria-label="Show Details" onClick="{{{{r.tog}}}}" style="font: inherit; width: 28px; height: 28px; border: 0; border-radius: 6px; background: transparent; cursor: pointer; display: inline-flex; align-items: center; justify-content: center">{CHEV}</button></td>{tds}</tr>
              <sc-if value="{{{{r.open}}}}" hint-placeholder-val="{{{{false}}}}"><tr style="background: {{{{r.bg}}}}"><td colspan="{len(cols) + 1}" style="padding: 4px 16px 16px 52px; border-bottom: 1px solid {{{{t.row}}}}"><div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); column-gap: 32px; row-gap: 14px"><sc-for list="{{{{r.facts}}}}" as="d" hint-placeholder-count="6"><div style="display: flex; flex-direction: column; gap: 4px; min-width: 0"><span style="font-size: 13px; line-height: 16px; color: {{{{t.muted}}}}">{{{{d.label}}}}</span><span style="font-size: 14px; line-height: 20px">{{{{d.value}}}}</span></div></sc-for></div></td></tr></sc-if>
            </sc-for>
          </tbody>
        </table>
      </div>
'''


def simple_table(lst, cols, minw=720, count=2):
    th = ''.join(f'<th scope="col" style="padding: 12px 16px; font-weight: 500; white-space: nowrap; border-bottom: 1px solid {{{{t.border}}}}; text-align: left{"; width: " + w if w else ""}">{l}</th>' for l, w, c in cols)
    tds = ''.join(f'<td style="padding: 12px 16px; border-bottom: 1px solid {{{{t.row}}}}; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: {w or "480px"}">{c}</td>' for l, w, c in cols)
    return f'''      <div style="overflow-x: auto; border: 1px solid {{{{t.border}}}}; border-radius: 6px">
        <table style="width: 100%; min-width: {minw}px; border-collapse: collapse; font-size: 14px; line-height: 20px">
          <thead><tr style="background: {{{{t.sidebar}}}}; color: {{{{t.muted}}}}; font-size: 13px; text-align: left">{th}</tr></thead>
          <tbody><sc-for list="{{{{{lst}}}}}" as="r" hint-placeholder-count="{count}"><tr>{tds}</tr></sc-for></tbody>
        </table>
      </div>
'''


def page(name, title, active, trail, height, parts, state, body):
    s = (HEAD.replace('@TITLE', title).replace('@ACTIVE', active).replace('@TRAIL', trail).replace('@H', str(height))
         + ''.join(parts)
         + TAIL.replace('@H', str(height)).replace('@STATE', json.dumps(state)).replace('@BODY', body))
    open(OUT + name, 'w').write(s)
    print('wrote', name)


# ---------------------------------------------------------------- shared data (JavaScript)
# Hazards: CAP 795 severity and likelihood. Each open hazard has one further mitigation action;
# hazard 2026-0006 shares its action with finding 2026-F03, so Actions holds 9.
HAZARDS_JS = r'''
    const sevL = { 5: 'Catastrophic', 4: 'Hazardous', 3: 'Major', 2: 'Minor', 1: 'Negligible' };
    const likL = { 5: 'Frequent', 4: 'Occasional', 3: 'Remote', 2: 'Improbable', 1: 'Extremely Improbable' };
    const grid = {
      5: ['Review', 'Unacceptable', 'Unacceptable', 'Unacceptable', 'Unacceptable'],
      4: ['Acceptable', 'Review', 'Unacceptable', 'Unacceptable', 'Unacceptable'],
      3: ['Acceptable', 'Review', 'Review', 'Unacceptable', 'Unacceptable'],
      2: ['Acceptable', 'Acceptable', 'Review', 'Review', 'Unacceptable'],
      1: ['Acceptable', 'Acceptable', 'Acceptable', 'Acceptable', 'Review']
    };
    const clsMark = { Unacceptable: 'r', Review: 'a', Acceptable: 'o' };
    const risk = (s, l) => { const cls = grid[s][l - 1]; return { s, l, cls, index: s * l, label: (s * l) + ' ' + cls, detail: sevL[s] + ' ' + s + ', ' + likL[l] + ' ' + l, m: mark(clsMark[cls]) }; };
    const hazardData = [
      { ref: '2026-0007', title: 'Hours Carried Forward Incorrectly When Paper Logbook Entries Are Transferred', source: 'Safety Report SR-2026-014', raised: '4 November 2026', existing: 'Second Person Checks the Totals When a Logbook Is Transferred', now: [3, 4], further: 'Import Totals Directly From the Technical Log, Reject Any Entry Where Hours Go Backwards', after: [3, 2], owner: 'Continuing Airworthiness Manager', due: '31 December 2026', days: 43, second: '', lastReview: '4 November 2026', nextReview: '18 December 2026' },
      { ref: '2026-0003', title: 'Airworthiness Directive Applicability Missed After a Propeller Change', source: 'Internal Safety Investigation', raised: '9 April 2026', existing: 'Directive Applicability Checked at Each Airworthiness Review', now: [4, 2], further: 'Re-Check Directive Applicability Whenever a Component Is Changed', after: [4, 1], owner: 'Continuing Airworthiness Manager', due: '15 January 2027', days: 58, second: 'Safety Manager', lastReview: '30 September 2026', nextReview: '31 December 2026' },
      { ref: '2026-0005', title: 'Airworthiness Review Certificate Expiry Not Tracked for Syndicate Aircraft', source: 'Hazard Report', raised: '22 June 2026', existing: 'Planner Keeps a Calendar Reminder', now: [3, 3], further: 'Alert the Owner and the Organisation 60 Days and 30 Days Before Expiry', after: [3, 1], owner: 'Lucy Grant', due: '30 November 2026', days: 12, second: 'Safety Manager', lastReview: '30 September 2026', nextReview: '31 December 2026' },
      { ref: '2026-0006', title: 'Contracted Maintenance Organisation Late Sending Certificates of Release to Service', source: 'Finding 2026-F03', raised: '25 September 2026', existing: 'Contract Sets a Deadline for Sending the Release', now: [2, 4], further: 'Review Contractor Performance Monthly, Hold the Aircraft Until the Release Is Received', after: [2, 2], owner: 'Compliance Monitoring Manager', due: '23 December 2026', days: 35, second: '', lastReview: '30 September 2026', nextReview: '31 December 2026' },
      { ref: '2026-0002', title: 'Defect Deferred Beyond Its Limit Without Approval', source: 'Safety Survey', raised: '3 March 2026', existing: 'Deferral Limit Written on the Defect Form', now: [3, 2], further: 'Show a Countdown on Every Deferred Defect, Block Release Once the Limit Passes', after: [3, 1], owner: 'Safety Manager', due: '31 December 2026', days: 43, second: '[Accountable Manager]', lastReview: '30 September 2026', nextReview: '31 December 2026' },
      { ref: '2026-0004', title: 'Emergency Locator Transmitter Battery Replacement Date Not Recorded', source: 'Airworthiness Review, G-CDEF', raised: '11 November 2026', existing: 'None in Place', now: [2, 3], further: 'Add the Battery Date to the Maintenance Programme as a Recurring Item', after: [2, 1], owner: 'Lucy Grant', due: '30 November 2026', days: 12, second: 'Safety Manager', lastReview: '11 November 2026', nextReview: '31 December 2026' },
      { ref: '2026-0001', title: 'Calibration Overdue on Tooling Used by a Contracted Engineer', source: 'Management of Change', raised: '20 January 2026', existing: 'Calibration Certificates Checked When the Contract Starts', now: [2, 2], further: 'Ask for Current Calibration Certificates at Every Visit', after: [2, 1], owner: 'Compliance Monitoring Manager', due: '28 February 2027', days: 102, second: 'Safety Manager', lastReview: '30 September 2026', nextReview: '31 December 2026' }
    ].map(h => ({ ...h, now: risk(h.now[0], h.now[1]), after: risk(h.after[0], h.after[1]) }));
'''

# ---------------------------------------------------------------- Hazard Log
MATRIX = '''      <div style="display: grid; grid-template-columns: 128px repeat(5, minmax(0, 1fr)); gap: 4px">
        <sc-for list="{{matrix}}" as="row" hint-placeholder-count="5">
          <div style="display: flex; flex-direction: column; justify-content: center; padding-right: 8px; font-size: 13px; line-height: 16px"><span style="font-weight: 500; color: {{t.text}}">{{row.label}}</span><span style="color: {{t.muted}}">Severity {{row.value}}</span></div>
          <sc-for list="{{row.cells}}" as="c" hint-placeholder-count="5">
            <div style="height: 56px; border-radius: 6px; padding: 8px 10px; box-sizing: border-box; display: flex; justify-content: space-between; align-items: flex-start; gap: 8px; background: {{c.bg}}; box-shadow: {{c.ring}}">
              <span style="display: inline-flex; align-items: center; gap: 6px; font-size: 13px; line-height: 16px; color: {{t.muted}}; min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis"><span aria-hidden="true" style="width: 8px; height: 8px; border-radius: 9999px; background: {{c.m.mc}}; box-shadow: {{c.m.mr}}; flex: none"></span>{{c.index}} {{c.cls}}</span>
              <span aria-label="{{c.aria}}" style="font-size: 16px; line-height: 20px; font-weight: 600; color: {{t.text}}">{{c.count}}</span>
            </div>
          </sc-for>
        </sc-for>
        <div></div>
        <sc-for list="{{likelihoods}}" as="l" hint-placeholder-count="5">
          <div style="padding-top: 4px; font-size: 13px; line-height: 16px; text-align: center"><span style="display: block; font-weight: 500">{{l.label}}</span><span style="color: {{t.muted}}">Likelihood {{l.value}}</span></div>
        </sc-for>
      </div>
'''

MAIN_BODY = HAZARDS_JS + r'''
    const st = this.state;
    const sorted = hazardData.slice().sort((a, b) => b.now.index - a.now.index || b.now.s - a.now.s);
    const n = c => sorted.filter(h => h.now.cls === c).length;
    const classes = seg('cls', [['all', 'All', sorted.length], ['Unacceptable', 'Unacceptable', n('Unacceptable')], ['Review', 'Review', n('Review')], ['Acceptable', 'Acceptable', n('Acceptable')]]);
    const views = seg('view', [['now', 'Current Risk'], ['after', 'After Further Mitigation']]);
    const hazards = sorted.filter(h => st.cls === 'all' || h.now.cls === st.cls).map(h => {
      const waiting = !h.second;
      return { ...h, ...ui(h.ref),
        status: waiting ? 'Awaiting Second Assessment' : 'Mitigation in Progress', sm: mark(waiting ? 'a' : 'o'),
        facts: [fact('Reference', h.ref), fact('Hazard', h.title), fact('Source', h.source), fact('Raised', h.raised),
          fact('Existing Mitigation', h.existing), fact('Current Risk', h.now.label + ', ' + h.now.detail),
          fact('Further Mitigation', h.further), fact('Revised Risk', h.after.label + ', ' + h.after.detail),
          fact('Owner', h.owner), fact('Action Due', h.due), fact('Second Assessor', h.second || 'Awaiting'),
          fact('Last Reviewed', h.lastReview), fact('Next Review', h.nextReview)] };
    });
    const key = st.view;
    const matrix = [5, 4, 3, 2, 1].map(s => ({ label: sevL[s], value: s,
      cells: [1, 2, 3, 4, 5].map(l => {
        const cls = grid[s][l - 1];
        const k = sorted.filter(h => h[key].s === s && h[key].l === l).length;
        return { index: s * l, cls, m: mark(clsMark[cls]), count: k ? String(k) : '', aria: k ? k + ' Hazards' : 'None', bg: k ? t.bg : t.empty, ring: k ? 'inset 0 0 0 1px ' + t.text : 'none' };
      }) }));
    const likelihoods = [1, 2, 3, 4, 5].map(l => ({ label: likL[l], value: l }));
    const classDefs = [
      { cls: 'Unacceptable', m: mark('r'), meaning: 'Intolerable', response: 'Major Mitigation Before the Activity Continues' },
      { cls: 'Review', m: mark('a'), meaning: 'Tolerable With Mitigation', response: 'Reduce to as Low as Reasonably Practicable, Accepted Only With the Accountable Manager’s Endorsement' },
      { cls: 'Acceptable', m: mark('o'), meaning: 'Not Likely or Severe Enough to Be of Concern', response: 'Consider Further Reduction' }
    ];
    const counts = { unacceptable: n('Unacceptable'), awaiting: sorted.filter(h => !h.second).length };
    return { t, dark, hazards, classes, views, matrix, likelihoods, classDefs, counts };'''

main_parts = [
    h1('Hazard Log'),
    buttons(btn('Print for Notice Board'), btn('Add a Hazard', primary=True)),
    strip([('{{counts.unacceptable}}', 'Unacceptable at Current Risk'), ('{{counts.awaiting}}', 'Awaiting Second Assessment'),
           ('30 September 2026', 'Last Log Review'), ('31 December 2026', 'Next Log Review')]),
    section('haz-h', 'Open Hazards', table('hazards', [
        ('Reference', '120px', 'left', txt('ref', True, True)),
        ('Hazard', '', 'left', txt('title')),
        ('Current Risk', '170px', 'left', status('r.now.m', 'r.now.label')),
        ('Revised Risk', '150px', 'left', status('r.after.m', 'r.after.label')),
        ('Owner', '220px', 'left', txt('owner')),
        ('Next Review', '170px', 'left', txt('nextReview')),
        ('Status', '240px', 'left', status('r.sm', 'r.status')),
    ], minw=1280, count=7), intro='Highest Current Risk First', right=segmented('classes', 'Current Risk')),
    section('matrix-h', 'Risk Tolerability Matrix', MATRIX, intro='Severity and Likelihood From CAP 795', right=segmented('views', 'Show Risk')),
    section('cls-h', 'Risk Classes', simple_table('classDefs', [
        ('Class', '200px', status('r.m', 'r.cls')), ('Meaning', '320px', '<span>{{r.meaning}}</span>'), ('Response', '', '<span>{{r.response}}</span>')], minw=900, count=3)),
]
MAIN_H = 1500
page('Main.dc.html', 'Hazard Log', 'hazards', 'Management System=Main.dc.html|Hazard Log', MAIN_H, main_parts,
     {'open': {}, 'cls': 'all', 'view': 'now'}, MAIN_BODY)

# Dark: wrapper showing Main in dark mode
open(OUT + 'Dark.dc.html', 'w').write(f'''<!doctype html>
<html lang="en-GB">
<head>
<meta charset="utf-8">
<title>Hazard Log, Dark</title>
<script src="./support.js"></script>
</head>
<body>
<x-dc>
<helmet>
<style>
@font-face{{font-family:"Geist Sans Embedded";src:url("/_blob/d039f9457dfa163de154da5ccb5ef1ce") format("woff2");font-weight:100 900;font-style:normal;font-display:block}}
@font-face{{font-family:"Geist Mono Embedded";src:url("/_blob/cbad824f95366da895c21559ece6cd03") format("woff2");font-weight:100 900;font-style:normal;font-display:block}}
body{{margin:0;background:#0A0A0A}}
</style>
</helmet>
<div style="background: #0A0A0A; min-height: 100vh">
  <dc-import name="Main" dark="{{{{true}}}}" hint-size="100%,{MAIN_H}px"></dc-import>
</div>
</x-dc>
<script type="text/x-dc" data-dc-script data-props='{{"$preview":{{"width":1440,"height":{MAIN_H}}}}}'>
class Component extends DCLogic {{
  renderVals() {{
    return {{}};
  }}
}}
</script>
</body>
</html>
''')
print('wrote Dark.dc.html')

# ---------------------------------------------------------------- Safety Reports
REPORTS_JS = r'''
    const reportData = [
      { ref: 'SR-2026-015', received: '17 November 2026', title: 'Torque Value on the Work Card Differed From the Maintenance Manual', type: 'Error', registration: 'None', outcome: 'Not Yet Assessed', state: 'assess', assessed: '', feedback: 'Not Yet Due' },
      { ref: 'SR-2026-014', received: '2 November 2026', title: 'Logbook Hours Did Not Match the Technical Log', type: 'Hazard', registration: 'None', outcome: 'Added to the Hazard Log as 2026-0007', state: 'hazard', assessed: '4 November 2026', feedback: 'Reporter Told 4 November 2026' },
      { ref: 'SR-2026-013', received: '14 October 2026', title: 'Fuel Sample Cup Left in the Cabin After Maintenance', type: 'Near Miss', registration: 'G-BXYZ', outcome: 'Loose Article Check Added to the Release Checklist', state: 'closed', assessed: '15 October 2026', feedback: 'Reporter Told 16 October 2026' },
      { ref: 'SR-2026-012', received: '29 September 2026', title: 'Poor Hangar Lighting Over the Inspection Bay', type: 'Concern', registration: 'None', outcome: 'Extra Lighting Fitted 6 October 2026', state: 'closed', assessed: '1 October 2026', feedback: 'Reporter Told 6 October 2026' },
      { ref: 'SR-2026-011', received: '9 September 2026', title: 'Torque Wrench Found Without Its Calibration Label', type: 'Near Miss', registration: 'None', outcome: 'Tool Withdrawn and Recalibrated, Shared at the October Staff Meeting', state: 'closed', assessed: '10 September 2026', feedback: 'Reporter Told 11 September 2026' }
    ];
'''
REPORTS_BODY = REPORTS_JS + r'''
    const stateInfo = { assess: ['To Assess', 'a'], hazard: ['In Hazard Log', 'o'], closed: ['Closed', 'g'] };
    const st = this.state;
    const n = k => reportData.filter(r => r.state === k).length;
    const filters = seg('show', [['all', 'All', reportData.length], ['assess', 'To Assess', n('assess')], ['hazard', 'In Hazard Log', n('hazard')], ['closed', 'Closed', n('closed')]]);
    const reports = reportData.filter(r => st.show === 'all' || r.state === st.show).map(r => ({ ...r, ...ui(r.ref),
      status: stateInfo[r.state][0], sm: mark(stateInfo[r.state][1]),
      facts: [fact('Reference', r.ref), fact('Report', r.title), fact('Type', r.type), fact('Aircraft Registration', r.registration),
        fact('Received', r.received), fact('Reporter', 'Confidential, Known to the Safety Manager Only'), fact('Assessed', r.assessed || 'Not Yet Assessed'),
        fact('Outcome', r.outcome), fact('Feedback to Reporter', r.feedback), fact('Status', stateInfo[r.state][0])] }));
    return { t, dark, reports, filters, toAssess: n('assess') };'''

reports_parts = [
    h1('Safety Reports'),
    buttons(btn('Report a Safety Issue', primary=True, href='SafetyReport.dc.html')),
    strip([('{{toAssess}}', 'To Assess'), ('2 Working Days', 'Average Time to Assess'), ('0', 'Feedback Outstanding')]),
    section('rep-h', 'Internal Safety Reports', table('reports', [
        ('Reference', '140px', 'left', txt('ref', True, True)),
        ('Report', '', 'left', txt('title')),
        ('Type', '130px', 'left', txt('type')),
        ('Received', '170px', 'left', txt('received')),
        ('Outcome', '320px', 'left', txt('outcome')),
        ('Status', '160px', 'left', status('r.sm', 'r.status')),
    ], minw=1200, count=5), intro='Confidential, Names Removed Before Anyone but the Safety Manager Sees a Report', right=segmented('filters', 'Status')),
]
page('Reports.dc.html', 'Safety Reports', 'reports', 'Management System=Main.dc.html|Safety Reports', 1100, reports_parts,
     {'open': {}, 'show': 'all'}, REPORTS_BODY)

# ---------------------------------------------------------------- Report a Safety Issue (form)
CHOICE = '''<div role="radiogroup" aria-label="@LABEL" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 8px">
            <sc-for list="{{@LIST}}" as="o" hint-placeholder-count="@N"><button type="button" role="radio" aria-checked="{{o.checked}}" onClick="{{o.pick}}" style="font: inherit; text-align: left; padding: 10px 14px; border-radius: 6px; cursor: pointer; border: 1px solid {{o.border}}; background: {{o.bg}}; color: {{t.text}}; box-shadow: {{o.ring}}; display: flex; flex-direction: column; gap: 2px"><span style="font-size: 14px; line-height: 20px; font-weight: 500">{{o.label}}</span><span style="font-size: 13px; line-height: 16px; color: {{t.muted}}">{{o.sub}}</span></button></sc-for>
          </div>'''

def choice(lst, label, n):
    return CHOICE.replace('@LIST', lst).replace('@LABEL', label).replace('@N', str(n))

def fieldset(legend, inner):
    return f'''        <fieldset style="margin: 0; padding: 0; border: 0; min-width: 0; display: flex; flex-direction: column; gap: 16px">
          <legend style="padding: 0 0 16px; font-size: 16px; line-height: 24px; font-weight: 600; letter-spacing: -0.32px">{legend}</legend>
{inner}
        </fieldset>
'''

def field(label, control, note=''):
    nt = f'<span style="font-size: 13px; line-height: 16px; color: {{{{t.muted}}}}">{note}</span>' if note else ''
    return f'<label style="{LABEL}"><span>{label}</span>{control}{nt}</label>'

form_html = f'''    <div style="display: flex; flex-direction: column; gap: 4px; margin-top: -16px">
      <h1 style="margin: 0; font-size: 24px; line-height: 32px; font-weight: 600; letter-spacing: -0.96px">Report a Safety Issue</h1>
      <span style="font-size: 14px; line-height: 20px; color: {{{{t.muted}}}}">Confidential Safety Report</span>
    </div>
    <sc-if value="{{{{sent}}}}" hint-placeholder-val="{{{{false}}}}">
      <div role="status" style="display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 12px; padding: 14px 16px; border-radius: 6px; background: {{{{t.note}}}}; font-size: 14px; line-height: 20px">
        <span style="display: inline-flex; align-items: flex-start; gap: 12px"><span aria-hidden="true" style="margin-top: 5px; width: 10px; height: 10px; border-radius: 9999px; background: #1FCB6E; flex: none"></span><span style="display: flex; flex-direction: column; gap: 2px"><span style="font-weight: 500">Report Sent, <span style="{MONO}">{{{{sentRef}}}}</span></span><span style="color: {{{{t.muted}}}}">Name Removed by the Safety Manager Before Assessment</span></span></span>
        <span style="display: flex; gap: 8px">{btn('Report Another', onclick='{{again}}')}{btn('Safety Reports', href='Reports.dc.html')}</span>
      </div>
    </sc-if>
    <div style="display: flex; flex-wrap: wrap; gap: 40px; align-items: flex-start">
      <form onSubmit="{{{{submit}}}}" style="flex: 999 1 560px; min-width: 0; display: flex; flex-direction: column; gap: 40px">
{fieldset('What Happened', f"""          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px">
            {field('Date of Event', '<input type="date" value="{{form.date}}" onChange="{{on.date}}" style="' + INPUT + '">')}
            {field('Local Time', '<input type="time" value="{{form.time}}" onChange="{{on.time}}" style="' + INPUT + '">')}
            {field('Aircraft Registration', '<select onChange="{{on.reg}}" style="' + INPUT + '"><sc-for list="{{regs}}" as="o" hint-placeholder-count="7"><option value="{{o.value}}" selected="{{o.selected}}">{{o.label}}</option></sc-for></select>')}
          </div>
          {field('Location', '<input type="text" value="{{form.place}}" onChange="{{on.place}}" placeholder="Hangar, Airfield or Office" style="' + INPUT + '">')}
          <div style="display: flex; flex-direction: column; gap: 6px"><span style="font-size: 13px; line-height: 16px; color: {{{{t.muted}}}}">Type of Report</span>{segmented('types', 'Type of Report')}</div>
          <label style="{LABEL}"><span>Describe the Event or Hazard</span><textarea rows="5" value="{{{{form.desc}}}}" onChange="{{{{on.desc}}}}" aria-invalid="{{{{descInvalid}}}}" placeholder="What Happened, What You Saw, What Made It More Likely" style="font: inherit; font-size: 14px; line-height: 20px; padding: 10px 12px; border-radius: 6px; border: 1px solid {{{{descBorder}}}}; background: {{{{t.bg}}}}; color: {{{{t.text}}}}; resize: vertical"></textarea><sc-if value="{{{{showError}}}}" hint-placeholder-val="{{{{false}}}}"><span role="alert" style="font-size: 13px; line-height: 16px; color: {{{{t.error}}}}">Description Needed Before Sending</span></sc-if></label>
          <label style="{LABEL}"><span>How Could It Be Prevented</span><textarea rows="3" value="{{{{form.prevent}}}}" onChange="{{{{on.prevent}}}}" placeholder="Optional" style="font: inherit; font-size: 14px; line-height: 20px; padding: 10px 12px; border-radius: 6px; border: 1px solid {{{{t.sBorder}}}}; background: {{{{t.bg}}}}; color: {{{{t.text}}}}; resize: vertical"></textarea></label>""")}
{fieldset('How Likely Is It to Happen Again', '          ' + choice('likely', 'How Likely Is It to Happen Again', 3))}
{fieldset('Worst Credible Outcome', '          ' + choice('worst', 'Worst Credible Outcome', 3))}
{fieldset('About You', f"""          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px">
            {field('Your Name', '<input type="text" value="{{form.name}}" onChange="{{on.name}}" style="' + INPUT + '">', 'Seen by the Safety Manager Only')}
            {field('Section or Organisation', '<input type="text" value="{{form.section}}" onChange="{{on.section}}" placeholder="Planning, Hangar or Contractor" style="' + INPUT + '">')}
          </div>""")}
        <div style="display: flex; flex-wrap: wrap; align-items: center; gap: 8px">{btn('Send Report', primary=True, submit=True)}{btn('Save Draft', onclick='{{saveDraft}}')}<sc-if value="{{{{drafted}}}}" hint-placeholder-val="{{{{false}}}}"><span role="status" style="margin-left: 8px; font-size: 13px; line-height: 16px; color: {{{{t.muted}}}}">Draft Saved</span></sc-if></div>
      </form>
      <aside style="flex: 1 1 300px; min-width: 0; display: flex; flex-direction: column; gap: 40px">
        <section aria-labelledby="next-h" style="display: flex; flex-direction: column; gap: 16px">
          <h2 id="next-h" style="margin: 0; font-size: 16px; line-height: 24px; font-weight: 600; letter-spacing: -0.32px">What Happens Next</h2>
          <ol style="margin: 0; padding: 0; list-style: none; border-top: 1px solid {{{{t.border}}}}">
            <sc-for list="{{{{steps}}}}" as="s" hint-placeholder-count="4"><li style="display: flex; gap: 12px; align-items: flex-start; padding: 12px 0; border-bottom: 1px solid {{{{t.border}}}}; font-size: 14px; line-height: 20px"><span style="font-family: 'Geist Mono Embedded', 'Geist Mono', monospace; font-size: 13px; color: {{{{t.muted}}}}; width: 16px; flex: none">{{{{s.n}}}}</span><span style="display: flex; flex-direction: column; gap: 2px"><span style="font-weight: 500">{{{{s.title}}}}</span><span style="color: {{{{t.muted}}}}">{{{{s.note}}}}</span></span></li></sc-for>
          </ol>
        </section>
        <section aria-labelledby="mine-h" style="display: flex; flex-direction: column; gap: 16px">
          <h2 id="mine-h" style="margin: 0; font-size: 16px; line-height: 24px; font-weight: 600; letter-spacing: -0.32px">Your Reports</h2>
          <ol style="margin: 0; padding: 0; list-style: none; border-top: 1px solid {{{{t.border}}}}">
            <sc-for list="{{{{mine}}}}" as="m" hint-placeholder-count="2"><li style="display: flex; flex-direction: column; gap: 2px; padding: 12px 0; border-bottom: 1px solid {{{{t.border}}}}; font-size: 14px; line-height: 20px"><span style="display: flex; justify-content: space-between; gap: 12px"><span style="{MONO}; color: {{{{t.muted}}}}">{{{{m.ref}}}}</span><span style="font-size: 13px; color: {{{{t.muted}}}}">{{{{m.date}}}}</span></span><span style="font-weight: 500">{{{{m.title}}}}</span><span style="color: {{{{t.muted}}}}">{{{{m.outcome}}}}</span></li></sc-for>
          </ol>
        </section>
      </aside>
    </div>
'''

FORM_BODY = r'''
    const st = this.state, f = st.form;
    const set = k => e => { const v = e && e.target ? e.target.value : e; this.setState({ form: Object.assign({}, this.state.form, { [k]: v }), drafted: false }); };
    const on = { date: set('date'), time: set('time'), reg: set('reg'), place: set('place'), desc: set('desc'), prevent: set('prevent'), name: set('name'), section: set('section') };
    const fleet = ['None', 'G-ABCD', 'G-BXYZ', 'G-CDEF', 'G-DGHI', 'G-EJKL', 'G-FMNO', 'G-HKLM'];
    const regs = fleet.map(r => ({ value: r, label: r, selected: f.reg === r }));
    const pickForm = (k, v) => () => this.setState({ form: Object.assign({}, this.state.form, { [k]: v }), drafted: false });
    const types = ['Error', 'Near Miss', 'Hazard', 'Concern'].map(k => { const on_ = f.type === k; return { label: k, count: '', pressed: on_ ? 'true' : 'false', bg: on_ ? t.raised : 'transparent', shadow: on_ ? '0 1px 2px rgba(0,0,0,0.12)' : 'none', pick: pickForm('type', k) }; });
    const opt = (k, v, label, sub) => { const on_ = f[k] === v; return { label, sub, checked: on_ ? 'true' : 'false', border: on_ ? t.text : t.sBorder, bg: on_ ? t.sidebar : t.bg, ring: on_ ? 'inset 0 0 0 1px ' + t.text : 'none', pick: pickForm(k, v) }; };
    const likely = [opt('likely', 1, 'Unlikely', 'Rated 1'), opt('likely', 2, 'Probable', 'Rated 2'), opt('likely', 3, 'Likely', 'Rated 3')];
    const worst = [opt('worst', 1, 'Negligible', 'Rated 1'), opt('worst', 3, 'Serious Incident', 'Rated 3'), opt('worst', 5, 'Fatal Accident', 'Rated 5')];
    const blank = !String(f.desc || '').trim();
    const showError = st.tried && blank;
    const steps = [
      { n: '1', title: 'Name Removed and Logged', note: 'Safety Manager, Usually Within 2 Working Days' },
      { n: '2', title: 'Investigated if Needed', note: 'Why It Happened, Not Who to Blame' },
      { n: '3', title: 'Risk Assessed', note: 'Added to the Hazard Log With Actions and Owners' },
      { n: '4', title: 'Feedback to You', note: 'Lessons Shared With Staff and Contractors' }
    ];
    const mine = (st.sent ? [{ ref: st.sentRef, date: '18 November 2026', title: String(f.desc).trim(), outcome: 'To Assess' }] : []).concat([
      { ref: 'SR-2026-014', date: '2 November 2026', title: 'Logbook Hours Did Not Match the Technical Log', outcome: 'Added to the Hazard Log as 2026-0007' },
      { ref: 'SR-2026-011', date: '9 September 2026', title: 'Torque Wrench Found Without Its Calibration Label', outcome: 'Closed, Tool Withdrawn and Recalibrated' }
    ]);
    const submit = e => { if (e && e.preventDefault) e.preventDefault(); if (blank) { this.setState({ tried: true }); return; } this.setState({ sent: true, tried: false, drafted: false, sentRef: 'SR-2026-016' }); };
    const again = () => this.setState({ sent: false, tried: false, drafted: false, form: Object.assign({}, this.state.form, { desc: '', prevent: '', place: '', reg: 'None' }) });
    return { t, dark, form: f, on, regs, types, likely, worst, steps, mine, submit, again,
      saveDraft: () => this.setState({ drafted: true }), drafted: !!st.drafted, sent: !!st.sent, sentRef: st.sentRef || '',
      showError, descInvalid: showError ? 'true' : 'false', descBorder: showError ? t.error : t.sBorder };'''

page('SafetyReport.dc.html', 'Report a Safety Issue', 'reports', 'Management System=Main.dc.html|Safety Reports=Reports.dc.html', 1500,
     [form_html],
     {'form': {'date': '2026-11-17', 'time': '14:30', 'reg': 'None', 'place': '', 'type': 'Hazard', 'desc': '', 'prevent': '', 'likely': 2, 'worst': 3, 'name': '[Your Name]', 'section': ''},
      'tried': False, 'sent': False, 'drafted': False, 'sentRef': ''}, FORM_BODY)

# ---------------------------------------------------------------- Compliance Monitoring
# CAO.A.100: every item audited every 12 months (up to 100% extension), records kept 2 years.
# Level 2: corrective action within 3 months, extendable with a plan (CAO.B.050, CAMO.B.350).
FINDINGS_JS = r'''
    const findingData = [
      { ref: '2026-F05', title: 'No Minutes Kept for the July Safety Committee Meeting', area: 'Safety Risk Management Audit', level: 'Level 2', raised: '20 October 2026', due: '20 January 2027', days: 63, owner: 'Safety Manager', cause: 'Nobody Given the Job of Taking Minutes', immediate: 'Meeting Outcomes Reconstructed and Signed by the Attendees', plan: 'Minute Taker Named on Every Agenda, Minutes Stored Within 5 Days', state: 'open', note: 'Plan Accepted 27 October 2026', linked: 'None' },
      { ref: '2026-F04', title: 'Annual Review of the Maintenance Programme Not Recorded for Two Aircraft', area: 'Maintenance Programmes Audit', level: 'Level 2', raised: '2 September 2026', due: '2 December 2026', days: 14, owner: 'Continuing Airworthiness Manager', cause: 'Review Dates Not Tracked, Relied on Memory', immediate: 'Reviews Carried Out and Recorded for G-BXYZ and G-FMNO', plan: 'Review Date Added to Every Programme, Alert 30 Days Before', state: 'verify', note: 'Action Submitted 14 November 2026', linked: 'None' },
      { ref: '2026-F03', title: 'Certificates of Release to Service Sent Late on Three Occasions', area: 'Contracted Maintenance Audit, Unannounced', level: 'Level 2', raised: '23 September 2026', due: '23 December 2026', days: 35, owner: 'Compliance Monitoring Manager', cause: 'Contract Deadline Not Followed in Practice', immediate: 'Outstanding Releases Obtained for All Three Aircraft', plan: 'Monthly Contractor Performance Review, Aircraft Held Until the Release Is Received', state: 'open', note: 'Plan Accepted 30 September 2026', linked: 'Hazard 2026-0006' },
      { ref: '2026-F02', title: 'Certificate of Release to Service Entered in Records After 30 Days', area: 'Records and Technical Logs Audit', level: 'Level 2', raised: '17 June 2026', due: '17 September 2026', days: -62, owner: 'Continuing Airworthiness Manager', cause: 'Paper Release Held Until the Next Office Visit', immediate: 'Release Entered for G-EJKL', plan: 'Releases Scanned in on the Day of Issue', state: 'closed', note: 'Verified 28 July 2026', linked: 'None' },
      { ref: '2026-F01', title: 'Directive Check Sheet Missing a Signature', area: 'Airworthiness Directives Audit', level: 'Level 2', raised: '8 April 2026', due: '8 July 2026', days: -133, owner: 'Continuing Airworthiness Manager', cause: 'Check Sheet Had No Signature Box', immediate: 'Sheet Signed by the Person Who Did the Check', plan: 'Check Sheet Redesigned With a Signature Box', state: 'closed', note: 'Verified 3 May 2026', linked: 'None' }
    ];
'''
AUDIT_BODY = FINDINGS_JS + r'''
    const st = this.state;
    const programme = [
      { area: 'Continuing Airworthiness Management', planned: 'January 2026', kind: 'Planned', done: '21 January 2026', next: 'January 2027', auditor: 'Compliance Monitoring Manager', findings: '0', st: 'done' },
      { area: 'Airworthiness Directives', planned: 'April 2026', kind: 'Planned', done: '8 April 2026', next: 'April 2027', auditor: 'Compliance Monitoring Manager', findings: '1', st: 'done' },
      { area: 'Records and Technical Logs', planned: 'June 2026', kind: 'Planned', done: '17 June 2026', next: 'June 2027', auditor: 'Compliance Monitoring Manager', findings: '1', st: 'done' },
      { area: 'Airworthiness Reviews', planned: 'July 2026', kind: 'Planned', done: '15 July 2026', next: 'July 2027', auditor: 'Compliance Monitoring Manager', findings: '0', st: 'done' },
      { area: 'Product Audit, G-BXYZ', planned: 'August 2026', kind: 'Unannounced', done: '5 August 2026', next: 'August 2027', auditor: 'Compliance Monitoring Manager', findings: '0', st: 'done' },
      { area: 'Maintenance Programmes', planned: 'September 2026', kind: 'Planned', done: '2 September 2026', next: 'September 2027', auditor: 'Compliance Monitoring Manager', findings: '1', st: 'done' },
      { area: 'Contracted Maintenance, [Contracted Maintenance Organisation]', planned: 'September 2026', kind: 'Unannounced', done: '23 September 2026', next: 'September 2027', auditor: 'Compliance Monitoring Manager', findings: '1', st: 'done' },
      { area: 'Safety Risk Management', planned: 'October 2026', kind: 'Planned', done: '20 October 2026', next: 'October 2027', auditor: 'Compliance Monitoring Manager', findings: '1', st: 'done' },
      { area: 'Staff, Training and Authorisations', planned: '26 November 2026', kind: 'Planned', done: '', next: '', auditor: 'Compliance Monitoring Manager', findings: '', st: 'due', days: 8 },
      { area: 'Compliance Monitoring System', planned: '30 November 2026', kind: 'Planned', done: '', next: '', auditor: '[Independent Auditor]', findings: '', st: 'due', days: 12 }
    ];
    const audits = programme.map((p, i) => ({ ...p, ...ui('a' + i),
      status: p.st === 'done' ? 'Completed' : 'Due in ' + p.days + ' Days', sm: mark(p.st === 'done' ? 'g' : 'a'),
      doneText: p.done || 'Not Yet Done',
      facts: [fact('Area', p.area), fact('Planned', p.planned), fact('Audit Type', p.kind), fact('Auditor', p.auditor), fact('Completed', p.done || 'Not Yet Done'),
        fact('Findings', p.findings || 'None Yet'), fact('Next Due', p.next || 'Within 12 Months of Completion')] }));
    const fState = { open: ['Open', 'a'], verify: ['Awaiting Verification', 'o'], closed: ['Closed', 'g'] };
    const n = k => findingData.filter(x => k === 'open' ? x.state !== 'closed' : x.state === k).length;
    const fFilters = seg('show', [['all', 'All', findingData.length], ['open', 'Open', n('open')], ['closed', 'Closed', n('closed')]]);
    const findings = findingData.filter(x => st.show === 'all' || (st.show === 'open' ? x.state !== 'closed' : x.state === 'closed')).map(x => {
      const s = x.state === 'open' && x.days <= 30 ? ['Due in ' + x.days + ' Days', 'a'] : fState[x.state];
      return { ...x, ...ui(x.ref), status: s[0], sm: mark(s[1]),
        facts: [fact('Reference', x.ref), fact('Finding', x.title), fact('From', x.area), fact('Level', x.level), fact('Raised', x.raised),
          fact('Root Cause', x.cause), fact('Immediate Action', x.immediate), fact('Corrective Action Plan', x.plan),
          fact('Owner', x.owner), fact('Corrective Action Due', x.due), fact('Linked', x.linked), fact('Status', s[0] + ', ' + x.note)] };
    });
    const levels = [
      { level: 'Level 1', meaning: 'Significant Non-Compliance That Lowers Safety or Seriously Endangers Flight Safety', response: 'Immediate Action, Activity Stopped or Limited Until Corrected' },
      { level: 'Level 2', meaning: 'Non-Compliance That May Lower Safety or Endanger Flight Safety', response: 'Corrective Action Within 3 Months, Extendable With an Accepted Plan' }
    ];
    const doneCount = programme.filter(p => p.st === 'done').length;
    return { t, dark, audits, findings, fFilters, levels, doneCount, total: programme.length, openCount: n('open') };'''

audit_parts = [
    h1('Compliance Monitoring'),
    buttons(btn('Plan Next Cycle'), btn('Raise a Finding', primary=True)),
    strip([('1 December 2025–30 November 2026', 'Audit Cycle'), ('{{doneCount}} of {{total}}', 'Audits Complete'), ('{{openCount}}', 'Findings Open'), ('0', 'Level 1 Findings')]),
    section('find-h', 'Findings', table('findings', [
        ('Reference', '120px', 'left', txt('ref', True, True)),
        ('Finding', '', 'left', txt('title')),
        ('Level', '100px', 'left', txt('level')),
        ('Raised', '170px', 'left', txt('raised')),
        ('Corrective Action Due', '190px', 'left', txt('due')),
        ('Owner', '240px', 'left', txt('owner')),
        ('Status', '210px', 'left', status('r.sm', 'r.status')),
    ], minw=1280, count=5), intro='Root Cause, Corrective Action Plan and Verification for Each Finding', right=segmented('fFilters', 'Status')),
    section('prog-h', 'Audit Programme', table('audits', [
        ('Area', '', 'left', txt('area', True)),
        ('Planned', '170px', 'left', txt('planned')),
        ('Audit Type', '140px', 'left', txt('kind')),
        ('Completed', '170px', 'left', txt('doneText')),
        ('Findings', '100px', 'right', txt('findings')),
        ('Next Due', '160px', 'left', txt('next')),
        ('Status', '170px', 'left', status('r.sm', 'r.status')),
    ], minw=1200, count=10), intro='Every Item Audited Every 12 Months, Auditors Independent of the Area Audited'),
    section('lvl-h', 'Finding Levels', simple_table('levels', [
        ('Level', '120px', '<span style="font-weight: 500">{{r.level}}</span>'), ('Meaning', '', '<span>{{r.meaning}}</span>'), ('Response', '', '<span>{{r.response}}</span>')], minw=900, count=2)),
]
page('Audit.dc.html', 'Compliance Monitoring', 'audit', 'Management System=Main.dc.html|Compliance Monitoring', 1560, audit_parts,
     {'open': {}, 'show': 'all'}, AUDIT_BODY)

# ---------------------------------------------------------------- Actions
ACTIONS_BODY = HAZARDS_JS + FINDINGS_JS + r'''
    const st = this.state;
    const fromHazards = hazardData.filter(h => h.ref !== '2026-0006').map(h => ({ kind: 'hazard', action: h.further, about: h.title, from: 'Hazard ' + h.ref, href: 'Main.dc.html', also: 'None', owner: h.owner, due: h.due, days: h.days, state: 'open', raised: h.raised }));
    const fromFindings = findingData.filter(x => x.state !== 'closed').map(x => ({ kind: 'finding', action: x.plan, about: x.title, from: 'Finding ' + x.ref, href: 'Audit.dc.html', also: x.linked === 'None' ? 'None' : 'Closes ' + x.linked, owner: x.owner, due: x.due, days: x.days, state: x.state, raised: x.raised }));
    const all = fromHazards.concat(fromFindings).sort((a, b) => a.days - b.days);
    const stat = a => a.state === 'verify' ? ['Awaiting Verification', 'o'] : (a.days < 0 ? ['Overdue', 'r'] : (a.days <= 30 ? ['Due in ' + a.days + ' Days', 'a'] : ['On Track', 'g']));
    const keep = (a, f) => f === 'all' || (f === 'soon' ? a.days <= 30 : a.kind === f);
    const cnt = f => all.filter(a => keep(a, f)).length;
    const filters = seg('show', [['all', 'All', cnt('all')], ['soon', 'Due in 30 Days', cnt('soon')], ['hazard', 'From Hazards', cnt('hazard')], ['finding', 'From Findings', cnt('finding')]]);
    const actions = all.filter(a => keep(a, st.show)).map((a, i) => { const s = stat(a); return { ...a, ...ui(a.from), status: s[0], sm: mark(s[1]),
      facts: [fact('Action', a.action), fact('From', a.from), fact('About', a.about), fact('Also', a.also), fact('Raised', a.raised), fact('Owner', a.owner), fact('Due', a.due), fact('Status', s[0])] }; });
    return { t, dark, actions, filters, openCount: all.length, soon: cnt('soon'), overdue: all.filter(a => a.days < 0).length, awaiting: all.filter(a => a.state === 'verify').length };'''

actions_parts = [
    h1('Actions'),
    buttons(btn('Export')),
    strip([('{{openCount}}', 'Open Actions'), ('{{soon}}', 'Due in 30 Days'), ('{{overdue}}', 'Overdue'), ('{{awaiting}}', 'Awaiting Verification')]),
    section('act-h', 'Open Actions', table('actions', [
        ('Action', '', 'left', txt('action', True)),
        ('From', '200px', 'left', link('from', 'href')),
        ('Owner', '240px', 'left', txt('owner')),
        ('Due', '170px', 'left', txt('due')),
        ('Status', '210px', 'left', status('r.sm', 'r.status')),
    ], minw=1100, count=9), intro='Closing an Action Updates the Hazard or Finding It Came From', right=segmented('filters', 'Source')),
]
page('Actions.dc.html', 'Actions', 'actions', 'Management System=Main.dc.html|Actions', 1100, actions_parts,
     {'open': {}, 'show': 'all'}, ACTIONS_BODY)
