"""Convert a hand-built DC table to one-line expandable rows.
expand(src, listname, alias, maxw) -> src with markup changed; JS wrap added separately."""
import re

CHEV = ('<td style="width: 40px; padding: 10px 0 10px 12px; border-bottom: 1px solid {{A.xLine}}"><button type="button" aria-expanded="{{A.xExp}}" aria-label="Show Details" onClick="{{A.xTog}}" style="font: inherit; width: 28px; height: 28px; border: 0; border-radius: 6px; background: transparent; cursor: pointer; display: inline-flex; align-items: center; justify-content: center"><svg aria-hidden="true" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="transform: rotate({{A.xRot}}); color: {{t.muted}}"><path d="M9 6l6 6-6 6"></path></svg></button></td>')
TH0 = '<th scope="col" style="width: 40px; padding: 12px 0 12px 12px; border-bottom: 1px solid {{t.border}}"><span style="position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0)">Details</span></th>'
DETAIL = ('<sc-if value="{{A.xOpen}}" hint-placeholder-val="{{false}}"><tr style="background: {{A.xBg}}"><td colspan="N" style="padding: 4px 16px 16px 52px; border-bottom: 1px solid {{t.row}}; white-space: normal">'
          '<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); column-gap: 32px; row-gap: 14px">'
          '<sc-for list="{{A.xFacts}}" as="xf" hint-placeholder-count="4"><div style="display: flex; flex-direction: column; gap: 4px"><span style="font-size: 13px; line-height: 16px; color: {{t.muted}}">{{xf.label}}</span><span style="font-size: 14px; line-height: 20px">{{xf.value}}</span></div></sc-for>'
          '</div></td></tr></sc-if>')
SKIP = {'colour', 'mark', 'href', 'bg', 'pressed', 'pick'}

def expand(src, name, alias, maxw=320, detail=True):
    i = src.index('<sc-for list="{{%s}}" as="%s"' % (name, alias))
    ts = src.rindex('<table', 0, i); te = src.index('</table>', i) + 8
    tbl = src[ts:te]
    labels = re.findall(r'<th scope="col"[^>]*>(.*?)</th>', tbl)
    tbl = re.sub(r'min-width: \d+px; border-collapse', 'min-width: 0; border-collapse', tbl, 1)
    tbl = tbl.replace('<tr style="background: {{t.sidebar}}; text-align: left; color: {{t.muted}}; font-size: 13px">',
                      '<tr style="background: {{t.sidebar}}; text-align: left; color: {{t.muted}}; font-size: 13px; white-space: nowrap">' + (TH0 if detail else ''), 1)
    fs = tbl.index('<sc-for'); fe = tbl.index('</sc-for>', fs)
    # the row
    rs = tbl.index('<tr', fs); re_ = tbl.index('</tr>', rs) + 5
    row = tbl[rs:re_]
    tds = re.findall(r'<td style="[^"]*">.*?</td>', row, re.S)
    keys = []
    new = []
    line = '{{%s.xLine}}' % alias if detail else '{{t.row}}'
    for td in tds:
        m = re.match(r'<td style="([^"]*)">(.*)</td>$', td, re.S)
        st, body = m.group(1), m.group(2)
        ks = [k for k in re.findall(r'\{\{%s\.(\w+)\}\}' % alias, body) if k not in SKIP]
        keys.append(ks[0] if ks else None)
        st = re.sub(r'padding: [^;]+', 'padding: 12px 16px', st)
        st = re.sub(r'border-bottom: 1px solid \{\{[^}]+\}\}', 'border-bottom: 1px solid ' + line, st)
        st = re.sub(r'; vertical-align: \w+', '', st)
        st = re.sub(r'; white-space: nowrap', '', st)
        st += '; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: %dpx' % maxw
        # drop stacked secondary spans (display: block) – they move to the detail row
        body = re.sub(r'<span style="display: block;[^"]*">\{\{%s\.\w+\}\}</span>' % alias, '', body)
        new.append('<td style="%s">%s</td>' % (st, body))
    bgv = '{{%s.xBg}}' % alias if detail else 'transparent'
    tr = '<tr style="background: %s">' % bgv + (CHEV.replace('A.', alias + '.') if detail else '') + ''.join(new) + '</tr>'
    if detail:
        tr += DETAIL.replace('A.', alias + '.').replace('colspan="N"', 'colspan="%d"' % (len(tds) + 1))
    tbl = tbl[:rs] + tr + tbl[re_:]
    src = src[:ts] + tbl + src[te:]
    return src, list(zip(labels, keys))

HELPER = """    const X = (id, list, cols, extra) => list.map((r, i) => {
      const k = id + '|' + i, on = !!(this.state.xo || {})[k];
      const facts = cols.filter(c => c[1] && r[c[1]]).map(c => ({ label: c[0], value: String(r[c[1]]) })).concat(extra ? extra(r).filter(f => f.value) : []);
      return Object.assign({}, r, { xOpen: on, xExp: on ? 'true' : 'false', xRot: on ? '90deg' : '0deg', xLine: on ? 'transparent' : t.row, xBg: on ? t.sidebar : 'transparent', xFacts: facts,
        xTog: () => { const n = Object.assign({}, this.state.xo || {}); n[k] = !n[k]; this.setState({ xo: n }); } });
    });
"""
