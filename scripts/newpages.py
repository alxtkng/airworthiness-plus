from gen import *

# Pages added for the 1321/2014 section structure. Terse Title Case, spelled out, no taglines.
AC = lambda r, sub=None: {'text': r, 'href': 'Aircraft.dc.html' if r == 'G-ABCD' else None, 'sub': sub}
REG = ('Aircraft Registration', '170px', 'left')

# Continuing Airworthiness: Release to Service (ML.A.801, M.A.801, CAO.A.070)
page('ReleaseToService.dc.html', 'Release to Service', 'crs', 1300, [
    header('Continuing Airworthiness', 'Release to Service', '', [btn('Issue a Certificate', primary=True)],
           trail='Continuing Airworthiness=Fleet.dc.html|Release to Service'),
    strip([('3', 'Issued, Last 30 Days'), ('1', 'Not Yet in Records'), ('0', 'Incomplete Maintenance'), ('0', 'Pilot-Owner Notice Overdue')]),
    section('crs-h', 'Certificates of Release to Service', table(
        [REG, ('Maintenance', '', 'left'), ('Issued By', '240px', 'left'), ('Completed', '170px', 'left'), ('In Records', '190px', 'left'), ('Limitations', '150px', 'left')],
        [[AC('G-CDEF'), {'text': '100-Hour Check', 'sub': 'WP-2026-043'}, {'text': 'Chris Moore, Certifying Staff', 'sub': 'UK.CAO.[Number]'}, '4 November 2026', '5 November 2026', 'None'],
         [AC('G-CDEF'), {'text': 'Propeller Spinner Replaced', 'sub': 'WP-2026-043'}, {'text': 'Chris Moore, Certifying Staff', 'sub': 'UK.CAO.[Number]'}, '4 November 2026', '5 November 2026', 'None'],
         [AC('G-ABCD'), {'text': 'Right Main Tyre Replaced', 'sub': 'Pilot-Owner Maintenance'}, {'text': '[Owner Name], Pilot-Owner', 'sub': 'Licence [Number]'}, '22 October 2026', {'text': 'Due 21 November 2026', 'dot': 'a', 'sub': 'Organisation Told 23 October'}, 'None']]),
        intro='In Records Within 30 Days of Completion'),
    section('who-h', 'Who May Release', table(
        [('Issued By', '260px', 'left'), ('Aircraft', '', 'left'), ('Tasks', '', 'left'), ('Conditions', '', 'left')],
        [['Organisation Certifying Staff', 'Within Scope of Approval', 'All Tasks Within Authorisation', 'Authorisation Current'],
         ['Independent Certifying Staff', 'Part-ML Aircraft', 'Not Complex Maintenance Tasks', 'Part-66 Licence Privileges'],
         ['Pilot-Owner', 'Owned Part-ML Aircraft, Not Commercial', 'Pilot-Owner Tasks in the Maintenance Programme', 'Tell the Contracted Organisation Within 30 Days']], minw=900)),
])

# Continuing Airworthiness: Contracts (ML.A.201, Appendix I to Part-ML; CAO.A.055 Work Orders)
page('Contracts.dc.html', 'Contracts', 'contracts', 1300, [
    header('Continuing Airworthiness', 'Contracts', '', [btn('Draw Up a Contract', primary=True)],
           trail='Continuing Airworthiness=Fleet.dc.html|Contracts'),
    section('cam-h', 'Continuing Airworthiness Management Contracts', table(
        [REG, ('Owner', '200px', 'left'), ('Tasks Contracted', '', 'left'), ('Signed', '170px', 'left'), ('Status', '170px', 'left')],
        [[AC('G-BXYZ'), {'text': '[Syndicate Name]', 'sub': 'Syndicate of 6'}, 'All Continuing Airworthiness Management Tasks', '15 January 2025', {'text': 'Active', 'dot': 'g', 'status': True}],
         [AC('G-CDEF'), {'text': '[Syndicate Name]', 'sub': 'Syndicate of 4'}, 'All Continuing Airworthiness Management Tasks', '8 April 2024', {'text': 'Active', 'dot': 'g', 'status': True}],
         [AC('G-DGHI'), {'text': '[Flying Club Name]', 'sub': 'Flying Club'}, 'All Continuing Airworthiness Management Tasks', '4 March 2025', {'text': 'Active', 'dot': 'g', 'status': True}],
         [AC('G-HKLM'), '[Owner Name]', 'All Continuing Airworthiness Management Tasks', '9 November 2026', {'text': 'Records Transfer', 'dot': 'a', 'status': True, 'sub': '14 of 18 Received'}],
         [AC('G-ABCD'), {'text': '[Owner Name]', 'sub': 'Pilot-Owner'}, 'Maintenance Programme Review and Airworthiness Review', '2 March 2026', {'text': 'Active', 'dot': 'g', 'status': True}]]),
        intro='Appendix I to Part-ML, Owner Tells the Civil Aviation Authority Within 2 Weeks if a Contract Ends'),
    section('wo-h', 'Maintenance Work Orders', table(
        [REG, ('Work Ordered', '', 'left'), ('Ordered By', '220px', 'left'), ('Agreed', '170px', 'left'), ('Work Package', '170px', 'left')],
        [[AC('G-ABCD'), 'Landing Light Replacement', '[Owner Name]', '12 November 2026', {'text': 'WP-2026-047', 'href': 'WorkPackages.dc.html'}],
         [AC('G-DGHI'), 'Stabilator Trim Cable Rectification', 'Continuing Airworthiness Manager', '14 November 2026', {'text': 'WP-2026-046', 'href': 'WorkPackages.dc.html'}],
         [AC('G-FMNO'), '50-Hour Check', '[Owner Name]', '16 November 2026', 'Not Planned']], minw=900)),
])

# Management System: Occurrence Reports (M.A.202, ML.A.202, 145.A.60, CAMO.A.160; UK Regulation 376/2014)
page('Occurrences.dc.html', 'Occurrence Reports', 'occurrences', 1100, [
    header('Management System', 'Occurrence Reports', '', [btn('Report an Occurrence', primary=True)],
           trail='Management System=Main.dc.html|Occurrence Reports'),
    strip([('1', 'Follow-Up Due'), ('0', 'Past 72 Hours'), ('3', 'Sent This Year')]),
    section('occ-h', 'Occurrence Reports', table(
        [('Reference', '140px', 'left'), REG, ('Occurrence', '', 'left'), ('Identified', '170px', 'left'), ('Sent To', '260px', 'left'), ('Status', '170px', 'left')],
        [[{'text': 'OR-2026-002', 'mono': True}, AC('G-DGHI'), 'Stabilator Trim Cable Frayed at Pulley', '14 November 2026', 'Civil Aviation Authority, Type Certificate Holder, Owner', {'text': 'Follow-Up Due', 'dot': 'a', 'status': True, 'sub': 'Preventive Action'}],
         [{'text': 'OR-2026-003', 'mono': True}, AC('G-FMNO'), 'Suspected Unapproved Part, Owner-Supplied Alternator', '6 November 2026', 'Civil Aviation Authority, Owner', {'text': 'Closed', 'dot': 'g', 'status': True, 'sub': 'Item Quarantined'}],
         [{'text': 'OR-2026-001', 'mono': True}, AC('G-BXYZ'), 'Fuel Contamination Found on Water Drain Check', '3 June 2026', 'Civil Aviation Authority, Owner', {'text': 'Closed', 'dot': 'g', 'status': True}]]),
        intro='Within 72 Hours of Identification, Then a Follow-Up Report'),
])

# Logistics: Suppliers (145.A.42, CAO.A.050, CAP 2375 2.1)
page('Suppliers.dc.html', 'Suppliers', 'suppliers', 1100, [
    header('Logistics', 'Suppliers', '', [btn('Find in Marketplace', href='Marketplace.dc.html'), btn('Evaluate a Supplier', primary=True)],
           trail='Logistics=PartsReceived.dc.html|Suppliers'),
    section('sup-h', 'Approved Suppliers', table(
        [('Supplier', '240px', 'left'), ('Supplies', '', 'left'), ('Release Documents', '260px', 'left'), ('Next Evaluation', '190px', 'left'), ('Status', '150px', 'left')],
        [['[Parts Distributor]', 'Components, Standard Parts and Materials', 'CAA Form 1 or Certificate of Conformity', '3 March 2027', {'text': 'Approved', 'dot': 'g', 'status': True}],
         ['[Engine Overhaul Organisation]', 'Piston Engine Overhaul', 'CAA Form 1', '20 June 2027', {'text': 'Approved', 'dot': 'g', 'status': True}],
         ['[Propeller Organisation]', 'Propeller Overhaul and Repair', 'CAA Form 1', {'text': '30 November 2026', 'dot': 'a', 'sub': '12 Days Left'}, {'text': 'Approved', 'dot': 'g', 'status': True}],
         ['[Calibration Laboratory]', 'Tool and Equipment Calibration', 'Calibration Certificate, Accredited Laboratory', '11 January 2027', {'text': 'Approved', 'dot': 'g', 'status': True}],
         ['[Oil Supplier]', 'Engine Oil and Grease', 'Certificate of Conformity', '—', {'text': 'Suspended', 'dot': 'r', 'status': True, 'sub': 'Batch Without Conformity'}]], minw=1000)),
])

# People: Authorisations (CAO.A.040, CAO.A.045, CAMO.A.305)
page('Authorisations.dc.html', 'Authorisations', 'auth', 1300, [
    header('People', 'Authorisations', '', [btn('Issue an Authorisation', primary=True)], tabs=('auth', 'auth'),
           trail='People=Staff.dc.html|Authorisations=Authorisations.dc.html|Authorisations'),
    section('cs-h', 'Certifying Staff', table(
        [('Name', '200px', 'left'), ('Licence', '200px', 'left'), ('Scope', '', 'left'), ('Recurrent Training Due', '200px', 'left'), ('Status', '170px', 'left')],
        [['Chris Moore', {'text': 'Part-66 B1.2', 'sub': 'UK.66.[Number]'}, 'Piston Aeroplanes, Lycoming and Continental Piston Engines', '14 August 2027', {'text': 'Current', 'dot': 'g', 'status': True}],
         ['Sam Patel', {'text': 'Part-66 B1.2', 'sub': 'UK.66.[Number]'}, 'Piston Aeroplanes, Lycoming and Continental Piston Engines', {'text': '6 December 2026', 'dot': 'a', 'sub': '18 Days Left'}, {'text': 'Current', 'dot': 'g', 'status': True}],
         ['[Name]', {'text': 'Part-66 L2', 'sub': 'UK.66.[Number]'}, 'ELA1 Aeroplanes, Wooden Structure', '2 May 2027', {'text': 'Lapsed', 'dot': 'r', 'status': True, 'sub': 'Under 6 Months in 2 Years'}]]),
        intro='Valid While Licence Valid, 6 Months of Experience in 2 Years and Recurrent Training in 2 Years'),
    section('ar-h', 'Airworthiness Review Staff', table(
        [('Name', '200px', 'left'), ('Accepted by the Civil Aviation Authority', '', 'left'), ('Last Review', '220px', 'left'), ('Status', '200px', 'left')],
        [['Lucy Grant', '9 June 2023', '11 November 2026, G-CDEF', {'text': 'Current', 'dot': 'g', 'status': True}],
         ['[Name]', '2 December 2021', '2 December 2025, G-EJKL', {'text': 'Lapses 2 December 2026', 'dot': 'a', 'status': True}]], minw=900),
        intro='Recency: 6 Months of Continuing Airworthiness Work in 2 Years, or 1 Review in 12 Months'),
])

# Organisation: Approval and Scope (CAO.A.020, Appendix I to Part-CAO, CAA Form 3-CAO)
page('Approval.dc.html', 'Approval and Scope', 'approval', 1300, [
    header('Organisation', 'Approval and Scope', '', [btn('Apply for a Change', href='Changes.dc.html')],
           trail='Organisation=Approval.dc.html|Approval and Scope'),
    strip([('UK.CAO.[Number]', 'CAA Form 3-CAO'), ('Unlimited', 'Duration'), ('4 of 4', 'Privileges Held')]),
    section('priv-h', 'Privileges', table(
        [('Privilege', '', 'left'), ('Point', '200px', 'left'), ('Held', '150px', 'left')],
        [['Maintenance', 'CAO.A.095(a)', 'Yes'],
         ['Continuing Airworthiness Management', 'CAO.A.095(b)', 'Yes'],
         ['Airworthiness Review', 'CAO.A.095(c)', 'Yes'],
         ['Permit to Fly', 'CAO.A.095(d)', 'Yes']], minw=800)),
    section('scope-h', 'Scope of Work', table(
        [('Class', '200px', 'left'), ('Rating', '', 'left'), ('Maintenance', '150px', 'left'), ('Management', '150px', 'left'), ('Review', '150px', 'left')],
        [['Aircraft', 'Aeroplanes, 2,730 Kilograms Maximum Take-Off Mass or Less', 'Yes', 'Yes', 'Yes'],
         ['Aircraft', 'Sailplanes and Powered Sailplanes', 'No', 'Yes', 'Yes'],
         ['Engines', 'Piston Engines, Lycoming and Continental', 'Yes', '—', '—'],
         ['Components', 'C14 Landing Gear', 'Yes', '—', '—'],
         ['Components', 'C16 Propellers', 'Yes', '—', '—']], minw=960),
        intro='Exact Limits in Exposition Chapter A.4'),
])

# Organisation: Exposition (CAO.A.025, AMC1 CAO.A.025)
page('Exposition.dc.html', 'Exposition', 'exposition', 1300, [
    header('Documentation', 'Combined Airworthiness Exposition', '', [btn('Start a Revision', primary=True)],
           trail='Documentation=Manuals.dc.html|Manuals and Procedures=Manuals.dc.html|Combined Airworthiness Exposition'),
    strip([('7', 'Current Revision'), ('30 October 2026', 'Approved'), ('1', 'Revision in Draft')]),
    section('parts-h', 'Parts', table(
        [('Part', '100px', 'left'), ('Title', '', 'left'), ('Chapters', '120px', 'right'), ('Last Amended', '200px', 'left')],
        [['A', 'General Description', '13', '30 October 2026'],
         ['B', 'General Procedures', '13', '30 October 2026'],
         ['C', 'Maintenance Procedures', '15', '12 March 2026'],
         ['D', 'Continuing Airworthiness Management Procedures', '13', '12 March 2026']], minw=860)),
    section('rev-h', 'Revisions', table(
        [('Revision', '120px', 'left'), ('Changes', '', 'left'), ('Route', '220px', 'left'), ('Approved', '200px', 'left')],
        [['8', 'A.4 Scope of Work, Piper PA-38 Series (Lycoming)', 'Own Procedure', {'text': 'Draft', 'dot': 'a'}],
         ['7', 'A.10 List of Certifying Staff, A.12 List of Airworthiness Review Staff', 'Own Procedure', '30 October 2026'],
         ['6', 'C.3 Components, Equipment, Tools and Material', 'Own Procedure', '12 March 2026']], minw=960)),
])

# Organisation: Changes (CAO.A.105, CAMO.A.130, 145.A.85)
page('Changes.dc.html', 'Changes', 'changes', 1100, [
    header('Organisation', 'Changes to the Organisation', '', [btn('Record a Change', primary=True)],
           trail='Organisation=Approval.dc.html|Changes'),
    section('chg-h', 'Changes', table(
        [('Change', '', 'left'), ('Route', '200px', 'left'), ('Date', '200px', 'left'), ('Status', '240px', 'left')],
        [['Nominated Person, Continuing Airworthiness Management', 'Prior Approval', 'Applied 2 November 2026', {'text': 'With the Civil Aviation Authority', 'dot': 'a'}],
         ['Piper PA-38 Series (Lycoming) Added to Scope', 'Own Procedure', 'Made 9 November 2026', {'text': 'Notify by 24 November 2026', 'dot': 'a'}],
         ['Exposition Revision 7', 'Own Procedure', 'Made 30 October 2026', 'Notified 5 November 2026']], minw=960),
        intro='Own Procedure Changes Notified Within 15 Days'),
])

# Organisation: Oversight (CAO.B.055, CAMO.B.305, 145.B.305)
page('Oversight.dc.html', 'Oversight', 'oversight', 1100, [
    header('Organisation', 'Civil Aviation Authority Oversight', '', [],
           trail='Organisation=Approval.dc.html|Oversight'),
    strip([('24 Months', 'Oversight Cycle'), ('March 2027', 'Next Audit'), ('0', 'Open Authority Findings')]),
    section('aud-h', 'Authority Audits', table(
        [('Date', '200px', 'left'), ('Audit', '', 'left'), ('Findings', '200px', 'left'), ('Status', '200px', 'left')],
        [['14 March 2025', 'Organisation Audit and Accountable Manager Meeting', '2 Level 2', 'Closed 9 June 2025'],
         ['2 October 2025', 'Product Audit, G-CDEF Airworthiness Review', 'None', 'Closed'],
         ['March 2027', 'Organisation Audit and Accountable Manager Meeting', '—', 'Planned']], minw=900)),
])
