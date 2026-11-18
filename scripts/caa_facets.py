import json, re
d = json.load(open('/home/claude/caa1112/marketplace.json'))
# Standard terms, spelled out in full
P145 = {'A1': 'A1 Aeroplanes Above 5 700 kg', 'A2': 'A2 Aeroplanes 5 700 kg and Below', 'A3': 'A3 Helicopters', 'A4': 'A4 Aircraft Other Than A1, A2 and A3',
        'B1': 'B1 Turbine Engines', 'B2': 'B2 Piston Engines', 'B3': 'B3 Auxiliary Power Units', 'D1': 'D1 Non-Destructive Testing'}
C = {1: 'Air Conditioning and Pressurisation', 2: 'Auto Flight', 3: 'Communications and Navigation', 4: 'Doors and Hatches', 5: 'Electrical Power and Lights',
     6: 'Equipment', 7: 'Engine', 8: 'Flight Controls', 9: 'Fuel', 10: 'Helicopter and Rotors', 11: 'Helicopter Transmission', 12: 'Hydraulic Power',
     13: 'Indicating and Recording System', 14: 'Landing Gear', 15: 'Oxygen', 16: 'Propellers', 17: 'Pneumatic and Vacuum Systems',
     18: 'Protection From Ice, Rain and Fire', 19: 'Windows', 20: 'Structural', 21: 'Water Ballast', 22: 'Propulsion Augmentation'}
for k, v in C.items(): P145['C%d' % k] = 'C%d %s' % (k, v)
POA = {'A1': 'A1 Large Aeroplanes', 'A2': 'A2 Small Aeroplanes', 'A3': 'A3 Large Helicopters', 'A4': 'A4 Small Helicopters', 'A5': 'A5 Gyroplanes',
       'A6': 'A6 Sailplanes', 'A7': 'A7 Motor Gliders', 'A8': 'A8 Manned Balloons', 'A9': 'A9 Airships', 'A10': 'A10 Light Sport Aeroplanes',
       'A11': 'A11 Very Light Aeroplanes', 'A12': 'A12 Other', 'B1': 'B1 Turbine Engines', 'B2': 'B2 Piston Engines', 'B3': 'B3 Auxiliary Power Units',
       'B4': 'B4 Propellers', 'C1': 'C1 Appliances', 'C2': 'C2 Parts', 'D1': 'D1 Maintenance', 'D2': 'D2 Issue of Permit to Fly'}
CAO_CAT = [('AEROPLANES UP TO 2 730', 'Aeroplanes up to 2 730 kg MTOM'), ('AEROPLANES UP TO 2730', 'Aeroplanes up to 2 730 kg MTOM'),
           ('HELICOPTERS UP TO 1 200', 'Helicopters up to 1 200 kg MTOM and 4 Occupants'), ('HELICOPTERS UP TO 1200', 'Helicopters up to 1 200 kg MTOM and 4 Occupants'),
           ('HELICOPTERS', 'Helicopters, Other-Than-Complex Motor-Powered'), ('SAILPLANE', 'Sailplanes and Powered Sailplanes'), ('BALLOON', 'Balloons'),
           ('AIRSHIP', 'Airships'), ('COMPLETE PISTON ENGINE', 'Complete Piston Engines'), ('COMPLETE TURBINE ENGINE', 'Complete Turbine Engines'),
           ('ELECTRIC', 'Complete Electric Engines'), ('COMPONENTS OTHER THAN', 'Components Other Than Complete Engines'), ('NON-DESTRUCTIVE', 'Non-Destructive Testing'), ('NDT', 'Non-Destructive Testing')]
PRIV = [('MAINTENANCE', 'Maintenance'), ('CONTINUING', 'Continuing Airworthiness Management'), ('REVIEW', 'Airworthiness Review'), ('PERMIT', 'Permit to Fly')]
DOA_ACT = ['TC', 'STC', 'Major Changes', 'Minor Changes', 'Major Repairs', 'Minor Repairs', 'Permit to Fly']
def code(s, prefixes):
    m = re.match(r'^\s*([ABCD]\d{1,2})\b', s.upper())
    return m.group(1) if m and m.group(1) in prefixes else None
labels = {}
for o in d['orgs']:
    a = o['a']; facets = set(); summary = []; detail = []
    for path, scope in o['rt']:
        P = path.upper(); S = scope.upper(); parts = [x.strip() for x in path.split('>')]
        if a == 'Part 145':
            k = None
            for seg in parts[::-1]:
                k = code(seg, P145)
                if k: break
            if k:
                f = '145|' + k; facets.add(f); labels[f] = P145[k]
                detail.append([P145[k], scope]); summary.append(k)
            else:
                detail.append([path, scope])
        elif a == 'Part-CAO':
            cat = next((lab for key, lab in CAO_CAT if key in P), None)
            cm = re.search(r'\bC(\d{1,2})\b', S + ' ' + P)
            if cat:
                f = 'CAO|' + cat; facets.add(f); labels[f] = cat
            privs = [lab for key, lab in PRIV if key in (S + ' ' + P.split('>')[-1] if False else S + ' ' + P)] or (['Maintenance'] if cat and 'COMPONENT' in cat.upper() or (cat and 'ENGINE' in cat.upper()) else [])
            for pv in privs:
                f = 'PRIV|' + pv; facets.add(f); labels[f] = pv
            if cm and int(cm.group(1)) in C:
                kk = 'C' + cm.group(1); f = '145|' + kk; facets.add(f); labels[f] = P145[kk]
            detail.append([cat or path, ', '.join(privs) if privs else scope])
            if cat: summary.append(cat + (': ' + ', '.join(privs) if privs else ''))
        elif a == 'Part 21G Production':
            k = None
            for seg in parts:
                k = code(seg, POA)
                if k: break
            if k:
                f = 'POA|' + k; facets.add(f); labels[f] = POA[k]
                detail.append([POA[k], scope]); summary.append(k)
            else: detail.append([path, scope])
        elif a == 'Part 21J Design':
            act = next((x for x in DOA_ACT if parts and parts[-1].upper() == x.upper()), None)
            if act:
                f = 'DOA|' + act; facets.add(f); labels[f] = act; summary.append(act)
            detail.append([path, scope])
        elif a == 'Part 147 Training':
            if 'BASIC' in P:
                f = '147|Basic Training'; facets.add(f); labels[f] = 'Basic Training'
            if 'TYPE' in P:
                f = '147|Type Training'; facets.add(f); labels[f] = 'Type Training'
            detail.append([path, scope])
        else:
            detail.append([path, scope])
    if a == 'Part-CAMO':
        summary = [s for _, s in o['rt']][:6]
    if a == 'Part 147 Training':
        summary = sorted({x.split('|')[-1] for x in facets if x.startswith('147|')})
    if a in ('BCAR', 'Alternative Procedures to Design Organisation Approval'):
        summary = sorted({p.split('>')[0].strip() for p, _ in o['rt'] if p})[:4]
    if 'Airworthiness Review' in o['sv']:
        facets.add('PRIV|Airworthiness Review'); labels['PRIV|Airworthiness Review'] = 'Airworthiness Review'
    seen = []
    for s in summary:
        if s and s not in seen: seen.append(s)
    o['rf'] = sorted(facets); o['rs'] = seen; o['rt'] = detail
d['labels'] = labels
d['approvals'] = ['Part-CAO', 'Part-CAMO', 'Part 145', 'Part 21J Design', 'Part 21G Production', 'Part 147 Training', 'BCAR', 'Alternative Procedures to Design Organisation Approval']
json.dump(d, open('/home/claude/caa1112/marketplace2.json', 'w'), ensure_ascii=False, separators=(',', ':'))
import collections, os
print(os.path.getsize('/home/claude/caa1112/marketplace2.json'))
c = collections.Counter(f for o in d['orgs'] for f in o['rf'])
for k, v in sorted(c.items()): print(v, k)
for o in d['orgs'][:400:80]: print(o['n'], o['a'], o['rs'][:6])
