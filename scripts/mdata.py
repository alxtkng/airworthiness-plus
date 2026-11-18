# Documentation: Maintenance Data (M.A.401, ML.A.401, 145.A.45, CAO.A.055, CAO.A.080, CAMO.A.325)
from gen import *
T = 'Documentation=Manuals.dc.html|'
OK = 'Current'
page('MaintenanceData.dc.html', 'Maintenance Data', 'mdata', 1500, [
    header('Documentation', 'Maintenance Data', '', [btn('Add Maintenance Data', primary=True)], trail=T + 'Maintenance Data'),
    strip([('9', 'Held and Current'), ('1', 'Amendment to Check'), ('1', 'Not Held'), ('1', 'Data Query')]),
    section('held-h', 'Data Held', table(
        [('Maintenance Data', '', 'left'), ('Author', '220px', 'left'), ('Applies To', '300px', 'left'), ('Revision', '120px', 'left'), ('Last Checked', '180px', 'left'), ('Status', '240px', 'left')],
        [['Piper PA-28 Series Maintenance Manual', 'Piper Aircraft', 'Piper PA-28 Series (Lycoming)', '[Revision]', '2 November 2026', OK],
         ['Cessna 152 Series Maintenance Manual', 'Textron Aviation', 'Cessna/Reims-Cessna 152/F152 Series (Lycoming)', '[Revision]', '2 November 2026', OK],
         ['Cessna 172 Series Maintenance Manual', 'Textron Aviation', 'Cessna/Reims-Cessna 172/F172 Series (Lycoming)', '[Revision]', '2 November 2026', OK],
         ['Grob G 115 Maintenance Manual', 'Grob Aircraft', 'Grob G115/120 Series (Lycoming)', '[Revision]', '4 October 2026', {'text': 'Amendment to Check, 20 November 2026', 'dot': 'a'}],
         ['Robin DR 400 Maintenance Manual', '[Type Certificate Holder]', 'Robin DR 400 series (Lycoming)', '[Revision]', '2 November 2026', OK],
         ['Piper PA-38 Series Maintenance Manual', 'Piper Aircraft', 'Piper PA-38 Series (Lycoming)', '—', '—', {'text': 'Not Held, Needed for G-HKLM', 'dot': 'a'}],
         ['Lycoming Service Instructions and Bulletins', 'Lycoming Engines', 'Piston Engines, Lycoming', '[Revision]', '16 November 2026', OK],
         ['Continental Service Information', 'Continental Aerospace Technologies', 'Piston Engines, Continental', '[Revision]', '16 November 2026', OK],
         ['Propeller Maintenance Manual', '[Propeller Manufacturer]', 'C16 Propellers', '[Revision]', '2 November 2026', OK],
         ['Airworthiness Directives', 'Civil Aviation Authority and State of Design', 'All Types in Scope', '—', '16 November 2026', OK],
         ['CAP 747 Mandatory Requirements for Airworthiness', 'Civil Aviation Authority', 'All United Kingdom Registered Aircraft', '[Revision]', '16 November 2026', OK]], minw=1320)),
    section('query-h', 'Data Queries', table(
        [('Reference', '140px', 'left'), ('Maintenance Data', '280px', 'left'), ('Query', '', 'left'), ('Raised', '180px', 'left'), ('Status', '260px', 'left')],
        [[{'text': 'SR-2026-015', 'mono': True, 'href': 'Reports.dc.html'}, 'Piper PA-28 Series Maintenance Manual', 'Torque Value on the Work Card Differed From the Maintenance Manual', '17 November 2026', {'text': 'To Assess, Work Card or Manual', 'dot': 'a'}]], minw=1100),
        intro='Recorded as a Safety Report and Notified to the Author'),
    section('cust-h', 'Customer Data', table(
        [('Aircraft Registration', '170px', 'left'), ('Maintenance Data', '', 'left'), ('Amendment Status Shown By', '320px', 'left'), ('Held Until', '200px', 'left')],
        [['G-BXYZ', 'Supplementary Type Certificate Instructions, Avionics Installation, [Supplementary Type Certificate Holder]', 'Written Confirmation From the Owner, 2 June 2026', 'End of Contract']], minw=1100),
        intro='Held While Work Is in Progress or for the Contract'),
])
