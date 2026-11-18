from gen import *

# People: Staff and Authorisations, Recency. Terse Title Case, spelled out, no taglines.
# Training detail lives in the Training section; this page links to it.
AUTH = 'Authorisations.dc.html'
REC = 'Recency.dc.html'
TRN = 'RecurrentTraining.dc.html'
LOG = 'Logbook.dc.html'
NONE = '—'

def lnk(text, href, sub=None, d=None):
    v = {'text': text, 'href': href}
    if sub:
        v['sub'] = sub
    if d:
        v['dot'] = d
    return v

# People: Staff (CAO.A.035, CAO.A.040, CAO.A.045)
page('Staff.dc.html', 'Staff', 'staff', 950, [
    header('People', 'Staff', '', [btn('Add a Person', primary=True)],
           trail='People=Staff.dc.html|Staff'),
    section('staff-h', 'Staff', table(
        [('Name', '200px', 'left'), ('Role', '', 'left'), ('Employment', '130px', 'left'), ('Licence', '150px', 'left'),
         ('Authorisation', '210px', 'left'), ('Recurrent Training', '200px', 'left'), ('Experience Logbook', '170px', 'left')],
        [[{'text': '[Accountable Manager]', 'sub': 'Signs the Exposition Statement'}, 'Accountable Manager', 'Employed', NONE, 'Not Required',
          lnk('Current', TRN, 'Safety Training'), NONE],
         [{'text': '[Name]', 'sub': 'Named in Exposition Chapter A.3'}, 'Nominated Person, Continuing Airworthiness Manager', 'Employed', NONE,
          lnk('Maintenance Programme Approval', AUTH, 'Exposition Chapter A.11'), lnk('Current', TRN, 'Safety Training'), NONE],
         [{'text': '[Name]', 'sub': 'Named in Exposition Chapter A.3'}, 'Nominated Person, Maintenance Manager', 'Employed', NONE,
          'Not Required', lnk('Current', TRN, 'Safety Training'), NONE],
         [{'text': 'Lucy Grant', 'sub': 'Accepted by the Civil Aviation Authority 9 June 2023'}, 'Airworthiness Review Staff, Continuing Airworthiness', 'Employed', NONE,
          lnk('Airworthiness Review', AUTH, 'Last Review 11 November 2026, G-CDEF'), lnk('Current', TRN, 'Continuation Training'), NONE],
         [{'text': '[Name]', 'sub': 'Last Review 2 December 2025, G-EJKL'}, 'Airworthiness Review Staff', 'Employed', NONE,
          lnk('Recency Lapses 2 December 2026', REC, '1 Review in 12 Months Needed', 'a'), lnk('Current', TRN, 'Continuation Training'), NONE],
         [{'text': 'Chris Moore', 'sub': 'UK.66.[Number]'}, 'Certifying Staff', 'Employed', 'Part-66 B1.2',
          lnk('Certifying Staff', AUTH, 'Piston Aeroplanes, Lycoming and Continental Piston Engines'), lnk('Due 14 August 2027', TRN, 'Human Factors, Fuel Tank Safety'), lnk('Open', LOG)],
         [{'text': 'Sam Patel', 'sub': 'UK.66.[Number]'}, 'Certifying Staff', 'Employed', 'Part-66 B1.2',
          lnk('Certifying Staff', AUTH, 'Piston Aeroplanes, Lycoming and Continental Piston Engines'), lnk('Due 6 December 2026', TRN, '18 Days Left', 'a'), lnk('Open', LOG)],
         [{'text': '[Name]', 'sub': 'UK.66.[Number]'}, 'Certifying Staff', 'Contracted', 'Part-66 L2',
          lnk('Lapsed', REC, 'Under 6 Months of Experience in 2 Years', 'r'), lnk('Due 2 May 2027', TRN, 'Human Factors'), lnk('Open', LOG)],
         [{'text': '[Name]', 'sub': 'Joined 1 September 2026'}, 'Support Staff, Planning and Records', 'Employed', NONE,
          lnk('Competency Assessment in Progress', 'Competence.dc.html', 'Before Unsupervised Work'), lnk('Initial Safety Training Due 1 March 2027', TRN, 'Within 6 Months of Joining'), NONE]],
        minw=1280)),
    section('former-h', 'Former Staff', table(
        [('Name', '200px', 'left'), ('Role', '', 'left'), ('Left', '180px', 'left'), ('Record Kept Until', '220px', 'left')],
        [['[Name]', 'Airworthiness Review Staff', '30 June 2025', {'text': '30 June 2027', 'sub': '2 Years After Leaving, CAO.A.045(e)'}]], minw=860)),
])

# People: Authorisations, Recency (CAO.A.040, 66.A.20(b), AMC 66.A.20(b)2, CAO.A.045(c), 145.A.35)
WINDOW = '19 November 2024–18 November 2026'
page('Recency.dc.html', 'Recency', 'recency', 1250, [
    header('People', 'Recency', '', [btn('Open Experience Logbooks', href=LOG)], tabs=('auth', 'recency'),
           trail='People=Staff.dc.html|Authorisations=Authorisations.dc.html|Recency'),
    section('cs-h', 'Certifying Staff', table(
        [('Name', '200px', 'left'), ('Licence', '150px', 'left'), ('Experience in 2 Years', '200px', 'left'), ('Similar Aircraft', '', 'left'),
         ('Last Maintenance', '240px', 'left'), ('Status', '200px', 'left')],
        [['Chris Moore', {'text': 'Part-66 B1.2', 'sub': 'UK.66.[Number]'}, {'text': '214 Days', 'sub': WINDOW},
          {'text': 'Metal, Wood and Composite Structure', 'sub': 'Piper PA-28 Series (Lycoming), Robin DR 400 series (Lycoming), Grob G115/120 Series (Lycoming)'},
          {'text': '18 November 2026, G-DGHI', 'sub': 'WP-2026-046'}, {'text': 'Current', 'dot': 'g', 'status': True}],
         ['Sam Patel', {'text': 'Part-66 B1.2', 'sub': 'UK.66.[Number]'}, {'text': '176 Days', 'sub': WINDOW},
          {'text': 'Metal, Wood and Composite Structure', 'sub': 'Cessna/Reims-Cessna 172/F172 Series (Lycoming), Robin DR 400 series (Lycoming), Grob G115/120 Series (Lycoming)'},
          {'text': '4 November 2026, G-CDEF', 'sub': 'WP-2026-043'}, {'text': 'Current', 'dot': 'g', 'status': True}],
         ['[Name]', {'text': 'Part-66 L2', 'sub': 'UK.66.[Number]'}, {'text': '61 Days', 'dot': 'r', 'sub': '100 Days Needed, ' + WINDOW},
          {'text': 'Wooden Structure', 'sub': 'ELA1 Aeroplanes'},
          {'text': '14 August 2025', 'sub': 'Contracted, No Work Since'},
          {'text': 'Lapsed', 'dot': 'r', 'status': True, 'sub': 'Restore: Supervised Experience, Then Competency Assessment'}]]),
        intro='6 Months of Experience in Any 2 Years, or 100 Days, on Each Aircraft in the Authorisation or a Similar Aircraft'),
    section('ar-h', 'Airworthiness Review Staff', table(
        [('Name', '200px', 'left'), ('Continuing Airworthiness Work in 2 Years', '', 'left'), ('Reviews in 12 Months', '190px', 'right'),
         ('Last Review', '240px', 'left'), ('Status', '220px', 'left')],
        [['Lucy Grant', {'text': '24 Months', 'sub': 'Continuing Airworthiness Management, Employed'}, {'text': '5', 'sub': 'G-DGHI, G-ABCD, G-BXYZ, G-FMNO, G-CDEF'},
          '11 November 2026, G-CDEF', {'text': 'Current', 'dot': 'g', 'status': True}],
         ['[Name]', {'text': '4 Months', 'sub': '6 Months Needed'}, {'text': '1', 'sub': 'G-EJKL'},
          '2 December 2025, G-EJKL', {'text': 'Lapses 2 December 2026', 'dot': 'a', 'status': True, 'sub': 'Restore: 1 Review Under Supervision'}]], minw=1000),
        intro='6 Months of Continuing Airworthiness Work in 2 Years, or 1 Review in 12 Months'),
    '    ' + callout('G-EJKL Airworthiness Review Due by 6 December 2026, a Review Before 2 December Keeps [Name] Current', 'a'),
    section('rule-h', 'What Counts', table(
        [('Rule', '260px', 'left'), ('Detail', '', 'left'), ('Point', '200px', 'left')],
        [['Duration', '6 Months Continuous or in Blocks, or 100 Days', 'AMC 66.A.20(b)2'],
         ['Credit', 'Up to 20 Percent From Training, Technical Support, Engineering or Planning on Similar Aircraft', 'AMC 66.A.20(b)2'],
         ['Nature', 'Servicing, Inspection, Testing, Troubleshooting, Repair, Modification, Component Changes, Supervision and Release', 'AMC 66.A.20(b)2'],
         ['Similar Aircraft', 'Same Propulsion, Flight Controls, Avionics and Structure', 'AMC 66.A.20(b)2'],
         ['Group Ratings', 'At Least 1 Type per Group and per Structure', 'AMC 66.A.20(b)2'],
         ['Airworthiness Review Staff', 'Lapsed Authorisation Restored by 1 Review Under Supervision of the Civil Aviation Authority or Current Airworthiness Review Staff', 'AMC CAO.A.045']], minw=960)),
])
