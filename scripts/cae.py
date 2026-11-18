# Exposition record: every CAE procedure (AMC1 CAO.A.025) and where it is done in Airworthiness+.
from gen import *
M = {'Exposition Text': None, 'Not Yet in Airworthiness+': None,
 'Approval and Scope': 'Approval.dc.html', 'Revisions': 'Revisions.dc.html', 'Changes': 'Changes.dc.html', 'Organisation Chart': 'OrgChart.dc.html',
 'Manhours and Capacity': 'Plan.dc.html', 'Authorisations': 'Authorisations.dc.html', 'Compliance Monitoring': 'Audit.dc.html', 'Contracts': 'Contracts.dc.html',
 'Recurrent Training': 'RecurrentTraining.dc.html', 'Competency Assessments': 'Competence.dc.html', 'Suppliers': 'Suppliers.dc.html', 'Aircraft': 'Fleet.dc.html',
 'Airworthiness Reviews': 'Reviews.dc.html', 'Work Packages': 'WorkPackages.dc.html', 'Enquiries and Quotes': 'Enquiries.dc.html', 'Goods In': 'PartsReceived.dc.html',
 'Stores': 'Stores.dc.html', 'Tools and Equipment': 'Tools.dc.html', 'Release to Service': 'ReleaseToService.dc.html', 'Defects': 'Defects.dc.html',
 'Maintenance Programmes': 'Programmes.dc.html', 'Aircraft Configuration': 'Components.dc.html', 'Manuals and Procedures': 'Manuals.dc.html', 'Maintenance Data': 'MaintenanceData.dc.html', 'Occurrence Reports': 'Occurrences.dc.html'}
def where(names):
    out = []
    for n in names.split(', '):
        out.append(n)
    first = names.split(', ')[0]
    v = {'text': names}
    if M.get(first): v['href'] = M[first]
    if first == 'Not Yet in Airworthiness+': v['dot'] = 'o'; v['status'] = True
    return v
P = {
'A': ('General Description', [
 ('A.1', 'Statement by the Accountable Manager', 'Exposition Text', 'CAO.A.025(a)(1)'),
 ('A.2', 'General Presentation of the Organisation', 'Approval and Scope', 'CAO.A.035(a)'),
 ('A.3', 'Description and Location of the Facilities', 'Approval and Scope', 'CAO.A.030'),
 ('A.4', 'Scope of Work', 'Approval and Scope', 'CAO.A.020(a)'),
 ('A.5', 'Exposition Amendments and Changes to the Organisation', 'Revisions, Changes', 'CAO.A.105'),
 ('A.6', 'Procedure for Alternative Means of Compliance', 'Changes', 'CAO.A.017'),
 ('A.7', 'Management Personnel', 'Organisation Chart', 'CAO.A.035(b)'),
 ('A.8', 'Organisation Chart', 'Organisation Chart', 'CAO.A.025(a)(4)'),
 ('A.9', 'Manpower Resources', 'Manhours and Capacity', 'CAO.A.035(d)'),
 ('A.10', 'List of Certifying Staff', 'Authorisations', 'CAO.A.025(a)(5)'),
 ('A.11', 'List of Staff Responsible for the Aircraft Maintenance Programme', 'Authorisations', 'CAO.A.025(a)(6)'),
 ('A.12', 'List of Airworthiness Review Staff', 'Authorisations', 'CAO.A.045(d)'),
 ('A.13', 'List of Staff Responsible for Issuing Permits to Fly', 'Authorisations', 'CAO.A.025(a)(8)')]),
'B': ('General Procedures', [
 ('B.1', 'Quality System or Organisational Review', 'Compliance Monitoring', 'CAO.A.100'),
 ('B.2', 'Audit Plan', 'Compliance Monitoring', 'CAO.A.100(b)'),
 ('B.3', 'Monitoring of Maintenance Contracts', 'Contracts', 'CAO.A.100(b)(2)'),
 ('B.4', 'Qualification, Assessment and Training of Staff', 'Recurrent Training, Competency Assessments', 'CAO.A.035(c)'),
 ('B.5', 'One-Off Certification Authorisation', 'Authorisations', 'CAO.A.040(b)'),
 ('B.6', 'Limited Certification Authorisation', 'Authorisations', 'CAO.A.040(c)'),
 ('B.7', 'Subcontracting', 'Suppliers', 'CAO.A.095(a)(2)'),
 ('B.8', 'Maintenance Data and Continuing Airworthiness Management Data', 'Maintenance Data', 'CAO.A.055(a)'),
 ('B.9', 'Records Management and Retention', 'Aircraft', 'CAO.A.090'),
 ('B.10', 'Carrying Out the Airworthiness Review', 'Airworthiness Reviews', 'CAO.A.085'),
 ('B.11', 'Conformity with Approved Flight Conditions', 'Not Yet in Airworthiness+', 'CAO.A.095(d)'),
 ('B.12', 'Issue of the Permit to Fly', 'Not Yet in Airworthiness+', 'CAO.A.095(d)')]),
'C': ('Maintenance Procedures', [
 ('C.1', 'Maintenance, General', 'Work Packages', 'CAO.A.025(a)(10)'),
 ('C.2', 'Work Order Acceptance', 'Enquiries and Quotes', 'CAO.A.055(b)'),
 ('C.3', 'Components, Equipment, Tools and Material', 'Goods In, Stores, Tools and Equipment', 'CAO.A.050'),
 ('C.4', 'Maintenance Facility', 'Approval and Scope', 'CAO.A.060(b)'),
 ('C.5', 'Maintenance Accomplishment and Maintenance Standards', 'Work Packages', 'CAO.A.060(c)'),
 ('C.6', 'Prevention of Maintenance Error', 'Exposition Text', 'CAO.A.060(g)'),
 ('C.7', 'Critical Maintenance Tasks and Error-Capturing Method', 'Work Packages', 'CAO.A.060(h)'),
 ('C.8', 'Fabrication', 'Not Yet in Airworthiness+', 'CAO.A.020(c)'),
 ('C.9', 'Certifying Staff Responsibilities and Maintenance Release', 'Release to Service', 'CAO.A.065'),
 ('C.10', 'Defects Arising During Maintenance', 'Defects', 'CAO.A.075(b)(6)'),
 ('C.11', 'Maintenance Away From the Approved Location', 'Work Packages', 'CAO.A.095(a)(3)'),
 ('C.12', 'Component Maintenance Under Aircraft or Engine Rating', 'Work Packages', 'Appendix I (b)'),
 ('C.13', 'Maintenance on Installed Engine or Component Under Engine or Component Rating', 'Work Packages', 'Appendix I (c)'),
 ('C.14', 'Special Procedures, Non-Destructive Testing and Engine Running', 'Exposition Text', 'CAO.A.030(a)'),
 ('C.15', 'Issue of the Airworthiness Review Certificate Under Maintenance Privilege', 'Airworthiness Reviews', 'CAO.A.095(c)(2)')]),
'D': ('Continuing Airworthiness Management Procedures', [
 ('D.1', 'Continuing Airworthiness Management, General', 'Aircraft', 'CAO.A.075'),
 ('D.2', 'Minimum Equipment List and Configuration Deviation List', 'Not Yet in Airworthiness+', 'CAO.A.075(a)'),
 ('D.3', 'Aircraft Maintenance Programme Development, Control and Periodic Review', 'Maintenance Programmes', 'CAO.A.075(b)(1)'),
 ('D.4', 'Airworthiness Directives and Other Mandatory Requirements', 'Aircraft Configuration', 'CAO.A.075(b)(5)'),
 ('D.5', 'Modifications and Repairs', 'Aircraft Configuration', 'CAO.A.075(b)(3)'),
 ('D.6', 'Pre-Flight Inspection', 'Exposition Text', 'CAO.A.075(a)'),
 ('D.7', 'Defects', 'Defects', 'CAO.A.075(b)(6)'),
 ('D.8', 'Contracts and Work Orders for Maintenance', 'Contracts', 'CAO.A.075(b)(4)'),
 ('D.9', 'Coordination of Maintenance Activities', 'Work Packages', 'CAO.A.075(b)(8)'),
 ('D.10', 'Mass and Balance Statement', 'Aircraft Configuration', 'CAO.A.075(b)(10)'),
 ('D.11', 'Issue of the Airworthiness Review Certificate or Recommendation', 'Airworthiness Reviews', 'CAO.A.095(c)(1)'),
 ('D.12', 'Airworthiness Review Certificate Extension', 'Airworthiness Reviews', 'CAO.A.095(b)(4)'),
 ('D.13', 'Maintenance Check Flights', 'Not Yet in Airworthiness+', 'CAO.A.075(a)')]),
'E': ('Supporting Documents', [
 ('E.1', 'Sample Documents', 'Manuals and Procedures', ''),
 ('E.2', 'List of Subcontracted Organisations', 'Suppliers', ''),
 ('E.3', 'List of Organisations Contracted by the Organisation', 'Suppliers', ''),
 ('E.4', 'Aircraft Technical Log System', 'Not Yet in Airworthiness+', ''),
 ('E.5', 'List of Approved Alternative Means of Compliance', 'Changes', ''),
 ('E.6', 'Contracts for Subcontracted Continuing Airworthiness Tasks', 'Contracts', '')]),
}
cols = [('Chapter', '100px', 'left'), ('Procedure', '', 'left'), ('In Airworthiness+', '300px', 'left'), ('Rule', '180px', 'left')]
notyet = sum(1 for p in P.values() for r in p[1] if r[2].startswith('Not Yet'))
parts = [
    header('Documentation', 'Combined Airworthiness Exposition', '', [btn('Start a Revision', primary=True)],
           trail='Documentation=Manuals.dc.html|Manuals and Procedures=Manuals.dc.html|Combined Airworthiness Exposition'),
    strip([('Revision 7', 'Current'), ('30 October 2026', 'Approved'), ('59', 'Procedures'), (str(notyet), 'Not Yet in Airworthiness+')]),
]
for k, (title, rows) in P.items():
    parts.append(section(k.lower() + '-h', 'Part %s, %s' % (k, title), table(cols,
        [[{'text': c, 'mono': True}, t, where(w), {'text': r, 'mono': True} if r else '—'] for c, t, w, r in rows], minw=1100)))
parts.append(section('rev-h', 'Revisions', table(
    [('Revision', '120px', 'left'), ('Changes', '', 'left'), ('Route', '220px', 'left'), ('Approved', '200px', 'left')],
    [['8', 'A.4 Scope of Work, Piper PA-38 Series (Lycoming)', 'Own Procedure', {'text': 'Draft', 'dot': 'a'}],
     ['7', 'A.10 List of Certifying Staff, A.12 List of Airworthiness Review Staff', 'Own Procedure', '30 October 2026'],
     ['6', 'C.3 Components, Equipment, Tools and Material', 'Own Procedure', '12 March 2026']], minw=960)))
page('Exposition.dc.html', 'Exposition', 'exposition', 3900, parts)
print(notyet)
