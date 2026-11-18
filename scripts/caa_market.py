import json, re
d = json.load(open('/home/claude/caa1112/orgs_raw.json'))
orgs = d['orgs']
susp = {o['ref']: o for o in orgs if o['source'] == 'Suspended' and o['ref']}
arc = {o['ref'] for o in orgs if o['source'] == 'ARC Privileges' and o['ref']}
LABEL = {'Part-CAO': 'Part-CAO', 'Part-CAMO': 'Part-CAMO', 'Part 145': 'Part 145', 'Part 21J': 'Part 21J Design', 'Part 21G': 'Part 21G Production',
         'Part 147': 'Part 147 Training', 'BCAR': 'BCAR', 'ADOA': 'Alternative Procedures to Design Organisation Approval'}
# Fleet: registration, structure word, type keywords
FLEET = [('G-ABCD', 'METAL', ['PA-28', 'PA28']), ('G-DGHI', 'METAL', ['PA-28', 'PA28']), ('G-EJKL', 'METAL', ['CESSNA 152', 'C152', '152/F152']),
         ('G-BXYZ', 'METAL', ['CESSNA 172', 'C172', '172/F172']), ('G-FMNO', 'COMPOSITE', ['GROB G 115', 'GROB G115', 'G115']), ('G-CDEF', 'WOOD', ['DR400', 'DR 400', 'ROBIN DR'])]
def tc(s):
    s = ' '.join(s.split())
    if s.isupper() and len(s) > 4:
        small = {'AND','OR','OF','THE','TO','IN','ON','FOR','A','AN','BY','WITH','UP'}
        w = []
        for i, x in enumerate(s.split(' ')):
            lx = x.lower()
            if any(c.isdigit() for c in x) or re.match(r'^[A-Z]{1,3}\d', x) or x in ('II','III','IV','MTOM','CS-STAN','NDT','ATA','EASA','CAA','UK','APU'):
                w.append(x)
            elif i and lx in small: w.append(lx)
            else: w.append('-'.join(p[:1].upper() + p[1:].lower() for p in x.split('-')))
        s = ' '.join(w)
    return s
out = []
for o in orgs:
    if o['source'] == 'ARC Privileges': continue
    src = o['source']
    if src == 'Suspended':
        cat = o['category'] or ''
        src = 'Part-CAO' if 'CAO' in cat else 'Part-CAMO' if 'CAMO' in cat else 'Part 145' if '145' in cat else 'Part 147' if '147' in cat else 'Part 21G' if '21G' in cat or 'POA' in cat else 'Part 21J' if '21J' in cat or 'DOA' in cat else 'BCAR' if 'BCAR' in cat else cat
    rt = []; text = []
    for r in o['ratings']:
        path = ' > '.join(tc(p) for p in r['path'][1:] if p)
        scope = '; '.join(tc(s) for s in r['scope'] if s)
        rt.append([path[:120], scope[:200]])
        text.append((' '.join(r['path']) + ' ' + ' '.join(r['scope'])).upper())
    T = ' | '.join(text)
    sv = set()
    if src == 'Part-CAO':
        for t in text:
            if 'AIRCRAFT' in t:
                if 'MAINTENANCE' in t and ('MAINTENANCE &' in t or 'MAINTENANCE /' in t or 'MAINTENANCE,' in t or t.strip().endswith('MAINTENANCE') or 'MAINTENANCE' in t.split('|')[-1] ): sv.add('Maintenance')
                if 'CONTINUING' in t: sv.add('Continuing Airworthiness Management')
                if 'REVIEW' in t: sv.add('Airworthiness Review')
            if 'COMPONENTS' in t: sv.add('Components')
    elif src == 'Part-CAMO':
        sv.add('Continuing Airworthiness Management')
    elif src in ('Part 145', 'BCAR'):
        if 'AIRCRAFT' in T: sv.add('Maintenance')
        if 'COMPONENT' in T or 'ENGINE' in T or 'SPECIALISED' in T: sv.add('Components')
        if src == 'BCAR' and ('A8-21' in T or 'DESIGN' in T or 'A8-1' in T or 'A8-8' in T or 'A8-9' in T): sv.add('Design')
    elif src in ('Part 21J', 'ADOA'): sv.add('Design')
    elif src == 'Part 21G': sv.add('Production')
    elif src == 'Part 147': sv.add('Training')
    if o['ref'] in arc: sv.add('Airworthiness Review')
    # Aircraft match
    ac = []
    for reg, struct, keys in FLEET:
        hit = False
        if src == 'Part-CAO' and any('AEROPLANES UP TO 2 730' in t or 'AEROPLANES UP TO 2730' in t for t in text): hit = True
        if src in ('Part 145', 'BCAR') and re.search(r'PISTON ENGINE[^|]*' + struct, T): hit = True
        if src in ('Part 145', 'BCAR') and re.search(r'PISTON ENGINE AEROPLANES - MIXED', T): hit = True
        if any(k in T for k in keys): hit = True
        if hit: ac.append(reg)
    s = susp.get(o['ref'])
    status = 'Suspended' if (o['source'] == 'Suspended' or o['suspended']) else 'Approved'
    addr = [a for a in o['address'] if a.upper() not in ('UK', 'UNITED KINGDOM')]
    site = o['website'].strip()
    email = site if '@' in site else ''
    site = '' if email else site
    out.append({'n': o['name'], 'r': o['ref'], 'a': LABEL.get(src, src), 'ad': addr, 'pc': o['postcode'], 'w': site, 'e': email, 'sd': tc(o['suspended']) if o['suspended'] else '',
                'o': tc(o['office']) if o['office'] else '', 'd': tc(o['approved']) if o['approved'] else '',
                'st': status, 'x': o['exposition'].replace('AW\\Exposition\\', ''), 'rt': rt, 'sv': sorted(sv), 'ac': ac})
out.sort(key=lambda x: x['n'].lower())
res = {'date': d['dates'].get('Part-CAO'), 'source': 'CAA Airworthiness Approved Organisations lists', 'orgs': out}
json.dump(res, open('/home/claude/caa1112/marketplace.json', 'w'), ensure_ascii=False, separators=(',', ':'))
import collections, os
print(len(out), os.path.getsize('/home/claude/caa1112/marketplace.json'))
print(collections.Counter(s for x in out for s in x['sv']))
print(collections.Counter(x['a'] for x in out))
print(collections.Counter(r for x in out for r in x['ac']))
print(collections.Counter(x['st'] for x in out), len(susp))
for x in out[:3]: print(json.dumps(x, ensure_ascii=False)[:500])
