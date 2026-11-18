"""Standardise Part 145 (and BCAR maintenance) ratings by product, using the Appendix II classes,
SRG1782 type names for aircraft, SRG1782 bracket engine terms for engines, and standard NDT method names.
Writes o['sc'] = [[product, code, name, limitation, note]] and o['rs'] summary; output marketplace3.json."""
import json, re, sys, collections
sys.path.insert(0, '/home/claude/scripts')
from gen import L

d = json.load(open('/home/claude/caa1112/marketplace2.json'))
srg = json.load(open('/home/claude/srg/rows.json'))

PRODUCT = {'A': 'Aircraft Maintenance', 'B': 'Engine Maintenance', 'C': 'Component Maintenance', 'D': 'Non-Destructive Testing'}
NAME = {'A1': 'Aeroplanes Above 5,700 Kilograms', 'A2': 'Aeroplanes 5,700 Kilograms or Less', 'A3': 'Helicopters', 'A4': 'Aircraft Other Than A1, A2 and A3',
        'B1': 'Turbine Engines', 'B2': 'Piston Engines', 'B3': 'Auxiliary Power Units', 'D1': 'Non-Destructive Testing'}
C = {1: 'Air Conditioning and Pressurisation', 2: 'Auto Flight', 3: 'Communications and Navigation', 4: 'Doors and Hatches', 5: 'Electrical Power and Lights',
     6: 'Equipment', 7: 'Engine and Auxiliary Power Unit', 8: 'Flight Controls', 9: 'Fuel', 10: 'Helicopter Rotors', 11: 'Helicopter Transmission', 12: 'Hydraulic Power',
     13: 'Indicating and Recording Systems', 14: 'Landing Gear', 15: 'Oxygen', 16: 'Propellers', 17: 'Pneumatic and Vacuum', 18: 'Protection From Ice, Rain and Fire',
     19: 'Windows', 20: 'Structural', 21: 'Water Ballast', 22: 'Propulsion Augmentation'}
for k, v in C.items(): NAME['C%d' % k] = v
NDT = [('EDDY', 'Eddy Current'), ('PENETRANT', 'Liquid Penetrant'), ('PENEDRANT', 'Liquid Penetrant'), ('DYE', 'Liquid Penetrant'), ('MAGNETIC', 'Magnetic Particle'),
       ('ULTRASON', 'Ultrasonic'), ('RADIOGRAPH', 'Radiography'), ('X-RAY', 'Radiography'), ('XRAY', 'Radiography'), ('THERMOGRAPH', 'Thermography'),
       ('INFRARED', 'Thermography'), ('SHEAROGRAPH', 'Shearography'), ('ACOUSTIC', 'Acoustic Emission'), ('BORESCOPE', 'Visual, Borescope'), ('BOROSCOPE', 'Visual, Borescope'),
       ('TAP TEST', 'Tap Test'), ('BOND', 'Bond Testing'), ('PHASED ARRAY', 'Ultrasonic')]

norm = lambda s: re.sub(r'[^a-z0-9]', '', s.lower())

# ---- aircraft: SRG1782 Part-66 type rating names ----
base = collections.defaultdict(set)
for r in srg:
    full = (r[5] or '').strip()
    if not full: continue
    b = re.sub(r'\s*\([^)]*\)\s*$', '', full).strip()
    base[norm(b)].add(full); base[norm(full)].add(full)
    if r[3]: base[norm(r[3])].add(full)

BASES = {}
for r in srg:
    full = (r[5] or '').strip()
    if full:
        b = re.sub(r'\s*\([^)]*\)\s*$', '', full).strip()
        BASES.setdefault(norm(b), set()).add(full)
def show(k):
    fulls = sorted(base[k]) if k in base else sorted(BASES[k])
    if len(fulls) == 1: return fulls[0]
    bs = {re.sub(r'\s*\([^)]*\)\s*$', '', f) for f in fulls}
    return bs.pop() if len(bs) == 1 else min(bs, key=len)
def aircraft(lim):
    raw = lim
    v0 = re.sub(r'^\([^)]*\)\s*', '', lim).strip()
    head = re.split(r'[,;]', v0, maxsplit=1)[0].strip()
    for v in [lim, v0, head, re.sub(r'(?i)\s*series$', '', head)]:
        k = norm(v)
        if k in base or k in BASES:
            rest = v0[len(head):].strip(' ,;') if v in (head,) or norm(v) != norm(v0) else ''
            return show(k), True, rest
    k = norm(head)
    cands = [b for b in BASES if len(b) >= 6 and (k.startswith(b) or b.startswith(k) and len(k) >= 6)]
    if cands:
        b = max(cands, key=len)
        return show(b), True, v0[len(head):].strip(' ,;')
    return None, False, ''
# ---- engines: SRG1782 bracket terms ----
MAKER = {'RR Corp': ['ROLLS-ROYCE CORP', 'ROLLS ROYCE CORP', 'RR CORP', 'ALLISON'], 'RRD': ['ROLLS-ROYCE DEUTSCHLAND', 'BMW ROLLS', 'RRD'],
         'RR': ['ROLLS-ROYCE', 'ROLLS ROYCE', 'RR '], 'PWC': ['PRATT & WHITNEY CANADA', 'PRATT AND WHITNEY CANADA', 'PWC', 'P&WC'],
         'PW': ['PRATT & WHITNEY', 'PRATT AND WHITNEY', 'P&W', 'PW'], 'GE': ['GENERAL ELECTRIC', 'GE '], 'CFM': ['CFM'], 'IAE': ['IAE', 'INTERNATIONAL AERO ENGINES'],
         'Honeywell': ['HONEYWELL', 'GARRETT', 'ALLIEDSIGNAL', 'ALLIED SIGNAL', 'AVCO'], 'Turbomeca': ['TURBOMECA', 'SAFRAN'], 'Williams': ['WILLIAMS'],
         'Walter': ['WALTER', 'GE AVIATION CZECH'], 'Lycoming': ['LYCOMING'], 'Continental': ['CONTINENTAL', 'TELEDYNE'], 'Rotax': ['ROTAX'], 'Franklin': ['FRANKLIN'],
         'Technify': ['TECHNIFY', 'CONTINENTAL DIESEL'], 'Thielert': ['THIELERT'], 'SMA': ['SMA '], 'Austro': ['AUSTRO'], 'LOM': ['LOM ']}
terms = collections.Counter()
for r in srg:
    for m in re.findall(r'\(([^)]+)\)', r[5] or ''):
        terms[m.strip()] += 1
ENG = []
for t in terms:
    mk = next((m for m in sorted(MAKER, key=len, reverse=True) if t == m or t.startswith(m + ' ')), None)
    if not mk and not re.match(r'^(CFM56|CFM LEAP)', t): continue
    model = t[len(mk):].strip() if mk and t != mk else ('' if mk else t)
    if t.startswith('CFM'): mk, model = 'CFM', t.replace('CFM ', '')
    if norm(model) in ('engine', 'engines', 'series'): model = ''
    ENG.append((t, mk, model))

def engine(lim):
    U = ' ' + lim.upper() + ' '
    N = norm(lim)
    best = None
    for t, mk, model in ENG:
        alias_ok = mk is None or any(a in U for a in MAKER.get(mk, [mk.upper()]))
        if model:
            mn = norm(model)
            if len(mn) >= 3 and mn in N and (alias_ok or len(mn) >= 4):
                if not best or len(mn) > len(norm(best[2])): best = (t, mk, model)
        elif alias_ok and not best:
            best = (t, mk, model)
    return (best[0], True) if best else (None, False)

def tidy(s):
    s = s.replace('—', '-').replace('–', '-')
    s = re.sub(r'\s+-\s+|\s*-\s*(?=not exceeding|Not Exceeding|NOT EXCEEDING)', ', ', s)
    s = re.sub(r'(?i)not exceeding\s*5\s*,?\s*700\s*kgs?', '5,700 Kilograms or Less', s)
    s = re.sub(r'(?i)(\d[\d ,]*)\s*kgs?\b', lambda m: '{:,}'.format(int(re.sub(r'\D', '', m.group(1)))) + ' Kilograms', s)
    s = re.sub(r'(?i)\bMTOM\b', 'Maximum Take-Off Mass', s).replace('&', 'and')
    s = re.sub(r'(?i)\bunpressurised\b', 'Not Pressurised', s)
    s = re.sub(r'\s+', ' ', s).strip(' ,;.')
    if s.isupper() or s.islower(): s = s.title()
    s = re.sub(r"\b(Rr|Cfm|Ge|Iae|Pwc|Apu|Ndt|Gtcp|Aps|Atr|Bae|Moe)\b", lambda m: m.group(1).upper(), s)
    s = re.sub(r'(?i)rolls[ -]royce', 'Rolls-Royce', s)
    return L(s)

MAKERS_AC = re.compile(r'(?i)airbus|boeing|beech|cessna|piper|bombardier|embraer|pilatus|britten|agusta|bell|eurocopter|sikorsky|robinson|diamond|socata|tecnam|grob|robin|de havilland|dassault|gulfstream|learjet|hawker|atr|bae|saab|dornier|leonardo|md |schweizer|enstrom|guimbal|vulcanair|daher|mooney|cirrus|extra')
def generic(lim):
    U = lim.upper()
    if MAKERS_AC.search(lim) or not re.search(r'AEROPLANE|HELICOPTER', U): return None
    heli = 'HELICOPTER' in U
    eng = ('Single ' if 'SINGLE' in U else 'Multi-' if 'MULTI' in U or 'TWIN' in U else '') + ('Turboprop' if 'TURBOPROP' in U else 'Turbine Engine' if 'TURBINE' in U else 'Piston Engine' if 'PIST' in U else '')
    struct = [w for k, w in [('METAL', 'Metal Structure'), ('WOOD', 'Wooden Structure'), ('COMPOSITE', 'Composite Structure'), ('MIXED', 'Mixed Structure'), ('FABRIC', 'Metal Tubing and Fabric Structure')] if k in U]
    press = 'Not Pressurised' if re.search(r'UNPRESS|NON[- ]PRESS|NOT PRESS', U) else 'Pressurised' if 'PRESSURISED' in U else ''
    m = re.search(r'(\d[\d ,]{2,5})\s*KG', U)
    w = '{:,} Kilograms or Less'.format(int(re.sub(r'\D', '', m.group(1)))) if m else ''
    parts = [((eng + ' ') if eng else '') + ('Helicopters' if heli else 'Aeroplanes')] + struct[:2] + ([press] if press else []) + ([w] if w else [])
    return ', '.join(parts)

def split_note(lim):
    parts = re.split(r';\s*(?=limited|Limited|LIMITED|excluding|Excluding|EXCLUDING|excludes|Excludes|EXCLUDES)', lim, maxsplit=1)
    return parts[0], (tidy(parts[1]) if len(parts) > 1 else '')

stats = collections.Counter()
for o in d['orgs']:
    if o['a'] not in ('Part 145', 'BCAR'): continue
    rows = []
    for path, scope in o['rt']:
        m = re.search(r'\b([ABCD])(\d{1,2})\b', path.upper().split('>')[-1]) or re.search(r'\b([ABCD])(\d{1,2})\b', path.upper())
        if not m: continue
        code = m.group(1) + m.group(2)
        if code not in NAME: continue
        if o['a'] == 'BCAR' and not re.search(r'AEROPLANES|HELICOPTERS|ENGINE|TURBINE|PISTON|APU|COMPONENT|NON[- ]DESTRUCTIVE|^C\d', path.upper()): continue
        p = PRODUCT[code[0]]
        raw = (scope or '').strip()
        lim, note = split_note(raw)
        if code[0] == 'A':
            std, ok, rest = aircraft(lim); stats['A ' + ('srg' if ok else 'tidy')] += 1
            if rest and not note: note = tidy(rest)
            g = None if std else generic(lim)
            if g: stats['A generic'] += 1
            lim = std or g or tidy(lim)
        elif code[0] == 'B':
            items = [x for x in re.split(r',\s*(?=[A-Z])', lim) if x.strip()] if code != 'B3' else [lim]
            mapped = []
            for x in items:
                std, ok = engine(x) if code != 'B3' else (None, False)
                stats['B ' + ('srg' if ok else 'tidy')] += 1
                v = std or tidy(x)
                if v and v not in mapped: mapped.append(v)
            for v in mapped[1:]:
                rows.append([p, code, NAME[code], v, note])
            lim = mapped[0] if mapped else 'Not Published'
        elif code[0] == 'C':
            t = norm(lim.replace('&', 'and'))
            if not t or t in (norm(code), norm(code + ' ' + NAME[code])) or norm(NAME[code]) in t and len(t) <= len(norm(code + NAME[code])) + 6 or re.fullmatch(r'c\d{1,2}[a-z ]*', lim.lower().replace('—', '').replace('-', '')) and len(t) < 40:
                lim = 'All Components in the Class'
            else:
                lim = tidy(lim)
        else:
            U = lim.upper()
            meth = [v for k, v in NDT if k in U]
            lim = meth[0] if meth else (tidy(lim) or 'Method Not Published')
        rows.append([p, code, NAME[code], lim, note])
    # merge identical rows, sort by product then class number
    seen, out = set(), []
    for r in rows:
        k = (r[1], r[3], r[4])
        if k in seen: continue
        seen.add(k); out.append(r)
    out.sort(key=lambda r: ('ABCD'.index(r[1][0]), int(r[1][1:]), r[3]))
    if out:
        o['sc'] = out
        summ = collections.OrderedDict()
        for r in out: summ.setdefault(r[1][0], [])
        for r in out:
            if r[1] not in summ[r[1][0]]: summ[r[1][0]].append(r[1])
        lab = {'A': 'Aircraft', 'B': 'Engines', 'C': 'Components', 'D': 'Non-Destructive Testing'}
        o['rs'] = ['; '.join(lab[k] + ' ' + ', '.join(v) for k, v in summ.items())]
json.dump(d, open('/home/claude/caa1112/marketplace3.json', 'w'), ensure_ascii=False, separators=(',', ':'))
print(stats)
import random
random.seed(3)
o145 = [o for o in d['orgs'] if o.get('sc')]
print(len(o145))
for o in random.sample(o145, 4):
    print(o['n'], o['rs'])
    for r in o['sc'][:12]: print('   ', r)
