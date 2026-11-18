from gen import *

# Planning group: Work Packages, Manhours and Capacity (Manhour Plan, Load and Capacity, Staff Roster), Settings, Planning.
# Terse Title Case labels, spelled out, sample data from SampleData.md. Today is Wednesday 18 November 2026.
AC = lambda r, sub=None: {'text': r, 'href': 'Aircraft.dc.html' if r == 'G-ABCD' else None, 'sub': sub}
REG = ('Aircraft Registration', '170px', 'left')
MONO = lambda r, sub=None, href=None: {'text': r, 'mono': True, 'sub': sub, 'href': href}
ST = lambda text, c, sub=None: {'text': text, 'dot': c, 'status': True, 'sub': sub}
CO = 'Contracts.dc.html'
PLANTRAIL = 'Planning=WorkPackages.dc.html|Manhours and Capacity=Plan.dc.html|'

# Planning: Work Packages (ML.A.402, M.A.402, 145.A.48, 145.A.35, CAO.A.040)
page('WorkPackages.dc.html', 'Work Packages', 'wp', 2300, [
    header('Planning', 'Work Packages', '', [btn('Build a Work Package', primary=True)],
           trail='Planning=WorkPackages.dc.html|Work Packages'),
    section('wp-h', 'Work Packages', table(
        [('Reference', '130px', 'left'), ('Aircraft Registration', '150px', 'left'), ('Work', '250px', 'left'), ('Work Order', '200px', 'left'), ('Dates', '170px', 'left'), ('Status', '130px', 'left')],
        [[MONO('WP-2026-046'), AC('G-DGHI', 'Piper PA-28 Series (Lycoming)'), {'text': 'Stabilator Trim Cable Rectification', 'sub': 'Bay 1, 17.0 Hours'}, {'text': 'Continuing Airworthiness Manager', 'href': CO, 'sub': 'Agreed 14 November 2026'}, {'text': '16–19 November 2026', 'sub': 'Release Planned Thursday 19 November'}, ST('In Work', 'a', '5 of 7 Tasks Closed, Aircraft Grounded Since 14 November')],
         [MONO('WP-2026-047'), AC('G-ABCD', 'Piper PA-28 Series (Lycoming)'), {'text': 'Landing Light Replacement', 'sub': 'Bay 2, 3.0 Hours, With Engine Oil and Filter Change'}, {'text': '[Owner Name]', 'href': CO, 'sub': 'Agreed 12 November 2026'}, {'text': '19 November 2026', 'sub': 'Thursday, Deferred Defect Limit 3 December 2026'}, ST('Issued', 'o', '0 of 3 Tasks Closed, Issued 16 November 2026')],
         [MONO('WP-2026-048'), AC('G-EJKL', 'Cessna/Reims-Cessna 152/F152 Series (Lycoming)'), {'text': 'Annual Check, Headset Socket', 'sub': 'Annual Check and Right Headset Socket, Bay 1, 32.0 Hours, Before Airworthiness Review'}, {'text': 'Not Received', 'dot': 'a', 'href': CO, 'sub': 'Needed Before Issue'}, {'text': '1–4 December 2026', 'sub': 'Review Certificate Valid to 6 December 2026'}, ST('Draft', 'o', 'Not Issued')],
         [MONO('WP-2026-043'), AC('G-CDEF', 'Robin DR 400 series (Lycoming)'), {'text': '100-Hour Check, Spinner Replacement', 'sub': '100-Hour Check and Propeller Spinner Replacement, Bay 1, 18.0 Hours'}, {'text': '[Owner Name]', 'href': CO}, {'text': '2–4 November 2026', 'sub': 'In Records 5 November 2026'}, ST('Released', 'g', '12 of 12 Tasks Closed, 4 November 2026, Chris Moore, B1.2')]])),
    section('task-h', 'Tasks, WP-2026-046', table(
        [('Task', '', 'left'), ('Critical Task', '130px', 'left'), ('Performed By', '230px', 'left'), ('Independent Inspection', '260px', 'left'), ('Hours', '90px', 'right'), ('Status', '130px', 'left')],
        [[{'text': 'Gain Access, Cabin Floor and Tail Cone Panels', 'sub': 'Maintenance Manual Chapter 27, Revision [Revision]'}, 'No', {'text': '[Name], L2', 'sub': 'Supervised by Sam Patel, B1.2'}, 'Not Required', '2.0', ST('Closed', 'g', '16 November 2026')],
         [{'text': 'Remove Frayed Stabilator Trim Cable', 'sub': 'Defect Found 14 November, Trim Check'}, 'No', 'Sam Patel, B1.2', 'Not Required', '1.5', ST('Closed', 'g', '17 November 2026')],
         [{'text': 'Inspect Pulleys, Fairleads and Trim Drum', 'sub': 'Aft Pulley Worn, Replaced'}, 'No', 'Sam Patel, B1.2', 'Not Required', '1.5', ST('Closed', 'g', '17 November 2026')],
         [{'text': 'Replace Aft Trim Cable Pulley', 'sub': 'Part Received With CAA Form 1'}, 'Yes', 'Sam Patel, B1.2', {'text': 'With Rigging', 'sub': 'Whole Trim System Inspected Once'}, '2.0', ST('Closed', 'g', '18 November 2026')],
         [{'text': 'Install New Stabilator Trim Cable', 'sub': 'Part Received With CAA Form 1'}, 'Yes', 'Sam Patel, B1.2', {'text': 'With Rigging', 'sub': 'Whole Trim System Inspected Once'}, '4.0', ST('Closed', 'g', '18 November 2026')],
         [{'text': 'Rig Cable Tension, Stops and Travel', 'sub': 'Handed Over 18 November, 16:30'}, 'Yes', {'text': '[Contract Engineer], B1.2', 'sub': 'Contracted'}, {'text': 'Chris Moore, B1.2', 'dot': 'a', 'sub': 'Planned Thursday 19 November, 11:00'}, '3.0', ST('Open', 'o')],
         [{'text': 'Refit Panels, General Verification and Functional Check', 'sub': 'Tools, Loose Items and Panels'}, 'No', 'Sam Patel, B1.2', 'Not Required', '2.0', ST('Open', 'o')]]),
        intro='5 of 7 Closed, 16.0 Hours Plus 1.0 Hour Independent Inspection', right=btn('Print Work Cards')),
    section('ii-h', 'Independent Inspection, Stabilator Trim System', checklist([
        ('o', 'Assembly and Locking', 'Turnbuckles Locked, Pulley Guards and Cable Retainers Fitted'),
        ('o', 'Cable Tension', 'To Maintenance Manual, Corrected for Hangar Temperature'),
        ('o', 'Stops and Travel', 'Full and Free Movement, Primary Stops Contacted Before Secondary'),
        ('o', 'Correct Sense of Movement', 'Trim Wheel, Indicator and Stabilator Tab Agree'),
    ]), intro='Critical Task, ML.A.402: Inspected by a Second Qualified Person Not Involved in the Work, 0 of 4 Complete'),
    section('cs-h', 'Certifying Staff', table(
        [('Name', '200px', 'left'), ('Licence', '160px', 'left'), ('Role', '', 'left'), ('Work Packages', '260px', 'left'), ('Status', '170px', 'left')],
        [['Sam Patel', {'text': 'Part-66 B1.2', 'sub': 'UK.66.[Number]'}, {'text': 'Performs and Releases', 'sub': 'Recurrent Training Due 6 December 2026'}, {'text': 'WP-2026-046, WP-2026-047', 'href': 'Authorisations.dc.html'}, ST('Current', 'g')],
         ['Chris Moore', {'text': 'Part-66 B1.2', 'sub': 'UK.66.[Number]'}, {'text': 'Independent Inspection, Releases WP-2026-048', 'sub': 'Not Involved in WP-2026-046 Work'}, {'text': 'WP-2026-046, WP-2026-048', 'href': 'Authorisations.dc.html'}, ST('Current', 'g')],
         ['[Contract Engineer]', {'text': 'Part-66 B1.2', 'sub': 'UK.66.[Number]'}, {'text': 'Performs Rigging, Does Not Release', 'sub': 'Contracted, Authorised 11 November 2026'}, 'WP-2026-046', ST('Current', 'g')],
         ['[Name]', {'text': 'Part-66 L2', 'sub': 'UK.66.[Number]'}, {'text': 'Supervised Work Only', 'sub': 'Authorisation Lapsed, Under 6 Months in 2 Years'}, 'WP-2026-046', 'Not Certifying']], minw=1000),
        intro='145.A.35: Licence Valid, 6 Months of Experience in 2 Years, Recurrent Training in 2 Years'),
    section('crs-h', 'Release to Service, WP-2026-046', checklist([
        ('g', 'Certifying Staff Authorisation Current', 'Sam Patel, B1.2'),
        ('o', 'Every Task Signed', '5 of 7'),
        ('o', 'Independent Inspection Done', 'Chris Moore, Planned Thursday 19 November'),
        ('o', 'General Verification', 'No Tools or Loose Items Left, Panels Refitted'),
        ('o', 'Defect Closed', 'Stabilator Trim Cable Frayed at Pulley'),
    ]), intro='1 of 5 Complete, Certificate in Records Within 30 Days of Completion',
        right=btn('Release to Service', href='ReleaseToService.dc.html')),
])

# Manhours and Capacity: Manhour Plan (145.A.30(d) and its AMC, CAO.A.035(d))
page('Plan.dc.html', 'Manhour Plan', 'plan', 1860, [
    header('Planning', 'Manhour Plan', '', [btn('Record an Absence'), btn('Review the Plan', primary=True)],
           tabs=('planning', 'plan'), trail=PLANTRAIL + 'Manhour Plan'),
    callout('December 2026 Certifying Staff Hours 34% Short Before Contracted Cover, Reported 16 November', 'a'),
    strip([('2 September 2026', 'Last Reviewed'), ('2 December 2026', 'Next Review Due'), ('3 Months', 'Review Interval')]),
    section('nov-h', 'November 2026', table(
        [('Function', '260px', 'left'), ('Staff', '', 'left'), ('Hours Needed', '140px', 'right'), ('Hours Available', '150px', 'right'), ('Shortfall', '120px', 'right'), ('Status', '150px', 'left')],
        [[{'text': 'Planning', 'sub': 'Work Packages and Manhour Plan'}, '[Maintenance Manager]', '24.0', '32.0', 'None', ST('Within Plan', 'g')],
         [{'text': 'Certifying Staff', 'sub': 'Perform, Supervise and Release'}, {'text': 'Chris Moore, Sam Patel, [Contract Engineer]', 'sub': '312.0 Employed, 48.0 Contracted'}, '300.0', '360.0', 'None', ST('Within Plan', 'g')],
         [{'text': 'Maintenance Support', 'sub': 'Supervised Work'}, '[Name], L2', '90.0', '96.0', 'None', ST('Within Plan', 'g')],
         [{'text': 'Independent Inspection', 'sub': 'Critical Tasks'}, 'Chris Moore, Sam Patel', '6.0', {'text': 'Within Certifying Staff', 'sub': 'Never the Person Who Did the Work'}, 'None', ST('Within Plan', 'g')],
         [{'text': 'Continuing Airworthiness Management', 'sub': 'Records, Directives, Programmes'}, 'Lucy Grant', '110.0', '127.5', 'None', ST('Within Plan', 'g')],
         [{'text': 'Airworthiness Reviews', 'sub': 'G-CDEF Done 11 November'}, 'Lucy Grant, [Name]', '16.0', '24.0', 'None', ST('Within Plan', 'g')],
         [{'text': 'Compliance Monitoring', 'sub': 'Audit Plan and Findings'}, '[Compliance Monitoring Manager]', '16.0', '16.0', 'None', ST('Within Plan', 'g')]]),
        intro='145.A.30(d): Enough Staff to Plan, Perform, Supervise, Inspect and Monitor the Work, 21 Working Days, 8 Hours a Day'),
    section('ahead-h', 'Months Ahead', table(
        [('Month', '170px', 'left'), ('Function', '', 'left'), ('Hours Needed', '140px', 'right'), ('Employed', '120px', 'right'), ('Contracted', '120px', 'right'), ('Shortfall', '200px', 'right'), ('Status', '150px', 'left')],
        [['December 2026', {'text': 'Certifying Staff', 'sub': 'Sam Patel Holiday 7–18 December, Chris Moore Holiday 21–31 December'}, '290.0', '192.0', '88.0', {'text': '34% Before Cover', 'dot': 'a', 'sub': '3% After Contracted Cover'}, ST('Reported', 'a', '16 November 2026')],
         ['December 2026', 'Maintenance Support', '72.0', '72.0', '0.0', 'None', ST('Within Plan', 'g')],
         ['December 2026', {'text': 'Airworthiness Reviews', 'sub': 'G-EJKL, Review Certificate Valid to 6 December 2026'}, '16.0', '24.0', '0.0', 'None', ST('Within Plan', 'g')],
         ['January 2027', 'Certifying Staff', '260.0', '320.0', '0.0', 'None', ST('Within Plan', 'g')],
         ['February 2027', 'Certifying Staff', '260.0', '320.0', '0.0', 'None', ST('Within Plan', 'g')]]),
        intro='Report a Shortfall Over 25% in a Calendar Month for Any Function to the Compliance Monitoring Manager and Accountable Manager'),
    section('rep-h', 'Shortfall Reports', table(
        [('Month', '170px', 'left'), ('Function', '200px', 'left'), ('Shortfall', '120px', 'right'), ('Reported To', '', 'left'), ('Reported', '160px', 'left'), ('Action', '220px', 'left')],
        [['December 2026', 'Certifying Staff', '34%', 'Compliance Monitoring Manager, Accountable Manager', {'text': '16 November 2026', 'sub': 'By [Maintenance Manager]'}, {'text': 'Contracted Cover Booked', 'sub': '[Contract Engineer], 88.0 Hours, Work Reassessed, G-FMNO 50-Hour Check to Week of 7 December'}]], minw=1000)),
    section('emp-h', 'Employed and Contracted Staff', table(
        [('Week', '200px', 'left'), ('Area and Shift', '', 'left'), ('Lowest Day', '220px', 'left'), ('Employed', '110px', 'right'), ('Contracted', '110px', 'right'), ('Employed Share', '140px', 'right'), ('Status', '150px', 'left')],
        [['16 November 2026', 'Hangar, Day Shift', 'Thursday 19 November', {'text': '2', 'sub': 'Chris Moore, Sam Patel'}, {'text': '1', 'sub': '[Contract Engineer]'}, '67%', ST('Within Rule', 'g')],
         ['7 December 2026', 'Hangar, Day Shift', 'Thursday 10 December', {'text': '1', 'sub': 'Chris Moore'}, {'text': '1', 'sub': '[Contract Engineer]'}, '50%', ST('At Limit', 'a', 'Any More Contracted Cover Needs Civil Aviation Authority Permission')],
         ['21 December 2026', 'Hangar, Day Shift', 'Thursday 24 December', {'text': '1', 'sub': 'Sam Patel'}, {'text': '1', 'sub': '[Contract Engineer]'}, '50%', ST('At Limit', 'a', 'Any More Contracted Cover Needs Civil Aviation Authority Permission')],
         ['28 December 2026', 'Hangar, Day Shift', 'Wednesday 30 December', {'text': '2', 'sub': 'Sam Patel, [Name]'}, {'text': '1', 'sub': '[Contract Engineer]'}, '67%', ST('Within Rule', 'g')]]),
        intro='At Least Half of the Staff Doing Maintenance on Each Shift Employed, Not Contracted'),
])

# Manhours and Capacity: Load and Capacity (145.A.47 production planning, 145.A.48(a))
page('Load.dc.html', 'Load and Capacity', 'load', 1100, [
    header('Planning', 'Load and Capacity', '', [btn('Build a Work Package', href='WorkPackages.dc.html')],
           tabs=('planning', 'load'), trail=PLANTRAIL + 'Load and Capacity'),
    section('wk-h', 'Weeks Ahead', table(
        [('Week', '190px', 'left'), ('Work Planned', '', 'left'), ('Package Hours', '140px', 'right'), ('Other Hours', '130px', 'right'), ('Hours Available', '150px', 'right'), ('Load', '90px', 'right'), ('Status', '190px', 'left')],
        [['16 November 2026', {'text': 'WP-2026-046, WP-2026-047', 'href': 'WorkPackages.dc.html'}, '20.0', '50.0', {'text': '122.5', 'sub': 'Chris Moore, Sam Patel, [Name], [Contract Engineer]'}, '57%', ST('Within Margin', 'g')],
         ['23 November 2026', {'text': 'None Planned', 'sub': 'G-BXYZ Cabin Entry Step Deferred to 27 November, Not Planned'}, '0.0', '50.0', '120.0', '42%', ST('Within Margin', 'g')],
         ['30 November 2026', {'text': 'WP-2026-048, G-ABCD 50-Hour Check', 'sub': 'G-ABCD Check Not Yet in a Work Package'}, '38.0', '50.0', {'text': '112.0', 'sub': 'Sam Patel Recurrent Training 3 December'}, '79%', ST('Within Margin', 'g')],
         ['7 December 2026', {'text': 'G-FMNO 50-Hour Check', 'sub': 'Work Order Agreed 16 November'}, '6.0', '50.0', {'text': '80.0', 'sub': 'Sam Patel Holiday'}, '70%', ST('Within Margin', 'g')],
         ['14 December 2026', {'text': 'G-BXYZ 100-Hour or Annual Check', 'sub': 'Due in 41.0 Hours'}, '28.0', '50.0', {'text': '88.0', 'sub': 'Sam Patel Holiday, [Contract Engineer] 24.0 Hours'}, '89%', ST('Over Margin', 'a', 'Move Work or Book More Cover')],
         ['21 December 2026', {'text': 'None Planned', 'sub': 'Christmas Day Friday 25 December'}, '0.0', '40.0', {'text': '72.0', 'sub': 'Chris Moore Holiday'}, '56%', ST('Within Margin', 'g')]]),
        intro='Efficiency Margin 85%, Other Hours: Goods In, Stores, Tools, Training and Unscheduled Defects'),
    section('np-h', 'Due and Not Yet Planned', table(
        [REG, ('Work', '', 'left'), ('Due', '240px', 'left'), ('Estimate', '120px', 'right'), ('Planned Week', '200px', 'left')],
        [[AC('G-BXYZ'), {'text': 'Cabin Entry Step Loose', 'sub': 'Deferred Defect'}, {'text': '27 November 2026', 'dot': 'a', 'sub': '9 Days Left'}, '1.5 Hours', {'text': 'Not Planned', 'dot': 'a'}],
         [AC('G-ABCD'), '50-Hour Check', {'text': '12.4 Hours', 'sub': 'About 3 Weeks at Current Use'}, '6.0 Hours', '30 November 2026'],
         [AC('G-FMNO'), {'text': '50-Hour Check', 'sub': 'Work Order Agreed 16 November'}, 'Owner Request', '6.0 Hours', '7 December 2026'],
         [AC('G-BXYZ'), '100-Hour or Annual Check', '41.0 Hours', '28.0 Hours', '14 December 2026'],
         [AC('G-CDEF'), {'text': 'Engine Overhaul', 'sub': 'To [Engine Overhaul Organisation]'}, '220 Hours', '12.0 Hours', 'Not Yet Due']]),
        intro='From Defects, Contracts and Maintenance Programmes'),
])

# Manhours and Capacity: Staff Roster (145.A.47(b) fatigue, 145.A.47(c) handover)
DAY = '08:00–16:30'
OFF = 'Off'
page('Roster.dc.html', 'Staff Roster', 'roster', 1620, [
    header('Planning', 'Staff Roster', '', [btn('Print Roster'), btn('Publish Week of 7 December', primary=True)],
           tabs=('planning', 'roster'), trail=PLANTRAIL + 'Staff Roster'),
    section('wk-h', 'Week of 16 November 2026', table(
        [('Name', '200px', 'left'), ('Monday 16', '130px', 'left'), ('Tuesday 17', '130px', 'left'), ('Wednesday 18', '130px', 'left'), ('Thursday 19', '130px', 'left'), ('Friday 20', '130px', 'left'), ('Hours', '90px', 'right')],
        [[{'text': 'Chris Moore', 'sub': 'B1.2, Employed'}, DAY, DAY, DAY, {'text': DAY, 'sub': 'Independent Inspection, WP-2026-046'}, DAY, '40.0'],
         [{'text': 'Sam Patel', 'sub': 'B1.2, Employed'}, DAY, DAY, DAY, {'text': '08:00–19:00', 'dot': 'a', 'sub': 'Extended, WP-2026-046 Release and WP-2026-047'}, DAY, '42.5'],
         [{'text': '[Name]', 'sub': 'L2, Contracted, Supervised Work'}, DAY, DAY, DAY, OFF, OFF, '24.0'],
         [{'text': '[Contract Engineer]', 'sub': 'B1.2, Contracted'}, OFF, OFF, DAY, {'text': DAY, 'sub': 'Rigging, WP-2026-046'}, OFF, '16.0'],
         [{'text': 'Lucy Grant', 'sub': 'Continuing Airworthiness, Employed'}, '09:00–17:00', '09:00–17:00', '09:00–17:00', '09:00–17:00', OFF, '30.0'],
         [{'text': '[Name]', 'sub': 'Airworthiness Review Staff, Employed'}, OFF, '09:00–17:00', OFF, OFF, OFF, '7.5']]),
        intro='Published 2 November 2026, Shift Hours Exclude a 30-Minute Break'),
    section('fat-h', 'Fatigue Checks', table(
        [('Name', '200px', 'left'), ('Check', '220px', 'left'), ('Planned', '', 'left'), ('Limit', '220px', 'left'), ('Status', '210px', 'left')],
        [['Sam Patel', {'text': 'Shift Length', 'sub': 'Thursday 19 November'}, '10.5 Hours', '10 Hours', ST('Risk Assessment Needed', 'a', 'Extra Supervision or Non-Critical Tasks After 16:30')],
         ['Sam Patel', {'text': 'Rest Between Shifts', 'sub': 'Thursday 19 to Friday 20 November'}, '13 Hours', 'At Least 11 Hours', ST('Within Limit', 'g')],
         ['Chris Moore', {'text': 'Critical Task Timing', 'sub': 'Independent Inspection, WP-2026-046'}, 'Thursday 19 November, 11:00', 'First Half of Shift', ST('Within Limit', 'g')],
         ['[Contract Engineer]', {'text': 'Hours Including Other Work', 'sub': 'Declared 13 November'}, '40.0 Hours', '48 Hours a Week', ST('Within Limit', 'g')]], minw=1000),
        intro='145.A.47: Plan Tasks and Shifts Around Human Performance Limits, Including Fatigue'),
    section('ho-h', 'Handovers', table(
        [('Handed Over', '170px', 'left'), ('Work Package', '140px', 'left'), ('From', '160px', 'left'), ('To', '180px', 'left'), ('Stage Reached', '', 'left'), ('Status', '210px', 'left')],
        [[{'text': '18 November, 16:30', 'sub': 'Wednesday'}, {'text': 'WP-2026-046', 'mono': True, 'href': 'WorkPackages.dc.html'}, 'Sam Patel', '[Contract Engineer]', {'text': '5 of 7 Tasks Closed, Rigging Not Started', 'sub': 'New Cable and Aft Pulley Fitted, Tension and Stops to Rig, Turnbuckles Not Locked'}, ST('Awaiting Acknowledgement', 'a', 'Planned Overlap 16:15–16:30')],
         [{'text': '16 November, 16:30', 'sub': 'Monday'}, {'text': 'WP-2026-046', 'mono': True, 'href': 'WorkPackages.dc.html'}, '[Name]', 'Sam Patel', {'text': 'Access Task Closed', 'sub': 'Cabin Floor and Tail Cone Panels Removed, Fasteners Bagged and Labelled'}, ST('Acknowledged', 'g', 'Sam Patel, 16:35')]], minw=1100),
        intro='Open Tasks, Stage Reached, Parts and Warnings, Acknowledged by the Incoming Person'),
    section('pub-h', 'Published Rosters', table(
        [('Week', '220px', 'left'), ('Published', '', 'left'), ('Changes Since', '200px', 'left'), ('Status', '200px', 'left')],
        [['23 November 2026', '9 November 2026', 'None', ST('Published', 'g')],
         ['30 November 2026', '16 November 2026', {'text': '1', 'sub': 'Sam Patel Recurrent Training 3 December'}, ST('Published', 'g')],
         ['7 December 2026', 'Due 23 November 2026', '—', ST('Not Published', 'a', '5 Days Left')]], minw=860),
        intro='Published 2 Weeks Ahead'),
])

# Settings, Planning: limits used by the Manhour Plan, Load and Capacity and Staff Roster
page('PlanSettings.dc.html', 'Planning Settings', 'plansettings', 2550, [
    header('Settings', 'Planning Settings', '', [btn('Edit Settings', primary=True)],
           tabs=('settings', 'plansettings'), trail='Settings=Settings.dc.html|Planning'),
    section('mp-h', 'Manhour Plan', table(
        [('Setting', '300px', 'left'), ('Value', '', 'left'), ('Source', '260px', 'left')],
        [['Plan Review', 'At Least Every 3 Months', 'AMC 145.A.30(d)'],
         ['Shortfall to Report', 'Over 25% of Available Hours in a Calendar Month, Any Function', 'AMC 145.A.30(d)'],
         ['Report To', 'Compliance Monitoring Manager, Accountable Manager', 'AMC 145.A.30(d)'],
         ['Employed Staff on Each Shift', {'text': 'At Least Half', 'sub': 'More Contracted Cover Only With Civil Aviation Authority Permission'}, 'AMC 145.A.30(d)'],
         ['Working Day', '8 Hours, Excluding a 30-Minute Break', 'Organisation'],
         ['Efficiency Margin', {'text': '85%', 'sub': 'Load at or Over This Share of Available Hours Shows Amber'}, 'Organisation']], minw=900)),
    section('min-h', 'Minimum Staff', table(
        [('Function', '300px', 'left'), ('Minimum', '120px', 'right'), ('Normal', '120px', 'right'), ('Applies On', '', 'left')],
        [['Certifying Staff', '1', '2', 'Days the Hangar Is Open'],
         ['Maintenance Support', '0', '1', 'Days the Hangar Is Open'],
         ['Continuing Airworthiness Management', '1', '1', 'Office Days'],
         ['Compliance Monitoring', '1', '1', '2 Days a Month']], minw=860)),
    section('sh-h', 'Shift Patterns', table(
        [('Shift', '260px', 'left'), ('Days', '', 'left'), ('Hours', '200px', 'left'), ('Staff', '200px', 'left')],
        [['Hangar, Day Shift', 'Monday to Friday', '08:00–16:30, 8 Hours', '4'],
         ['Office', 'Monday to Thursday', '09:00–17:00, 7.5 Hours', '2'],
         ['Saturday Overtime', {'text': 'Booked When the Load Needs It', 'sub': 'Counts Towards Fatigue Limits'}, '08:00–12:00, 4 Hours', 'By Agreement']], minw=900)),
    section('fat-h', 'Fatigue and Handover', table(
        [('Setting', '300px', 'left'), ('Value', '', 'left'), ('Source', '260px', 'left')],
        [['Longest Shift', {'text': '10 Hours', 'sub': 'Longer Only After a Risk Assessment'}, 'Organisation, 145.A.47'],
         ['Rest Between Shifts', 'At Least 11 Hours', 'Organisation, 145.A.47'],
         ['Weekly Hours, Including Other Work', '48 Hours', 'Organisation, 145.A.47'],
         ['Critical Tasks', 'First Half of the Shift', 'Organisation, 145.A.47'],
         ['Roster Published', '2 Weeks Ahead', 'Organisation, 145.A.47'],
         ['Handover', {'text': 'Written, Acknowledged by the Incoming Person', 'sub': 'Planned Overlap 15 Minutes'}, 'Organisation, 145.A.47']], minw=900)),
    section('abs-h', 'Absence Types', table(
        [('Absence', '260px', 'left'), ('Counts Against Leave', '200px', 'left'), ('Linked To', '', 'left')],
        [['Holiday', 'Yes', 'Annual Leave Allowance, 25 Days'],
         ['Sickness', 'No', '—'],
         ['Training', 'No', 'Recurrent Training'],
         ['Jury Service', 'No', '—']], minw=800)),
    section('cal-h', 'Bank Holidays', table(
        [('Holiday', '', 'left'), ('Date', '300px', 'left')],
        [['Christmas Day', 'Friday 25 December 2026'],
         ['Boxing Day, Substitute Day', 'Monday 28 December 2026'],
         ['New Year’s Day', 'Friday 1 January 2027']], minw=700)),
    section('his-h', 'Change History', table(
        [('Date', '200px', 'left'), ('Change', '', 'left'), ('By', '260px', 'left')],
        [['2 September 2026', 'Manhour Plan Reviewed, No Change', '[Maintenance Manager]'],
         ['2 June 2026', 'Longest Shift Lowered From 12 to 10 Hours', '[Maintenance Manager]'],
         ['4 January 2026', 'Efficiency Margin Set to 85%', '[Maintenance Manager]']], minw=860)),
])
