# Storage for Backups Away From the Server

Date: 19 November 2026. REQ-151; CAO.A.090(e); threats TH-040, TH-041; Issue 27. A recommendation for Alex King. Nothing has been bought, and buying it is his.

## What the Storage Must Do

From `backup-and-restore.md`:

| Need | Why |
|---|---|
| Hold what it is given so that it cannot be deleted or overwritten for a set period, by anyone, the account owner included | TH-041. A stolen server credential, or a mistake, cannot destroy the backups |
| Give the server a credential that can add and cannot delete | The same |
| Be in the United Kingdom | The question of where records are held is then answered once, in `data-protection/record-of-processing.md` |
| Be run by a different company from the one that hosts the server | One failure or one closed account does not take both |
| Charge by what is stored, with no monthly minimum | A backup of the slice is small: the one in the restore test of 19 November 2026 was 235,881 bytes |

The backup is encrypted before it leaves the server, to a key the server does not hold (TH-040). So the storage company cannot read it, whichever is chosen.

## What Was Found

Looked for on 19 November 2026. **The providers' own price lists and documentation could not be opened from the build session: its network does not reach them.** What follows is from third-party price trackers and reviews. Every figure and every feature is To Be Checked on the provider's own pages before buying.

| Provider | United Kingdom | Cannot Be Deleted | Charge, as Reported | Monthly Minimum, as Reported |
|---|---|---|---|---|
| Amazon S3, Europe (London) | Yes | Object Lock | About 0.024 US dollars for a gigabyte a month | None reported |
| Wasabi, London | Yes | Object Lock | About 6.99 US dollars for a terabyte a month | Charged as 1 terabyte; an object deleted early is charged for its minimum period |
| IDrive e2 | London reported in 2023; not confirmed now | Object Lock | Reports differ: 4 to 6 US dollars for a terabyte a month | Charged as 1 terabyte |
| Backblaze B2 | Not found: a European region is reported, no United Kingdom one | Object Lock | About 6.95 US dollars for a terabyte a month | None reported |

## Recommendation

**Amazon S3 in the London region, with Object Lock in its compliance mode.**

- It is the only one of the four found to be both in the United Kingdom and charged by what is stored with no minimum. At this size the cost is pence a month; two of the others would charge for a terabyte to hold megabytes.
- Compliance mode is the setting in which nobody, the account owner included, can delete a locked object or shorten its period. To Be Checked on Amazon's own pages before the bucket is made, because it cannot be undone for objects already locked.
- The lock periods follow `backup-and-restore.md`, which proposes every daily backup for 35 days and the first of each month for 12 months: 35 days by default, and 12 months set on the first backup of a month when it is written. Both periods are his to confirm, and the second needs a small change to `backup.sh` at deployment.

Two things are not known here and decide whether this stands:

1. **Who hosts the server.** If it is Amazon, the storage should be with another company, and Wasabi in London is then the choice despite its minimum.
2. **Whether the company already has an account with any of these.**

## What Alex King Does

1. Open or use an account, with two-factor sign-in on it.
2. Make one bucket in the London region with versioning and Object Lock on, compliance mode, default period 35 days.
3. Make one credential for the server that may add objects to that bucket and nothing else.
4. Put that credential on the server himself. It is never typed into a build session and never committed.

After that the delete attempt in `backup-and-restore.md` is run and shown refused, and REQ-151 can be tested.
