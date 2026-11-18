from gen import *

# Continuing Airworthiness pages. Copy is terse Title Case labels: no sentences, no full stops.
CR = 'Continuing Airworthiness'
AC = lambda r, sub=None: {'text': r, 'href': 'Aircraft.dc.html' if r == 'G-ABCD' else None}
WP = lambda r, sub=None: {'text': r, 'href': 'WorkPackages.dc.html', 'sub': sub}

# Defects (CAME 1.1b, 1.8; MOE 2.15)
page('Defects.dc.html', 'Defects', 'defects', 1300, [
    header(CR, 'Open and Deferred Defects', '',
           [btn('Record a Defect'), btn('Deferral Limits', href='Settings.dc.html')], tabs=('defects', 'defects'), trail='Continuing Airworthiness=Fleet.dc.html|Defects=Defects.dc.html|Open and Deferred'),
    section('open-h', 'Open Defects', table(
        [('Aircraft Registration', '170px', 'left'), ('Defect', '', 'left'), ('Decision', '260px', 'left'), ('Limit', '190px', 'left'), ('Work Package', '170px', 'left')],
        [
            [AC('G-DGHI'), {'text': 'Stabilator Trim Cable Frayed at Pulley', 'dot': 'r', 'sub': 'Found 14 November, Trim Check'}, {'text': 'Not Deferrable', 'sub': 'Chris Moore, B1'}, {'text': 'Grounded', 'sub': 'Since 14 November 2026'}, WP('WP-2026-046', '5 of 7 Tasks Closed')],
            [AC('G-ABCD'), {'text': 'Left Landing Light Inoperative', 'dot': 'a', 'sub': 'Placarded, Daylight Only'}, {'text': 'Deferred', 'sub': 'Pilot-in-Command, 3 November'}, {'text': '3 December 2026', 'sub': '15 Days Left'}, WP('WP-2026-047', 'Issued for 19 November')],
            [AC('G-BXYZ'), {'text': 'Cabin Entry Step Loose', 'dot': 'a', 'sub': 'No Effect on Flight, Step Out of Use'}, {'text': 'Deferred', 'sub': 'Sam Patel, B1, 28 October'}, {'text': '27 November 2026', 'sub': '9 Days Left'}, 'Not Planned'],
            [AC('G-EJKL'), {'text': 'Right Headset Socket Crackle', 'sub': 'Left Socket Serviceable'}, {'text': 'Deferred', 'sub': 'Pilot-in-Command, 12 November'}, {'text': '12 December 2026', 'sub': '24 Days Left'}, {'text': 'With Airworthiness Review', 'sub': 'Physical Survey 19 November'}],
        ])),
    section('closed-h', 'Closed, Last 30 Days', table(
        [('Aircraft Registration', '170px', 'left'), ('Defect', '', 'left'), ('Rectification', '260px', 'left'), ('Closed', '190px', 'left')],
        [[AC('G-ABCD'), 'Right Main Tyre Worn to Limit', {'text': 'Tyre Replaced', 'sub': 'Pilot-Owner Maintenance'}, '22 October 2026'],
         [AC('G-CDEF'), 'Propeller Spinner Crack', {'text': 'Spinner Replaced', 'sub': 'WP-2026-043'}, '4 November 2026']], minw=900)),
])

# Maintenance Programmes (CAME 1.2, 1.2.8)
page('Programmes.dc.html', 'Maintenance Programmes', 'programmes', 1800, [
    header(CR, 'Maintenance Programmes', '',
           [btn('Build a Programme', primary=True)], trail='Continuing Airworthiness=Fleet.dc.html|Maintenance Programmes'),
    section('list-h', 'Programmes', table(
        [('Aircraft Registration', '170px', 'left'), ('Programme', '', 'left'), ('Based On', '230px', 'left'), ('Departures', '110px', 'right'), ('Annual Review Due', '200px', 'left')],
        [[AC('G-ABCD'), {'text': 'Owner Declared, Issue 3', 'sub': '[Owner Name]'}, 'Minimum Inspection Programme and Manufacturer’s Instructions', '0', '2 March 2027'],
         [AC('G-BXYZ'), {'text': 'Organisation Approved, Issue 5', 'sub': '[Your Name]'}, 'Manufacturer’s Instructions', '0', {'text': '15 January 2027', 'sub': 'Opens 16 December'}],
         [AC('G-CDEF'), 'Organisation Approved, Issue 2', 'Manufacturer’s Instructions', '0', '8 April 2027'],
         [AC('G-DGHI'), 'Organisation Approved, Issue 4', 'Manufacturer’s Instructions', '2', '4 March 2027'],
         [AC('G-EJKL'), 'Owner Declared, Issue 1', 'Minimum Inspection Programme', '0', {'text': 'With Airworthiness Review', 'sub': 'Owner Managed'}],
         [AC('G-FMNO'), 'Owner Declared, Issue 2', 'Minimum Inspection Programme and Manufacturer’s Instructions', '0', {'text': '10 December 2026', 'dot': 'a', 'sub': 'Open, 22 Days Left'}]]),
        intro='Minimum Inspection Programme: Annual or 100 Hours, Whichever First, Tolerance 1 Month or 10 Hours'),
    section('dev-h', 'Departures From Manufacturer’s Instructions, G-DGHI', table(
        [('Task', '200px', 'left'), ('Manufacturer', '180px', 'left'), ('Programme', '220px', 'left'), ('Compensating Measures', '', 'left'), ('Owner Copy', '140px', 'left')],
        [[{'text': 'Engine Overhaul', 'sub': 'Lycoming O-360'}, '2,000 Hours or 12 Years', 'On Condition, Reviewed Every 100 Hours', {'text': 'Oil Analysis Every 50 Hours, Compression and Borescope Every 100 Hours', 'sub': 'Club Use, About 300 Hours a Year'}, 'Sent 4 March 2026'],
         ['Vacuum Pump Replacement', '500 Hours', 'On Condition', {'text': 'Standby Vacuum Source Fitted', 'sub': 'Pump Checked Every 50 Hours'}, 'Sent 4 March 2026']])),
    section('rev-h', 'Annual Review, G-FMNO', checklist([
        ('g', 'Maintenance Results This Year', '2 Defects, No Repeats'),
        ('g', 'Last Airworthiness Review', '27 April 2026, Programme Adequate'),
        ('o', 'Minimum Inspection Programme and Manufacturer’s Revisions', 'Maintenance Manual Revision [Revision] to Check'),
        ('g', 'Configuration, Type and Operation', 'No Change, Private Flying'),
        ('o', 'Pilot-Owners', 'Awaiting Owner Confirmation'),
        ('g', 'Directives, Airworthiness Limitations and Data Sheet', 'Checked 16 November 2026'),
    ]), intro='4 of 6 Complete', right=btn('Complete the Review', primary=True)),
])

# Airworthiness Directives (CAME 1.4; MOE 2.11)
page('Directives.dc.html', 'Airworthiness Directives', 'directives', 1600, [
    header(CR, 'Airworthiness Directives', '',
           [btn('Check for New Directives'), btn('Export Status Report', primary=True)], tabs=('config', 'directives'), trail='Continuing Airworthiness=Fleet.dc.html|Aircraft Configuration=Components.dc.html|Airworthiness Directives'),
    callout('G-CDEF Propeller at Overhaul, Applicability Check Before Refit', 'a'),
    section('src-h', 'Sources', table(
        [('Source', '', 'left'), ('Covers', '', 'left'), ('Last Checked', '200px', 'left'), ('Next Check', '200px', 'left')],
        [['Civil Aviation Authority', 'United Kingdom Directives, All Aircraft', '16 November 2026', '30 November 2026'],
         ['CAP 747 Mandatory Requirements for Airworthiness', {'text': 'Generic Requirements and Concessions', 'sub': 'Issue [Issue]'}, '2 November 2026', 'Each Amendment'],
         [{'text': 'Federal Aviation Administration', 'sub': 'State of Design'}, 'Piper and Cessna Airframes, Lycoming Engines, Sensenich and McCauley Propellers', {'text': '16 November 2026', 'sub': 'Biweekly [Reference]'}, '30 November 2026'],
         [{'text': 'European Union Aviation Safety Agency', 'sub': 'State of Design'}, 'Robin and Grob Airframes', '16 November 2026', '30 November 2026']], minw=960)),
    section('st-h', 'Status, G-ABCD', table(
        [('Directive', '170px', 'left'), ('Applies To', '130px', 'left'), ('Subject', '', 'left'), ('Method', '190px', 'left'), ('Done', '170px', 'left'), ('Next Due', '150px', 'left')],
        [[{'text': '[Reference] Revision 1', 'mono': True}, 'Engine', 'Vacuum Pump Drive Coupling Inspection', 'Repetitive Inspection', {'text': '6,300.0 Hours', 'sub': '[Date]'}, {'text': '6,524.6 Hours', 'sub': '112 Hours Left'}],
         [{'text': '[Reference]', 'mono': True}, 'Airframe', 'Exhaust Muffler Crack Inspection', 'Repetitive Inspection', {'text': '6,224.6 Hours', 'sub': '[Date]'}, {'text': '6,824.6 Hours', 'sub': '412 Hours Left'}],
         [{'text': '[Reference]', 'mono': True}, 'Airframe', 'Stabilator Attachment Fitting Inspection', 'Repetitive Inspection', {'text': '5,600.6 Hours', 'sub': '[Date]'}, {'text': '7,600.6 Hours', 'sub': '1,188 Hours Left'}],
         [{'text': '[Reference] Revision 2', 'mono': True}, 'Airframe', {'text': 'Fuel Selector Valve Placard', 'sub': 'Part A Complete, Part B Not Applicable to Serial Number'}, 'One-Off, Placard Replaced', {'text': '6,105.2 Hours', 'sub': 'March 2024'}, 'Complete'],
         [{'text': '[Reference]', 'mono': True}, 'Propeller', {'text': 'Constant Speed Propeller Hub Inspection', 'sub': 'Fixed Pitch Propeller Fitted'}, 'Not Applicable', '', '']])),
])

# Modifications and Repairs (CAME 1.6-1.7; MOE 2.9, 2.12)
page('Mods.dc.html', 'Modifications and Repairs', 'mods', 1500, [
    header(CR, 'Modifications and Repairs', '',
           [btn('Record a Change', primary=True)], tabs=('config', 'mods'), trail='Continuing Airworthiness=Fleet.dc.html|Aircraft Configuration=Components.dc.html|Modifications and Repairs'),
    section('sb-h', 'Service Bulletins', table(
        [('Aircraft Registration', '170px', 'left'), ('Bulletin', '', 'left'), ('Owner Decision', '280px', 'left'), ('Recorded', '170px', 'left')],
        [[AC('G-ABCD'), {'text': 'Seat Rail and Stop Inspection', 'sub': '[Reference], Recommended'}, 'Every 50-Hour Check', '2 March 2026'],
         [AC('G-ABCD'), {'text': 'Engine Valve Guide Inspection', 'sub': '[Reference], Recommended'}, 'Every 100-Hour Check', '2 March 2026'],
         [AC('G-BXYZ'), {'text': 'Alternator Mounting Bracket Inspection', 'sub': '[Reference], Recommended'}, {'text': 'Awaiting Syndicate', 'sub': 'Sent 10 November'}, {'text': 'Reminder 24 November', 'dot': 'a'}],
         [AC('G-EJKL'), {'text': 'Seat Belt Replacement', 'sub': '[Reference], Optional'}, {'text': 'Declined', 'sub': 'Belts On Condition, Annual Check'}, '6 June 2026']], minw=960)),
    section('ch-h', 'Changes and Repairs', table(
        [('Aircraft Registration', '170px', 'left'), ('Change or Repair', '', 'left'), ('Approval Route', '230px', 'left'), ('Mass Effect', '130px', 'right'), ('Records', '190px', 'left')],
        [[AC('G-BXYZ'), {'text': 'Panel-Mounted Navigator', 'sub': 'October 2026'}, 'Standard Change, [Reference]', '+1.2 Kilograms', {'text': 'Weight Schedule Update', 'dot': 'a', 'href': 'Weighing.dc.html'}],
         [AC('G-FMNO'), {'text': 'Light-Emitting Diode Landing Light', 'sub': 'April 2026'}, 'Minor Change, [Reference]', '−0.3 Kilograms', 'Complete'],
         [AC('G-DGHI'), {'text': 'Left Wingtip Repair, Hangar Damage', 'sub': 'July 2025'}, 'Manufacturer’s Structural Repair Data', '0 Kilograms', 'Complete'],
         [AC('G-ABCD'), {'text': 'Mode S Transponder with Position Output', 'sub': 'May 2022'}, 'Standard Change, [Reference]', '+0.4 Kilograms', 'Complete'],
         [AC('G-CDEF'), {'text': 'Propeller Overhaul', 'sub': 'In Progress, November 2026'}, 'Maintenance, Same Part Number', '0 Kilograms', {'text': 'Directive Check Before Refit', 'dot': 'a', 'href': 'Directives.dc.html'}]])),
])

# Repeat Defects (CAME 1.5, 1.10)
page('Reliability.dc.html', 'Repeat Defects', 'reliability', 1200, [
    header(CR, 'Repeat Defects', '',
           [btn('Export')], tabs=('defects', 'reliability'), trail='Continuing Airworthiness=Fleet.dc.html|Defects=Defects.dc.html|Repeat Defects'),
    section('rep-h', 'Repeats and Watch List', table(
        [('Type Rating', '240px', 'left'), ('System', '170px', 'left'), ('Defect', '', 'left'), ('In 12 Months', '120px', 'right'), ('Action', '300px', 'left')],
        [[{'text': 'Piper PA-28 Series (Lycoming)', 'sub': 'G-ABCD, G-DGHI'}, 'Chapter 33, Lights', {'text': 'Landing Light Failure', 'dot': 'a', 'sub': 'G-ABCD November and February, G-DGHI June'}, '3', {'text': 'Repeat', 'sub': 'Add Lamp Holder Check to 50-Hour Check'}],
         [{'text': 'Piper PA-28 Series (Lycoming)', 'sub': 'G-DGHI'}, 'Chapter 27, Flight Controls', {'text': 'Stabilator Trim Cable Wear', 'sub': 'G-DGHI November 2026 and December 2025'}, '2', {'text': 'Watching', 'sub': 'Pulley Alignment, WP-2026-046'}],
         [{'text': 'Cessna/Reims-Cessna 152/F152 Series (Lycoming)', 'sub': 'G-EJKL'}, 'Chapter 23, Communications', {'text': 'Headset Socket Fault', 'sub': 'G-EJKL November'}, '1', 'No Action'],
         [{'text': 'Robin DR 400 series (Lycoming)', 'sub': 'G-CDEF'}, 'Chapter 61, Propeller', {'text': 'Spinner Cracking', 'sub': 'G-CDEF November'}, '1', 'No Action']]),
        intro='Repeat: 3 of the Same Defect on One Type in 12 Months'),
])

# Weight and Balance (CAME 1.12)
page('Weighing.dc.html', 'Weight and Balance', 'weighing', 1100, [
    header(CR, 'Weight and Balance', '',
           [btn('Upload a Weighing Report', primary=True)], tabs=('config', 'weighing'), trail='Continuing Airworthiness=Fleet.dc.html|Aircraft Configuration=Components.dc.html|Weight and Balance'),
    section('wb-h', 'Fleet', table(
        [('Aircraft Registration', '170px', 'left'), ('Last Weighed', '160px', 'left'), ('Schedule', '150px', 'left'), ('Changes Since Weighing', '', 'left'), ('Net Change', '120px', 'right'), ('Status', '220px', 'left')],
        [[AC('G-BXYZ'), '[Date] 2019', 'Issue 6', 'Navigator, October 2026', '+1.2 Kilograms', {'text': 'Schedule Update', 'dot': 'a', 'sub': 'From Standard Change'}],
         [AC('G-DGHI'), '[Date] 2017', 'Issue 9', '3 Changes, All Scheduled', '+4.1 Kilograms', {'text': 'Reweigh', 'dot': 'a', 'sub': 'Over [Threshold] Threshold'}],
         [AC('G-ABCD'), 'May 2022', 'Issue 4', 'None', '0 Kilograms', 'Current'],
         [AC('G-CDEF'), '[Date] 2021', 'Issue 3', 'Propeller Overhaul, Same Part Number', '0 Kilograms', 'Current'],
         [AC('G-EJKL'), '[Date] 2020', 'Issue 2', 'None', '0 Kilograms', 'Current'],
         [AC('G-FMNO'), '[Date] 2018', 'Issue 5', 'Landing Light, Scheduled', '−0.3 Kilograms', 'Current']])),
])

# Aircraft Transfers (CAME 1.3.3-1.3.4)
page('Transfers.dc.html', 'Aircraft Transfers', 'transfers', 1400, [
    header(CR, 'Aircraft Transfers', '',
           [btn('Start a Transfer In', primary=True)], tabs=('aircraft', 'transfers'), trail='Continuing Airworthiness=Fleet.dc.html|Aircraft=Fleet.dc.html|Transfers'),
    section('in-h', 'Transfer In, G-HKLM', checklist([
        ('g', 'Type Within Scope of Approval', 'Piper PA-38 Series (Lycoming)'),
        ('g', 'Management Contract', 'Signed 9 November 2026, [Owner Name]'),
        ('g', 'Import Checks', 'Not Applicable, United Kingdom Register'),
        ('g', 'Records Handover Plan', '[Previous Organisation], Sent 12 November'),
        ('a', 'Records Received and Checked', '14 of 18, Engine Logbook Volume 1 Requested 13 November'),
        ('a', 'Continuing Airworthiness Records Review', 'In Progress, Lucy Grant'),
        ('o', 'Records Entered', 'Configuration Baseline, Directives and Life Limits'),
        ('o', 'Maintenance Programme', 'Owner Declared or Organisation Approved'),
        ('o', 'Bridging Check', 'With Next 100-Hour Check if Programme Changes'),
        ('o', 'Exposition Scope of Work', 'Updated on Completion'),
    ]), intro='Started 9 November 2026, 4 of 10 Complete', right=btn('Set Up Configuration', href='ConfigSetup.dc.html')),
    section('out-h', 'Transfer Out and Record Export',
            '<p style="margin: 0; font-size: 14px; line-height: 20px; color: {{t.muted}}">None in Progress</p>\n' +
            '<div style="display: flex; flex-wrap: wrap; gap: 8px">' + btn('Export G-ABCD Records') + btn('Export All Aircraft') + '</div>\n'),
])

# Components and Life Limits (Aircraft Configuration)
page('Components.dc.html', 'Components and Life Limits', 'components', 1700, [
    header(CR, 'Components and Life Limits', '',
           [btn('Add a Component')], tabs=('config', 'components'), trail='Continuing Airworthiness=Fleet.dc.html|Aircraft Configuration=Components.dc.html|Components and Life Limits'),
    strip([('38', 'Tracked'), ('1', 'At Overhaul'), ('1', 'On Condition Beyond Manufacturer’s Interval'), ('3', 'Due in 6 Months')]),
    section('near-h', 'Nearest Limits', table(
        [('Component', '', 'left'), ('Fitted To', '140px', 'left'), ('Limit', '230px', 'left'), ('Since New or Overhaul', '170px', 'right'), ('Remaining', '170px', 'right')],
        [[{'text': 'Propeller, Fixed Pitch', 'dot': 'a', 'sub': 'Part Number [Part Number], Serial Number [Serial Number]'}, {'text': 'Off-Wing', 'sub': 'From G-CDEF'}, '2,000 Hours or 6 Years', '1,412 Hours, 6 Years', {'text': 'At Overhaul', 'sub': 'Due Back 25 November'}],
         [{'text': 'Engine, Lycoming O-360', 'dot': 'a', 'sub': 'Serial Number [Serial Number]'}, AC('G-DGHI'), 'On Condition, Reviewed Every 100 Hours', '2,140 Hours', {'text': 'Review at 9,900.0', 'sub': 'Justified Departure'}],
         [{'text': 'Emergency Locator Transmitter Battery', 'sub': 'Part Number [Part Number]'}, AC('G-ABCD'), 'Battery Date', 'Fitted February 2022', {'text': '3 Months', 'sub': 'February 2027'}],
         [{'text': 'Fire Extinguisher', 'sub': 'Part Number [Part Number]'}, AC('G-BXYZ'), 'Label Inspection Date', '[Date]', {'text': '4 Months', 'sub': 'March 2027'}],
         [{'text': 'Engine, Lycoming O-360', 'sub': 'Serial Number [Serial Number]'}, AC('G-CDEF'), '2,000 Hours, Manufacturer Recommendation', '1,780 Hours', {'text': '220 Hours', 'sub': 'Mid 2027'}],
         [{'text': 'Vacuum Pump', 'sub': 'Part Number [Part Number]'}, AC('G-ABCD'), '500 Hours, Manufacturer Recommendation', '182 Hours', {'text': '318 Hours', 'sub': 'Mid 2028'}]]),
        intro='6 Nearest of 38'),
    section('rec-h', 'Component Record, Propeller [Serial Number]', checklist([
        ('g', 'Fitted to G-CDEF, [Date] 2020', '6,319.5 Airframe Hours, Release Certificate on File'),
        ('g', '100-Hour or Annual Check Inspections', 'Last at 7,640.0 Airframe Hours, No Findings'),
        ('g', 'Spinner Crack, 2 November 2026', 'Spinner Replaced, Old Spinner Scrapped'),
        ('g', 'Removed at 6-Year Limit, 2 November 2026', '1,412 Hours Since Overhaul, WP-2026-043, Unserviceable Tag Fitted'),
        ('a', 'At [Propeller Organisation]', 'Due Back 25 November, via Goods In'),
        ('o', 'Directive Applicability Before Refit', 'Raised by Removal'),
    ])),
])
print('ok')
