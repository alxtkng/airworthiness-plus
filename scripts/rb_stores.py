from gen import *

# Logistics: Goods In and Stores, on the design system.
# Sources: M.A.501 to 504, ML.A.501 to 504, 145.A.42, CAO.A.030(b), CAO.A.050(c), AMC1 CAO.A.030 (h) to (n),
# CAP 3037 (receiving inspection, quarantine, suspected unapproved parts), CAP 2375 2.2 and 2.3.

REG = ('Aircraft Registration', '170px', 'left')
AC = lambda r, sub=None: {'text': r, 'href': 'Aircraft.dc.html' if r == 'G-ABCD' else None, 'sub': sub}
WP = lambda w, sub=None: {'text': w, 'mono': True, 'href': 'WorkPackages.dc.html', 'sub': sub}
ST = lambda text, c, sub=None: {'text': text, 'dot': c, 'status': True, 'sub': sub}
MONO = lambda r: {'text': r, 'mono': True}

TRAIL_GI = 'Logistics=PartsReceived.dc.html|Goods In=PartsReceived.dc.html|Receiving Inspection'
TRAIL_ST = 'Logistics=PartsReceived.dc.html|Stores=Stores.dc.html|Stock'
TRAIL_Q = 'Logistics=PartsReceived.dc.html|Stores=Stores.dc.html|Quarantine and Scrap'

# Goods In: Receiving Inspection (M.A.501(b) and GM, ML.A.501, 145.A.42(b), CAO.A.050(c), CAP 3037)
page('PartsReceived.dc.html', 'Receiving Inspection', 'received', 1800, [
    header('Logistics', 'Receiving Inspection', '', [btn('Receive an Item', primary=True)],
           tabs=('goodsin', 'received'), trail=TRAIL_GI),
    section('rx-h', 'Received', table(
        [('Received', '170px', 'left'), ('Item', '', 'left'), ('Class', '200px', 'left'), ('Supplier', '230px', 'left'),
         ('Release Document', '230px', 'left'), ('Status', '200px', 'left')],
        [['18 November 2026', {'text': 'Emergency Locator Transmitter Battery', 'sub': 'Part Number [Part Number], for G-ABCD 100-Hour Check'},
          'Serviceable Component', '[Parts Distributor]', 'CAA Form 1', ST('Awaiting Inspection', 'o', '2 of 7 Checks Done')],
         ['16 November 2026', {'text': 'Stabilator Trim Cable Assembly', 'sub': 'Part Number [Part Number], for WP-2026-046, Eligible for G-DGHI'},
          'Serviceable Component', '[Parts Distributor]', {'text': 'CAA Form 1', 'sub': 'Tracking Number [Number]'}, ST('Accepted', 'g', 'Chris Moore, B1')],
         ['16 November 2026', {'text': 'Engine Oil Filter', 'sub': 'Part Number [Part Number], for WP-2026-047'},
          'Serviceable Component', '[Parts Distributor]', {'text': 'CAA Form 1', 'sub': 'Tracking Number [Number]'}, ST('Accepted', 'g', 'Sam Patel, B1')],
         ['16 November 2026', {'text': 'Landing Light Lamp, Light-Emitting Diode', 'sub': 'Part Number [Part Number], for WP-2026-047, With Standard Change'},
          'Serviceable Component', '[Parts Distributor]', {'text': 'CAA Form 1', 'sub': 'Tracking Number [Number]'}, ST('Accepted', 'g', 'Sam Patel, B1')],
         ['15 November 2026', {'text': 'Stabilator Trim Cable Assembly', 'sub': 'Part Number Suffix Not Eligible for G-DGHI Modification Status'},
          'Serviceable Component', '[Parts Distributor]', 'CAA Form 1', ST('Rejected', 'r', 'Returned to Supplier 15 November 2026')],
         ['12 November 2026', {'text': 'Engine Oil', 'sub': 'Batch [Batch Number], 24 Litres'},
          'Material', '[Parts Distributor]', {'text': 'Certificate of Conformity', 'sub': 'Manufacturing and Supplier Source Stated'}, ST('Accepted', 'g', 'Chris Moore, B1')],
         ['12 November 2026', {'text': 'Bolts, [Specification]', 'sub': 'Batch [Batch Number], Quantity 50'},
          'Standard Part', '[Parts Distributor]', {'text': 'Certificate of Conformity', 'sub': 'Specification and Batch Number'}, ST('Accepted', 'g', 'Chris Moore, B1')],
         ['10 November 2026', {'text': 'Sealant', 'sub': 'Batch [Batch Number], Shelf Life to 30 November 2026'},
          'Material', '[Parts Distributor]', 'Certificate of Conformity', ST('Accepted', 'g', 'Sam Patel, B1')],
         ['6 November 2026', {'text': 'Alternator', 'sub': 'Bought by the Owner of G-FMNO, Not an Approved Supplier'},
          'Serviceable Component', 'Owner Supplied', {'text': 'CAA Form 1', 'sub': 'Serial Number Does Not Match the Part'},
          ST('Quarantined', 'r', 'Suspected Unapproved Part, Reported to the Civil Aviation Authority 7 November 2026')],
         ['28 October 2026', {'text': 'Engine Oil', 'sub': 'Batch [Batch Number], 20 Litres'},
          'Material', '[Oil Supplier]', 'None', ST('Rejected', 'r', 'Returned to Supplier, Supplier Suspended')]],
        minw=1180)),
    section('ins-h', 'Emergency Locator Transmitter Battery', checklist([
        ('g', 'Supplier', '[Parts Distributor], Approved Supplier, Matches Order [Order Number]'),
        ('g', 'Release Document', 'CAA Form 1, Part Number, Serial Number and Quantity Match the Item'),
        ('o', 'Part Number and Modification Status', 'Against the Aircraft Data for G-ABCD'),
        ('o', 'Condition and Packaging', 'No Damage, Original Packaging, Terminals Protected'),
        ('o', 'Shelf Life', 'Battery Expiry Date Recorded for Stores'),
        ('o', 'Suspected Unapproved Part Checks', 'Markings, Data Plate, Documents Not Altered, Price and Source as Expected'),
        ('o', 'Accept or Quarantine', 'Serviceable Tag and Stores Location, or Quarantine Store With Reason'),
    ]), intro='Received 18 November 2026, 2 of 7 Checks Done'),
    section('doc-h', 'Release Documents Accepted', table(
        [('Class', '240px', 'left'), ('Release Document', '', 'left'), ('Traceability', '340px', 'left')],
        [['Serviceable Component', 'CAA Form 1 or Equivalent', 'Part Number and Serial Number'],
         ['Standard Part', 'Certificate of Conformity to the Specification', 'Specification and Batch Number'],
         ['Material', 'Certificate of Conformity With Manufacturing and Supplier Source', 'Specification and Batch Number'],
         ['Unserviceable Component', 'Unserviceable Tag, Straight to Quarantine', 'Part Number, Serial Number and Removal Record']],
        minw=900)),
])

# Stores: Stock (M.A.501(a), ML.A.501, 145.A.42(a), CAO.A.030(b), AMC1 CAO.A.030 (h) to (j), CAP 2375 2.2 and 2.3)
page('Stores.dc.html', 'Stock', 'stores', 1760, [
    header('Logistics', 'Stock', '', [btn('Stock Check'), btn('Issue to a Work Package', primary=True)],
           tabs=('stores', 'stores'), trail=TRAIL_ST),
    callout('Sealant, Batch [Batch Number], Shelf Life Ends 30 November 2026, 12 Days', 'a'),
    section('cls-h', 'Component Classes', table(
        [('Class', '240px', 'left'), ('Held In', '', 'left'), ('Tag', '240px', 'left'), ('Items', '120px', 'right')],
        [['Serviceable Component', {'text': 'Bay A and Tyre Rack', 'sub': 'Released on CAA Form 1 or Equivalent'}, 'Serviceable Tag', '4'],
         ['Unserviceable Component', {'text': 'Quarantine Store, Locked', 'href': 'Quarantine.dc.html'}, 'Unserviceable Tag', '2'],
         ['Unsalvageable Component', {'text': 'Quarantine Store, Secure Area', 'href': 'Quarantine.dc.html'}, 'Unsalvageable Tag', '1'],
         ['Standard Part', {'text': 'Bay B', 'sub': 'Certificate of Conformity to the Specification'}, 'Batch Label', '2'],
         ['Material', {'text': 'Bay C and Flammables Cabinet', 'sub': 'Certificate of Conformity, Manufacturing and Supplier Source'}, 'Batch Label', '3']],
        minw=900)),
    section('st-h', 'Stock', table(
        [('Item', '', 'left'), ('Class', '200px', 'left'), ('Location', '200px', 'left'), ('Quantity', '120px', 'right'),
         ('Shelf Life', '190px', 'left'), ('Reserved For', '200px', 'left')],
        [[{'text': 'Engine Oil Filter', 'sub': 'Part Number [Part Number], CAA Form 1 Tracking Number [Number]'}, 'Serviceable Component', 'Bay A, Shelf 2', '3', 'Not Applicable', WP('WP-2026-047', '1 of 3')],
         [{'text': 'Landing Light Lamp, Light-Emitting Diode', 'sub': 'Part Number [Part Number], CAA Form 1 Tracking Number [Number]'}, 'Serviceable Component', 'Bay A, Shelf 4', '1', 'Not Applicable', WP('WP-2026-047')],
         [{'text': 'Vacuum Pump', 'sub': 'Part Number [Part Number], CAA Form 1 Tracking Number [Number]'}, 'Serviceable Component', 'Bay A, Shelf 1', '1', 'Not Applicable', 'Not Reserved'],
         [{'text': 'Tyre, 6.00-6', 'sub': 'Part Number [Part Number], CAA Form 1 Tracking Number [Number]'}, 'Serviceable Component', 'Tyre Rack', '2', 'Not Applicable', 'Not Reserved'],
         [{'text': 'Bolts, [Specification]', 'sub': 'Batch [Batch Number]'}, 'Standard Part', 'Bay B, Drawer 7', '46', 'Not Applicable', 'Not Reserved'],
         [{'text': 'Split Pins, [Specification]', 'sub': 'Batch [Batch Number]'}, 'Standard Part', 'Bay B, Drawer 3', '118', 'Not Applicable', 'Not Reserved'],
         [{'text': 'Engine Oil', 'sub': 'Batch [Batch Number]'}, 'Material', 'Bay C', '24 Litres', '31 August 2029', WP('WP-2026-047', '8 Litres')],
         [{'text': 'Safety Wire, 0.032 Inch', 'sub': 'Batch [Batch Number]'}, 'Material', 'Bay C', '1 Reel', 'Not Applicable', WP('WP-2026-047', 'As Needed')],
         [{'text': 'Sealant', 'sub': 'Batch [Batch Number], Manufacturer’s Storage Instructions Followed'}, 'Material', 'Flammables Cabinet', '2 Cartridges', {'text': '30 November 2026', 'dot': 'a', 'sub': '12 Days'}, 'Not Reserved']],
        minw=1180)),
    section('iss-h', 'Issued to Maintenance', table(
        [('Issued', '190px', 'left'), ('Item', '', 'left'), ('Quantity', '110px', 'right'), ('Work Package', '170px', 'left'), REG, ('Issued To', '190px', 'left')],
        [['16 November 2026', {'text': 'Stabilator Trim Cable Assembly', 'sub': 'Part Number [Part Number], CAA Form 1 With the Item'}, '1', WP('WP-2026-046'), AC('G-DGHI'), 'Chris Moore, B1'],
         ['16 November 2026', {'text': 'Split Pins, [Specification]', 'sub': 'Batch [Batch Number]'}, '2', WP('WP-2026-046'), AC('G-DGHI'), 'Chris Moore, B1'],
         ['2 November 2026', {'text': 'Propeller Spinner', 'sub': 'Part Number [Part Number], CAA Form 1 With the Item'}, '1', WP('WP-2026-043'), AC('G-CDEF'), 'Sam Patel, B1'],
         ['2 November 2026', {'text': 'Engine Oil Filter', 'sub': 'Part Number [Part Number]'}, '1', WP('WP-2026-043'), AC('G-CDEF'), 'Sam Patel, B1'],
         ['2 November 2026', {'text': 'Engine Oil', 'sub': 'Batch [Batch Number]'}, '8 Litres', WP('WP-2026-043'), AC('G-CDEF'), 'Sam Patel, B1']],
        minw=1100), intro='Issued Only Against a Work Package, by Staff Authorised for Stores'),
])

# Stores: Quarantine and Scrap (M.A.504, ML.A.504, 145.A.42(c), AMC1 CAO.A.030 (k) to (n), CAP 3037)
page('Quarantine.dc.html', 'Quarantine and Scrap', 'quarantine', 1260, [
    header('Logistics', 'Quarantine and Scrap', '', [btn('Quarantine an Item', primary=True)],
           tabs=('stores', 'quarantine'), trail=TRAIL_Q),
    section('us-h', 'Unserviceable', table(
        [('Item', '', 'left'), ('Reason', '', 'left'), ('Since', '180px', 'left'), ('Decision', '200px', 'left'), ('Status', '230px', 'left')],
        [[{'text': 'Alternator', 'sub': 'Owner Supplied for G-FMNO, Part Number [Part Number], Unserviceable Tag'},
          'Suspected Unapproved Part, CAA Form 1 Does Not Match', '6 November 2026', {'text': 'Store', 'sub': 'Chris Moore, B1, 7 November 2026'},
          ST('Held for the Civil Aviation Authority', 'r', 'Suspected Unapproved Part Report Sent 7 November 2026')],
         [{'text': 'Magneto', 'sub': 'Found in Bay A at the Stock Check, Part Number [Part Number], Unserviceable Tag'},
          'No Release Document, Status Cannot Be Determined', '9 November 2026', {'text': 'Maintain', 'sub': 'Chris Moore, B1, 10 November 2026'},
          ST('Awaiting Despatch', 'a', 'To [Engine Overhaul Organisation] for Inspection and CAA Form 1')]],
        minw=1100), intro='Locked Quarantine Store, Kept Apart From Serviceable Stock'),
    section('un-h', 'Unsalvageable', table(
        [('Item', '', 'left'), ('Reason', '', 'left'), ('Decision', '230px', 'left'), ('Decided By', '190px', 'left'), ('Status', '230px', 'left')],
        [[{'text': 'Stabilator Trim Cable', 'sub': 'Removed From G-DGHI 15 November 2026, WP-2026-046, Unsalvageable Tag'},
          'Non-Repairable Defect, Frayed at Pulley', {'text': 'Store', 'sub': 'Retained for OR-2026-002 Follow-Up'}, {'text': 'Chris Moore, B1', 'sub': '16 November 2026'},
          ST('Held in Secure Area', 'a', 'Mutilate After the Follow-Up Report')],
         [{'text': 'Propeller Spinner', 'sub': 'Removed From G-CDEF 2 November 2026, WP-2026-043'},
          'Non-Repairable Defect, Cracked', 'Mutilate', {'text': 'Sam Patel, B1', 'sub': '2 November 2026'},
          ST('Mutilated', 'g', '6 November 2026, Cut Into Several Pieces')],
         [{'text': 'Main Tyre', 'sub': 'Removed From G-ABCD 22 October 2026, Pilot-Owner Maintenance'},
          'Worn Beyond Limit', 'Mutilate', {'text': 'Chris Moore, B1', 'sub': '23 October 2026, Owner Agreed'},
          ST('Mutilated', 'g', '23 October 2026, Bead and Sidewall Cut Through')]],
        minw=1100), intro='Never Back Into Stock Unless the Life Limit Is Extended or a Repair Is Approved'),
    section('rt-h', 'Returned to Supplier', table(
        [('Item', '', 'left'), ('Supplier', '240px', 'left'), ('Returned', '190px', 'left'), ('Reason', '', 'left'), ('Status', '200px', 'left')],
        [[{'text': 'Stabilator Trim Cable Assembly', 'sub': 'Part Number [Part Number], CAA Form 1 Tracking Number [Number]'},
          '[Parts Distributor]', '15 November 2026', 'Part Number Suffix Not Eligible for G-DGHI', {'text': 'Replaced', 'sub': 'Eligible Assembly Received 16 November 2026'}],
         [{'text': 'Engine Oil', 'sub': 'Batch [Batch Number], 20 Litres'},
          '[Oil Supplier]', '29 October 2026', 'No Certificate of Conformity', {'text': 'Credited', 'sub': 'Supplier Suspended'}]],
        minw=1100)),
    section('rs-h', 'Responsibilities', table(
        [('Responsibility', '', 'left'), ('Named Person', '260px', 'left'), ('Procedure', '220px', 'left')],
        [['Decision on Unserviceable Components: Maintain, Store or Mutilate', 'Chris Moore, B1', 'Exposition C.3'],
         ['Unsalvageable Components, Secure Area and Final Disposal', 'Chris Moore, B1', 'Exposition C.3'],
         ['Access to the Quarantine Store', 'Chris Moore and Sam Patel', 'Exposition C.3']],
        minw=900)),
])
print('ok')
