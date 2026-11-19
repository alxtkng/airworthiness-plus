# What Each Action May Set

OWASP ASVS 5.0, 8.1.2; REQ-006. The table under Setting is written from the code by `python manage.py field_rules`, and a test fails if the two differ.

The role matrix in `design-system/Decisions.md` says which roles may take each action. This says what each action may read and set.

## Reading

- A user reads the records of their own organisation and of no other. The database enforces it for every table (`architecture/decisions/0002-data-layer.md`), and every page is tested with a user of another organisation.
- Every role may View Records, and with it reads every field of every aircraft, programme, directive, maintenance data, review, certificate, import and problem record of the organisation, and their history.
- The Users page, with user names, roles and whether each person can sign in, is read by the Administrator only. A person's name is shown wherever a record says who did something.
- The access log is read by the Administrator on the Access Log page, and through the export of the organisation by a role that may Export Records. The Records Export page lists the exports made.
- No one reads a password, a second-factor key or a session identifier through the application. They are in no page, no history entry and no export (`tests/test_exports.py`). A first password and a second-factor key are each shown once, to the person who needs them, when they are made.

## Setting

Each line is an address that changes something: the action it needs, the roles that hold that action, and every value it accepts. A value not listed is ignored. Where no value is listed, the address does one thing to the record it names.

<!-- The table below is written by the command. Do not edit it by hand. -->

| Action | Roles | Address | What It Does | Values It May Set |
|---|---|---|---|---|
| Add or Change Aircraft | Continuing Airworthiness Manager, Planning and Records | `/aircraft/add/` | Add an aircraft | Aircraft Registration; Type Rating; Serial Number; Aircraft Manufacturer; Manufacturer’s Designation; Owned By; Regime; Date of Airframe Hours; Airframe Hours; Airframe Cycles; Records Expected for a Transfer In |
| Add or Change Aircraft | Continuing Airworthiness Manager, Planning and Records | `/aircraft/<uuid:aircraft_id>/details/` | Record the serial number, manufacturer and designation of an aircraft | Aircraft Serial Number; Aircraft Manufacturer; Manufacturer’s Designation |
| Enter Utilisation | Continuing Airworthiness Manager, Planning and Records | `/aircraft/<uuid:aircraft_id>/hours-and-cycles/` | Enter hours and cycles. The page names the aircraft throughout (REQ-026) | Counter; Date; Total Hours; Total Cycles; Corrects an Earlier Entry; Confirm This Unusual Increase |
| Add or Change Aircraft | Continuing Airworthiness Manager, Planning and Records | `/aircraft/<uuid:aircraft_id>/unserviceable/` | Record the aircraft as Unserviceable, with a reason and a date (REQ-023) | Reason; Unserviceable Since |
| Add or Change Aircraft | Continuing Airworthiness Manager, Planning and Records | `/aircraft/<uuid:aircraft_id>/serviceable/` | Record the aircraft as Serviceable (REQ-023) | None |
| Add or Change Aircraft | Continuing Airworthiness Manager, Planning and Records | `/aircraft/<uuid:aircraft_id>/counters/` | Add an engine or a propeller as a counter (REQ-020) | Counter; Position; Serial Number |
| Add or Change Aircraft | Continuing Airworthiness Manager, Planning and Records | `/aircraft/<uuid:aircraft_id>/records-received/` | Update the count of records received, and move a complete transfer to the Fleet | Records Received; Whether the Transfer Is Complete |
| Change Maintenance Programme | Continuing Airworthiness Manager | `/aircraft/<uuid:aircraft_id>/programme/set-up/` | Record or change the programme of an aircraft (REQ-040) | Basis; Minimum Inspection Programme For; Programme Reference; Planning Hours a Day; Planning Cycles a Day |
| Change Maintenance Programme | Continuing Airworthiness Manager | `/aircraft/<uuid:aircraft_id>/programme/tasks/add/` | Add a task to the programme (REQ-041) | Task; Kind; Runs Against; Source; Every Hours; Every Cycles; Every Months; Every Days; First at Hours; First at Cycles; First at Months; First at Days; Counted From, If Never Yet Done; Hours Then; Cycles Then |
| Record Maintenance Programme Review | Continuing Airworthiness Manager, Airworthiness Review Staff | `/aircraft/<uuid:aircraft_id>/programme/review/` | Record the annual review of the programme (REQ-053) | Reviewed |
| Record Accomplishment | Continuing Airworthiness Manager, Planning and Records | `/aircraft/<uuid:aircraft_id>/work/add/` | Record work done on the aircraft (REQ-050 to REQ-052) | Programme Task, If It Was One; Work; Completed; Hours; Cycles; Certificate of Release to Service; Release Entered in the Records, If Before Today; Pilot-Owner Maintenance; Organisation Told |
| Change Maintenance Programme | Continuing Airworthiness Manager | `/tasks/<uuid:task_id>/retire/` | Take a task out of the programme. It stays in the record | None |
| Record Accomplishment | Continuing Airworthiness Manager, Planning and Records | `/work/<uuid:work_id>/release/` | Record that the certificate of release to service is in the records (REQ-051) | Certificate of Release to Service |
| Record Airworthiness Directive | Continuing Airworthiness Manager, Planning and Records | `/directives/add/` | Record a directive (REQ-060) | Directive Number; Issuing Authority; Subject; Effective Date; Revision; Supersedes |
| Decide Directive Applicability | Continuing Airworthiness Manager | `/aircraft/<uuid:aircraft_id>/directives/<uuid:directive_id>/decide/` | Decide whether one directive applies to one aircraft (REQ-061 to REQ-063) | Applicability; Basis; Action Runs Against; Counted From; Hours Then; Cycles Then; First Within Hours; First Within Cycles; First Within Months; First Within Days; Then Every Hours; Then Every Cycles; Then Every Months; Then Every Days |
| Record Directive Compliance | Continuing Airworthiness Manager, Planning and Records | `/directive-decisions/<uuid:applicability_id>/comply/` | Record compliance with a directive on one aircraft (REQ-064) | Method of Compliance; Completed; Hours; Cycles; Certificate of Release to Service; Release Entered in the Records, If Before Today |
| Decide Directive Applicability | Continuing Airworthiness Manager | `/directive-decisions/<uuid:applicability_id>/terminate/` | Record a terminating action. Earlier compliance stays in the record (REQ-066) | Terminating Action; Terminated |
| Record Maintenance Data | Continuing Airworthiness Manager, Planning and Records | `/maintenance-data/add/` | Record a set of maintenance data (REQ-080) | Title; Author; Kind; Applies to Type Ratings, One on Each Line; Carries Mandatory Instructions or Airworthiness Limitations; Held; Revision; Revision Date; Amendment Service; Next Amendment Check By; Provided By, If Customer-Provided; Amendment Status Shown By; Shown On |
| Record Maintenance Data | Continuing Airworthiness Manager, Planning and Records | `/maintenance-data/<uuid:data_set_id>/revisions/` | Record a new revision, superseding the current one (REQ-085) | Revision; Revision Date |
| Record Amendment Check | Continuing Airworthiness Manager, Planning and Records | `/maintenance-data/<uuid:data_set_id>/checks/` | Record a check of the amendment status (REQ-082) | Checked; Result; Next Amendment Check By |
| Record Maintenance Data | Continuing Airworthiness Manager, Planning and Records | `/maintenance-data/<uuid:data_set_id>/customer-status/` | Record how the customer showed the amendment status of their data (REQ-086) | Amendment Status Shown By; Shown On |
| Record Maintenance Data | Continuing Airworthiness Manager, Planning and Records | `/maintenance-data/<uuid:data_set_id>/no-longer-held/` | Mark data as No Longer Held (REQ-087) | No Longer Held From |
| Manage Users and Roles | Administrator | `/review-staff/add/` | Record a person as airworthiness review staff | Person; Authorisation Reference; Accepted; Qualified Under Part-66; Months of Continuing Airworthiness Management in the 2-Year Period; Last Review Before These Records |
| Manage Users and Roles | Administrator | `/review-staff/<uuid:staff_id>/involvement/` | Change the recorded months of involvement. A lapse already reached is recorded first | Months of Continuing Airworthiness Management in the 2-Year Period; Last Review Before These Records |
| Manage Users and Roles | Administrator | `/review-staff/<uuid:staff_id>/restoration/` | Record a review under supervision that restores a lapsed authorisation (REQ-114) | Review Under Supervision; Supervised by Review Staff; Or Supervised by the Civil Aviation Authority, Named |
| Add or Change Aircraft | Continuing Airworthiness Manager, Planning and Records | `/aircraft/<uuid:aircraft_id>/review/certificates/` | Record a certificate issued elsewhere, or by the organisation before these records | Certificate Reference; Issued by Review Staff of This Organisation, Before These Records; Or Issued Elsewhere By; Date of Issue; Date of Expiry; Airframe Flight Hours at the Review |
| Carry Out Airworthiness Review | Airworthiness Review Staff | `/aircraft/<uuid:aircraft_id>/review/start/` | Start a review of an aircraft, as the signed-in member of review staff | None |
| Carry Out Airworthiness Review | Airworthiness Review Staff | `/reviews/<uuid:review_id>/details/` | Record who assisted at the survey, the airframe hours and the state of the programme | Assisted at the Survey By; Airframe Flight Hours at the Review; Maintenance Programme |
| Issue Airworthiness Review Certificate | Airworthiness Review Staff | `/reviews/<uuid:review_id>/issue/` | Issue the certificate for a completed review (REQ-109, REQ-110) | None |
| Carry Out Airworthiness Review | Airworthiness Review Staff | `/review-items/<uuid:item_id>/` | Record the result of one point | Result; Evidence Sampled; Finding |
| Carry Out Airworthiness Review | Airworthiness Review Staff | `/review-items/<uuid:item_id>/close/` | Record how a finding was closed | How It Was Closed |
| Issue Airworthiness Review Certificate | Airworthiness Review Staff | `/certificates/<uuid:certificate_id>/void/` | Void a certificate. It stays in the record and its serial is not used again | Reason |
| Extend Airworthiness Review Certificate | Continuing Airworthiness Manager, Airworthiness Review Staff | `/certificates/<uuid:certificate_id>/extend/` | Extend a certificate, each condition of ML.A.901(c) confirmed (REQ-104 to REQ-106) | Continuously Managed by This Organisation for the Previous 12 Months; Maintained for the Previous 12 Months by Approved Maintenance Organisations; No Evidence or Reason to Believe the Aircraft Is Not Airworthy |
| Record Copy Sent to the Civil Aviation Authority | Continuing Airworthiness Manager, Airworthiness Review Staff, Planning and Records | `/certificates/<uuid:certificate_id>/copy-sent/` | Record the copy of a certificate sent to the authority (REQ-111) | Copy Sent |
| Record Copy Sent to the Civil Aviation Authority | Continuing Airworthiness Manager, Airworthiness Review Staff, Planning and Records | `/extensions/<uuid:extension_id>/copy-sent/` | Record the copy of an extended certificate sent to the authority (REQ-111) | Copy Sent |
| Export Records | Administrator, Continuing Airworthiness Manager, Airworthiness Review Staff, Planning and Records | `/records-export/organisation/` | Export the complete record of the organisation | None |
| Export Records | Administrator, Continuing Airworthiness Manager, Airworthiness Review Staff, Planning and Records | `/aircraft/<uuid:aircraft_id>/export/` | Export the complete record of one aircraft | None |
| Import Records | Continuing Airworthiness Manager | `/imports/load/` | Load a file. It is loaded whole, or not at all with the reasons shown | What the File Holds; Source Records; File |
| Check Imported Records | Continuing Airworthiness Manager, Airworthiness Review Staff, Planning and Records | `/imports/<uuid:load_id>/check/` | Record the values checked against the source. Each is ticked or given by hand | For Each Value Loaded: That It Agrees with the Source, or the Value in the Source |
| Add to Problem Log | Administrator, Continuing Airworthiness Manager, Airworthiness Review Staff, Planning and Records | `/problem-log/add/` | Add an entry to the problem log | Problem |
| Add to Problem Log | Administrator, Continuing Airworthiness Manager, Airworthiness Review Staff, Planning and Records | `/problem-log/<uuid:problem_id>/notes/` | Add the action, the solution or a note to an entry | Add; What Was Done or Found |
| Change Organisation Record | Administrator | `/organisation/approval/` | Record the written approval to keep records in the system | Approval Reference; Approval Dated |
| Change Organisation Record | Administrator | `/organisation/parallel-run/` | Record the day the parallel run began | Parallel Run Started |
| Manage Users and Roles | Administrator | `/users/add/` | Add a user. The system makes their first password and shows it once | Full Name; User Name; Roles; Code From the Administrator's Authenticator Application |
| Manage Users and Roles | Administrator | `/users/<uuid:user_id>/roles/` | Set the roles a user holds | Roles; Code From the Administrator's Authenticator Application |
| Manage Users and Roles | Administrator | `/users/<uuid:user_id>/active/` | Make a user inactive, or active again | Active or Inactive; Code From the Administrator's Authenticator Application |
| Manage Users and Roles | Administrator | `/users/<uuid:user_id>/password/` | Give a user a new first password, made by the system and shown once | Code From the Administrator's Authenticator Application |
| Manage Users and Roles | Administrator | `/users/<uuid:user_id>/second-factor/` | Clear a user's second factor so that they set one up again | Code From the Administrator's Authenticator Application |
| Manage Users and Roles | Administrator | `/users/<uuid:user_id>/sessions/` | End every session of a user, for example when a device is lost | Code From the Administrator's Authenticator Application |
| None | Any Signed-In User, for Themselves | `/account/password/` | Change the signed-in user's own password | Current Password; New Password; New Password Again; Code From Your Authenticator Application |
| None | Any Signed-In User, for Themselves | `/account/sessions/` | End every other session of the signed-in user. This one continues | Code From Your Authenticator Application |
| None | Any Signed-In User, for Themselves | `/account/sessions/<uuid:session_id>/end/` | End one other session of the signed-in user | Code From Your Authenticator Application |
| None | Anyone, to Sign In or Out | `/sign-in/` | First step: user name and password | User Name; Password |
| None | Anyone, to Sign In or Out | `/sign-in/code/` | Second step: the code from the authenticator application | Code From the Authenticator Application |
| None | Anyone, to Sign In or Out | `/sign-in/set-up/` | First sign-in: add the account to an authenticator application and confirm a code | Code From the Authenticator Application |
| None | Anyone, to Sign In or Out | `/sign-out/` | End the session on the server | None |

<!-- End of the table written by the command. -->

## Values No Action Sets

The system sets these itself, whatever is sent:

- the organisation a record belongs to, which is the organisation of the signed-in user
- who made a change and when, and every entry of the history with its hash
- the serial and reference of a certificate issued in these records, and the last day of its validity
- the points of a review, which are those of ML.A.903
- the entries of the access log
- whether a password must be changed, and when a first password was given

## Values Fixed by the State of the Record

- Nothing is deleted. A change to a record adds an entry to its history, which keeps what the record said before.
- A certificate: its reference, dates, aircraft, issuer and serial never change once recorded. It can be voided, with a reason, and never made valid again. The day its copy was sent can be recorded.
- A review and its points cannot be changed once its certificate is issued. Before that, only the review staff member carrying it out records on it.
- An import, the values it loaded and the checks made of them are added to and never changed. Hours and cycles loaded by one person are checked by another.
- A note on a problem, an entry of the history and an entry of the access log are added and never changed.
- The last active Administrator of an organisation cannot lose the role or be made inactive, and no one makes themselves inactive.
- The highest certificate serial stated for an organisation is set only by the owner of the tables, outside the application, and is never lowered.
