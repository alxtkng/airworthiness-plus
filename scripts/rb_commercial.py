from gen import *

# Commercial: Enquiries and Quotes, Customers, Invoices. Ties to Contracts (work orders), Work Packages and Release to Service.
AC = lambda r, sub=None: {'text': r, 'href': 'Aircraft.dc.html' if r == 'G-ABCD' else None, 'sub': sub}
REG = ('Aircraft Registration', '170px', 'left')
S = lambda text, d=None, sub=None: {'text': text, 'dot': d, 'status': True, 'sub': sub} if d else {'text': text, 'sub': sub}
WP = lambda r: {'text': r, 'href': 'WorkPackages.dc.html'}
Q = lambda r: {'text': r, 'mono': True, 'href': 'Quotes.dc.html'}
TRAIL = 'Commercial=Marketplace.dc.html|Enquiries and Quotes=Enquiries.dc.html|'

# ---------- Enquiries ----------
page('Enquiries.dc.html', 'Enquiries', 'enquiries', 1250, [
    header('Commercial', 'Enquiries', '', [btn('Record an Enquiry', primary=True)], tabs=('enquiries', 'enquiries'), trail=TRAIL + 'Enquiries'),
    section('new-h', 'Open Enquiries', table(
        [('Reference', '140px', 'left'), ('From', '220px', 'left'), REG, ('Asked For', '', 'left'), ('Received', '170px', 'left'), ('Source', '150px', 'left'), ('Status', '170px', 'left')],
        [[{'text': 'E-2026-036', 'mono': True}, {'text': '[Prospective Customer]', 'sub': 'Not Yet a Customer'}, '[Registration]', {'text': 'Annual Check, Robin DR 400 series (Lycoming)', 'sub': 'Wooden Structure'}, '17 November 2026', 'Marketplace', S('To Answer', 'a', 'Reply by 19 November')],
         [{'text': 'E-2026-035', 'mono': True}, '[Owner Name]', AC('G-EJKL'), 'Annual Check and Right Headset Socket', '10 November 2026', 'Existing Customer', S('Quoted', sub='Q-2026-023')],
         [{'text': 'E-2026-034', 'mono': True}, '[Owner Name]', AC('G-FMNO'), '50-Hour Check', '13 November 2026', 'Existing Customer', S('Accepted', sub='Q-2026-022')]]),
        intro='Reply to New Enquiries Within 2 Working Days'),
    section('closed-h', 'Closed, Last 90 Days', table(
        [('Reference', '140px', 'left'), ('From', '220px', 'left'), REG, ('Asked For', '', 'left'), ('Outcome', '260px', 'left')],
        [[{'text': 'E-2026-033', 'mono': True}, '[Flying Club Name]', AC('G-DGHI'), 'Stabilator Trim Cable Rectification', {'text': 'Accepted, Q-2026-021', 'sub': 'Work Order 14 November'}],
         [{'text': 'E-2026-032', 'mono': True}, '[Owner Name]', AC('G-ABCD'), 'Landing Light Replacement', {'text': 'Accepted, Q-2026-020', 'sub': 'Work Order 12 November'}],
         [{'text': 'E-2026-031', 'mono': True}, '[Owner Name]', AC('G-HKLM'), 'Continuing Airworthiness Management', {'text': 'Contract Signed 9 November 2026', 'sub': 'Transfer In'}],
         [{'text': 'E-2026-029', 'mono': True}, '[Prospective Customer]', '[Registration]', 'Engine Overhaul, Turbine', {'text': 'Declined', 'sub': 'Outside Scope of Approval'}]], minw=1000)),
])

# ---------- Quotes ----------
page('Quotes.dc.html', 'Quotes', 'quotes', 1300, [
    header('Commercial', 'Quotes', '', [btn('Write a Quote', primary=True)], tabs=('enquiries', 'quotes'), trail=TRAIL + 'Quotes'),
    section('q-h', 'Quotes', table(
        [('Reference', '140px', 'left'), ('Customer', '200px', 'left'), REG, ('Work', '', 'left'), ('Total', '130px', 'right'), ('Valid To', '170px', 'left'), ('Status', '200px', 'left')],
        [[Q('Q-2026-023'), '[Owner Name]', AC('G-EJKL'), {'text': 'Annual Check and Right Headset Socket', 'sub': 'Planned as WP-2026-048, 1 to 4 December'}, '£1,860.00', '17 December 2026', S('Awaiting Acceptance', 'a', 'Sent 17 November')],
         [Q('Q-2026-022'), '[Owner Name]', AC('G-FMNO'), '50-Hour Check', '£420.00', '16 December 2026', S('Accepted', sub='Work Order 16 November, Not Planned')],
         [Q('Q-2026-021'), '[Flying Club Name]', AC('G-DGHI'), 'Stabilator Trim Cable Rectification', '£980.00', '14 December 2026', S('Accepted', sub=WP('WP-2026-046')['text'])],
         [Q('Q-2026-020'), '[Owner Name]', AC('G-ABCD'), 'Landing Light Replacement, Engine Oil and Filter Change', '£315.00', '12 December 2026', S('Accepted', sub='WP-2026-047')],
         [Q('Q-2026-019'), '[Syndicate Name]', AC('G-CDEF'), '100-Hour Check and Propeller Spinner', '£2,140.00', '—', S('Invoiced', sub='INV-2026-0141')]]),
        intro='An Accepted Quote Becomes the Written Work Order, Agreed Before Work Starts'),
    section('lines-h', 'Q-2026-023 Lines', table(
        [('Line', '', 'left'), ('Basis', '220px', 'left'), ('Quantity', '120px', 'right'), ('Amount', '140px', 'right')],
        [['Annual Check, Cessna/Reims-Cessna 152/F152 Series (Lycoming)', 'Maintenance Programme, Owner Declared, Issue 1', '16 Hours', '£1,280.00'],
         ['Right Headset Socket Replacement', 'Deferred Defect, Limit 12 December 2026', '1.5 Hours', '£120.00'],
         ['Parts and Materials', 'From Stores or [Parts Distributor]', 'Estimate', '£310.00'],
         ['Airworthiness Review Support', 'Physical Survey With the Check', '1.5 Hours', '£150.00']], minw=900),
        intro='Total £1,860.00, Excluding Value Added Tax'),
])

# ---------- Customers ----------
page('Customers.dc.html', 'Customers', 'customers', 1100, [
    header('Commercial', 'Customers', '', [btn('Add a Customer', primary=True)], trail='Commercial=Marketplace.dc.html|Customers'),
    section('c-h', 'Customers', table(
        [('Customer', '220px', 'left'), ('Aircraft Registration', '180px', 'left'), ('Contract', '', 'left'), ('Open Work', '200px', 'left'), ('Balance', '130px', 'right'), ('Since', '150px', 'left')],
        [[{'text': '[Syndicate Name]', 'sub': 'Syndicate of 6'}, AC('G-BXYZ'), {'text': 'Continuing Airworthiness Management', 'href': 'Contracts.dc.html'}, 'None', '£0.00', 'January 2025'],
         [{'text': '[Syndicate Name]', 'sub': 'Syndicate of 4'}, AC('G-CDEF'), {'text': 'Continuing Airworthiness Management', 'href': 'Contracts.dc.html'}, 'Propeller at Overhaul', {'text': '£2,140.00', 'sub': 'INV-2026-0141, Due 5 December'}, 'April 2024'],
         [{'text': '[Flying Club Name]', 'sub': 'Flying Club'}, AC('G-DGHI'), {'text': 'Continuing Airworthiness Management', 'href': 'Contracts.dc.html'}, WP('WP-2026-046'), '£0.00', 'March 2025'],
         [{'text': '[Owner Name]', 'sub': 'Pilot-Owner'}, AC('G-ABCD'), {'text': 'Maintenance Programme Review and Airworthiness Review', 'href': 'Contracts.dc.html'}, WP('WP-2026-047'), '£0.00', 'March 2026'],
         [{'text': '[Owner Name]', 'sub': 'Pilot-Owner'}, AC('G-EJKL'), 'None, Work Orders Only', {'text': 'Q-2026-023', 'sub': 'Awaiting Acceptance'}, '£0.00', 'December 2025'],
         [{'text': '[Owner Name]', 'sub': 'Pilot-Owner'}, AC('G-FMNO'), 'None, Work Orders Only', {'text': '50-Hour Check', 'sub': 'Not Planned'}, {'text': '£185.00', 'dot': 'r', 'sub': 'INV-2026-0137, 14 Days Overdue'}, 'May 2024'],
         [{'text': '[Owner Name]', 'sub': 'Pilot-Owner'}, AC('G-HKLM'), {'text': 'Continuing Airworthiness Management', 'href': 'Contracts.dc.html'}, {'text': 'Transfer In', 'href': 'Transfers.dc.html'}, '£0.00', 'November 2026']]),
        intro='7 Customers, 7 Aircraft'),
])

# ---------- Invoices ----------
page('Invoices.dc.html', 'Invoices', 'invoices', 1100, [
    header('Commercial', 'Invoices', '', [btn('Raise an Invoice', primary=True)], trail='Commercial=Marketplace.dc.html|Invoices'),
    strip([('£2,325.00', 'Unpaid'), ('£185.00', 'Overdue')]),
    section('i-h', 'Invoices', table(
        [('Invoice', '150px', 'left'), ('Customer', '200px', 'left'), REG, ('Work', '', 'left'), ('Amount', '130px', 'right'), ('Due', '170px', 'left'), ('Status', '170px', 'left')],
        [[{'text': 'INV-2026-0141', 'mono': True}, '[Syndicate Name]', AC('G-CDEF'), {'text': '100-Hour Check and Propeller Spinner', 'sub': 'WP-2026-043, Released 4 November'}, '£2,140.00', '5 December 2026', S('Unpaid', sub='17 Days Left')],
         [{'text': 'INV-2026-0140', 'mono': True}, '[Syndicate Name]', AC('G-BXYZ'), {'text': 'Continuing Airworthiness Management, Quarter 4', 'sub': 'Contract Fee'}, '£360.00', '31 October 2026', S('Paid', 'g', '28 October 2026')],
         [{'text': 'INV-2026-0139', 'mono': True}, '[Flying Club Name]', AC('G-DGHI'), {'text': 'Continuing Airworthiness Management, Quarter 4', 'sub': 'Contract Fee'}, '£360.00', '31 October 2026', S('Paid', 'g', '30 October 2026')],
         [{'text': 'INV-2026-0137', 'mono': True}, '[Owner Name]', AC('G-FMNO'), {'text': 'Owner-Supplied Alternator, Receiving Inspection and Quarantine', 'sub': 'Suspected Unapproved Part, OR-2026-003'}, '£185.00', '4 November 2026', S('Overdue', 'r', '14 Days')]]),
        intro='Raised When the Certificate of Release to Service Is Issued'),
])
print('done')
