from gen import *

# Training section: Recurrent Training, Aircraft Maintenance Licence (Basic Examinations, Experience Logbook,
# Type Training, On the Job Training) and Competency Assessments. Assessment.dc.html is hand-written.
TR = 'Training=RecurrentTraining.dc.html'
AML = TR + '|Aircraft Maintenance Licence=BasicExaminations.dc.html|'
AC = lambda r, sub=None: {'text': r, 'href': 'Aircraft.dc.html' if r == 'G-ABCD' else None, 'sub': sub}
WP = lambda r, sub=None: {'text': r, 'href': 'WorkPackages.dc.html', 'mono': True, 'sub': sub}
REG = ('Aircraft Registration', '170px', 'left')
OK = lambda s='Current', sub=None: {'text': s, 'dot': 'g', 'status': True, 'sub': sub}
AMB = lambda s, sub=None: {'text': s, 'dot': 'a', 'status': True, 'sub': sub}
RED = lambda s, sub=None: {'text': s, 'dot': 'r', 'status': True, 'sub': sub}
NR = {'text': 'Not Required for Role'}
C172 = 'Cessna/Reims-Cessna 172/F172 Series (Lycoming)'

# Recurrent Training (145.A.30(e) and AMC, AMC 145.A.30(e) fuel tank safety, 145.A.35(d) continuation training)
page('RecurrentTraining.dc.html', 'Recurrent Training', 'recurrent', 1240, [
    header('Training', 'Recurrent Training', '', [btn('Book Training', primary=True)],
           trail=TR + '|Recurrent Training'),
    section('rt-h', 'Recurrent Training by Person', table(
        [('Name', '190px', 'left'), ('Human Factors', '170px', 'left'), ('Electrical Wiring Interconnection System', '200px', 'left'),
         ('Fuel Tank Safety', '170px', 'left'), ('Continuation Training', '180px', 'left'), ('Status', '170px', 'left')],
        [[{'text': 'Sam Patel', 'sub': 'Certifying Staff, Part-66 B1.2'}, {'text': '6 December 2026', 'dot': 'a', 'sub': 'Last 6 December 2024'},
          {'text': '22 May 2027', 'sub': 'Last 22 May 2025'}, {'text': '22 May 2027', 'sub': 'Phase 2 Last 22 May 2025'},
          {'text': '6 December 2026', 'dot': 'a', 'sub': 'Procedures, Regulation Changes'}, AMB('Due in 18 Days', 'Booked 1 December 2026')],
         [{'text': '[Name]', 'sub': 'Airworthiness Review Staff'}, {'text': '30 October 2026', 'dot': 'r', 'sub': 'Last 30 October 2024'},
          NR, NR, NR, RED('Overdue', 'Booked 2 December 2026')],
         [{'text': 'Chris Moore', 'sub': 'Certifying Staff, Part-66 B1.2'}, {'text': '14 August 2027', 'sub': 'Last 14 August 2025'},
          {'text': '14 August 2027', 'sub': 'Last 14 August 2025'}, {'text': '20 March 2027', 'sub': 'Phase 2 Last 20 March 2025'},
          {'text': '14 August 2027', 'sub': 'Procedures, Regulation Changes'}, OK()],
         [{'text': 'Ellie Ward', 'sub': 'Mechanic, Joined 6 January 2025'}, {'text': '14 February 2027', 'sub': 'Initial 14 February 2025'},
          {'text': '3 March 2027', 'sub': 'Initial 3 March 2025'}, {'text': '10 November 2027', 'sub': 'Phase 1 3 March 2025, Phase 2 10 November 2025'},
          {'text': 'Not Required for Role', 'sub': 'Not Certifying Staff'}, OK()],
         [{'text': 'Lucy Grant', 'sub': 'Airworthiness Review Staff'}, {'text': '9 June 2027', 'sub': 'Last 9 June 2025'}, NR, NR, NR, OK()],
         [{'text': '[Name]', 'sub': 'Certifying Staff, Part-66 L2'}, {'text': '2 May 2027', 'sub': 'Last 2 May 2025'},
          {'text': '2 May 2027', 'sub': 'Last 2 May 2025'}, {'text': 'Not Required for Role', 'sub': 'ELA1 Aeroplanes, Wooden Structure'},
          {'text': '2 May 2027', 'sub': 'Procedures, Regulation Changes'}, OK()]], minw=1180),
        intro='Due Dates From the Last Completed Session'),
    section('bk-h', 'Booked Sessions', table(
        [('Date', '190px', 'left'), ('Training', '', 'left'), ('People', '260px', 'left'), ('Delivered By', '240px', 'left')],
        [['1 December 2026', {'text': 'Continuation Training and Human Factors', 'sub': 'Procedures, Regulation Changes, Human Factors'}, 'Sam Patel', '[Training Provider]'],
         ['2 December 2026', 'Human Factors', '[Name], Airworthiness Review Staff', '[Training Provider]']], minw=900)),
    section('cy-h', 'Training Cycles', table(
        [('Training', '260px', 'left'), ('First Due', '', 'left'), ('Then', '200px', 'left'), ('Point', '200px', 'left')],
        [['Human Factors', 'Within 6 Months of Joining', 'Every 2 Years', '145.A.30(e)'],
         ['Fuel Tank Safety', 'Phase 1 Within 6 Months, Phase 2 Within 12 Months', 'Every 2 Years', 'AMC 145.A.30(e)'],
         ['Electrical Wiring Interconnection System', 'Initial Course', 'As Set in the Exposition', 'AMC 20-22'],
         ['Continuation Training', {'text': 'Before First Authorisation', 'sub': 'Technology, Procedures, Regulation Changes, Human Factors'}, 'In Each 2-Year Period', '145.A.35(d)']], minw=900)),
])

# Basic Examinations (66.A.25, Appendix I and II to Part-66, Part-147)
P147 = '[Part-147 Organisation]'
def mod(m, name, date, by=P147, score=None):
    y = int(date.split()[-1]) + 10
    valid = ' '.join(date.split()[:-1]) + ' ' + str(y)
    return ['Module ' + m, name, 'B1.2', date, by, {'text': '[Reference]', 'mono': True}, valid, OK('Passed', score)]
page('BasicExaminations.dc.html', 'Basic Examinations', 'exams', 1640, [
    header('Training', 'Basic Examinations', '', [btn('Record a Result'), btn('Book an Examination', primary=True)], tabs=('licence', 'exams'),
           trail=AML + 'Basic Examinations'),
    section('ew-h', 'Ellie Ward, Toward Part-66 B1.2', table(
        [('Module', '120px', 'left'), ('Subject', '', 'left'), ('Category', '100px', 'left'), ('Date', '170px', 'left'),
         ('Examined By', '220px', 'left'), ('Certificate of Recognition', '200px', 'left'), ('Valid for Application To', '200px', 'left'), ('Result', '150px', 'left')],
        [mod('1', 'Mathematics', '12 October 2023', score='88%'),
         mod('2', 'Physics', '7 December 2023', score='81%'),
         mod('3', 'Electrical Fundamentals', '15 March 2024', score='79%'),
         mod('4', 'Electronic Fundamentals', '20 May 2024', score='84%'),
         mod('5', 'Digital Techniques, Electronic Instrument Systems', '9 September 2024', score='77%'),
         mod('6', 'Materials and Hardware', '18 November 2024', score='82%'),
         mod('7A', 'Maintenance Practices', '3 March 2025', score='86%'),
         mod('8', 'Basic Aerodynamics', '12 June 2025', score='90%'),
         mod('9A', 'Human Factors', '8 September 2025', score='85%'),
         mod('10', 'Aviation Legislation', '1 December 2025', by='Civil Aviation Authority', score='80%'),
         mod('16', 'Piston Engine', '14 May 2026', score='83%'),
         ['Module 11B', 'Aeroplane Aerodynamics, Structures and Systems', 'B1.2',
          {'text': '14 October 2026', 'sub': 'Retake 25 November 2026, After Part-147 Retraining'}, P147, 'Not Issued', '—',
          AMB('Failed, Retake Booked', 'Multi-Choice 71%, Attempt 1 of 3 in 12 Months')],
         ['Module 17A', 'Propeller', 'B1.2', {'text': 'Booked 9 December 2026'}, P147, '—', '—', {'text': 'Not Sat', 'dot': 'o', 'status': True}]],
        minw=1400),
        intro='11 of 13 Modules Passed'),
    section('lh-h', 'Licence Holders', table(
        [('Name', '200px', 'left'), ('Licence', '200px', 'left'), ('Modules', '', 'left'), ('Validity of Passes', '320px', 'left')],
        [['Chris Moore', {'text': 'Part-66 B1.2', 'sub': 'UK.66.[Number]'}, 'All B1.2 Modules', 'Used for Licence Issue, No Expiry'],
         ['Sam Patel', {'text': 'Part-66 B1.2', 'sub': 'UK.66.[Number]'}, 'All B1.2 Modules', 'Used for Licence Issue, No Expiry'],
         ['[Name]', {'text': 'Part-66 L2', 'sub': 'UK.66.[Number]'}, 'All L2 Modules', 'Used for Licence Issue, No Expiry']], minw=960)),
    section('rl-h', 'Examination Rules', table(
        [('Rule', '300px', 'left'), ('Value', '', 'left'), ('Point', '220px', 'left')],
        [['Examined By', 'Part-147 Organisation or the Civil Aviation Authority', '66.A.25'],
         ['Pass Mark', '75% for Each Module, Multi-Choice and Essay', 'Appendix II to Part-66'],
         ['Validity', {'text': '10 Years Before the Licence Application', 'sub': 'Unless Already Used for an Issued Category'}, '66.A.25'],
         ['Retake After a Failure', {'text': 'Not Before 90 Days', 'sub': '30 Days After Part-147 Retraining in the Failed Subjects'}, 'Appendix II to Part-66'],
         ['Part Failed', 'Retake Only the Multi-Choice or Essay Part Failed', 'Appendix II to Part-66'],
         ['Attempts', {'text': 'At Most 3 in 12 Months', 'sub': 'Written Statement of Earlier Attempts'}, 'Appendix II to Part-66']], minw=900)),
])

# Experience Logbook (66.A.30, AMC 66.A.20(b)2 record fields)
LOGCOLS = [('Date', '170px', 'left'), REG, ('ATA Chapter', '120px', 'left'), ('Operation Performed', '', 'left'),
           ('Line or Base', '120px', 'left'), ('Activity', '120px', 'left'), ('Duration', '120px', 'left'), ('Countersigned', '220px', 'left')]
def entry(date, reg, typ, ch, op, mx, act, dur, sup, wp=None, signed=True):
    return [{'text': date}, AC(reg, typ), {'text': ch, 'mono': True}, {'text': op, 'sub': wp}, mx, act, dur,
            OK('Countersigned', sup) if signed else AMB('Awaiting Countersignature', sup)]
page('Logbook.dc.html', 'Experience Logbook', 'logbook', 1300, [
    header('Training', 'Experience Logbook', '', [btn('Export for Licence Application'), btn('Add an Entry', primary=True)], tabs=('licence', 'logbook'),
           trail=AML + 'Experience Logbook'),
    section('pr-h', 'Ellie Ward, Basic Experience Toward Part-66 B1.2', checklist([
        ('a', 'Basic Experience, 31 of 36 Months', 'No Approved Basic Training Course, 3 Years Required'),
        ('g', 'Recent Experience, 22 Months on Piston Aeroplanes', 'At Least 1 Year Required'),
        ('g', 'All Experience Within the Last 10 Years', 'From April 2024'),
        ('a', '1 Entry Awaiting Countersignature', 'Sam Patel, 17 November 2026'),
    ]), intro='Recorded in the CAP 741 Logbook'),
    section('en-h', 'Entries', table(LOGCOLS,
        [entry('17 November 2026', 'G-DGHI', 'Piper PA-28 Series (Lycoming)', '27', 'Stabilator Trim Cable Replaced', 'Base', 'Perform', '1 Day', 'Sam Patel, B1.2', 'WP-2026-046', signed=False),
         entry('4 November 2026', 'G-CDEF', 'Robin DR 400 series (Lycoming)', '61', 'Propeller Spinner Replaced', 'Base', 'Perform', '0.5 Day', 'Chris Moore, B1.2', 'WP-2026-043'),
         entry('2–4 November 2026', 'G-CDEF', 'Robin DR 400 series (Lycoming)', '05', '100-Hour Check', 'Base', 'Perform', '3 Days', 'Chris Moore, B1.2', 'WP-2026-043'),
         entry('3 June 2026', 'G-BXYZ', C172, '28', 'Fuel Contamination, Water Drain Check and Tank Flush', 'Line', 'Perform', '1 Day', 'Sam Patel, B1.2'),
         entry('12 May 2026', 'G-BXYZ', C172, '32', 'Main Wheel Brake Linings Replaced, Brakes Bled', 'Base', 'Perform', '0.5 Day', 'Sam Patel, B1.2'),
         entry('21 April 2026', 'G-ABCD', 'Piper PA-28 Series (Lycoming)', '85', 'Cylinder Compression Check', 'Base', 'Perform', '0.5 Day', 'Chris Moore, B1.2'),
         entry('9 March 2026', 'G-EJKL', 'Cessna/Reims-Cessna 152/F152 Series (Lycoming)', '74', 'Magneto Timing Check', 'Base', 'Perform', '0.5 Day', 'Chris Moore, B1.2')],
        minw=1300),
        intro='Toward Category B1.2, [Your Organisation], UK.CAO.[Number]'),
    section('em-h', 'Employment', table(
        [('Organisation', '260px', 'left'), ('Period', '260px', 'left'), ('Work', '', 'left'), ('Months', '100px', 'right')],
        [['[Your Organisation]', 'January 2025 to Now', 'Mechanic, Scheduled Checks and Defect Rectification', '22'],
         ['[Previous Employer]', 'April 2024 to December 2024', 'Mechanic, Light Aircraft Maintenance', '9']], minw=900)),
])

# Type Training (66.A.45, Appendix III to Part-66, Part-147)
page('TypeTraining.dc.html', 'Type Training', 'type', 1260, [
    header('Training', 'Type Training', '', [btn('Book a Type Course', primary=True)], tabs=('licence', 'type'),
           trail=AML + 'Type Training'),
    section('tc-h', 'Type Courses', table(
        [('Name', '180px', 'left'), ('Type Rating', '', 'left'), ('Category', '100px', 'left'), ('Theory Element', '200px', 'left'),
         ('Practical Element', '200px', 'left'), ('Apply By', '170px', 'left'), ('Status', '170px', 'left')],
        [['Ellie Ward', C172, 'B1.2', {'text': '9–20 March 2026', 'sub': 'Examination Passed 20 March 2026, 86%'},
          {'text': '13–24 April 2026', 'sub': 'Assessed by Designated Assessor'}, {'text': '9 March 2029', 'sub': '3 Years From Start of Theory'},
          OK('Complete', 'Certificate of Recognition [Reference]')],
         ['Chris Moore', 'Grob G115/120 Series (Lycoming)', 'B1.2', {'text': 'Booked 18–22 January 2027', 'sub': P147},
          {'text': 'Booked 25–29 January 2027', 'sub': P147}, '—', {'text': 'Booked', 'dot': 'o', 'status': True}]], minw=1240)),
    section('el-h', 'Ellie Ward, ' + C172, checklist([
        ('g', 'Theory Element, 9–20 March 2026', P147 + ', Attendance 100%'),
        ('g', 'Type Examination Passed, 86%', 'Pass Mark 75%'),
        ('g', 'Practical Element, 13–24 April 2026', 'Tasks From the Practical Training Table, Assessed by a Designated Assessor'),
        ('g', 'Certificate of Recognition Issued, 24 April 2026', 'Theory and Practical Elements'),
        ('a', 'On the Job Training in Progress', 'First Type Rating in the First Licence Category'),
        ('o', 'Type Rating Application', 'By 9 March 2029'),
    ]), intro='4 of 6 Complete'),
    section('tr-h', 'Type Training Rules', table(
        [('Rule', '300px', 'left'), ('Value', '', 'left'), ('Point', '220px', 'left')],
        [['Course', 'Part-147 Organisation, Theory Element and Practical Element', '66.A.45, Appendix III to Part-66'],
         ['Examination', {'text': 'Pass Mark 75%', 'sub': 'Certificate of Recognition Not Issued if Attendance Is Below the Minimum'}, 'Appendix III to Part-66'],
         ['Time Limit', 'Theory and Practical Both Started and Completed Within 3 Years Before the Type Rating Application', 'Appendix III to Part-66'],
         ['First Type Rating', 'On the Job Training Also Needed in the First Licence Category', '66.A.45']], minw=900)),
])

# On the Job Training (Appendix III to Part-66, Section 6)
def ojt(date, reg, task, ref, loc, sup='Sam Patel, B1.2'):
    return [{'text': date}, AC(reg), task, {'text': ref, 'mono': True}, loc, OK('Countersigned', sup)]
LOC = '[Your Organisation], [Base]'
page('Training.dc.html', 'On the Job Training', 'ojt', 1760, [
    header('Training', 'On the Job Training', '', [btn('Record a Task'), btn('Request Final Assessment', primary=True)], tabs=('licence', 'ojt'),
           trail=AML + 'On the Job Training'),
    section('st-h', 'Ellie Ward, ' + C172 + ', B1.2', checklist([
        ('g', 'First Type Rating in the First Licence Category', 'On the Job Training Required'),
        ('g', 'Eligible to Start', 'Theory Element Complete 20 March 2026, Over 50% of Basic Experience'),
        ('a', 'Tasks Completed, 31 of 40', 'On the Job Training Programme, Issue 1'),
        ('g', '31 of 31 Tasks After the Theory Course', 'At Least 50% Required'),
        ('g', 'Started 30 March 2026, Within the 3-Year Window', 'Apply by 9 March 2029, Type Training Window Ends First'),
        ('o', 'Mentor Recommendation', 'Sam Patel, After the Last Task'),
        ('o', 'Final Assessment', 'Chris Moore, Civil Aviation Authority Told the Date in Advance'),
    ]), intro='4 of 7 Complete'),
    section('lg-h', 'On the Job Training Logbook', table(
        [('Date', '170px', 'left'), REG, ('Task', '', 'left'), ('Job Card or Work Package', '200px', 'left'), ('Location', '220px', 'left'),
         ('Mentor', '220px', 'left')],
        [ojt('13 November 2026', 'G-BXYZ', '100-Hour Inspection Items Checked', '[Job Card]', LOC),
         ojt('12 November 2026', 'G-BXYZ', 'Elevator Trim Rigged and Checked', '[Job Card]', LOC),
         ojt('11 November 2026', 'G-BXYZ', 'Wheel Brakes Bled', '[Job Card]', LOC),
         ojt('10 November 2026', 'G-BXYZ', 'Fuel Strainer Located and Inspected', '[Job Card]', LOC),
         ojt('16 June 2026', 'G-BXYZ', 'Flap Rigging Checked', '[Job Card]', LOC),
         ojt('7 April 2026', 'G-BXYZ', 'Engine Oil and Filter Changed', '[Job Card]', LOC)], minw=1300),
        intro='Each Task Signed by Ellie Ward and Countersigned by the Mentor'),
    section('ma-h', 'Mentor and Assessor', table(
        [('Role', '160px', 'left'), ('Name', '200px', 'left'), ('Licence', '200px', 'left'), ('Requirement', '', 'left'), ('Status', '160px', 'left')],
        [['Mentor', 'Sam Patel', {'text': 'Part-66 B1.2', 'sub': 'UK.66.[Number]'}, 'Same Category Held at Least 1 Year, Type Rating on the Aircraft', OK('Meets')],
         ['Assessor', 'Chris Moore', {'text': 'Part-66 B1.2', 'sub': 'UK.66.[Number]'}, {'text': 'Same Category Held at Least 3 Years, Same or Similar Type Rating', 'sub': 'Not a Mentor of Ellie Ward'}, OK('Meets')]], minw=1000)),
    section('fa-h', 'Final Assessment', table(
        [('Rule', '300px', 'left'), ('Value', '', 'left')],
        [['When', 'After the Logbook Is Complete and the Mentor Recommendation Is Signed'],
         ['Civil Aviation Authority', 'Told the Date Well in Advance'],
         ['Result', 'Passed or Failed, Signed by Assessor and Candidate'],
         ['Retake', {'text': 'After 3 Months', 'sub': 'Earlier With Additional Training and a New Mentor Recommendation'}],
         ['After 3 Failures', 'Repeat the Whole On the Job Training']], minw=800)),
])

# Competency Assessments (145.A.30(e) and AMC, CAO.A.040)
AS = lambda: {'text': 'Open', 'href': 'Assessment.dc.html'}
page('Competence.dc.html', 'Competency Assessments', 'competence', 1540, [
    header('Training', 'Competency Assessments', '', [btn('Start an Assessment', primary=True, href='Assessment.dc.html')],
           trail='Training=RecurrentTraining.dc.html|Competency Assessments'),
    section('ca-h', 'Assessments', table(
        [('Name', '200px', 'left'), ('Reason', '', 'left'), ('Assessor', '240px', 'left'), ('Date', '170px', 'left'), ('Result', '200px', 'left'), ('Authorisation', '220px', 'left')],
        [[{'text': '[Name]', 'href': 'Assessment.dc.html', 'sub': 'Planner, Joined 1 September 2026'}, {'text': 'Initial Assessment', 'sub': 'Intended Position'},
          'Continuing Airworthiness Manager', '18 November 2026', AMB('In Progress', '2 Scores Below 5'), 'Not Yet Authorised'],
         [{'text': '[Name]', 'sub': 'Certifying Staff, Part-66 L2'}, {'text': 'Lapse in Recent Experience', 'sub': 'Under 6 Months in 2 Years'},
          'Chris Moore, B1.2', '25 November 2026', {'text': 'Booked', 'dot': 'o', 'status': True}, {'text': 'Lapsed', 'dot': 'r'}],
         [{'text': '[Name]', 'sub': 'Airworthiness Review Staff'}, {'text': 'Reassessment After Support', 'sub': 'Previous Average 4.6, Continuing Airworthiness'},
          'Continuing Airworthiness Manager', '2 December 2026', {'text': 'Booked', 'dot': 'o', 'status': True}, {'text': 'Reviews Under Supervision', 'dot': 'a'}],
         [{'text': 'Ellie Ward', 'sub': 'Mechanic'}, {'text': 'Periodic', 'sub': 'Position Held'}, 'Chris Moore, B1.2', '9 October 2026', OK('Competent', 'Average 6.8, None Below 5'), 'Work Under Supervision'],
         [{'text': 'Lucy Grant', 'sub': 'Airworthiness Review Staff'}, {'text': 'Periodic', 'sub': 'Position Held'}, 'Continuing Airworthiness Manager', '4 October 2026', OK('Competent', 'Average 7.4, None Below 5'), 'Full'],
         [{'text': 'Sam Patel', 'sub': 'Certifying Staff, Part-66 B1.2'}, {'text': 'Periodic', 'sub': 'Position Held'}, 'Maintenance Manager', '14 April 2026', OK('Competent', 'Average 7.9, None Below 5'), 'Full'],
         [{'text': 'Chris Moore', 'sub': 'Certifying Staff, Part-66 B1.2'}, {'text': 'Periodic', 'sub': 'Position Held'}, 'Maintenance Manager', '20 March 2026', OK('Competent', 'Average 8.2, None Below 5'), 'Full']],
        minw=1240), intro='Minimum Level 5 on a Scale of 1 to 10'),
    section('sm-h', 'Support Measures', table(
        [('Name', '240px', 'left'), ('Measure', '200px', 'left'), ('Need', '', 'left'), ('Progress', '200px', 'left'), ('By', '170px', 'left')],
        [['[Name], Airworthiness Review Staff', 'Mentoring', {'text': 'Forecasting Airworthiness Directives, Maintenance Programme Review', 'sub': 'Both Scored 4'}, '3 of 5 Mentored Reviews', '2 December 2026'],
         ['[Name], Airworthiness Review Staff', 'Formal Training', 'Human Factors, Overdue', 'Booked 2 December 2026', '2 December 2026'],
         ['[Name], Planner', 'Working Under Supervision', {'text': 'Work Packages Checked Before Issue', 'sub': 'Continuing Airworthiness Manager'}, 'Assessment in Progress', 'Until Reassessed']], minw=1100)),
    section('ab-h', 'Changes in Ability', table(
        [('Name', '240px', 'left'), ('Change', '', 'left'), ('Reported', '170px', 'left'), ('Next Step', '240px', 'left')],
        [['[Name], Airworthiness Review Staff', 'New Prescription Glasses for Close Work', '22 July 2026', OK('No Change Needed', 'Eyesight Test Passed')]], minw=900)),
    section('wh-h', 'When to Assess', table(
        [('Trigger', '', 'left'), ('Assessed For', '260px', 'left')],
        [['Before First Authorisation or Unsupervised Work', 'Intended Position'],
         ['Periodically', 'Position Held'],
         ['After Training, Mentoring or Supervision', 'Position Held'],
         ['Change in Ability, Temporary or Permanent', 'Position Held'],
         ['Authorisation Extended to a New Type or Task', 'Intended Scope'],
         ['Recent Experience Lapsed', 'Position Held']], minw=800)),
])
