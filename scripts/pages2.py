from gen import *

CR = 'Continuing Airworthiness'
PT = 'Parts, Tools and Equipment'
AC = lambda r, sub=None: {'text': r, 'href': 'Aircraft.dc.html' if r == 'G-ABCD' else None}

# Components and Life Limits (Aircraft Configuration tab)
page('Components.dc.html', 'Components and Life Limits', 'components', 1900, [
    header(CR, 'Aircraft Configuration',
           'Every tracked component in the fleet, nearest limit first. Each engine, propeller and component has its own record that follows it from aircraft to aircraft and to overhaul.',
           [btn('Add a Component')], tabs=('config', 'components'), trail='Continuing Airworthiness=Fleet.dc.html|Aircraft Configuration=Components.dc.html|Components and Life Limits'),
    strip([('38', 'tracked components'), ('1', 'off-wing at overhaul'), ('1', 'on condition beyond the manufacturer’s interval'), ('3', 'due in the next 6 months')]),
    section('near-h', 'Nearest Limits', table(
        [('Component', '', 'left'), ('Fitted To', '140px', 'left'), ('Limit', '230px', 'left'), ('Since New or Overhaul', '170px', 'right'), ('Remaining', '170px', 'right')],
        [[{'text': 'Propeller, fixed pitch', 'dot': 'a', 'sub': 'Part number [Part Number], serial number [Serial Number]'}, {'text': 'Off-wing', 'sub': 'Removed from G-CDEF'}, '2,000 hours or 6 years', '1,412 hours, 6 years', {'text': 'At overhaul', 'sub': 'Due back 25 November'}],
         [{'text': 'Engine, Lycoming O-360', 'dot': 'a', 'sub': 'Serial number [Serial Number]'}, AC('G-DGHI'), 'On condition, reviewed every 100 hours', '2,140 hours', {'text': 'Next review at 9,900.0', 'sub': 'Programme departure, justified'}],
         [{'text': 'Emergency locator transmitter battery', 'dot': 'g', 'sub': 'Part number [Part Number]'}, AC('G-ABCD'), 'By the date on the battery', 'Fitted February 2022', {'text': '3 months', 'sub': 'February 2027'}],
         [{'text': 'Fire extinguisher', 'dot': 'g', 'sub': 'Part number [Part Number]'}, AC('G-BXYZ'), 'Inspection by the date on the label', '[Date]', {'text': '4 months', 'sub': 'March 2027'}],
         [{'text': 'Engine, Lycoming O-360', 'dot': 'g', 'sub': 'Serial number [Serial Number]'}, AC('G-CDEF'), '2,000 hours, manufacturer recommendation', '1,780 hours', {'text': '220 hours', 'sub': 'About mid 2027'}],
         [{'text': 'Vacuum pump', 'dot': 'g', 'sub': 'Part number [Part Number]'}, AC('G-ABCD'), '500 hours, manufacturer recommendation', '182 hours', {'text': '318 hours', 'sub': 'About mid 2028'}]]),
        intro='6 nearest of 38'),
    section('rec-h', 'Component Record, Propeller [Serial Number]', checklist([
        ('g', 'Fitted to G-CDEF, [Date] 2020', 'Fitted after overhaul at 6,319.5 airframe hours. Release certificate on file.'),
        ('g', 'Inspected at each 100-Hour or Annual Check', 'Last at 7,640.0 airframe hours, no findings.'),
        ('g', 'Spinner crack found and spinner replaced, 2 November 2026', 'Recorded as a defect. Old spinner scrapped and made unusable.'),
        ('g', 'Removed for overhaul at the 6-year limit, 2 November 2026', '1,412 hours since overhaul. Work package WP-2026-043. Unserviceable tag fitted with the reason for removal.'),
        ('a', 'At [Propeller Overhaul Organisation], due back 25 November', 'Will come back with a release certificate and go through Parts Received.'),
        ('o', 'Directive applicability checked before refit', 'Triggered automatically by the removal. See Airworthiness Directives.'),
    ])),
    foot(),
])

# Parts Received
page('PartsReceived.dc.html', 'Parts Received', 'received', 1700, [
    header(PT, 'Parts',
           'Every part, standard part and material coming into the organisation is inspected before it can be used. Anything that fails goes straight to quarantine.',
           [btn('Receive a Part', primary=True)], tabs=('parts', 'received')),
    strip([('6', 'received this month'), ('5', 'accepted'), ('1', 'quarantined'), ('1', 'expected, G-CDEF propeller')]),
    section('rx-h', 'Received in November', table(
        [('Received', '130px', 'left'), ('Part', '', 'left'), ('From', '190px', 'left'), ('Release Document', '210px', 'left'), ('Result', '200px', 'left')],
        [[{'text': '16 November', 'bold': False}, {'text': 'Engine oil filter', 'sub': 'Part number [Part Number], for WP-2026-047'}, '[Supplier]', 'Manufacturer’s certificate of conformity', {'text': 'Accepted', 'dot': 'g', 'sub': 'Ben Clarke'}],
         [{'text': '16 November', 'bold': False}, {'text': 'Landing light lamp', 'sub': 'Part number [Part Number], for WP-2026-047'}, '[Supplier]', 'Manufacturer’s certificate of conformity', {'text': 'Accepted', 'dot': 'g', 'sub': 'Ben Clarke'}],
         [{'text': '15 November', 'bold': False}, {'text': 'Stabilator trim cable assembly', 'sub': 'Part number [Part Number], for WP-2026-046'}, '[Supplier]', 'CAA Form 1, tracking number [Number]', {'text': 'Accepted', 'dot': 'g', 'sub': 'Ben Clarke'}],
         [{'text': '12 November', 'bold': False}, {'text': 'Bolts, batch [Batch Number]', 'sub': 'Standard parts, quantity 50'}, '[Supplier]', 'Certificate of conformity with specification and batch number', {'text': 'Accepted', 'dot': 'g', 'sub': 'Tom Evans'}],
         [{'text': '10 November', 'bold': False}, {'text': 'Sealant, batch [Batch Number]', 'sub': 'Material'}, '[Supplier]', 'Certificate of conformity', {'text': 'Accepted', 'dot': 'g', 'sub': 'Shelf life to 30 November 2026'}],
         [{'text': '6 November', 'bold': False}, {'text': 'Alternator', 'sub': 'Bought by an owner online'}, 'Private seller', 'Release certificate serial number does not match the part', {'text': 'Quarantined', 'dot': 'r', 'sub': 'Reported as a suspected unapproved part'}]]),
        intro='Results are recorded by the person who did the receiving inspection.'),
    section('chk-h', 'Receiving Inspection Checks', checklist([
        ('g', 'Condition and packaging', 'No damage, caps and plugs fitted, correct packaging for sensitive parts.'),
        ('g', 'Release document', 'Matches the part number, serial or batch number and quantity, and is the right type for a new or used part.'),
        ('g', 'Shelf life', 'Not expired, and the expiry date is recorded for stores.'),
        ('g', 'Directive and modification status', 'Checked for components where it matters.'),
        ('g', 'Order', 'Matches what was ordered.'),
        ('g', 'Tag and record', 'Serviceable tag fitted and the part linked to its release document, so it can be traced from any aircraft it is fitted to.'),
    ])),
    foot(),
])

# Stores
page('Stores.dc.html', 'Stores', 'stores', 1400, [
    header(PT, 'Parts',
           'What is in stores, where it is, and what is reserved. Serviceable, unserviceable and scrap items are kept apart, and each item shows its shelf life.',
           [btn('Stock Check')], tabs=('parts', 'stores')),
    callout('Sealant batch [Batch Number] reaches the end of its shelf life on 30 November. Use it or move it to quarantine.', 'a'),
    section('st-h', 'Serviceable Stock', table(
        [('Part', '', 'left'), ('Location', '140px', 'left'), ('Quantity', '100px', 'right'), ('Shelf Life', '170px', 'left'), ('Reserved For', '190px', 'left')],
        [[{'text': 'Engine oil filter', 'sub': 'Part number [Part Number]'}, 'Bay A, shelf 2', '3', 'Not applicable', {'text': 'WP-2026-047, 1', 'href': 'WorkPackages.dc.html'}],
         [{'text': 'Landing light lamp', 'sub': 'Part number [Part Number]'}, 'Bay A, shelf 4', '2', 'Not applicable', {'text': 'WP-2026-047, 1', 'href': 'WorkPackages.dc.html'}],
         [{'text': 'Sealant', 'sub': 'Batch [Batch Number]'}, 'Flammables cabinet', '2', {'text': '30 November 2026', 'dot': 'a'}, 'Not reserved'],
         [{'text': 'Bolts', 'sub': 'Batch [Batch Number]'}, 'Bay B, drawer 7', '46', 'Not applicable', 'Not reserved'],
         [{'text': 'Emergency locator transmitter battery', 'sub': 'Part number [Part Number]'}, 'Bay A, shelf 1', '1', {'text': 'Replace by [Date]', 'dot': 'g'}, 'G-ABCD, 100-Hour Check'],
         [{'text': 'Tyre, 6.00-6', 'sub': 'Part number [Part Number]'}, 'Tyre rack', '2', {'text': 'Manufactured [Date]', 'dot': 'g'}, 'Not reserved']], minw=980),
        intro='Only people authorised for stores can issue parts. Every issue is recorded against a work package.'),
    foot(),
])

# Quarantine and Scrap
page('Quarantine.dc.html', 'Quarantine and Scrap', 'quarantine', 1400, [
    header(PT, 'Parts',
           'Unserviceable and suspect parts, kept locked away and tagged until someone decides what happens to them. Scrapped parts are made unusable so they can never return to service.',
           [btn('Quarantine a Part')], tabs=('parts', 'quarantine')),
    section('q-h', 'In Quarantine', table(
        [('Part', '', 'left'), ('Why', '', 'left'), ('Since', '140px', 'left'), ('Decision', '230px', 'left')],
        [[{'text': 'Alternator', 'dot': 'r', 'sub': 'Bought by an owner online'}, 'Release certificate does not match the part. Suspected unapproved part.', '6 November', {'text': 'Reported to the CAA', 'sub': 'Occurrence report sent 7 November'}],
         [{'text': 'Vacuum pump', 'dot': 'a', 'sub': 'Removed from G-DGHI'}, 'Unserviceable tag: low suction at idle. Fitted 410 hours.', '14 November', {'text': 'Decide: repair or scrap', 'sub': 'Owner asked 15 November'}],
         [{'text': 'Propeller', 'dot': 'o', 'sub': 'From G-CDEF'}, 'Removed at the 6-year limit, sent for overhaul with its tag.', '2 November', {'text': 'At overhaul', 'sub': 'Due back 25 November'}]], minw=980),
        intro='Each tag records the reason for removal, hours in service, and whether the aircraft had an accident or incident.'),
    section('sc-h', 'Scrapped This Year', table(
        [('Part', '', 'left'), ('Made Unusable', '190px', 'left'), ('By', '160px', 'left'), ('Manufacturer Told', '190px', 'left')],
        [[{'text': 'Propeller spinner', 'sub': 'From G-CDEF, cracked'}, '6 November 2026, cut in two', 'Ben Clarke', 'Not required'],
         [{'text': 'Main tyre', 'sub': 'From G-ABCD, worn to limit'}, '22 October 2026, sidewall cut', 'Pilot-owner', 'Not required']], minw=900)),
    foot(),
])
print('ok')
