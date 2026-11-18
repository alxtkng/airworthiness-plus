from gen import *

CR = 'Continuing Airworthiness'
AC = lambda r, sub=None: {'text': r, 'href': 'Aircraft.dc.html' if r == 'G-ABCD' else None}

# 1. Defects and Deferrals (CAME 1.1b, 1.8; MOE 2.15)
page('Defects.dc.html', 'Defects and Deferrals', 'defects', 1500, [
    header(CR, 'Defects',
           'Every open defect across the fleet, who decided it could wait, and how long it can wait. Light aircraft have no minimum equipment list, so deferral follows the Part-ML rules and the limits set by the organisation.',
           [btn('Record a Defect'), btn('Deferral Limits', href='Settings.dc.html')], tabs=('defects', 'defects'), trail='Continuing Airworthiness=Fleet.dc.html|Defects=Defects.dc.html|Open and Deferred'),
    strip([('4', 'open defects'), ('1', 'aircraft grounded'), ('0', 'past their limit'), ('2', 'already in a work package')]),
    section('open-h', 'Open Defects', table(
        [('Aircraft', '120px', 'left'), ('Defect', '', 'left'), ('Decision', '260px', 'left'), ('Limit', '190px', 'left'), ('Work Package', '170px', 'left')],
        [
            [AC('G-DGHI', 'Piper PA-28-181'), {'text': 'Stabilator trim cable frayed at the pulley', 'dot': 'r', 'sub': 'Found 14 November during the trim check'}, 'Cannot be deferred. Decided by Chris Moore, B1.', {'text': 'Grounded', 'sub': 'Since 14 November 2026'}, {'text': 'WP-2026-046', 'href': 'WorkPackages.dc.html', 'sub': 'In work, 5 of 7 tasks closed'}],
            [AC('G-ABCD', 'Piper PA-28-140'), {'text': 'Left landing light inoperative', 'dot': 'a', 'sub': 'Placarded. Daylight flying only.'}, 'Deferred by the pilot-in-command on 3 November.', {'text': '3 December 2026', 'sub': '15 days left'}, {'text': 'WP-2026-047', 'href': 'WorkPackages.dc.html', 'sub': 'Issued for 19 November'}],
            [AC('G-BXYZ', 'Cessna 172S'), {'text': 'Cabin entry step loose', 'dot': 'a', 'sub': 'No effect on flight. Step not to be used.'}, 'Deferred by Sam Patel, B1, on 28 October.', {'text': '27 November 2026', 'sub': '9 days left'}, 'Not yet planned'],
            [AC('G-EJKL', 'Cessna 152'), {'text': 'Crackle on the right headset socket', 'dot': 'g', 'sub': 'Left socket working normally'}, 'Deferred by the pilot-in-command on 12 November.', {'text': '12 December 2026', 'sub': '24 days left'}, {'text': 'With the airworthiness review', 'sub': 'Visit planned for early December'}],
        ])),
    section('closed-h', 'Closed in the Last 30 Days', table(
        [('Aircraft', '120px', 'left'), ('Defect', '', 'left'), ('Fixed By', '260px', 'left'), ('Closed', '190px', 'left')],
        [[AC('G-ABCD'), {'text': 'Right main tyre worn to limit', 'dot': 'g'}, 'Pilot-owner maintenance, release signed by the pilot-owner', '22 October 2026'],
         [AC('G-CDEF', 'Robin DR400/180'), {'text': 'Propeller spinner crack', 'dot': 'g'}, 'Spinner replaced with the propeller removal, WP-2026-043', '4 November 2026']], minw=900)),
    foot(),
])

# 2. Maintenance Programmes (CAME 1.2, 1.2.8)
page('Programmes.dc.html', 'Maintenance Programmes', 'programmes', 2100, [
    header(CR, 'Maintenance Programmes',
           'One programme for each aircraft, built on the Minimum Inspection Programme or the manufacturer’s instructions. Every departure from the manufacturer is justified and a copy is sent to the owner.',
           [btn('Build a Programme', primary=True)], trail='Continuing Airworthiness=Fleet.dc.html|Maintenance Programmes'),
    section('list-h', 'Programmes', table(
        [('Aircraft', '120px', 'left'), ('Programme', '', 'left'), ('Based On', '230px', 'left'), ('Departures', '110px', 'right'), ('Annual Review Due', '200px', 'left')],
        [[AC('G-ABCD', 'Piper PA-28-140'), {'text': 'Owner declared, Issue 3', 'sub': 'Declared by [Owner Name]'}, 'Minimum Inspection Programme and manufacturer’s instructions', '0', {'text': '2 March 2027', 'dot': 'g'}],
         [AC('G-BXYZ', 'Cessna 172S'), {'text': 'Approved by the organisation, Issue 5', 'sub': 'Approved by [Your Name]'}, 'Manufacturer’s instructions', '0', {'text': '15 January 2027', 'dot': 'g', 'sub': 'Review opens 16 December'}],
         [AC('G-CDEF', 'Robin DR400/180'), {'text': 'Approved by the organisation, Issue 2'}, 'Manufacturer’s instructions', '0', {'text': '8 April 2027', 'dot': 'g'}],
         [AC('G-DGHI', 'Piper PA-28-181'), {'text': 'Approved by the organisation, Issue 4'}, 'Manufacturer’s instructions', '2', {'text': '4 March 2027', 'dot': 'g'}],
         [AC('G-EJKL', 'Cessna 152'), {'text': 'Owner declared, Issue 1'}, 'Minimum Inspection Programme', '0', {'text': 'With the airworthiness review', 'dot': 'g', 'sub': 'Owner managed aircraft'}],
         [AC('G-FMNO', 'Grob G 115'), {'text': 'Owner declared, Issue 2'}, 'Minimum Inspection Programme and manufacturer’s instructions', '0', {'text': '10 December 2026', 'dot': 'a', 'sub': 'Review open, 22 days left'}]]),
        intro='Minimum Inspection Programme: every 12 months or 100 hours, whichever comes first. Tolerance 1 month or 10 hours.'),
    section('dev-h', 'Departures From the Manufacturer’s Instructions, G-DGHI', table(
        [('Task', '200px', 'left'), ('Manufacturer Says', '200px', 'left'), ('Instead', '220px', 'left'), ('Justification and Compensating Measures', '', 'left'), ('Owner Copy', '140px', 'left')],
        [[{'text': 'Engine overhaul', 'sub': 'Lycoming O-360'}, '2,000 hours or 12 years', 'On condition, reviewed every 100 hours', 'Club aircraft flying about 300 hours a year, so calendar time is not the driver. Oil analysis every 50 hours, compression and borescope checks every 100 hours, trend reviewed at each 100-Hour Check.', {'text': 'Sent 4 March 2026', 'dot': 'g'}],
         [{'text': 'Vacuum pump replacement'}, '500 hours', 'On condition with a standby vacuum source fitted', 'Standby source gives redundancy for the attitude and heading instruments. Pump checked at each 50-Hour Check.', {'text': 'Sent 4 March 2026', 'dot': 'g'}]])),
    section('rev-h', 'Annual Review, G-FMNO', checklist([
        ('g', 'Results of the maintenance performed this year', 'Two defects in 12 months, neither a repeat. No change needed.'),
        ('g', 'Results of the last airworthiness review', 'Review on 27 April 2026 found the programme adequate.'),
        ('o', 'Revisions to the Minimum Inspection Programme or the manufacturer’s data', 'Manufacturer’s maintenance manual revision [Revision] to be checked.'),
        ('g', 'Changes in configuration, type and specifics of operation', 'No changes. Private flying only.'),
        ('o', 'Changes in the list of pilot-owners', 'Ask the owner to confirm. No change recorded since Issue 2.'),
        ('g', 'Mandatory requirements, directives, airworthiness limitations and the data sheet', 'Directive status checked 16 November 2026.'),
    ]), intro='4 of 6 inputs complete', right=btn('Complete the Review', primary=True)),
    foot(),
])

# 3. Airworthiness Directives (CAME 1.4; MOE 2.11)
page('Directives.dc.html', 'Airworthiness Directives', 'directives', 1900, [
    header(CR, 'Aircraft Configuration',
           'Directive status for every aircraft, engine and propeller, in the format CAP 2153 asks for. Directives that do not apply are listed with the reason, and superseded ones are left out.',
           [btn('Check for New Directives'), btn('Export Status Report', primary=True)], tabs=('config', 'directives'), trail='Continuing Airworthiness=Fleet.dc.html|Aircraft Configuration=Components.dc.html|Airworthiness Directives'),
    callout('G-CDEF’s propeller is away for overhaul. Applicability is checked again before it is refitted.', 'a'),
    section('src-h', 'Sources Checked', table(
        [('Source', '', 'left'), ('Covers', '', 'left'), ('Last Checked', '200px', 'left'), ('Next Check', '200px', 'left')],
        [[{'text': 'Civil Aviation Authority airworthiness directives', 'dot': 'g'}, 'United Kingdom directives for all aircraft', '16 November 2026', '30 November 2026'],
         [{'text': 'CAP 747 Mandatory Requirements for Airworthiness', 'dot': 'g'}, 'Generic requirements and concessions, Issue [Issue]', '2 November 2026', 'On each new amendment'],
         [{'text': 'Federal Aviation Administration, state of design', 'dot': 'g'}, 'Piper and Cessna airframes, Lycoming engines, Sensenich and McCauley propellers', 'Biweekly [Reference], 16 November 2026', '30 November 2026'],
         [{'text': 'European Union Aviation Safety Agency, state of design', 'dot': 'g'}, 'Robin and Grob airframes', '16 November 2026', '30 November 2026']], minw=960)),
    section('st-h', 'Status, G-ABCD', table(
        [('Directive and Revision', '170px', 'left'), ('Applies To', '130px', 'left'), ('Subject', '', 'left'), ('Method', '190px', 'left'), ('Done', '170px', 'left'), ('Next Due', '150px', 'left')],
        [[{'text': '[Reference] Revision 1', 'mono': True}, 'Engine', {'text': 'Vacuum pump drive coupling inspection', 'dot': 'g'}, 'Repetitive inspection', {'text': '6,300.0 hours', 'sub': '[Date]'}, {'text': '6,524.6 hours', 'sub': '112 hours left'}],
         [{'text': '[Reference]', 'mono': True}, 'Airframe', {'text': 'Exhaust muffler inspection for cracks', 'dot': 'g'}, 'Repetitive inspection', {'text': '6,224.6 hours', 'sub': '[Date]'}, {'text': '6,824.6 hours', 'sub': '412 hours left'}],
         [{'text': '[Reference]', 'mono': True}, 'Airframe', {'text': 'Stabilator attachment fitting inspection', 'dot': 'g'}, 'Repetitive inspection', {'text': '5,600.6 hours', 'sub': '[Date]'}, {'text': '7,600.6 hours', 'sub': '1,188 hours left'}],
         [{'text': '[Reference] Revision 2', 'mono': True}, 'Airframe', {'text': 'Fuel selector valve placard', 'dot': 'g', 'sub': 'Part A, placard, complete. Part B does not apply to this serial number.'}, 'One-off, replace placard', {'text': '6,105.2 hours', 'sub': 'March 2024'}, {'text': 'Complete'}],
         [{'text': '[Reference]', 'mono': True}, 'Propeller', {'text': 'Constant speed propeller hub inspection', 'dot': 'o', 'sub': 'Not applicable. A fixed pitch propeller is fitted.'}, 'Not applicable', '', '']])),
    foot(),
])

# 4. Modifications and Repairs (CAME 1.6-1.7; MOE 2.9, 2.12)
page('Mods.dc.html', 'Modifications and Repairs', 'mods', 1700, [
    header(CR, 'Aircraft Configuration',
           'Service bulletins and other optional information, with the owner’s decision on each, and every change or repair with the route by which it was approved.',
           [btn('Record a Change', primary=True)], tabs=('config', 'mods'), trail='Continuing Airworthiness=Fleet.dc.html|Aircraft Configuration=Components.dc.html|Modifications and Repairs'),
    section('sb-h', 'Service Bulletins and Owner Decisions', table(
        [('Aircraft', '120px', 'left'), ('Bulletin', '', 'left'), ('Owner Decision', '280px', 'left'), ('Recorded', '170px', 'left')],
        [[AC('G-ABCD'), {'text': 'Seat rail and stop inspection', 'sub': '[Reference], recommended'}, 'Include at every 50-Hour Check', {'text': '2 March 2026', 'dot': 'g'}],
         [AC('G-ABCD'), {'text': 'Engine valve guide inspection', 'sub': '[Reference], recommended'}, 'Include at every 100-Hour Check', {'text': '2 March 2026', 'dot': 'g'}],
         [AC('G-BXYZ'), {'text': 'Alternator mounting bracket inspection', 'sub': '[Reference], recommended'}, 'Awaiting the syndicate’s decision. Sent 10 November.', {'text': 'Reminder 24 November', 'dot': 'a'}],
         [AC('G-EJKL'), {'text': 'Seat belt replacement', 'sub': '[Reference], optional'}, 'Declined. Belts inspected on condition at each annual check.', {'text': '6 June 2026', 'dot': 'g'}]], minw=960)),
    section('ch-h', 'Changes and Repairs', table(
        [('Aircraft', '120px', 'left'), ('Change or Repair', '', 'left'), ('Approval Route', '230px', 'left'), ('Mass Effect', '130px', 'right'), ('Records', '190px', 'left')],
        [[AC('G-BXYZ'), {'text': 'Panel-mounted navigator fitted', 'sub': 'October 2026'}, 'Standard change, [Reference]', '+1.2 kilograms', {'text': 'Weight schedule update needed', 'dot': 'a', 'href': 'Weighing.dc.html'}],
         [AC('G-FMNO', 'Grob G 115'), {'text': 'Light-emitting diode landing light', 'sub': 'April 2026'}, 'Minor change, [Reference]', '−0.3 kilograms', {'text': 'Complete', 'dot': 'g'}],
         [AC('G-DGHI'), {'text': 'Left wingtip repair after hangar damage', 'sub': 'July 2025'}, 'Repair to the manufacturer’s structural repair data', '0 kilograms', {'text': 'Complete', 'dot': 'g'}],
         [AC('G-ABCD'), {'text': 'Mode S transponder with position output', 'sub': 'May 2022'}, 'Standard change, [Reference]', '+0.4 kilograms', {'text': 'Complete', 'dot': 'g'}],
         [AC('G-CDEF'), {'text': 'Propeller overhaul', 'sub': 'In progress, November 2026'}, 'Maintenance, not a change. Same part number.', '0 kilograms', {'text': 'Directive check before refit', 'dot': 'a', 'href': 'Directives.dc.html'}]])),
    foot(),
])

# 5. Repeat Defects (CAME 1.5, 1.10)
page('Reliability.dc.html', 'Repeat Defects', 'reliability', 1400, [
    header(CR, 'Defects',
           'Defects grouped by aircraft type and system over the last 12 months, so a weak spot in a maintenance programme shows up before it causes a problem. This is the light aircraft version of a reliability programme.',
           [btn('Export')], tabs=('defects', 'reliability'), trail='Continuing Airworthiness=Fleet.dc.html|Defects=Defects.dc.html|Repeat Defects'),
    section('rep-h', 'Repeats and Watch List', table(
        [('Aircraft Type', '170px', 'left'), ('System', '170px', 'left'), ('Defect', '', 'left'), ('In 12 Months', '120px', 'right'), ('Suggested Action', '300px', 'left')],
        [[{'text': 'Piper PA-28', 'sub': 'G-ABCD, G-DGHI'}, 'Chapter 33, lights', {'text': 'Landing light failure', 'dot': 'a', 'sub': 'G-ABCD November and February, G-DGHI June'}, '3', 'Repeat. Add a lamp holder and connector check to the 50-Hour Check at the next programme reviews.'],
         [{'text': 'Piper PA-28', 'sub': 'G-DGHI'}, 'Chapter 27, flight controls', {'text': 'Stabilator trim cable wear', 'dot': 'o', 'sub': 'G-DGHI November 2026 and December 2025'}, '2', 'Watching. One more makes it a repeat. Pulley alignment checked in WP-2026-046.'],
         [{'text': 'Cessna 152 and 172S', 'sub': 'G-EJKL, G-BXYZ'}, 'Chapter 23, communications', {'text': 'Headset socket faults', 'dot': 'o', 'sub': 'G-EJKL November, G-BXYZ May'}, '2', 'Watching.'],
         [{'text': 'Robin DR400/180', 'sub': 'G-CDEF'}, 'Chapter 61, propeller', {'text': 'Spinner cracking', 'dot': 'o', 'sub': 'G-CDEF November'}, '1', 'No action.']]),
        intro='A repeat is 3 or more of the same defect on one aircraft type in 12 months'),
    foot(),
])

# 6. Weight and Balance (CAME 1.12)
page('Weighing.dc.html', 'Weight and Balance', 'weighing', 1300, [
    header(CR, 'Aircraft Configuration',
           'The current weight and balance statement for each aircraft, and every change to the aircraft’s mass since it was last weighed. The statement given to the pilot always reflects the current configuration.',
           [btn('Upload a Weighing Report', primary=True)], tabs=('config', 'weighing'), trail='Continuing Airworthiness=Fleet.dc.html|Aircraft Configuration=Components.dc.html|Weight and Balance'),
    section('wb-h', 'Fleet', table(
        [('Aircraft', '120px', 'left'), ('Last Weighed', '160px', 'left'), ('Schedule', '150px', 'left'), ('Changes Since Weighing', '', 'left'), ('Net Change', '120px', 'right'), ('Status', '220px', 'left')],
        [[AC('G-BXYZ', 'Cessna 172S'), '[Date] 2019', 'Issue 6', 'Navigator fitted October 2026, not yet in the schedule', '+1.2 kilograms', {'text': 'Update the schedule', 'dot': 'a', 'sub': 'Raised by the standard change'}],
         [AC('G-DGHI', 'Piper PA-28-181'), '[Date] 2017', 'Issue 9', 'Three changes since weighing, all in the schedule', '+4.1 kilograms', {'text': 'Reweigh suggested', 'dot': 'a', 'sub': 'Above the organisation threshold of [Threshold]'}],
         [AC('G-ABCD', 'Piper PA-28-140'), 'May 2022', 'Issue 4', 'None', '0 kilograms', {'text': 'Up to date', 'dot': 'g'}],
         [AC('G-CDEF', 'Robin DR400/180'), '[Date] 2021', 'Issue 3', 'Propeller overhaul, same part number', '0 kilograms', {'text': 'Up to date', 'dot': 'g'}],
         [AC('G-EJKL', 'Cessna 152'), '[Date] 2020', 'Issue 2', 'None', '0 kilograms', {'text': 'Up to date', 'dot': 'g'}],
         [AC('G-FMNO', 'Grob G 115'), '[Date] 2018', 'Issue 5', 'Landing light change, in the schedule', '−0.3 kilograms', {'text': 'Up to date', 'dot': 'g'}]])),
    foot(),
])

# 7. Aircraft Transfers (CAME 1.3.3-1.3.4)
page('Transfers.dc.html', 'Aircraft Transfers', 'transfers', 1700, [
    header(CR, 'Aircraft',
           'Guided checklists for bringing an aircraft under management and for handing one over. Records always leave in an open format the next organisation can use.',
           [btn('Start a Transfer In', primary=True)], tabs=('aircraft', 'transfers'), trail='Continuing Airworthiness=Fleet.dc.html|Aircraft=Fleet.dc.html|Transfers'),
    section('in-h', 'Transfer In, G-HKLM, Piper PA-38-112', checklist([
        ('g', 'Aircraft type is within the scope of approval', 'Piper PA-38 group already on the approval.'),
        ('g', 'Owner contacted and management contract signed', 'Signed 9 November 2026 by [Owner Name].'),
        ('g', 'Import checks', 'Not applicable. The aircraft is already on the United Kingdom register.'),
        ('g', 'Plan agreed with the previous organisation for handing over the records', '[Previous Organisation], records sent 12 November.'),
        ('a', 'All records received and checked against the transfer checklist', '14 of 18 items received. Engine logbook volume 1 requested on 13 November.'),
        ('a', 'Full review of the continuing airworthiness records', 'In progress, Lucy Grant.'),
        ('o', 'Records entered into Airworthiness+', 'Hours, directives, components and life limits.'),
        ('o', 'Maintenance programme set up', 'Owner to declare a programme, or the organisation to approve one.'),
        ('o', 'Bridging check decided', 'Planned with the next 100-Hour Check if the programme changes.'),
        ('o', 'Aircraft added to the scope of work in the exposition', 'Updated automatically when the transfer is completed.'),
    ]), intro='Started 9 November 2026, 4 of 10 steps complete'),
    section('out-h', 'Transfer Out and Record Export',
            '<p style="margin: 0; font-size: 14px; line-height: 20px; color: {{t.body}}">No aircraft are leaving at the moment.</p>\n' +
            '<div style="display: flex; flex-wrap: wrap; gap: 8px">' + btn('Export G-ABCD Records') + btn('Export All Aircraft') + '</div>\n'),
    foot('Example data. G-HKLM and names in square brackets are placeholders.'),
])
print('ok')
