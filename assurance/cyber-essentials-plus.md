# Cyber Essentials Plus: Gaps

Step 7 of private beta. Date: 19 November 2026. Certification, its cost and its timing are Alex King's decisions.

## Status of This Document

Cyber Essentials is the United Kingdom government scheme run for the National Cyber Security Centre; Cyber Essentials Plus adds a hands-on audit by a certification body. The scheme's current requirements document could not be read in this session, because the build environment cannot reach the National Cyber Security Centre's website. **Every statement below of what the scheme asks is from memory of earlier versions and is To Be Checked against the current Requirements for IT Infrastructure before it is relied on.** Nothing here should be quoted to a customer or an assessor as it stands.

The scheme certifies an organisation, Airworthiness Limited, not the product. It covers the devices and services the company uses to do its work. What those are is known only to Alex King, so most rows below are questions.

## The Five Controls

| Control | What the Scheme Asks, To Be Checked | Known Today | Gap or Question |
|---|---|---|---|
| Firewalls | Every device in scope is behind a firewall; inbound connections are refused unless there is a documented need; default passwords on routers and firewalls are changed | The application answers only through the reverse proxy on HTTPS. The server's own firewall rules have not been seen | Which ports does the server answer on, and is each needed? What firewall protects the devices used for development and administration, at home and elsewhere? |
| Secure configuration | Unneeded software and accounts are removed; default passwords changed; a device locks; services that sign users in resist guessing | The application has no default account, no administration interface, locks sign-in after 5 failures and asks every user for two factors | The same for the server's management, the hosting account, GitHub, the domain registrar and email: are unused accounts removed, and is everything unneeded switched off? |
| Security update management | Software is supported by its maker and licensed; updates for serious vulnerabilities are applied within 14 days of release; unsupported software is removed | Python, Django and PostgreSQL versions are pinned and in support; `pip-audit` fails the build on a known vulnerability; a bill of materials is made on every build | Who applies operating system updates to the server, and how quickly? The same for every laptop and telephone used for the work. `operations/vulnerability-management.md` (Step 8) sets the times for the application |
| User access control | Each person has their own account; administrator accounts are used only for administration; multi-factor sign-in for every cloud service; passwords are long enough or protected by lock-out | The application: own accounts, role matrix, two factors for all. GitHub: two-factor sign-in is To Be Confirmed | Is multi-factor sign-in on for the hosting account, the server's management, GitHub, the registrar, email and anything holding backups? Is day-to-day work done from an account that is not an administrator of the device? |
| Malware protection | Each device has anti-malware software kept up to date, or runs only approved applications | Nothing known | What protects each laptop and telephone? The server runs only the services deployed to it; how that is shown to an assessor is To Be Checked |

## What the Plus Audit Adds, To Be Checked

- A scan from outside of everything the company exposes to the internet. For us that includes the service's address and the server's management address.
- A scan from inside of a sample of devices, signed in, looking for missing updates.
- Tests that malware protection works on those devices.
- Checks that multi-factor sign-in is in place on cloud services and that administrator accounts are separate.

## Gaps We Can See From Here

1. **The scope is not written down.** A list of every device, cloud service and account the company uses for this work is the first thing an assessor asks for. It does not exist in the repository, and should not hold anything private if it is added.
2. **The server is shared.** Corrected 20 November 2026: there is no existing server, so this does not arise until one is rented. As first written: Other projects run on it. Whether the certification can cover the server while they are on it, or whether this service needs to be apart from them, is a question for the certification body.
3. **Server updates.** No one is recorded as responsible for operating system updates on the server, and no time is set. Step 8 proposes one.
4. **Backups are a cloud service.** Wherever backups are kept off the server comes into scope and needs multi-factor sign-in.
5. **One person.** Separation of administrator and everyday accounts, and cover when that person is away, need a written answer for a company of one.

## Suggested Order

1. Alex King lists the devices, services and accounts in scope, privately.
2. Read the current requirements document and correct this one against it.
3. Take the scheme's own self-assessment questions for Cyber Essentials; fix what fails.
4. Choose a certification body and ask the two questions above about the shared server.
5. Cyber Essentials first, then the Plus audit within the time the scheme allows after it.
