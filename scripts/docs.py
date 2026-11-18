# Documentation section: Manuals and Procedures, Revisions, Required Reading, Notices.
from gen import *

T = 'Documentation=Manuals.dc.html|'

page('Manuals.dc.html', 'Manuals and Procedures', 'manuals', 1100, [
    header('Documentation', 'Manuals and Procedures', '', [btn('Add a Document', primary=True)],
           trail=T + 'Manuals and Procedures'),
    strip([('5', 'Controlled Documents'), ('2', 'Revisions in Progress'), ('1', 'Review Due in 30 Days')]),
    section('doc-h', 'Controlled Documents', table(
        [('Document', '', 'left'), ('Type', '160px', 'left'), ('Revision', '120px', 'left'), ('Effective', '180px', 'left'), ('Owner', '260px', 'left'), ('Next Review', '180px', 'left')],
        [[{'text': 'Combined Airworthiness Exposition', 'href': 'Exposition.dc.html'}, 'Exposition', 'Revision 7', '30 October 2026', '[Compliance Monitoring Manager]', '30 October 2027'],
         ['Safety Policy and Objectives', 'Policy', 'Issue 3', '1 June 2026', '[Accountable Manager]', '1 June 2027'],
         ['Company Forms', 'Forms', 'Issue 12', '30 October 2026', '[Compliance Monitoring Manager]', '30 October 2027'],
         ['Human Factors Training Syllabus', 'Training', 'Issue 2', '6 January 2026', '[Compliance Monitoring Manager]', '6 January 2027'],
         ['Hangar Rules and Fire Precautions', 'Local Procedure', 'Issue 4', '12 March 2026', '[Maintenance Manager]', {'text': '12 December 2026, 24 Days', 'dot': 'a'}]], minw=1180)),
])

page('Revisions.dc.html', 'Revisions', 'revisions', 1100, [
    header('Documentation', 'Revisions', '', [btn('Start a Revision', primary=True)],
           trail=T + 'Revisions'),
    section('rev-h', 'Revisions', table(
        [('Document', '', 'left'), ('Revision', '120px', 'left'), ('Changes', '', 'left'), ('Route', '180px', 'left'), ('Status', '220px', 'left')],
        [['Combined Airworthiness Exposition', 'Revision 8', 'A.4 Scope of Work, Piper PA-38 Series (Lycoming)', 'Own Procedure', {'text': 'Draft', 'dot': 'a'}],
         ['Company Forms', 'Issue 13', 'Receiving Inspection Record', 'Internal', {'text': 'In Review', 'dot': 'a'}],
         ['Combined Airworthiness Exposition', 'Revision 7', 'A.10 List of Certifying Staff, A.12 List of Airworthiness Review Staff', 'Own Procedure', 'Issued 30 October 2026'],
         ['Company Forms', 'Issue 12', 'Work Package Cover Sheet', 'Internal', 'Issued 30 October 2026'],
         ['Hangar Rules and Fire Precautions', 'Issue 4', 'Fire Extinguisher Locations', 'Internal', 'Issued 12 March 2026']], minw=1180)),
])

page('RequiredReading.dc.html', 'Required Reading', 'reading', 1100, [
    header('Documentation', 'Required Reading', '', [btn('Assign Reading', primary=True)],
           trail=T + 'Required Reading'),
    strip([('2', 'Open Items'), ('1', 'Overdue Acknowledgement'), ('5', 'Awaiting Acknowledgement')]),
    section('read-h', 'Required Reading', table(
        [('Document', '', 'left'), ('Assigned To', '200px', 'left'), ('Acknowledged', '140px', 'left'), ('Due', '220px', 'left'), ('Outstanding', '', 'left')],
        [['N-2026-004 Trim Cable Inspection', 'All Staff', '7 of 12', {'text': '25 November 2026, 7 Days', 'dot': 'a'}, 'Sam Patel, [Contract Engineer], [Independent Auditor], [Name], [Name]'],
         ['Combined Airworthiness Exposition, Revision 7', 'All Staff', '11 of 12', {'text': '13 November 2026, 5 Days Overdue', 'dot': 'r'}, '[Name], Part-66 L2'],
         ['Combined Airworthiness Exposition, New Starter', '[Contract Engineer]', '0 of 1', 'Before Authorisation Is Issued', '[Contract Engineer]'],
         ['Company Forms, Issue 12', 'Certifying Staff and Mechanics', '5 of 5', 'Complete', ''],
         ['N-2026-003 Suspected Unapproved Parts', 'All Staff', '12 of 12', 'Complete', '']], minw=1180)),
])

page('Notices.dc.html', 'Notices', 'notices', 1100, [
    header('Documentation', 'Notices', '', [btn('Issue a Notice', primary=True)],
           trail=T + 'Notices'),
    section('ntc-h', 'Notices', table(
        [('Reference', '140px', 'left'), ('Type', '160px', 'left'), ('Subject', '', 'left'), ('Issued', '180px', 'left'), ('Acknowledged', '140px', 'left')],
        [[{'text': 'N-2026-004', 'mono': True}, 'Safety Notice', 'Trim Cable Inspection, from OR-2026-002 G-DGHI', '18 November 2026', {'text': '7 of 12', 'dot': 'a'}],
         [{'text': 'N-2026-003', 'mono': True}, 'Quality Notice', 'Suspected Unapproved Parts, from OR-2026-003 G-FMNO', '8 November 2026', '12 of 12'],
         [{'text': 'N-2026-002', 'mono': True}, 'Quality Notice', 'Engine Oil Batch Rejected, [Oil Supplier] Suspended', '29 October 2026', '5 of 5'],
         [{'text': 'N-2026-001', 'mono': True}, 'Safety Notice', 'Fuel Drain Checks, from OR-2026-001 G-BXYZ', '3 March 2026', '12 of 12']], minw=1100)),
])
