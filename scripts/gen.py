# Generator for static Airworthiness+ pages in the shared layout.
import html
OUT = '/home/claude/overhaul/project/'
C = {'g': '#1FCB6E', 'a': '#FFB224', 'r': '#FF5A4E'}
E = html.escape

HEAD = '''<!doctype html>
<html lang="en-GB">
<head>
<meta charset="utf-8">
<title>%s</title>
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
  <div style="flex: 1 1 248px; max-width: 100%%; display: flex">
    <dc-import name="Sidebar" active="%s" dark="{{dark}}" hint-size="248px,%dpx"></dc-import>
  </div>
  <main style="flex: 999 1 640px; min-width: 0; box-sizing: border-box; padding: 32px 40px 64px; display: flex; flex-direction: column; gap: 40px">
'''

TAIL = '''  </main>
</div>
</x-dc>
<script type="text/x-dc" data-dc-script data-props='{"dark":{"editor":"boolean","default":false},"$preview":{"width":1440,"height":%d}}'>
class Component extends DCLogic {
  constructor(props) { super(props); this.state = { open: {} }; }
  renderVals() {
    const dark = this.props.dark === true || this.props.dark === 'true';
    const t = dark
      ? { scheme: 'dark', bg: '#0A0A0A', sidebar: '#000000', border: '#2E2E2E', row: '#2E2E2E', text: '#EDEDED', muted: '#A1A1A1', body: '#EDEDED', pBg: '#EDEDED', pFg: '#0A0A0A', sBorder: '#2E2E2E', note: '#000000' }
      : { scheme: 'light', bg: '#FFFFFF', sidebar: '#FAFAFA', border: '#EBEBEB', row: '#EBEBEB', text: '#171717', muted: '#666666', body: '#171717', pBg: '#171717', pFg: '#FFFFFF', sBorder: '#EBEBEB', note: '#FAFAFA' };
    const ids = __IDS__;
    const o = this.state.open, open = {}, exp = {}, rot = {}, tog = {}, line = {}, bg = {};
    ids.forEach(id => { const on = !!o[id]; open[id] = on; exp[id] = on ? 'true' : 'false'; rot[id] = on ? '90deg' : '0deg'; line[id] = on ? 'transparent' : t.row; bg[id] = on ? t.sidebar : 'transparent';
      tog[id] = () => { const n = Object.assign({}, this.state.open); n[id] = !n[id]; this.setState({ open: n }); }; });
    return { t, dark, open, exp, rot, tog, line, bg };
  }
}
</script>
</body>
</html>
'''

def btn(label, primary=False, href=None):
    st = ('border: 0; background: {{t.pBg}}; color: {{t.pFg}}' if primary
          else 'border: 1px solid {{t.sBorder}}; background: {{t.bg}}; color: {{t.text}}')
    if href:
        return f'<a href="{href}" style="font-size: 14px; font-weight: 500; height: 40px; line-height: 38px; box-sizing: border-box; padding: 0 16px; border-radius: 6px; {st}; display: inline-block">{E(label)}</a>'
    return f'<button type="button" style="font: inherit; font-size: 14px; font-weight: 500; height: 40px; padding: 0 16px; border-radius: 6px; {st}; cursor: pointer">{E(label)}</button>'

SR = 'position: absolute; width: 1px; height: 1px; margin: -1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap'

def header(crumb, h1, desc=None, buttons=(), tabs=None, trail=None):
    # Navigation model: sidebar is global, the breadcrumb names the section, section tabs are local.
    # No visible page title on section pages: the breadcrumb already names it.
    b = ''.join(buttons)
    parts = (trail or crumb).split('|')
    if tabs and trail and len(parts) > 1:
        parts = parts[:-1]
    parts[-1] = parts[-1].split('=')[0]
    tr = '|'.join(parts)
    top = f'    <dc-import name="TopBar" trail="{E(tr)}" line="{"false" if tabs else "true"}" dark="{{{{dark}}}}" hint-size="1100px,56px"></dc-import>\n'
    h = f'    <h1 style="{SR}">{E(h1)}</h1>\n'
    if tabs:
        return top + h + f'''    <div style="margin-top: -36px; display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 16px; margin-left: -40px; margin-right: -40px; padding: 0 40px; box-shadow: inset 0 -1px 0 {{{{t.border}}}}">
      <dc-import name="Tabs" set="{tabs[0]}" active="{tabs[1]}" line="false" dark="{{{{dark}}}}" hint-size="760px,44px"></dc-import>
      <div style="display: flex; flex-wrap: wrap; gap: 8px; padding: 2px 0">{b}</div>
    </div>
'''
    return top + h + (f'''    <div style="display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 8px; margin-top: -16px">{b}</div>
''' if b else '')


SMALLW = {'a','an','and','as','at','but','by','for','if','in','nor','of','on','or','per','the','to','via','with'}
def _cap(w, first):
    if not w or any(c.isupper() for c in w) or any(c.isdigit() for c in w):
        return w
    lead = ''
    while w and not w[0].isalpha():
        lead += w[0]; w = w[1:]
    if not w:
        return lead
    parts = w.split('-')
    out = []
    for i, p in enumerate(parts):
        if (i or not first) and p.lower() in SMALLW:
            out.append(p.lower())
        else:
            out.append(p[:1].upper() + p[1:])
    return lead + '-'.join(out)

# Regulatory designations are shown exactly as SRG1782 writes them, never re-cased.
VERBATIM = ['Piper PA-28 Series (Lycoming)', 'Piper PA-38 Series (Lycoming)', 'Cessna/Reims-Cessna 152/F152 Series (Lycoming)',
            'Cessna/Reims-Cessna 172/F172 Series (Lycoming)', 'Robin DR 400 series (Lycoming)', 'Grob G115/120 Series (Lycoming)',
            'PA-28-140 (Cherokee Cruiser)', 'PA-28-181 (Archer II)', 'DR 400/180', 'G 115']

def L(s):
    """Terse Title Case label with typographic punctuation."""
    if not isinstance(s, str) or not s:
        return s
    keep = {}
    for i, v in enumerate(sorted(VERBATIM, key=len, reverse=True)):
        if v in s:
            k = 'QZ%dQZ' % i
            keep[k] = v
            s = s.replace(v, k)
    s = s.strip().replace("'", '\u2019').replace(' - ', ' \u2013 ')
    while s.endswith('.'):
        s = s[:-1]
    words = s.split(' ')
    res = []
    for i, w in enumerate(words):
        first = i == 0 or (res and res[-1].endswith(':'))
        res.append(_cap(w, first))
    out = ' '.join(res)
    for k, v in keep.items():
        out = out.replace(k, v)
    return out

SMALL = {'a','an','and','as','at','by','for','in','of','on','or','the','to','with','a'}
def tcase(text):
    w = text.split(' ')
    return ' '.join(x if (i and x.lower() in SMALL) or not x[:1].isalpha() else x[:1].upper() + x[1:] for i, x in enumerate(w))

def strip(items):
    s = ''.join(f'<span><span style="color: {{{{t.text}}}}; font-weight: 500">{E(v)}</span> {E(L(l))}</span>' for v, l in items)
    return f'    <div style="display: flex; flex-wrap: wrap; column-gap: 40px; row-gap: 8px; padding: 14px 16px; border-radius: 6px; border: 1px solid {{{{t.border}}}}; font-size: 14px; line-height: 20px; font-weight: 400; color: {{{{t.muted}}}}">{s}</div>\n'

def dot(c):
    if c == 'o':
        return '<span aria-hidden="true" style="width: 10px; height: 10px; border-radius: 9999px; box-shadow: inset 0 0 0 1.5px {{t.muted}}; flex: none; display: inline-block"></span>'
    return f'<span aria-hidden="true" style="width: 10px; height: 10px; border-radius: 9999px; background: {C[c]}; flex: none; display: inline-block"></span>'

def cell(v, strong=False):
    # v: str, or dict(text, sub, dot, mono, bold, href)
    if isinstance(v, str):
        v = L(v)
        if False:
            return f'<span style="color: {{{{t.body}}}}">{E(v)}</span>'
        return f'<span style="font-weight: {500 if strong else 400}">{E(v)}</span>'
    txt = E(L(v.get('text', '')))
    if v.get('href'):
        txt = f'<a href="{v["href"]}" style="color: {{{{t.text}}}}; text-decoration: underline; text-underline-offset: 3px; text-decoration-color: {{{{t.sBorder}}}}">{txt}</a>'
    style = ''
    style += 'font-weight: 500;' if v.get('bold', strong) else 'font-weight: 400;'
    if v.get('mono'):
        style += " font-family: 'Geist Mono Embedded', 'Geist Mono', monospace; font-size: 13px;"
    main = f'<span style="{style}">{txt}</span>'
    if v.get('dot') in ('a', 'r') or (v.get('dot') and v.get('status')):
        main = f'<span style="display: inline-flex; align-items: center; gap: 8px">{dot(v["dot"])}{main}</span>'
    if v.get('sub'):
        main = f'<span style="display: flex; flex-direction: column; gap: 2px">{main}<span style="color: {{{{t.muted}}}}; font-size: 13px; line-height: 18px; font-weight: 400">{E(L(v["sub"]))}</span></span>'
    return main

ROWS = []
CHEV = '<svg aria-hidden="true" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="transform: rotate({{rot.%s}}); color: {{t.muted}}"><path d="M9 6l6 6-6 6"></path></svg>'

def plain(v):
    return {k: x for k, x in v.items() if k != 'sub'} if isinstance(v, dict) else v

def has_text(v):
    return bool(v.get('text') or v.get('sub')) if isinstance(v, dict) else bool(v)

def table(cols, rows, minw=1040):
    # One line per row, truncated; a disclosure button opens the full row detail beneath it.
    th = ''.join(f'<th scope="col" style="padding: 12px 16px; font-weight: 500; white-space: nowrap; border-bottom: 1px solid {{{{t.border}}}}; text-align: {a}{"; width: " + w if w else ""}">{E(l)}</th>' for l, w, a in cols)
    th = '<th scope="col" style="width: 40px; padding: 12px 0 12px 12px; border-bottom: 1px solid {{t.border}}"><span style="position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0)">Details</span></th>' + th
    body = ''
    for r in rows:
        rid = 'r%d' % (len(ROWS) + 1)
        ROWS.append(rid)
        line = '{{line.%s}}' % rid
        btn_ = (f'<td style="width: 40px; padding: 10px 0 10px 12px; border-bottom: 1px solid {line}; vertical-align: middle">'
                f'<button type="button" aria-expanded="{{{{exp.{rid}}}}}" aria-label="Show Details" onClick="{{{{tog.{rid}}}}}" style="font: inherit; width: 28px; height: 28px; border: 0; border-radius: 6px; background: transparent; cursor: pointer; display: inline-flex; align-items: center; justify-content: center">{CHEV % rid}</button></td>')
        tds = ''.join(
            f'<td style="padding: 12px 16px; border-bottom: 1px solid {line}; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: {(w if w else "360px")}; text-align: {cols[i][2]}">{cell(plain(v), i == 0)}</td>'
            for i, (v, (l, w, a)) in enumerate(zip(r, cols)))
        facts = ''.join(
            f'<div style="display: flex; flex-direction: column; gap: 4px; min-width: 0"><span style="font-size: 13px; line-height: 16px; color: {{{{t.muted}}}}">{E(cols[i][0])}</span><span style="font-size: 14px; line-height: 20px">{cell(v)}</span></div>'
            for i, v in enumerate(r) if has_text(v))
        detail = (f'<sc-if value="{{{{open.{rid}}}}}" hint-placeholder-val="{{{{false}}}}"><tr><td colspan="{len(cols) + 1}" style="padding: 4px 16px 16px 52px; border-bottom: 1px solid {{{{t.row}}}}">'
                  f'<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); column-gap: 32px; row-gap: 14px">{facts}</div></td></tr></sc-if>')
        body += f'<tr style="background: {{{{bg.{rid}}}}}">{btn_}{tds}</tr>{detail}\n'
    return f'''<div style="overflow-x: auto; border: 1px solid {{{{t.border}}}}; border-radius: 6px">
<table style="width: 100%; min-width: {minw}px; border-collapse: collapse; font-size: 14px; line-height: 20px">
<thead><tr style="background: {{{{t.sidebar}}}}; color: {{{{t.muted}}}}; font-size: 13px; text-align: left">{th}</tr></thead>
<tbody>
{body}</tbody>
</table>
</div>
'''

def section(hid, heading, inner, intro='', right=''):
    i = f'<p style="margin: 0; font-size: 13px; line-height: 18px; font-weight: 400; color: {{{{t.muted}}}}">{E(L(intro))}</p>' if intro else ''
    return f'''    <section aria-labelledby="{hid}" style="display: flex; flex-direction: column; gap: 16px">
      <div style="display: flex; flex-wrap: wrap; justify-content: space-between; align-items: baseline; gap: 12px"><h2 id="{hid}" style="margin: 0; font-size: 16px; line-height: 24px; font-weight: 600; letter-spacing: -0.32px">{E(L(heading))}</h2>{right}</div>
      {i}
{inner}    </section>
'''

def checklist(items):
    li = ''
    for c, text, note in items:
        n = f'<span style="color: {{{{t.muted}}}}; font-size: 14px">{E(L(note))}</span>' if note else ''
        li += f'<li style="display: flex; gap: 12px; align-items: flex-start; padding: 12px 0; border-bottom: 1px solid {{{{t.border}}}}; font-size: 14px; line-height: 20px"><span style="margin-top: 5px; display: inline-flex">{dot(c)}</span><span style="display: flex; flex-direction: column; gap: 2px"><span style="font-weight: 500">{E(L(text))}</span>{n}</span></li>\n'
    return f'<ol style="margin: 0; padding: 0; list-style: none; border-top: 1px solid {{{{t.border}}}}">\n{li}</ol>\n'

def callout(text, c=None):
    d = dot(c) if c in ('a', 'r') else ''
    return f'<div style="display: flex; gap: 12px; align-items: flex-start; padding: 14px 16px; border-radius: 6px; background: {{{{t.note}}}}; font-size: 14px; line-height: 20px; color: {{{{t.body}}}}"><span style="margin-top: 5px; display: inline-flex">{d}</span><span>{E(L(text))}</span></div>\n'

def foot(text=None):
    return ''
    return f'    <p style="margin: 0; font-size: 13px; line-height: 18px; font-weight: 400; color: {{{{t.muted}}}}">{E(text)}</p>\n'

def page(name, title, active, height, parts):
    import json as _j
    s = HEAD % (E(title), active, height) + ''.join(parts) + (TAIL % height).replace('__IDS__', _j.dumps(ROWS))
    del ROWS[:]
    import os
    only = os.environ.get('ONLY')
    if only and name not in only.split(','):
        return name
    open(OUT + name, 'w').write(s)
    return name
