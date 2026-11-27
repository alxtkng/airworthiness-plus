# ADR 0004. Work package records

27 November 2026

Work packages extend the system into the planning and documentation of maintenance carried out under a written work order. The applicable sources are CAO.A.055, AMC1 CAO.A.055, CAO.A.060, 145.A.45(e), 145.A.48(c), 145.A.50 and ML.A.801. REQ-320 to REQ-323 add the package, work cards, the issue and release checks, and their records export.

Issue takes a snapshot of the selected revision for each card. Later amendment checks and supersessions can update the Maintenance Data register while earlier packages keep the reference used.

The release uses the existing aircraft certificate workflow. The certificate references one package and its cards. Closure writes each card to its own aircraft, programme or directive record and links the common certificate in the same transaction. Record evidence as provided by the organisation. Staff qualifications for independent inspection are evidenced separately from their release authorisation.
