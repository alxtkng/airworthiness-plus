from gen import *
import json

# People: Staff (sortable, filterable) and Organisation Chart (CAO.A.025(a)(4), Exposition Chapter A.8).
# Hand-built pages on the shared layout. One people list feeds both pages.

PEOPLE = [
    # id, name, detail, role, group, reportsTo, employment, licence, authorisation, training, logbook
    dict(id='am', name='[Accountable Manager]', detail='Signs the Exposition Statement', role='Accountable Manager', group='management', to='', emp='Employed', lic='', auth=('Not Required', '', ''), trn=('Current', 'Safety Training', ''), log=''),
    dict(id='cam', name='[Continuing Airworthiness Manager]', detail='Nominated Person, Exposition Chapter A.7', role='Continuing Airworthiness Manager', group='management', to='am', emp='Employed', lic='', auth=('Maintenance Programme Approval', 'Exposition Chapter A.11', ''), trn=('Current', 'Safety Training', ''), log=''),
    dict(id='mm', name='[Maintenance Manager]', detail='Nominated Person, Exposition Chapter A.7', role='Maintenance Manager', group='management', to='am', emp='Employed', lic='', auth=('Not Required', '', ''), trn=('Current', 'Safety Training', ''), log=''),
    dict(id='cmm', name='[Compliance Monitoring Manager]', detail='Independent of the Work Monitored', role='Compliance Monitoring Manager', group='management', to='am', emp='Employed', lic='', auth=('Not Required', '', ''), trn=('Current', 'Safety Training', ''), log=''),
    dict(id='lg', name='Lucy Grant', detail='Accepted by the Civil Aviation Authority 9 June 2023', role='Airworthiness Review Staff', group='review', to='cam', emp='Employed', lic='', auth=('Airworthiness Review', 'Last Review 11 November 2026, G-CDEF', ''), trn=('Current', 'Continuation Training', ''), log=''),
    dict(id='ar2', name='[Name]', detail='Last Review 2 December 2025, G-EJKL', role='Airworthiness Review Staff', group='review', to='cam', emp='Employed', lic='', auth=('Recency Lapses 2 December 2026', '1 Review in 12 Months Needed', 'a'), trn=('Human Factors Overdue', 'Due 30 October 2026', 'r'), log=''),
    dict(id='pl', name='[Name]', detail='Joined 1 September 2026', role='Planning and Records', group='other', to='mm', emp='Employed', lic='', auth=('Competency Assessment in Progress', 'Before Unsupervised Work', ''), trn=('Initial Safety Training Due 1 March 2027', 'Within 6 Months of Joining', ''), log=''),
    dict(id='cm', name='Chris Moore', detail='UK.66.[Number]', role='Certifying Staff', group='certifying', to='mm', emp='Employed', lic='Part-66 B1.2', auth=('Certifying Staff', 'Piston Aeroplanes, Lycoming and Continental Piston Engines', ''), trn=('Due 14 August 2027', 'Human Factors, Fuel Tank Safety', ''), log='Open'),
    dict(id='sp', name='Sam Patel', detail='UK.66.[Number]', role='Certifying Staff', group='certifying', to='mm', emp='Employed', lic='Part-66 B1.2', auth=('Certifying Staff', 'Piston Aeroplanes, Lycoming and Continental Piston Engines', ''), trn=('Due 6 December 2026', '18 Days Left', 'a'), log='Open'),
    dict(id='l2', name='[Name]', detail='UK.66.[Number]', role='Certifying Staff', group='certifying', to='mm', emp='Contracted', lic='Part-66 L2', auth=('Lapsed', 'Under 6 Months of Experience in 2 Years', 'r'), trn=('Due 2 May 2027', 'Human Factors', ''), log='Open'),
    dict(id='ce', name='[Contract Engineer]', detail='UK.66.[Number]', role='Certifying Staff', group='certifying', to='mm', emp='Contracted', lic='Part-66 B1.2', auth=('Not Yet Issued', 'Contracted Cover From December 2026', ''), trn=('Before Authorisation', 'Human Factors, Procedures', ''), log=''),
    dict(id='ew', name='Ellie Ward', detail='Joined 6 January 2025', role='Mechanic, Trainee', group='other', to='mm', emp='Employed', lic='Working Toward Part-66 B1.2', auth=('Supervised Work Only', 'On the Job Training, 31 of 40 Tasks', ''), trn=('Current', 'Human Factors', ''), log='Open'),
    dict(id='ia', name='[Independent Auditor]', detail='Internal Audits, Cycle Ending 30 November 2026', role='Auditor', group='other', to='cmm', emp='Contracted', lic='', auth=('Not Required', '', ''), trn=('Not Required', '', ''), log=''),
]
NAMES = {p['id']: p['role'] if p['name'].startswith('[') and p['group'] == 'management' else p['name'] for p in PEOPLE}
for p in PEOPLE:
    p['toName'] = '' if not p['to'] else next(q['role'] for q in PEOPLE if q['id'] == p['to'])
GROUPS = [['all', 'All'], ['management', 'Management'], ['certifying', 'Certifying Staff'], ['review', 'Airworthiness Review Staff'], ['other', 'Other Staff']]

T = """    const dark = this.props.dark === true || this.props.dark === 'true';
    const t = dark
      ? { scheme: 'dark', bg: '#0A0A0A', sidebar: '#000000', border: '#2E2E2E', row: '#2E2E2E', text: '#EDEDED', muted: '#A1A1A1', body: '#EDEDED', pBg: '#EDEDED', pFg: '#0A0A0A', sBorder: '#2E2E2E', empty: '#1A1A1A', raised: '#2E2E2E' }
      : { scheme: 'light', bg: '#FFFFFF', sidebar: '#FAFAFA', border: '#EBEBEB', row: '#EBEBEB', text: '#171717', muted: '#666666', body: '#171717', pBg: '#171717', pFg: '#FFFFFF', sBorder: '#EBEBEB', empty: '#F2F2F2', raised: '#FFFFFF' };
    const C = { a: '#FFB224', r: '#FF5A4E' };
    const PEOPLE = %s;
""" % json.dumps(PEOPLE, ensure_ascii=False)

def script(body, height, state):
    return f'''  </main>
</div>
</x-dc>
<script type="text/x-dc" data-dc-script data-props='{{"dark":{{"editor":"boolean","default":false}},"$preview":{{"width":1440,"height":{height}}}}}'>
class Component extends DCLogic {{
  constructor(props) {{ super(props); this.state = {state}; }}
  renderVals() {{
{T}{body}
  }}
}}
</script>
</body>
</html>
'''

ARROW = '<svg aria-hidden="true" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="display: {{c.arrow}}; transform: rotate({{c.turn}})"><path d="M12 5v14M6 13l6 6 6-6"></path></svg>'
CHEV = '<svg aria-hidden="true" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="transform: rotate({{p.rot}}); color: {{t.muted}}"><path d="M9 6l6 6-6 6"></path></svg>'
CELL = 'padding: 12px 16px; border-bottom: 1px solid {{p.line}}; white-space: nowrap; overflow: hidden; text-overflow: ellipsis'
DOT = '<span aria-hidden="true" style="width: 10px; height: 10px; border-radius: 9999px; background: {{%s.colour}}; display: {{%s.mark}}; flex: none"></span>'

# ---------- Staff ----------
staff_body = f'''
    <div style="display: flex; flex-wrap: wrap; align-items: flex-end; gap: 16px">
      <label style="display: flex; flex-direction: column; gap: 6px; font-size: 13px; color: {{{{t.muted}}}}">
        <span>Search</span>
        <input type="search" value="{{{{q}}}}" onChange="{{{{onQuery}}}}" placeholder="Name, Role or Licence" style="font: inherit; font-size: 14px; height: 36px; box-sizing: border-box; padding: 0 12px; border-radius: 6px; border: 1px solid {{{{t.sBorder}}}}; background: {{{{t.bg}}}}; color: {{{{t.text}}}}; width: 280px">
      </label>
      <div role="group" aria-label="Staff Group" style="display: inline-flex; flex-wrap: wrap; padding: 3px; border-radius: 6px; background: {{{{t.empty}}}}; gap: 2px">
        <sc-for list="{{{{groups}}}}" as="f" hint-placeholder-count="5">
          <button type="button" aria-pressed="{{{{f.pressed}}}}" onClick="{{{{f.pick}}}}" style="font: inherit; font-size: 13px; font-weight: 500; height: 32px; padding: 0 12px; border-radius: 6px; border: 0; cursor: pointer; color: {{{{t.text}}}}; background: {{{{f.bg}}}}; box-shadow: {{{{f.shadow}}}}">{{{{f.label}}}} <span style="color: {{{{t.muted}}}}">{{{{f.count}}}}</span></button>
        </sc-for>
      </div>
      <label style="display: flex; flex-direction: column; gap: 6px; font-size: 13px; color: {{{{t.muted}}}}">
        <span>Employment</span>
        <select onChange="{{{{onEmp}}}}" style="font: inherit; font-size: 14px; height: 36px; box-sizing: border-box; padding: 0 12px; border-radius: 6px; border: 1px solid {{{{t.sBorder}}}}; background: {{{{t.bg}}}}; color: {{{{t.text}}}}; min-width: 180px">
          <sc-for list="{{{{emps}}}}" as="o" hint-placeholder-count="3"><option value="{{{{o.value}}}}" selected="{{{{o.selected}}}}">{{{{o.label}}}}</option></sc-for>
        </select>
      </label>
    </div>

    <section aria-labelledby="staff-h" style="display: flex; flex-direction: column; gap: 12px; margin-top: -16px">
      <h2 id="staff-h" style="position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0)">Staff</h2>
      <div style="overflow-x: auto; border: 1px solid {{{{t.border}}}}; border-radius: 6px">
        <table style="width: 100%; min-width: 1100px; border-collapse: collapse; font-size: 14px; line-height: 20px">
          <thead><tr style="background: {{{{t.sidebar}}}}; color: {{{{t.muted}}}}; font-size: 13px; text-align: left; white-space: nowrap">
            <th scope="col" style="width: 40px; padding: 12px 0 12px 12px; border-bottom: 1px solid {{{{t.border}}}}"><span style="position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0)">Details</span></th>
            <sc-for list="{{{{cols}}}}" as="c" hint-placeholder-count="7">
              <th scope="col" aria-sort="{{{{c.sort}}}}" style="padding: 0 8px; border-bottom: 1px solid {{{{t.border}}}}; font-weight: 500; width: {{{{c.w}}}}">
                <button type="button" onClick="{{{{c.pick}}}}" style="font: inherit; font-size: 13px; font-weight: 500; height: 44px; padding: 0 8px; border: 0; background: transparent; color: {{{{c.colour}}}}; cursor: pointer; display: inline-flex; align-items: center; gap: 6px">{{{{c.label}}}}{ARROW}</button>
              </th>
            </sc-for>
          </tr></thead>
          <tbody>
            <sc-for list="{{{{rows}}}}" as="p" hint-placeholder-count="13">
              <tr style="background: {{{{p.bg}}}}">
                <td style="width: 40px; padding: 10px 0 10px 12px; border-bottom: 1px solid {{{{p.line}}}}"><button type="button" aria-expanded="{{{{p.expanded}}}}" aria-label="Show Details" onClick="{{{{p.toggle}}}}" style="font: inherit; width: 28px; height: 28px; border: 0; border-radius: 6px; background: transparent; cursor: pointer; display: inline-flex; align-items: center; justify-content: center">{CHEV}</button></td>
                <td style="{CELL}; max-width: 240px; font-weight: 500">{{{{p.name}}}}</td>
                <td style="{CELL}; max-width: 240px">{{{{p.role}}}}</td>
                <td style="{CELL}; max-width: 240px">{{{{p.toName}}}}</td>
                <td style="{CELL}">{{{{p.emp}}}}</td>
                <td style="{CELL}; max-width: 200px">{{{{p.licText}}}}</td>
                <td style="{CELL}; max-width: 260px"><a href="{{{{p.authHref}}}}" style="display: inline-flex; align-items: center; gap: 8px; color: {{{{t.text}}}}">{DOT % ('p.authS', 'p.authS')}{{{{p.authS.text}}}}</a></td>
                <td style="{CELL}; max-width: 260px"><a href="RecurrentTraining.dc.html" style="display: inline-flex; align-items: center; gap: 8px; color: {{{{t.text}}}}">{DOT % ('p.trnS', 'p.trnS')}{{{{p.trnS.text}}}}</a></td>
              </tr>
              <sc-if value="{{{{p.open}}}}" hint-placeholder-val="{{{{false}}}}">
                <tr style="background: {{{{p.bg}}}}"><td colspan="8" style="padding: 4px 16px 16px 52px; border-bottom: 1px solid {{{{t.row}}}}">
                  <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); column-gap: 32px; row-gap: 14px">
                    <sc-for list="{{{{p.facts}}}}" as="f" hint-placeholder-count="5"><div style="display: flex; flex-direction: column; gap: 4px"><span style="font-size: 13px; line-height: 16px; color: {{{{t.muted}}}}">{{{{f.label}}}}</span><span style="font-size: 14px; line-height: 20px">{{{{f.value}}}}</span></div></sc-for>
                    <sc-if value="{{{{p.hasLog}}}}" hint-placeholder-val="{{{{false}}}}"><div style="display: flex; align-items: flex-end"><a href="Logbook.dc.html" style="font-size: 14px; font-weight: 500; color: {{{{t.text}}}}; text-decoration: underline; text-underline-offset: 3px; text-decoration-color: {{{{t.border}}}}">Open Experience Logbook</a></div></sc-if>
                  </div>
                </td></tr>
              </sc-if>
            </sc-for>
          </tbody>
        </table>
      </div>
      <span style="font-size: 13px; line-height: 18px; color: {{{{t.muted}}}}">{{{{countLabel}}}}</span>
    </section>

    <section aria-labelledby="former-h" style="display: flex; flex-direction: column; gap: 16px">
      <h2 id="former-h" style="margin: 0; font-size: 16px; line-height: 24px; font-weight: 600; letter-spacing: -0.32px">Former Staff</h2>
      <div style="overflow-x: auto; border: 1px solid {{{{t.border}}}}; border-radius: 6px">
        <table style="width: 100%; min-width: 860px; border-collapse: collapse; font-size: 14px; line-height: 20px; white-space: nowrap">
          <thead><tr style="background: {{{{t.sidebar}}}}; color: {{{{t.muted}}}}; font-size: 13px; text-align: left">
            <th scope="col" style="padding: 12px 16px; font-weight: 500; border-bottom: 1px solid {{{{t.border}}}}">Name</th>
            <th scope="col" style="padding: 12px 16px; font-weight: 500; border-bottom: 1px solid {{{{t.border}}}}">Role</th>
            <th scope="col" style="padding: 12px 16px; font-weight: 500; border-bottom: 1px solid {{{{t.border}}}}">Left</th>
            <th scope="col" style="padding: 12px 16px; font-weight: 500; border-bottom: 1px solid {{{{t.border}}}}">Record Kept Until</th>
          </tr></thead>
          <tbody><tr>
            <td style="padding: 12px 16px; font-weight: 500">[Name]</td>
            <td style="padding: 12px 16px">Airworthiness Review Staff</td>
            <td style="padding: 12px 16px">30 June 2025</td>
            <td style="padding: 12px 16px">30 June 2027, 2 Years After Leaving</td>
          </tr></tbody>
        </table>
      </div>
    </section>
'''

staff_js = '''    const st = this.state;
    const q = st.q.trim().toLowerCase();
    const rank = c => c === 'r' ? 0 : c === 'a' ? 1 : 2;
    const status = s => ({ text: s[0], colour: C[s[2]] || 'transparent', mark: s[2] ? 'inline-block' : 'none', rank: rank(s[2]) });
    const match = p => !q || (p.name + ' ' + p.role + ' ' + p.lic + ' ' + p.toName).toLowerCase().indexOf(q) !== -1;
    const byEmp = p => !st.emp || p.emp === st.emp;
    const base = PEOPLE.filter(p => match(p) && byEmp(p));
    const groups = %s.map(g => {
      const on = st.group === g[0];
      return { label: g[1], count: String(g[0] === 'all' ? base.length : base.filter(p => p.group === g[0]).length), pressed: on ? 'true' : 'false', bg: on ? t.raised : 'transparent', shadow: on ? '0 1px 2px rgba(0,0,0,0.12)' : 'none', pick: () => this.setState({ group: g[0] }) };
    });
    const emps = [['', 'All Employment'], ['Employed', 'Employed'], ['Contracted', 'Contracted']].map(e => ({ value: e[0], label: e[1], selected: st.emp === e[0] }));
    const keys = { name: p => p.name, role: p => p.role, to: p => p.toName, emp: p => p.emp, lic: p => p.lic, auth: p => status(p.auth).rank + p.auth[0], trn: p => status(p.trn).rank + p.trn[0] };
    const colDefs = [['name', 'Name', '220px'], ['role', 'Role', ''], ['to', 'Reports To', '220px'], ['emp', 'Employment', '130px'], ['lic', 'Licence', '170px'], ['auth', 'Authorisation', '240px'], ['trn', 'Recurrent Training', '240px']];
    const cols = colDefs.map(c => {
      const on = st.sort === c[0];
      return { label: c[1], w: c[2] || 'auto', sort: on ? (st.dir > 0 ? 'ascending' : 'descending') : 'none', arrow: on ? 'inline-block' : 'none', turn: st.dir > 0 ? '180deg' : '0deg', colour: on ? t.text : t.muted,
        pick: () => this.setState({ sort: c[0], dir: on ? -st.dir : 1 }) };
    });
    const k = keys[st.sort] || keys.name;
    const list = base.filter(p => st.group === 'all' || p.group === st.group)
      .slice().sort((a, b) => { const x = k(a), y = k(b); return (x < y ? -1 : x > y ? 1 : 0) * st.dir; });
    const rows = list.map(p => {
      const on = !!st.open[p.id];
      const facts = [{ label: 'Detail', value: p.detail }, { label: 'Reports To', value: p.toName || 'None' }, { label: 'Authorisation', value: p.auth[0] + (p.auth[1] ? ', ' + p.auth[1] : '') }, { label: 'Recurrent Training', value: p.trn[0] + (p.trn[1] ? ', ' + p.trn[1] : '') }];
      return Object.assign({}, p, { licText: p.lic || '—', authS: status(p.auth), trnS: status(p.trn), authHref: p.auth[2] === 'r' || p.auth[0].indexOf('Recency') === 0 ? 'Recency.dc.html' : 'Authorisations.dc.html',
        facts, hasLog: !!p.log, open: on, expanded: on ? 'true' : 'false', rot: on ? '90deg' : '0deg', line: on ? 'transparent' : t.row, bg: on ? t.sidebar : 'transparent',
        toggle: () => { const n = Object.assign({}, st.open); n[p.id] = !n[p.id]; this.setState({ open: n }); } });
    });
    const countLabel = rows.length + ' of ' + PEOPLE.length + ' People';
    return { t, dark, q: st.q, onQuery: e => this.setState({ q: e.target.value }), onEmp: e => this.setState({ emp: e.target.value }), groups, emps, cols, rows, countLabel };''' % json.dumps(GROUPS)

def write(name, title, active, height, body, js, state):
    s = HEAD % (E(title), active, height) + body + script(js, height, state)
    open(OUT + name, 'w').write(s)

write('Staff.dc.html', 'Staff', 'staff', 1200,
      header('People', 'Staff', '', [btn('Add a Person', primary=True)], tabs=('staff', 'staff'), trail='People=Staff.dc.html|Staff=Staff.dc.html|All Staff') + staff_body,
      staff_js, "{ q: '', group: 'all', emp: '', sort: 'name', dir: 1, open: {} }")

# ---------- Organisation Chart ----------
CARD = '''<div style="border: 1px solid {{t.border}}; border-radius: 6px; padding: 12px 16px; background: {{t.bg}}; display: flex; flex-direction: column; gap: 2px; min-width: 0">
            <span style="display: flex; align-items: center; gap: 8px; font-size: 14px; line-height: 20px; font-weight: 500">%s{{%s.name}}</span>
            <span style="font-size: 13px; line-height: 18px; color: {{t.muted}}">{{%s.role}}</span>
            <span style="font-size: 13px; line-height: 18px; color: {{t.muted}}; display: {{%s.empShow}}">Contracted</span>
          </div>'''
org_body = f'''
    <section aria-labelledby="chart-h" style="display: flex; flex-direction: column; gap: 16px">
      <div style="display: flex; flex-wrap: wrap; justify-content: space-between; align-items: baseline; gap: 12px">
        <h2 id="chart-h" style="margin: 0; font-size: 16px; line-height: 24px; font-weight: 600; letter-spacing: -0.32px">Chains of Responsibility</h2>
        <span style="font-size: 13px; line-height: 18px; color: {{{{t.muted}}}}">Exposition Chapter A.8, Revision 7</span>
      </div>
      <div role="tree" aria-label="Organisation Chart" style="display: flex; flex-direction: column; align-items: center">
        <div role="treeitem" aria-level="1" style="width: 300px">{CARD % ('', 'top', 'top', 'top')}</div>
        <div aria-hidden="true" style="width: 1px; height: 24px; background: {{{{t.sBorder}}}}"></div>
        <div style="width: 100%; display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 32px">
          <sc-for list="{{{{teams}}}}" as="m" hint-placeholder-count="3">
            <div role="group" style="display: flex; flex-direction: column; align-items: stretch; min-width: 0">
              <div aria-hidden="true" style="position: relative; height: 24px"><div style="position: absolute; top: 0; left: {{{{m.l}}}}; right: {{{{m.r}}}}; border-top: 1px solid {{{{t.sBorder}}}}"></div><div style="position: absolute; top: 0; left: 50%; width: 1px; height: 24px; background: {{{{t.sBorder}}}}"></div></div>
              <div role="treeitem" aria-level="2">{CARD % ('', 'm', 'm', 'm')}</div>
              <div style="margin-left: 20px; padding-left: 20px; border-left: 1px solid {{{{t.sBorder}}}}; display: flex; flex-direction: column; gap: 12px; padding-top: 12px">
                <sc-for list="{{{{m.people}}}}" as="p" hint-placeholder-count="4">
                  <div role="treeitem" aria-level="3">{CARD % (DOT % ('p', 'p'), 'p', 'p', 'p')}</div>
                </sc-for>
              </div>
            </div>
          </sc-for>
        </div>
      </div>
    </section>

    <section aria-labelledby="np-h" style="display: flex; flex-direction: column; gap: 16px">
      <h2 id="np-h" style="margin: 0; font-size: 16px; line-height: 24px; font-weight: 600; letter-spacing: -0.32px">Management Personnel</h2>
      <div style="overflow-x: auto; border: 1px solid {{{{t.border}}}}; border-radius: 6px">
        <table style="width: 100%; min-width: 900px; border-collapse: collapse; font-size: 14px; line-height: 20px; white-space: nowrap">
          <thead><tr style="background: {{{{t.sidebar}}}}; color: {{{{t.muted}}}}; font-size: 13px; text-align: left">
            <th scope="col" style="padding: 12px 16px; font-weight: 500; border-bottom: 1px solid {{{{t.border}}}}">Role</th>
            <th scope="col" style="padding: 12px 16px; font-weight: 500; border-bottom: 1px solid {{{{t.border}}}}">Responsible For</th>
            <th scope="col" style="padding: 12px 16px; font-weight: 500; border-bottom: 1px solid {{{{t.border}}}}">Reports To</th>
            <th scope="col" style="padding: 12px 16px; font-weight: 500; border-bottom: 1px solid {{{{t.border}}}}">Point</th>
          </tr></thead>
          <tbody>
            <sc-for list="{{{{mgmt}}}}" as="r" hint-placeholder-count="4"><tr>
              <td style="padding: 12px 16px; border-bottom: 1px solid {{{{t.row}}}}; font-weight: 500">{{{{r.role}}}}</td>
              <td style="padding: 12px 16px; border-bottom: 1px solid {{{{t.row}}}}">{{{{r.what}}}}</td>
              <td style="padding: 12px 16px; border-bottom: 1px solid {{{{t.row}}}}">{{{{r.to}}}}</td>
              <td style="padding: 12px 16px; border-bottom: 1px solid {{{{t.row}}}}">{{{{r.point}}}}</td>
            </tr></sc-for>
          </tbody>
        </table>
      </div>
    </section>
'''
org_js = '''    const card = p => ({ name: p.name, role: p.role, empShow: p.emp === 'Contracted' ? 'block' : 'none', colour: C[p.auth[2]] || C[p.trn[2]] || 'transparent', mark: (p.auth[2] || p.trn[2]) ? 'inline-block' : 'none' });
    const top = card(PEOPLE.find(p => p.id === 'am'));
    const order = ['cam', 'mm', 'cmm'];
    const teams = order.map((id, i) => Object.assign(card(PEOPLE.find(p => p.id === id)), {
      l: i === 0 ? '50%' : '-16px', r: i === order.length - 1 ? '50%' : '-16px',
      people: PEOPLE.filter(p => p.to === id).map(card) }));
    const mgmt = [
      { role: 'Accountable Manager', what: 'Finance and Resources, Exposition Statement', to: 'None', point: 'CAO.A.035(a)' },
      { role: 'Continuing Airworthiness Manager', what: 'Continuing Airworthiness Management, Airworthiness Review', to: 'Accountable Manager', point: 'CAO.A.035(b)' },
      { role: 'Maintenance Manager', what: 'Maintenance, Planning, Logistics', to: 'Accountable Manager', point: 'CAO.A.035(b)' },
      { role: 'Compliance Monitoring Manager', what: 'Quality System, Internal Audits, Independent of the Work', to: 'Accountable Manager', point: 'CAO.A.100(a)' }
    ];
    return { t, dark, top, teams, mgmt };'''

write('OrgChart.dc.html', 'Organisation Chart', 'orgchart', 1300,
      header('People', 'Organisation Chart', '', [btn('Edit Chart')], tabs=('staff', 'orgchart'), trail='People=Staff.dc.html|Staff=Staff.dc.html|Organisation Chart') + org_body,
      org_js, '{}')
print('ok')
