from gen import *

# Dashboard, Settings and Help. Today is 18 November 2026; the dashboard horizon is 30 days (Settings, Alert Lead Times).
AC = lambda r, sub=None: {'text': r, 'href': 'Aircraft.dc.html' if r == 'G-ABCD' else None, 'sub': sub}
PG = lambda label, href: {'text': label, 'href': href}
DUE = lambda text, c='a', sub=None: {'text': text, 'dot': c, 'sub': sub}
REG = ('Aircraft Registration', '170px', 'left')
ITEM = ('Item', '', 'left')
DUECOL = ('Due', '230px', 'left')
LEFT = ('Remaining', '130px', 'right')
PAGE = ('Page', '220px', 'left')

# ---------------------------------------------------------------- Dashboard
page('Home.dc.html', 'Dashboard', 'home', 2690, [
    header('Dashboard', 'Dashboard', trail='Dashboard'),
    section('ca-h', 'Continuing Airworthiness', table(
        [REG, ITEM, DUECOL, LEFT, PAGE],
        [[AC('G-DGHI'), {'text': 'Unserviceable, Stabilator Trim Cable', 'sub': 'WP-2026-046, 5 of 7 Tasks Closed'}, DUE('Grounded Since 14 November 2026', 'r'), '—', PG('Aircraft', 'Fleet.dc.html')],
         [AC('G-CDEF'), {'text': 'Copy of Review Certificate to the Civil Aviation Authority', 'sub': 'Issued 11 November 2026, Within 10 Days'}, DUE('21 November 2026'), '3 Days', PG('Airworthiness Reviews', 'Reviews.dc.html')],
         [AC('G-ABCD'), {'text': 'Certificate of Release to Service Not Yet in Records', 'sub': 'Right Main Tyre Replaced, Pilot-Owner, 22 October 2026'}, DUE('21 November 2026'), '3 Days', PG('Release to Service', 'ReleaseToService.dc.html')],
         [AC('G-CDEF'), {'text': 'Own Propeller Due Back From Overhaul', 'sub': 'Loan Propeller Fitted on WP-2026-043, [Propeller Organisation], via Goods In'}, DUE('25 November 2026'), '7 Days', PG('Aircraft Configuration', 'Components.dc.html')],
         [AC('G-BXYZ'), {'text': 'Deferred Defect Limit, Cabin Entry Step Loose', 'sub': 'Deferred by Sam Patel, B1, 28 October, Not Planned'}, DUE('27 November 2026'), '9 Days', PG('Defects', 'Defects.dc.html')],
         [AC('G-ABCD'), {'text': 'Deferred Defect Limit, Left Landing Light Inoperative', 'sub': 'Placarded, Daylight Only, WP-2026-047'}, DUE('3 December 2026'), '15 Days', PG('Defects', 'Defects.dc.html')],
         [AC('G-EJKL'), {'text': 'Airworthiness Review Certificate Expires', 'sub': 'Physical Survey Booked 19 November 2026, Review Keeps [Name] Current'}, DUE('6 December 2026'), '18 Days', PG('Airworthiness Reviews', 'Reviews.dc.html')],
         [AC('G-FMNO'), {'text': 'Maintenance Programme Annual Review', 'sub': 'Owner Declared, Issue 2, 4 of 6 Complete'}, DUE('10 December 2026'), '22 Days', PG('Maintenance Programmes', 'Programmes.dc.html')],
         [AC('G-EJKL'), {'text': 'Deferred Defect Limit, Right Headset Socket Crackle', 'sub': 'With Airworthiness Review'}, DUE('12 December 2026'), '24 Days', PG('Defects', 'Defects.dc.html')],
         [AC('G-ABCD'), {'text': '50-Hour Check', 'sub': 'WP-2026-047, Planned 19 November 2026'}, DUE('6,425.0 Hours'), '12.4 Hours', PG('Aircraft Record', 'Aircraft.dc.html')],
         [AC('G-HKLM'), {'text': 'Transfer In, Records 14 of 18 Received', 'sub': 'Engine Logbook Volume 1 Requested 13 November'}, 'Not Set', '—', PG('Transfers', 'Transfers.dc.html')],
         [AC('G-FMNO'), {'text': 'Work Order Not Planned, 50-Hour Check', 'sub': 'Agreed 16 November 2026, [Owner Name]'}, 'Not Set', '—', PG('Contracts', 'Contracts.dc.html')]])),
    section('ms-h', 'Management System', table(
        [('Reference', '170px', 'left'), ITEM, DUECOL, LEFT, PAGE],
        [[{'text': 'OR-2026-002', 'mono': True}, {'text': 'Occurrence Follow-Up Report, G-DGHI', 'sub': 'Stabilator Trim Cable Frayed at Pulley, Removed Cable Retained in Secure Area'}, DUE('Follow-Up Due'), '—', PG('Occurrence Reports', 'Occurrences.dc.html')],
         [{'text': 'SR-2026-015', 'mono': True}, {'text': 'Safety Report to Assess', 'sub': 'Torque Value on the Work Card Differed From the Maintenance Manual, Received 17 November 2026'}, DUE('Not Yet Assessed'), '—', PG('Safety Reports', 'Reports.dc.html')],
         [{'text': 'Internal Audit'}, {'text': 'Staff, Training and Authorisations', 'sub': 'Cycle Ends 30 November 2026, 8 of 10 Audits Complete'}, DUE('26 November 2026'), '8 Days', PG('Compliance Monitoring', 'Audit.dc.html')],
         [{'text': '2026-0005', 'mono': True}, {'text': 'Action, Alerts 60 and 30 Days Before Review Certificate Expiry', 'sub': 'From the Hazard Log, Lucy Grant'}, DUE('30 November 2026'), '12 Days', PG('Actions', 'Actions.dc.html')],
         [{'text': '2026-0004', 'mono': True}, {'text': 'Action, Emergency Locator Transmitter Battery Date in the Programme', 'sub': 'From the Hazard Log, Lucy Grant'}, DUE('30 November 2026'), '12 Days', PG('Actions', 'Actions.dc.html')],
         [{'text': 'Internal Audit'}, {'text': 'Compliance Monitoring System', 'sub': '[Independent Auditor], Cycle Ends 30 November 2026'}, DUE('30 November 2026'), '12 Days', PG('Compliance Monitoring', 'Audit.dc.html')],
         [{'text': '2026-F04', 'mono': True}, {'text': 'Finding Corrective Action, Awaiting Verification', 'sub': 'Level 2, Annual Review of the Maintenance Programme Not Recorded for Two Aircraft, Action Submitted 14 November 2026'}, DUE('2 December 2026'), '14 Days', PG('Compliance Monitoring', 'Audit.dc.html')],
         [{'text': '2026-0007', 'mono': True}, {'text': 'Hazard Awaiting Second Assessment', 'sub': 'Hours Carried Forward Incorrectly When Paper Logbook Entries Are Transferred, Next Review 18 December 2026'}, DUE('18 December 2026'), '30 Days', PG('Hazard Log', 'Main.dc.html')],
         [{'text': '2026-0006', 'mono': True}, {'text': 'Hazard Awaiting Second Assessment', 'sub': 'Contracted Maintenance Organisation Late Sending Certificates of Release to Service, Linked to Finding 2026-F03'}, DUE('Not Assessed'), '—', PG('Hazard Log', 'Main.dc.html')]])),
    section('pe-h', 'People', table(
        [('Name', '170px', 'left'), ITEM, DUECOL, LEFT, PAGE],
        [[{'text': '[Name]'}, {'text': 'Certifying Staff Authorisation Lapsed, Part-66 L2', 'sub': 'ELA1 Aeroplanes, Wooden Structure, 61 Days of Experience in 2 Years, 100 Days Needed'}, DUE('Lapsed', 'r'), '—', PG('Authorisations', 'Authorisations.dc.html')],
         [{'text': '[Name]'}, {'text': 'Airworthiness Review Staff Recency Lapses', 'sub': '4 Months of Work in 2 Years, G-EJKL Review Before 2 December Keeps Current'}, DUE('2 December 2026'), '14 Days', PG('Recency', 'Recency.dc.html')]])),
    section('tr-h', 'Training', table(
        [('Name', '170px', 'left'), ITEM, DUECOL, LEFT, PAGE],
        [[{'text': '[Name]', 'sub': 'Airworthiness Review Staff'}, {'text': 'Human Factors Training Overdue', 'sub': 'Last 30 October 2024, Booked 2 December 2026'}, DUE('30 October 2026', 'r'), '19 Days Overdue', PG('Recurrent Training', 'RecurrentTraining.dc.html')],
         [{'text': 'Sam Patel', 'sub': 'Certifying Staff, Part-66 B1.2'}, {'text': 'Human Factors and Continuation Training Due', 'sub': 'Booked 1 December 2026'}, DUE('6 December 2026'), '18 Days', PG('Recurrent Training', 'RecurrentTraining.dc.html')]])),
    section('do-h', 'Documentation', table(
        [('Document', '170px', 'left'), ITEM, DUECOL, LEFT, PAGE],
        [[{'text': 'Grob G 115', 'sub': 'Maintenance Manual'}, {'text': 'Maintenance Data Amendment to Check', 'sub': 'Applies to G-FMNO'}, DUE('20 November 2026'), '2 Days', PG('Maintenance Data', 'MaintenanceData.dc.html')],
         [{'text': 'Exposition', 'sub': 'Revision 7'}, {'text': 'Required Reading Overdue', 'sub': '11 of 12 Acknowledged, [Name], Part-66 L2 Outstanding'}, {'text': '13 November 2026', 'dot': 'r'}, '5 Days Overdue', PG('Required Reading', 'RequiredReading.dc.html')],
         [{'text': 'N-2026-004', 'sub': 'Safety Notice'}, {'text': 'Required Reading, Trim Cable Inspection', 'sub': '7 of 12 Acknowledged'}, DUE('25 November 2026'), '7 Days', PG('Required Reading', 'RequiredReading.dc.html')]])),
    section('or-h', 'Organisation', table(
        [('Change', '170px', 'left'), ITEM, DUECOL, LEFT, PAGE],
        [[{'text': 'Scope of Work', 'sub': 'Made 9 November 2026, Own Procedure'}, {'text': 'Notify the Civil Aviation Authority, Piper PA-38 Series (Lycoming) Added to Scope', 'sub': 'Own Procedure Changes Notified Within 15 Days'}, DUE('24 November 2026'), '6 Days', PG('Changes', 'Changes.dc.html')]])),
    section('lo-h', 'Logistics', table(
        [('Subject', '170px', 'left'), ITEM, DUECOL, LEFT, PAGE],
        [[{'text': 'Sealant', 'sub': 'Batch [Batch Number]'}, {'text': 'Shelf Life Ends'}, DUE('30 November 2026'), '12 Days', PG('Stores', 'Stores.dc.html')],
         [{'text': '[Propeller Organisation]', 'sub': 'Propeller Overhaul and Repair, CAA Form 1'}, {'text': 'Supplier Evaluation Due'}, DUE('30 November 2026'), '12 Days', PG('Suppliers', 'Suppliers.dc.html')]])),
    section('co-h', 'Commercial', table(
        [('Subject', '170px', 'left'), ITEM, DUECOL, LEFT, PAGE],
        [[{'text': 'E-2026-036', 'sub': '[Prospective Customer]'}, {'text': 'Answer Enquiry, Annual Check'}, DUE('19 November 2026'), '1 Day', PG('Enquiries and Quotes', 'Enquiries.dc.html')],
         [{'text': 'INV-2026-0137', 'sub': 'G-FMNO, [Owner Name]'}, {'text': 'Invoice Overdue, £185.00'}, {'text': '4 November 2026', 'dot': 'r'}, '14 Days Overdue', PG('Invoices', 'Invoices.dc.html')],
         [{'text': 'Q-2026-023', 'sub': 'G-EJKL, [Owner Name]'}, {'text': 'Quote Awaiting Acceptance, Work Planned 1 December'}, DUE('1 December 2026'), '13 Days', PG('Enquiries and Quotes', 'Quotes.dc.html')]])),
])

# ---------------------------------------------------------------- Help
ALLW, ORGW, MNTW = 'All Approvals', 'Part-CAO, Part-CAMO, Part-145', 'Part-CAO, Part-145'
SEC = [
    ('Aircraft', 'Continuing Airworthiness', 'Fleet.dc.html', 'Each Aircraft, Status, Next Due, Airworthiness Reviews and Transfers', ALLW, 'ML.A.901, ML.A.903'),
    ('Defects', 'Continuing Airworthiness', 'Defects.dc.html', 'Open and Deferred Defects, Deferral Limits, Repeat Defects', ALLW, 'ML.A.403'),
    ('Maintenance Programmes', 'Continuing Airworthiness', 'Programmes.dc.html', 'Programme per Aircraft, Departures, Annual Review', ALLW, 'ML.A.302'),
    ('Aircraft Configuration', 'Continuing Airworthiness', 'Components.dc.html', 'Components and Life Limits, Airworthiness Directives, Modifications and Repairs, Weight and Balance', ALLW, 'ML.A.503, ML.A.304'),
    ('Release to Service', 'Continuing Airworthiness', 'ReleaseToService.dc.html', 'Certificates of Release to Service, Who May Release', 'Owner, Part-CAO, Part-145', 'ML.A.801, ML.A.305'),
    ('Contracts', 'Continuing Airworthiness', 'Contracts.dc.html', 'Continuing Airworthiness Management Contracts, Maintenance Work Orders', ALLW, 'Appendix I to Part-ML'),
    ('Hazard Log', 'Management System', 'Main.dc.html', 'Hazards, Risk Assessment and Mitigation', 'Part-CAMO, Part-145', 'CAMO.A.200, 145.A.200'),
    ('Safety Reports', 'Management System', 'Reports.dc.html', 'Internal Safety Reports From Staff', 'Part-CAMO, Part-145', 'CAMO.A.202, 145.A.202'),
    ('Occurrence Reports', 'Management System', 'Occurrences.dc.html', 'Reports to the Civil Aviation Authority and Follow-Up Reports', ALLW, 'ML.A.202, M.A.202'),
    ('Compliance Monitoring', 'Management System', 'Audit.dc.html', 'Audit Plan, Internal Audits and Findings', ORGW, 'CAO.A.100, CAMO.A.200'),
    ('Actions', 'Management System', 'Actions.dc.html', 'Actions From Hazards and From Findings', ORGW, 'CAO.A.100'),
    ('Work Packages', 'Planning', 'WorkPackages.dc.html', 'Planned Maintenance, Tasks and Sign-Off', MNTW, 'CAO.A.070'),
    ('Manhours and Capacity', 'Planning', 'Plan.dc.html', 'Manhour Plan, Load and Capacity, Staff Roster', MNTW, '145.A.30'),
    ('Goods In', 'Logistics', 'PartsReceived.dc.html', 'Receiving Inspection of Parts and Materials', MNTW, 'CAP 3037'),
    ('Stores', 'Logistics', 'Stores.dc.html', 'Stock, Quarantine and Scrap', MNTW, 'ML.A.504'),
    ('Tools and Equipment', 'Logistics', 'Tools.dc.html', 'Tool Register, Calibration, Service Providers, Alternative Tooling', MNTW, '145.A.40'),
    ('Suppliers', 'Logistics', 'Suppliers.dc.html', 'Approved Suppliers and Evaluations', MNTW, '145.A.42, CAO.A.050'),
    ('Staff', 'People', 'Staff.dc.html', 'Staff Records and Roles', ORGW, 'CAO.A.040'),
    ('Authorisations', 'People', 'Authorisations.dc.html', 'Certifying Staff and Airworthiness Review Staff, Recency', ORGW, '145.A.35, CAO.A.045'),
    ('Recurrent Training', 'Training', 'RecurrentTraining.dc.html', 'Human Factors, Fuel Tank Safety and Continuation Training Due Dates', ORGW, '145.A.30(e)'),
    ('Aircraft Maintenance Licence', 'Training', 'BasicExaminations.dc.html', 'Basic Examinations, Experience Logbook, Type Training, On the Job Training', ORGW, 'Part-66'),
    ('Competency Assessments', 'Training', 'Competence.dc.html', 'Assessments of Knowledge, Performance, Ability and Behaviours', ORGW, '145.A.30(e)'),
    ('Manuals and Procedures', 'Documentation', 'Manuals.dc.html', 'Controlled Documents, Including the Combined Airworthiness Exposition', ORGW, 'CAO.A.025'),
    ('Maintenance Data', 'Documentation', 'MaintenanceData.dc.html', 'Maintenance Data Held, Amendment Status, Data Queries and Customer Data', ALLW, 'ML.A.401, 145.A.45, CAO.A.055'),
    ('Revisions', 'Documentation', 'Revisions.dc.html', 'Revisions in Progress and Issued', ORGW, 'CAO.A.025'),
    ('Required Reading', 'Documentation', 'RequiredReading.dc.html', 'Staff Acknowledgement of Revisions and Notices', ORGW, 'GM1 145.A.200(a)(4)'),
    ('Notices', 'Documentation', 'Notices.dc.html', 'Safety, Quality and Technical Notices', ORGW, 'GM1 145.A.200(a)(4)'),
    ('Approval and Scope', 'Organisation', 'Approval.dc.html', 'CAA Form 3-CAO, Privileges and Scope of Work', ORGW, 'CAO.A.020'),
    ('Changes', 'Organisation', 'Changes.dc.html', 'Changes to the Organisation and Notification', ORGW, 'CAO.A.105'),
    ('Oversight', 'Organisation', 'Oversight.dc.html', 'Civil Aviation Authority Audits and Findings', ORGW, 'CAO.B.055'),
    ('Marketplace', 'Commercial', 'Marketplace.dc.html', 'Organisations and Engineers to Contract', ALLW, ''),
    ('Enquiries and Quotes', 'Commercial', 'Enquiries.dc.html', 'Enquiries, Quotes and Acceptance as the Written Work Order', ORGW, 'CAO.A.055(b)'),
    ('Customers', 'Commercial', 'Customers.dc.html', 'Owners and Operators, Their Aircraft, Contracts and Balances', ORGW, 'Appendix I to Part-ML'),
    ('Invoices', 'Commercial', 'Invoices.dc.html', 'Invoices Raised on Release to Service', ORGW, 'None'),
]

FACTS = [
    ('Certificate of Release to Service in Records', 'Within 30 Days of Completion', 'ML.A.305, M.A.305'),
    ('Pilot-Owner Tells the Contracted Organisation', 'Within 30 Days of the Task', 'Appendix I to Part-ML'),
    ('Airworthiness Review Certificate Validity', '1 Year, Extendable Twice by 1 Year in a Controlled Environment', 'ML.A.901'),
    ('Early Airworthiness Review', 'Up to 90 Days Before Expiry, Keeps the Expiry Pattern', 'ML.A.901'),
    ('Copy of Review Certificate to the Civil Aviation Authority', 'Within 10 Days', 'ML.A.904, Appendix I'),
    ('Airworthiness Review Staff Recency', '6 Months of Continuing Airworthiness Work in 2 Years, or 1 Review in 12 Months', 'CAO.A.045, CAMO.A.305'),
    ('Certifying Staff Authorisation', 'Licence Valid, 6 Months or 100 Days of Experience in 2 Years, Recurrent Training in 2 Years', 'CAO.A.040, 66.A.20(b), 145.A.35'),
    ('Minimum Inspection Programme', 'Annual or 100 Hours, Whichever First, Tolerance 1 Month or 10 Hours', 'AMC ML.A.302'),
    ('Maintenance Programme Review', 'At Least Annually', 'ML.A.302'),
    ('Occurrence Report', 'Within 72 Hours, Then a Follow-Up', 'ML.A.202, M.A.202'),
    ('Part-CAO Own-Procedure Changes', 'Notified Within 15 Days', 'CAO.A.105'),
    ('Level 2 Finding', 'Corrective Action Within 3 Months, Extendable With a Plan', 'CAO.B.050, CAMO.B.350'),
    ('Authority Oversight Cycle', '24 Months, up to 36 or 48 With a Good Record', 'CAMO.B.305, 145.B.305'),
    ('Internal Audit', 'Every Item Every 12 Months, up to 100% Extension', 'CAO.A.100, CAMO.A.200'),
    ('Contract Ended for Non-Compliance', 'Owner Tells the Civil Aviation Authority Within 2 Weeks', 'Appendix I to Part-ML'),
    ('Maintenance Records Retention', '36 Months After Release, Totals and Directive Status 12 Months After Withdrawal', 'ML.A.305'),
    ('Human Factors Training', 'Within 6 Months of Joining, Then Every 2 Years', '145.A.30(e)'),
    ('Fuel Tank Safety Training', 'Phase 1 Within 6 Months, Phase 2 Within 12 Months, Then Every 2 Years', 'AMC 145.A.30(e)'),
    ('Airworthiness Review Staff Records', 'Kept 2 Years After the Person Leaves', 'CAO.A.045(e)'),
    ('Lapsed Airworthiness Review Staff', 'Restored by 1 Review Under Supervision', 'AMC CAO.A.045'),
    ('Component Classes', 'Serviceable With Release Document, Unserviceable, Unsalvageable, Standard Part, Material', 'M.A.501, ML.A.501, 145.A.42'),
    ('Unsalvageable Items', 'Secure Area, Mutilated, or Kept for Training or Research, With a Named Person Responsible', 'ML.A.504, AMC1 CAO.A.030(n)'),
    ('Contracted Software for Records', 'Each Organisation Sees Only Its Own Data, Only Its Own Staff Enter Data', 'AMC CAO.A.090, AMC CAMO.A.220'),
]

BEH = [
    ('4.1', 'Decision Taking and Judgement Making', 'Uses Factual Evidence, Anticipates Problems, Keeps Preconceptions Out, Open to Changing Their Mind'),
    ('4.2', 'Professionalism', 'Knows Their Own Limits, Explains the Risks, Calm Under Pressure, Asks for Advice When Unsure'),
    ('4.3', 'Integrity', 'Resists Commercial Pressure, Never Cuts Corners, Keeps Standards Consistently High'),
    ('4.4', 'Adaptability', 'Accepts Change, Learns From Mistakes, Looks at a Problem From Different Angles'),
    ('4.5', 'Leadership', 'Helps Others Reach Their Objectives, Motivates Others, Works With Little Supervision, Owns Completion'),
    ('4.6', 'Team Working', 'Equal Courtesy at Every Level, Reduces Conflict, Coaches Less Experienced Colleagues'),
]

page('Guide.dc.html', 'Help', 'guide', 4500, [
    header('Help', 'Help', trail='Help'),
    section('sec-h', 'Sidebar Items', table(
        [('Item', '230px', 'left'), ('Section', '210px', 'left'), ('Holds', '', 'left'), ('Shown For', '240px', 'left'), ('Point', '180px', 'left')],
        [[PG(n, h), s, d, w, p or '—'] for n, s, h, d, w, p in SEC], minw=1100),
        right='<a href="Settings.dc.html" style="font-size: 14px; color: {{t.text}}; text-decoration: underline; text-underline-offset: 3px; text-decoration-color: {{t.sBorder}}">Approvals Held in Settings</a>'),
    section('mark-h', 'Status Marks', table(
        [('Mark', '260px', 'left'), ('Means', '', 'left'), ('Where', '320px', 'left')],
        [[{'text': 'Red', 'dot': 'r', 'status': True}, 'Overdue, Lapsed or Unserviceable', 'Any Row, Next to the Date or Status'],
         [{'text': 'Amber', 'dot': 'a', 'status': True}, 'Due Within the Alert Lead Time', 'Any Row, Next to the Date or Status'],
         [{'text': 'Green', 'dot': 'g', 'status': True}, 'Current, Serviceable or Approved', 'Status Column and Status Fact Only'],
         [{'text': 'Open', 'dot': 'o', 'status': True}, 'Not Started or Awaiting Verification', 'Status Column and Checklists']], minw=900)),
    section('lim-h', 'Time Limits Used in Alerts', table(
        [('Rule', '360px', 'left'), ('Limit', '', 'left'), ('Point', '240px', 'left')],
        [list(f) for f in FACTS], minw=1000),
        right='<a href="Settings.dc.html" style="font-size: 14px; color: {{t.text}}; text-decoration: underline; text-underline-offset: 3px; text-decoration-color: {{t.sBorder}}">Alert Lead Times in Settings</a>'),
    section('scale-h', 'Competency Assessment Scale', table(
        [('Score', '160px', 'left'), ('Meaning', '', 'left'), ('Then', '360px', 'left')],
        [['1', 'No Understanding of the Subject', 'Development Action, Work Under Supervision'],
         ['5', 'Minimum Level of Competence', 'Below 5 Needs a Development Action'],
         ['10', 'Highly Competent, Able to Train or Mentor Peers', 'None']], minw=900),
        intro='',
        right='<a href="Competence.dc.html" style="font-size: 14px; color: {{t.text}}; text-decoration: underline; text-underline-offset: 3px; text-decoration-color: {{t.sBorder}}">Competency Assessments</a>'),
    section('ass-h', 'Assessment Stages', table(
        [('Stage', '260px', 'left'), ('Checks', '', 'left')],
        [['Pre-Interview Checks', 'Job Description, Experience, Basic Training, Human Factors, Continuation Training, Recency, Occupational Health'],
         ['Knowledge and Understanding', 'Regulations for the Scope of Approval, Technical Grasp of Daily Tasks, Organisation Procedures and Reporting'],
         ['Performance', 'Real Work Observed by a Suitably Qualified Manager, Team Leader or Supervisor'],
         ['Ability', 'Physical and Mental Ability for the Role, New Glasses or Medication Can Trigger a Reassessment'],
         ['Behaviours and Attitudes', 'Six Factors, 4.1–4.6'],
         ['After the Assessment', 'Analyse Every Answer, Give Support, Limit or Suspend Authorisations if Needed, Reassess']], minw=900)),
    section('beh-h', 'Behaviours and Attitudes', table(
        [('Factor', '120px', 'left'), ('Name', '320px', 'left'), ('What to Look For', '', 'left')],
        [[{'text': n, 'mono': True}, t_, l] for n, t_, l in BEH], minw=900)),
])

# ---------------------------------------------------------------- Settings, Organisation (interactive: approvals held change the sidebar count)
import json as _json
SET_H = 2620
LINK = 'color: {{t.text}}; text-decoration: underline; text-underline-offset: 3px; text-decoration-color: {{t.sBorder}}'
INPUT = 'font: inherit; font-size: 14px; font-weight: 400; height: 40px; box-sizing: border-box; padding: 0 12px; border-radius: 6px; border: 1px solid {{t.sBorder}}; background: {{t.bg}}; color: {{t.text}}'
NUM = INPUT + '; width: 88px; text-align: right'
H2 = 'margin: 0; font-size: 16px; line-height: 24px; font-weight: 600; letter-spacing: -0.32px'
META = 'font-size: 14px; line-height: 20px; color: {{t.muted}}'
TH = 'padding: 12px 16px; font-weight: 500; white-space: nowrap; border-bottom: 1px solid {{t.border}}'
TD = 'padding: 8px 16px; border-bottom: 1px solid {{t.row}}; white-space: nowrap; overflow: hidden; text-overflow: ellipsis'

def short_table(cols, rows, minw=860):
    th = ''.join(f'<th scope="col" style="{TH}; text-align: {a}{"; width: " + w if w else ""}">{E(l)}</th>' for l, w, a in cols)
    body = ''
    for r in rows:
        tds = ''
        for i, (v, (l, w, a)) in enumerate(zip(r, cols)):
            weight = 500 if i == 0 else 400
            tds += f'<td style="{TD}; height: 40px; text-align: {a}; font-weight: {weight}">{v}</td>'
        body += f'<tr>{tds}</tr>\n'
    return f'''<div style="overflow-x: auto; border: 1px solid {{{{t.border}}}}; border-radius: 6px">
<table style="width: 100%; min-width: {minw}px; border-collapse: collapse; font-size: 14px; line-height: 20px">
<thead><tr style="background: {{{{t.sidebar}}}}; color: {{{{t.muted}}}}; font-size: 13px; text-align: left">{th}</tr></thead>
<tbody>
{body}</tbody>
</table>
</div>
'''

def num(value, label, unit):
    return f'<span style="display: inline-flex; align-items: center; gap: 8px; justify-content: flex-end"><input type="number" min="0" value="{value}" aria-label="{E(label)}" style="{NUM}"><span style="color: {{{{t.muted}}}}">{E(unit)}</span></span>'

def sect(hid, heading, inner, right='', intro=''):
    i = f'<p style="margin: 0; {META}">{E(intro)}</p>' if intro else ''
    return f'''    <section aria-labelledby="{hid}" style="display: flex; flex-direction: column; gap: 16px">
      <div style="display: flex; flex-wrap: wrap; justify-content: space-between; align-items: baseline; gap: 12px"><h2 id="{hid}" style="{H2}">{E(heading)}</h2>{right}</div>
      {i}
{inner}    </section>
'''

def field(label, value, typ='text'):
    return f'<label style="display: flex; flex-direction: column; gap: 6px; font-size: 13px; line-height: 16px; color: {{{{t.muted}}}}">{E(label)}<input type="{typ}" value="{E(value)}" style="{INPUT}"></label>'

details = f'''<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; max-width: 960px">
{field('Organisation Name', '[Your Organisation]')}
{field('Address', '[Address]')}
{field('Telephone', '[Telephone]', 'tel')}
{field('Email for Alerts', '[Email]', 'email')}
<div style="display: flex; flex-direction: column; gap: 6px"><span style="font-size: 13px; line-height: 16px; color: {{{{t.muted}}}}">Approval Reference</span><span style="font-size: 14px; line-height: 40px; font-weight: 500; font-family: 'Geist Mono Embedded', 'Geist Mono', monospace">UK.CAO.[Number]</span></div>
<div style="display: flex; flex-direction: column; gap: 6px"><span style="font-size: 13px; line-height: 16px; color: {{{{t.muted}}}}">Certificate, Privileges and Scope of Work</span><a href="Approval.dc.html" style="font-size: 14px; line-height: 40px; font-weight: 500; {LINK}">Approval and Scope</a></div>
</div>
'''

approvals = '''<fieldset style="margin: 0; padding: 0; border: 0; min-width: 0">
<legend style="position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0)">Approvals Held</legend>
<ul style="margin: 0; padding: 0; list-style: none; border-top: 1px solid {{t.border}}">
<sc-for list="{{approvals}}" as="a" hint-placeholder-count="4">
<li style="padding: 12px 0; border-bottom: 1px solid {{t.border}}; font-size: 14px; line-height: 20px">
<label style="display: flex; gap: 12px; align-items: flex-start; cursor: pointer">
<input type="checkbox" checked="{{a.checked}}" onChange="{{a.toggle}}" style="width: 18px; height: 18px; margin: 1px 0 0; accent-color: {{t.text}}">
<span style="display: flex; flex-direction: column; gap: 2px"><span style="font-weight: 500">{{a.label}}</span><span style="color: {{t.muted}}">{{a.note}}</span></span>
</label>
</li>
</sc-for>
</ul>
</fieldset>
'''

defer = short_table(
    [('Decision By', '330px', 'left'), ('Applies To', '', 'left'), ('Default Limit', '200px', 'right'), ('Point', '170px', 'left')],
    [['Pilot-in-Command', 'Defects on Non-Required Equipment', num(30, 'Pilot-in-Command, Non-Required Equipment', 'Days'), 'ML.A.403(b)(1)'],
     ['Pilot-in-Command, Minimum Equipment List', 'Required Equipment Listed in the Minimum Equipment List', '<span style="color: {{t.muted}}">Category Limit in the List</span>', 'ML.A.403(b)(2)'],
     ['Pilot-in-Command, With Agreement', 'Other Defects, Part-NCO, Owner or Organisation Agrees', num(30, 'Pilot-in-Command With Agreement', 'Days'), 'ML.A.403(b)(3)'],
     ['Certifying Staff', 'Other Defects', num(30, 'Certifying Staff', 'Days'), 'ML.A.403(b)(4)']], minw=1000)

ALERTS = [
    ('Airworthiness Review Certificate Expiry', num(60, 'First Alert', 'Days') + '<span style="display: inline-block; width: 12px"></span>' + num(30, 'Second Alert', 'Days'), 'Airworthiness Reviews'),
    ('Hour-Based Checks and Life Limits', num(15, 'Hour-Based Checks', 'Hours'), 'Aircraft, Aircraft Configuration'),
    ('Calendar Checks and Programme Reviews', num(30, 'Calendar Checks', 'Days'), 'Aircraft, Maintenance Programmes'),
    ('Deferred Defect Limits', num(30, 'Deferred Defect Limits', 'Days'), 'Defects'),
    ('Certificates Not Yet in Records', num(30, 'Certificates Not Yet in Records', 'Days'), 'Release to Service'),
    ('Findings, Actions and Internal Audits', num(30, 'Findings and Actions', 'Days'), 'Compliance Monitoring, Actions'),
    ('Authorisations and Recency', num(30, 'Authorisations and Recency', 'Days'), 'Authorisations'),
    ('Recurrent Training', num(30, 'Recurrent Training', 'Days'), 'Recurrent Training'),
    ('Changes to Notify', '<span style="color: {{t.muted}}">From the Day the Change Is Made</span>', 'Changes'),
    ('Supplier Evaluations, Shelf Life and Calibration', num(30, 'Supplier Evaluations', 'Days'), 'Suppliers, Stores, Tools and Equipment'),
]
alerts = short_table([('Alert', '360px', 'left'), ('Lead Time', '320px', 'right'), ('Shown On', '', 'left')], [list(a) for a in ALERTS], minw=1000)

USERS = [
    ('[Accountable Manager]', 'Accountable Manager', 'View All'),
    ('[Name]', 'Nominated Person, Continuing Airworthiness Manager', 'Administrator'),
    ('[Name]', 'Nominated Person, Maintenance Manager', 'Edit Maintenance and Planning'),
    ('Lucy Grant', 'Airworthiness Review Staff, Continuing Airworthiness', 'Edit Continuing Airworthiness'),
    ('[Name]', 'Airworthiness Review Staff', 'Edit Continuing Airworthiness'),
    ('Chris Moore', 'Certifying Staff, Part-66 B1.2', 'Edit Maintenance, Issue Releases'),
    ('Sam Patel', 'Certifying Staff, Part-66 B1.2', 'Edit Maintenance, Issue Releases'),
    ('[Name]', 'Certifying Staff, Part-66 L2, Contracted', 'View Only Until Authorisation Restored'),
    ('[Name]', 'Support Staff, Planning and Records', 'Edit Planning and Records'),
    ('[Owner Name]', 'Pilot-Owner, G-ABCD', 'View Own Aircraft'),
]
users = short_table([('Name', '240px', 'left'), ('Role', '', 'left'), ('Access', '340px', 'left')], [[E(a), E(b), E(c)] for a, b, c in USERS], minw=900)

SR_ = 'position: absolute; width: 1px; height: 1px; margin: -1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap'
hdr = f'''    <dc-import name="TopBar" trail="Settings" line="false" dark="{{{{dark}}}}" hint-size="1100px,56px"></dc-import>
    <h1 style="{SR_}">Settings, Organisation</h1>
    <div style="margin-top: -36px; display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 16px; margin-left: -40px; margin-right: -40px; padding: 0 40px; box-shadow: inset 0 -1px 0 {{{{t.border}}}}">
      <dc-import name="Tabs" set="settings" active="org" line="false" dark="{{{{dark}}}}" hint-size="760px,44px"></dc-import>
      <div style="display: flex; flex-wrap: wrap; gap: 8px; padding: 2px 0">{btn('Save Changes', primary=True)}</div>
    </div>
'''

parts = [hdr,
    sect('org-h', 'Organisation Details', details),
    sect('appr-h', 'Approvals Held', approvals, right='<span style="' + META + '">Sidebar Shows {{shown}} of {{total}} Items</span>'),
    sect('def-h', 'Deferral Limits', defer, intro='Limit in the Maintenance Data Applies When Shorter, ML.A.403(c)'),
    sect('alert-h', 'Alert Lead Times', alerts, intro='Dashboard Shows Each Item From Its Lead Time'),
    sect('user-h', 'Users and Roles', users, right=btn('Invite a User'), intro='Each Organisation Sees Only Its Own Data, Only Its Own Staff Enter Data'),
]

SIDEBAR_ITEMS = [  # label, approvals that show it (from Sidebar.dc.html)
    ['Dashboard', 'all'], ['Aircraft', 'all'], ['Defects', 'all'], ['Maintenance Programmes', 'all'], ['Aircraft Configuration', 'all'],
    ['Release to Service', 'owner cao 145'], ['Contracts', 'all'], ['Hazard Log', 'camo 145'], ['Safety Reports', 'camo 145'],
    ['Occurrence Reports', 'all'], ['Compliance Monitoring', 'cao camo 145'], ['Actions', 'cao camo 145'], ['Work Packages', 'cao 145'],
    ['Manhours and Capacity', 'cao 145'], ['Goods In', 'cao 145'], ['Stores', 'cao 145'], ['Tools and Equipment', 'cao 145'], ['Suppliers', 'cao 145'],
    ['Staff', 'cao camo 145'], ['Authorisations', 'cao camo 145'], ['Recurrent Training', 'cao camo 145'], ['Aircraft Maintenance Licence', 'cao camo 145'],
    ['Competency Assessments', 'cao camo 145'], ['Manuals and Procedures', 'cao camo 145'], ['Maintenance Data', 'all'], ['Revisions', 'cao camo 145'], ['Required Reading', 'cao camo 145'], ['Notices', 'cao camo 145'], ['Approval and Scope', 'cao camo 145'], ['Changes', 'cao camo 145'],
    ['Oversight', 'cao camo 145'], ['Marketplace', 'all']]

SCRIPT = '''<script type="text/x-dc" data-dc-script data-props='{"dark":{"editor":"boolean","default":false},"$preview":{"width":1440,"height":%d}}'>
class Component extends DCLogic {
  constructor(props) { super(props); this.state = { held: { owner: false, cao: true, camo: false, p145: false } }; }
  renderVals() {
    const dark = this.props.dark === true || this.props.dark === 'true';
    const t = dark
      ? { scheme: 'dark', bg: '#0A0A0A', sidebar: '#000000', border: '#2E2E2E', row: '#2E2E2E', text: '#EDEDED', muted: '#A1A1A1', body: '#EDEDED', pBg: '#EDEDED', pFg: '#0A0A0A', sBorder: '#2E2E2E', note: '#000000' }
      : { scheme: 'light', bg: '#FFFFFF', sidebar: '#FAFAFA', border: '#EBEBEB', row: '#EBEBEB', text: '#171717', muted: '#666666', body: '#171717', pBg: '#171717', pFg: '#FFFFFF', sBorder: '#EBEBEB', note: '#FAFAFA' };
    const items = %s;
    const keys = { owner: 'owner', cao: 'cao', camo: 'camo', p145: '145' };
    const held = this.state.held;
    const on = Object.keys(held).filter(k => held[k]).map(k => keys[k]);
    const shown = items.filter(([, who]) => who === 'all' ? on.length > 0 : who.split(' ').some(w => on.indexOf(w) !== -1)).length;
    const defs = [
      ['owner', 'Owner', 'Continuing Airworthiness, Occurrence Reports and Marketplace'],
      ['cao', 'Part-CAO', 'Held, UK.CAO.[Number], Adds Compliance Monitoring, Actions, Planning, Logistics, People, Training and Organisation'],
      ['camo', 'Part-CAMO', 'Adds Hazard Log, Safety Reports, Compliance Monitoring, Actions, People, Training and Organisation'],
      ['p145', 'Part-145', 'Adds Hazard Log, Safety Reports, Planning, Logistics, People, Training and Organisation']
    ];
    const approvals = defs.map(([k, label, note]) => ({ label, note, checked: !!held[k],
      toggle: () => { const n = Object.assign({}, this.state.held); n[k] = !n[k]; this.setState({ held: n }); } }));
    return { t, dark, approvals, shown: String(shown), total: String(items.length) };
  }
}
</script>
</body>
</html>
''' % (SET_H, _json.dumps(SIDEBAR_ITEMS))

head = HEAD % ('Settings', 'org', SET_H)
TAIL_HTML = '  </main>\n</div>\n</x-dc>\n'
import os as _os
if not _os.environ.get('ONLY') or 'Settings.dc.html' in _os.environ.get('ONLY', '').split(','):
    open(OUT + 'Settings.dc.html', 'w').write(head + ''.join(parts) + TAIL_HTML + SCRIPT)
