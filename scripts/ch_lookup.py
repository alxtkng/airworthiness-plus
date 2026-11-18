"""Look up each Marketplace legal entity on the Companies House public search and record candidates.
Output /home/claude/ch/results.json: {key: {name, postcodes, query, candidates:[{number,name,address,status}], match, number}}"""
import json, re, html, time, os, urllib.parse, subprocess
OUT = '/home/claude/ch/results.json'
os.makedirs('/home/claude/ch', exist_ok=True)
d = json.load(open('/home/claude/caa1112/marketplace3.json'))

def ekey(n):
    n = n.lower()
    n = re.sub(r'\s+t/a\b.*$', '', n)
    n = re.sub(r'\bltd\b\.?', 'limited', n)
    n = re.sub(r'\bco\b\.?', 'company', n)
    return re.sub(r'[^a-z0-9]', '', n)
def cnorm(n):
    n = html.unescape(n).lower().replace('&', 'and')
    n = re.sub(r'\bltd\b\.?', 'limited', n); n = re.sub(r'\bplc\b', 'publiclimitedcompany', n)
    n = re.sub(r'\(the\)|\bthe\b', '', n)
    return re.sub(r'[^a-z0-9]', '', n)
pcn = lambda p: re.sub(r'\s+', '', (p or '').upper())

groups = {}
for o in d['orgs']:
    groups.setdefault(ekey(o['n']), []).append(o)
res = json.load(open(OUT)) if os.path.exists(OUT) else {}
for i, (k, os_) in enumerate(sorted(groups.items())):
    if k in res: continue
    names = [re.sub(r'(?i)\s+t/a\b.*$', '', o['n']).strip() for o in os_]
    name = sorted(names, key=lambda x: (not re.search(r'(?i)limited$', x), len(x)))[0]
    pcs = sorted({pcn(o.get('pc')) for o in os_ if o.get('pc')})
    q = urllib.parse.quote_plus(name)
    try:
        s = subprocess.run(['curl', '-sS', '-m', '20', 'https://find-and-update.company-information.service.gov.uk/search/companies?q=' + q], capture_output=True, text=True).stdout
    except Exception as e:
        s = ''
    cands = []
    for it in re.findall(r'<li class="type-company">(.*?)</li>', s, re.S):
        m = re.search(r'href="/company/(\w+)"[^>]*>(.*?)</a>', it, re.S)
        if not m: continue
        text = re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', it))).strip()
        addr = text.split(' - ', 1)[-1]
        status = 'Dissolved' if 'Dissolved' in text else 'Active'
        cands.append({'number': m.group(1), 'name': re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', '', m.group(2)))).strip(), 'text': text[:240], 'status': status})
    exact = [c for c in cands if cnorm(c['name']) == cnorm(name)]
    pc_hit = [c for c in exact if any(p and p in pcn(c['text']) for p in pcs)]
    if len(exact) == 1:
        match, number = ('exact and postcode' if pc_hit else 'exact name'), exact[0]['number']
    elif len(pc_hit) == 1:
        match, number = 'exact and postcode', pc_hit[0]['number']
    else:
        match, number = ('ambiguous' if exact or cands else 'none'), None
    res[k] = {'name': name, 'all_names': sorted(set(o['n'] for o in os_)), 'refs': [o['r'] for o in os_], 'postcodes': pcs, 'candidates': cands[:8], 'match': match, 'number': number}
    if i % 20 == 0:
        json.dump(res, open(OUT, 'w'), indent=0)
    time.sleep(0.6)
json.dump(res, open(OUT, 'w'), indent=0)
import collections
print(collections.Counter(v['match'] for v in res.values()))
