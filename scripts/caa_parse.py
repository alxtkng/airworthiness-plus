import re, json, sys, glob, os
LABELS = re.compile(r'(Reference Number|Category\s{2,}|Category$|Website|Regional Office|Approval Date|Suspension/|Revocation Date)')
FOOT = re.compile(r'^\s*\d{1,2} [A-Z][a-z]+ \d{4}\s+Page \d+ of \d+\s*$')
PC = re.compile(r'\b([A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2})\b')
def frags(line, start=0):
    out = []
    for m in re.finditer(r'\S+(?: \S+)*', line):
        if m.start() >= start:
            out.append((m.start(), m.group(0)))
    return out
def parse(path, source):
    L = open(path).read().split('\n')
    date = None
    ents = []; cur = None; mode = None
    for raw in L:
        line = raw.replace('\f', '').rstrip()
        if FOOT.match(line):
            date = date or ' '.join(line.split()[:3]); continue
        if line.startswith('CAA - ') or re.match(r'^Category \S', line): continue
        if line.startswith('Name '):
            cur = {'source': source, 'name': line[4:].strip(), 'address': [], 'ratings': [], 'exposition': '', 'fields': {}}
            ents.append(cur); mode = 'addr'; continue
        if cur is None: continue
        if line.startswith('Organisational Data'):
            mode = 'org'; continue
        if mode == 'addr':
            if not line.strip(): continue
            m = LABELS.search(line)
            left = line[:m.start()] if m else line
            right = line[m.start():] if m else ''
            left = left.replace('Address', '', 1) if left.startswith('Address') else left
            if left.strip(): cur['address'].append(left.strip())
            if right:
                mm = re.match(r'(Reference Number|Category|Website|Regional Office|Approval Date|Suspension/|Revocation Date)\s*(.*)', right.strip())
                if mm: cur['fields'][mm.group(1)] = mm.group(2).strip()
            continue
        if mode == 'org':
            if line.startswith('Exposition'):
                cur['exposition'] = ' '.join(line.split()[1:]); cur['_last'] = None; continue
            if line.startswith('Ratings'):
                body = line[len('Ratings'):]
                fs = frags(body)
                if not fs: continue
                pathtxt = fs[0][1]; cols = fs[1:]
                r = {'path': pathtxt, 'cols': [[p, t] for p, t in cols]}
                cur['ratings'].append(r); cur['_last'] = r; continue
            if line.strip() and cur.get('_last') is not None:
                body = line[len('Ratings'):] if len(line) > 7 else line
                for p, t in frags(body):
                    r = cur['_last']
                    if not r['cols'] or p < r['cols'][0][0] - 20:
                        r['path'] += ' ' + t if p < 40 else ''
                        if p >= 40 and not r['cols']: r['cols'].append([p, t])
                        continue
                    best = min(r['cols'], key=lambda c: abs(c[0] - p))
                    best[1] += ' ' + t
            elif line.strip() and not line.startswith(' '):
                cur['_last'] = None
    out = []
    for e in ents:
        e.pop('_last', None)
        nm = e['name']
        ref = e['fields'].get('Reference Number', '')
        tags = re.findall(r'\(([^)]*)\)', nm)
        clean = nm
        for t in tags:
            if t == ref or t in ('GA',) or re.match(r'^[A-Z0-9\.\-/ ]+$', t) and any(c.isdigit() for c in t):
                clean = clean.replace('(' + t + ')', '')
        clean = ' '.join(clean.split())
        addr = []
        for a in e['address']:
            if a not in addr: addr.append(a)
        pcs = [m.group(1) for a in addr for m in [PC.search(a)] if m]
        pc = pcs[-1] if pcs else ''
        country = addr[-1] if addr and not PC.search(addr[-1]) else ''
        ratings = []
        for r in e['ratings']:
            p = r['path'].replace('AW\\Ratings\\', '')
            ratings.append({'path': p.split('\\'), 'scope': [' '.join(c[1].split()) for c in r['cols']]})
        site = e['fields'].get('Website', '')
        out.append({'name': clean, 'ref': ref, 'ga': 'GA' in tags, 'category': e['fields'].get('Category', ''), 'source': e['source'],
                    'address': addr, 'postcode': pc, 'country': country, 'website': site,
                    'office': e['fields'].get('Regional Office', ''), 'approved': e['fields'].get('Approval Date', ''),
                    'suspended': e['fields'].get('Revocation Date', '') or e['fields'].get('Suspension/', ''),
                    'exposition': e['exposition'], 'ratings': ratings})
    return out, date
if __name__ == '__main__':
    allr = []; dates = {}
    for f, src in [('cao','Part-CAO'),('camo','Part-CAMO'),('part145','Part 145'),('part21j','Part 21J'),('part21g','Part 21G'),('part147','Part 147'),('bcar','BCAR'),('arc','ARC Privileges'),('adoa','ADOA'),('suspended','Suspended')]:
        rows, d = parse('/home/claude/caa1112/%s.txt' % f, src)
        dates[src] = d; allr += rows
        print(src, len(rows), d)
    json.dump({'dates': dates, 'orgs': allr}, open('/home/claude/caa1112/orgs_raw.json', 'w'), ensure_ascii=False, indent=0)
