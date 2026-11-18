"""Cleanse Marketplace data after caa_scope.py: limitations, organisation names, company numbers.
Input marketplace3.json + /home/claude/ch/final.json; output marketplace4.json."""
import json, re, collections, sys
sys.path.insert(0, '/home/claude/scripts')
from gen import L

d = json.load(open('/home/claude/caa1112/marketplace3.json'))
final = json.load(open('/home/claude/ch/final.json'))
srg = json.load(open('/home/claude/srg/rows.json'))
VERB = set()
for r in srg:
    full = (r[5] or '').strip()
    if full:
        VERB.add(full); VERB.add(re.sub(r'\s*\([^)]*\)\s*$', '', full).strip())
        for m in re.findall(r'\(([^)]+)\)', full): VERB.add(m.strip())

KEEP = {'GTCP', 'APS', 'PW', 'PWC', 'RR', 'RRD', 'GE', 'CFM', 'IAE', 'LEAP', 'HGT', 'TPE', 'TFE', 'PT6', 'JT8D', 'BR', 'AE', 'CT7', 'ATR', 'BAE', 'MD', 'EC', 'AS', 'AW', 'SA', 'BN2', 'DH', 'CL', 'BD', 'ERJ', 'EMB', 'PC', 'SF50', 'DA', 'TB', 'UK', 'USA', 'II', 'III', 'IV'}

def recase(s):
    if s in VERB: return s
    words = re.split(r'(\s+|/|-|\(|\))', s)
    out = []
    for w in words:
        if not w.strip() or w in '/-()': out.append(w); continue
        if w.upper() in KEEP or re.search(r'\d', w): out.append(w.upper() if re.fullmatch(r'[A-Za-z]*\d[\w.]*', w) and not re.fullmatch(r'\d+(st|nd|rd|th)?', w.lower()) else w); continue
        if w.isupper() and len(w) > 3: out.append(w.capitalize()); continue
        out.append(w)
    return L(''.join(out))

BOILER = [r'(?i)\s*,?\s*as (?:defined|detailed|listed|specified) (?:in|within|by) (?:the )?(?:company(?:\'s)? )?(?:approved )?(capability list|moe|exposition|scope of (?:work|approval)[^;,]*)',
          r'(?i)\s*,?\s*to the limits defined (?:in|with|within) the company (moe|exposition)',
          r'(?i)\s*,?\s*in accordance with (?:the )?(?:scope|limits)[^;]*?(moe|exposition|capability list)',
          r'(?i)\s*,?\s*limited to those types and variants identified in the scope of approval[^;]*']

def clean_item(x, code):
    x = x.strip(' ;,.')
    if not x or re.match(r'(?i)^note\s*\d', x): return None, None
    note = None
    for b in BOILER:
        m = re.search(b, x)
        if m:
            x = (x[:m.start()] + x[m.end():]).strip(' ;,.')
    x = re.sub(r'(?i)\bboroscope\b|\bborescope\b', 'Borescope', x)
    if re.search(r'(?i)borescope|blade blending|capability list|exposition|\bmoe\b|scope of (work|approval)', x):
        return None, None
    x = re.sub(r'(?i)\s*\(allied signal\)', '', x)
    x = re.sub(r'(?i)\bhoneywell international\s*/\s*allied ?signal\b', 'Honeywell', x)
    x = re.sub(r'(?i)\b(allied ?signal|garrett)\b', 'Honeywell', x)
    x = re.sub(r'(?i)\bpratt (?:and|&) whitney canada\b', 'PWC', x)
    x = re.sub(r'(?i)\bpratt (?:and|&) whitney\b', 'PW', x)
    x = re.sub(r'(?i)\bGTCP(?=\d)', 'GTCP ', x)
    x = re.sub(r'\b(PWC?) (?=PW)', '', x)
    x = re.sub(r'(?i)\bgeneral electric(?: company)?\b', 'GE', x)
    x = re.sub(r'(?i)\bcfm international(?: sa)?\b', 'CFM', x)
    x = re.sub(r'(?i)\bleap\s*-\s*', 'LEAP-', x)
    x = re.sub(r'(?i)\brolls[ -]royce(?: plc)?\b', 'RR', x)
    x = re.sub(r'\s*\((?:Ea|EA)\)', '', x)
    x = re.sub(r'\bGE,? GE(?=\d)', 'GE ', x)
    x = re.sub(r'(?i)\binternational aero engines \(iae\),?', 'IAE', x)
    x = re.sub(r'(?i)sundrstrand', 'Sundstrand', x)
    if re.search(r'(?i)\b[A-Z]{1,2}\d{1,2}[A-Z]? ?\d[A-Z]{2}\b|\baddress\b|\bc/o\b', x): return None, None
    x = re.sub(r'(?i)\bAPUs\b', 'Auxiliary Power Units', x)
    x = re.sub(r'(?i)\bAPU\b', 'Auxiliary Power Unit', x)
    x = re.sub(r'(?i)\bMOE\b', 'Exposition', x)
    x = re.sub(r'(?i)\bNDT\b', 'Non-Destructive Testing', x)
    x = re.sub(r'(?i)^(?:of\s+)?(?:turbine engines|auxiliary power units)$', '', x)
    x = re.sub(r'\s+', ' ', x).strip(' ;,.')
    if re.fullmatch(r'(?i)(limited to maintenance|maintenance)', x): x, note = '', note or 'Maintenance Only'
    return (recase(x) if x else ''), note

def org_name(n):
    n = re.sub(r'\s+', ' ', n).strip()
    if n.isupper(): n = n.title()
    n = re.sub(r'(?i)\bltd\b\.?', 'Limited', n)
    n = re.sub(r'(?i)\bplc\b\.?', 'Public Limited Company', n)
    n = re.sub(r'(?i)\bt/a\b', 'Trading as', n)
    n = re.sub(r'(?i)\bco\.(?=\s|$)', 'Company', n)
    n = re.sub(r'(?i)\b(uk)\b', 'UK', n)
    return n

def ekey(n):
    n = n.lower(); n = re.sub(r'\s+t/a\b.*$', '', n); n = re.sub(r'\bltd\b\.?', 'limited', n); n = re.sub(r'\bco\b\.?', 'company', n)
    return re.sub(r'[^a-z0-9]', '', n)

stats = collections.Counter()
for o in d['orgs']:
    f = final.get(ekey(o['n']))
    if f and f['number']:
        o['ch'] = f['number']; o['chs'] = f['status'] or ''
    if o.get('sc'):
        out, seen = [], set()
        for p, code, name, lim, note in o['sc']:
            items = [i for i in re.split(r';\s*', lim) if i.strip()] or ['']
            n0 = note
            for it in items:
                x, n2 = clean_item(it, code)
                if x is None: stats['dropped'] += 1; continue
                nn = ', '.join([v for v in [n2, recase(n0) if n0 and not re.match(r'(?i)^note', n0) else None] if v])
                k = (code, x, nn)
                if k in seen: continue
                seen.add(k); out.append([p, code, name, x, nn])
        # drop an empty limitation row when the same class also has specific ones
        has = collections.Counter(r[1] for r in out if r[3])
        o['sc'] = [r for r in out if r[3] or not has[r[1]] or r[4]]
json.dump(d, open('/home/claude/caa1112/marketplace4.json', 'w'), ensure_ascii=False, separators=(',', ':'))
rows = [r for o in d['orgs'] for r in o.get('sc', [])]
loud = [r for r in rows if re.search(r'\b[A-Z]{5,}\b', r[3]) and r[3] not in VERB]
print(stats, len(rows), 'still loud', len(loud))
for r in loud[:12]: print('  ', r[1], r[3])
for code in ['B1', 'B3']:
    print(code, collections.Counter(r[3] for r in rows if r[1] == code).most_common(12))
print([o['n'] for o in d['orgs'] if 'Public' in o['n'] or 'Trading' in o['n']][:6])
