# Qlik Cloud (SaaS): What happens to a departed user's sheets and content

Scope: Qlik Cloud only (Qlik Sense Enterprise SaaS / Qlik Cloud Analytics capacity editions / Qlik Cloud Government). Research date: 2026-10-16. Client-managed QSEoW is out of scope.

## Q1. What happens to user-created content (apps, sheets, bookmarks, stories) when a user is deleted vs. disabled vs. removed from the IdP?

### Takeaway
Deleting a user in Qlik Cloud does NOT delete their apps, spaces, scripts or data connections; these "remain in the tenant without an owner" (orphaned). Alerts/notifications and automations (plus automation connections) ARE deleted. The official deletion docs are silent about sheets, bookmarks and stories, but Qlik Support and qlik.dev material indicate private/community app objects remain inside the app as orphaned objects (not deleted), while approved/base sheets cannot be orphaned at all. Disabling a user or removing their entitlement leaves owned resources intact. Removing the user from the IdP is a separate step: deletion in Qlik alone does not stop an IdP user logging back in (creating a new user record with a new ID).

### Cited Findings
**Deletion: official help (user-based and capacity-based subscription pages say the same)**
- When a user is deleted, "any spaces, applications, scripts, and data connections they owned will remain in the tenant without an owner"; Qlik says these "must be reassigned to a new owner" (ideally before deletion), otherwise reload failures can occur. — [Qlik Help: Deleting users (capacity-based)](https://help.qlik.com/en-US/cloud-services/Subsystems/Hub/Content/Sense_Hub/Admin/SaaS-delete-users-capacity-model.htm); [Qlik Help: Deleting users](https://help.qlik.com/en-US/cloud-services/Subsystems/Hub/Content/Sense_Hub/Admin/SaaS-delete-users.htm)
- Reload schedules owned by the user: "ownership must be reassigned or a new schedule created" to avoid scheduled reload failures. — [Qlik Help: Deleting users](https://help.qlik.com/en-US/cloud-services/Subsystems/Hub/Content/Sense_Hub/Admin/SaaS-delete-users.htm)
- Published apps: "The published copy of the application will inherit the owner of the source application"; to change it, change the source app owner and republish. — [Qlik Help: Deleting users](https://help.qlik.com/en-US/cloud-services/Subsystems/Hub/Content/Sense_Hub/Admin/SaaS-delete-users.htm)
- "Notifications and alerts owned by the user are deleted from the system." "Automations and automation connections owned by the user are deleted from the system." — [Qlik Help: Deleting users](https://help.qlik.com/en-US/cloud-services/Subsystems/Hub/Content/Sense_Hub/Admin/SaaS-delete-users.htm)
- Other effects: all PII removed; any active session invalidated; "API keys associated with the user are revoked"; audit log entries of the deletion event are retained. Users can only be deleted one at a time, and an admin cannot delete themself. — [Qlik Help: Deleting users](https://help.qlik.com/en-US/cloud-services/Subsystems/Hub/Content/Sense_Hub/Admin/SaaS-delete-users.htm)
- The official "Deleting users" pages do not mention sheets, bookmarks, stories, private content or community content at all. — [Qlik Help: Deleting users (capacity-based)](https://help.qlik.com/en-US/cloud-services/Subsystems/Hub/Content/Sense_Hub/Admin/SaaS-delete-users-capacity-model.htm)
- Qlik Support lists "Orphaned personal objects (owner deleted)" as recoverable/reassignable, so private objects of a deleted user still exist in the app after deletion. A deleted sheet, by contrast, "cannot be recovered." (Article created 2024-03-08, last updated 2026-09-04.) — [Qlik Support: Is it possible to recover a deleted app or sheet?](https://community.qlik.com/t5/Official-Support-Articles/Qlik-Cloud-Analytics-Is-it-Possible-to-Recover-a-Deleted-App-or/ta-p/2428385)
- A customer comment on that article (PythonMCSJ, 2025-02-28; not verified by Qlik) reports that after Azure IdP-driven user deletion, private and community content (sheets, bookmarks, stories) was NOT deleted in the orphaned apps, and they moved it all back to the restored users with an OAuth M2M token and a PowerShell script. Restored users received new user IDs, so content stayed tied to the old IDs until reassigned. — [Qlik Support article comments](https://community.qlik.com/t5/Official-Support-Articles/Qlik-Cloud-Analytics-Is-it-Possible-to-Recover-a-Deleted-App-or/ta-p/2428385)
- qlik.dev (OEM maintenance guidance): "Inactive user's sheets are often orphaned, unless they have a published status of `true`." Sheets with an approved status of `true` are base sheets and "cannot be orphaned." "Private sheets are owned by individual users." — [qlik.dev: Maintenance activities](https://www.qlik.dev/manage/oem/operate/maintenance/)

**Disabled / entitlement removed**
- "Removing a user's entitlement does not affect any resources owned by the user." With dynamic assignment enabled, an active user gets an entitlement back at next login; "To prevent this, you can disable the user." — [Qlik Help: Managing user entitlements](https://help.qlik.com/en-US/cloud-services/Subsystems/Hub/Content/Sense_Hub/Admin/SaaS-user-allocations.htm)
- Qlik help describes the Disabled status as: "The user entitlement is removed and the user cannot access their account or use the product. All alerts owned by the user will be disabled." (Wording seen in a search snippet from help.qlik.com entitlement pages; the exact page could not be re-fetched to confirm.) — [Qlik Help: Managing user entitlements (capacity)](https://help.qlik.com/en-US/cloud-services/Content/Sense_Hub/Admin/SaaS-user-entitlements-capacity-model.htm)

**IdP removal**
- Deleting a user in Qlik Cloud does not stop an IdP user logging in again: a new login creates "a new tenant user record", possibly with automatic license assignment. Qlik advises removing the user from the IdP too. Deleting the tenant user "does not remove them from Qlik Account." — [Qlik Help: Deleting users](https://help.qlik.com/en-US/cloud-services/Subsystems/Hub/Content/Sense_Hub/Admin/SaaS-delete-users.htm)

### Inferences
- Disabling a user (or removing their entitlement) is the "safe" offboarding state for content. The user record and its ID still exist, so private, community and approved sheets keep a valid owner, and an admin can still script ownership transfers. Deletion is the step that orphans content.
- If someone with the same IdP identity logs in after deletion, Qlik creates a new user record with a new ID. That person does not get their old content back automatically, because objects stay tied to the deleted user ID.
- Because deletion orphans private/community objects rather than deleting them, content in managed spaces is not destroyed by user deletion. The risk is that it becomes unmanageable through the UI.

### Gaps
- No official help page states explicitly whether a deleted user's community (published-but-not-approved) sheets stay visible to consumers in managed spaces. Evidence that they remain comes indirectly from the qlik.dev "orphaned" wording and a customer report, not from a Qlik test statement.
- I could not re-fetch the help page that defines the "Disabled" status to confirm the exact wording.
- Nothing found on whether removing a user through SCIM/IdP deprovisioning sets Disabled or Deleted automatically in Qlik Cloud.

## Q2. What ownership-transfer options are documented?

### Takeaway
Through the UI, admins can change the owner of spaces, apps, scripts and data connections in Administration > Content (filter Owner = "Deleted User"). Individual sheets, bookmarks and stories have no UI owner-transfer. For these, use the Apps REST API (`POST /v1/apps/{appId}/objects/{objectId}/actions/change-owner`, also available as `qlik app object change-owner` and `apps.updateAppObjectOwner` in qlik-api), called by an OAuth M2M "private content bot" with the `admin.apps` scope. Changing an app's owner does NOT transfer the previous owner's private sheets.

### Cited Findings
- UI steps to reassign before deletion: Administration activity center > Spaces > filter by owner > "..." > Change owner > Apply. Repeat for applications, scripts and data connections on the Content page. — [Qlik Help: Deleting users](https://help.qlik.com/en-US/cloud-services/Subsystems/Hub/Content/Sense_Hub/Admin/SaaS-delete-users.htm)
- Orphaned apps after deletion: Administration > Content > Apps tab, filter the Owner column by "Deleted User", then ellipsis > Change Owner. (Article dated 2024-09-27.) — [Qlik Support: Can the owner of orphaned apps be changed?](https://community.qlik.com/t5/Official-Support-Articles/Qlik-Cloud-Analytics-Can-the-owner-of-orphaned-Apps-be-changed/ta-p/2484034)
- Change-owner endpoint for app objects, announced 2023-05-09: `POST /v1/apps/{appId}/objects/{objectId}/actions/change-owner`, body `{"ownerId":"string"}`. Built to support client-managed-to-cloud migration, so that private and community content (bookmarks, stories, sheets, snapshots) is preserved. Restriction: "You must own the object to change it's ownership to another user." — [qlik.dev changelog 38](https://qlik.dev/changelog/38-api-updates-changeowner/)
- Qlik Support procedure for orphaned personal objects: create an OAuth M2M client, make sure the `admin.apps` scopes are enabled, authenticate qlik-cli with it, list objects with `qlik app object ls -a APPID`, then run `qlik app object change-owner --appId APPID --objectId OBJECTID --ownerId NEWOWNERID`. Caveat: "We currently don't show the current owner of each object. You will need to find a way to identify the correct object." — [Qlik Support: Recover deleted app or sheet](https://community.qlik.com/t5/Official-Support-Articles/Qlik-Cloud-Analytics-Is-it-Possible-to-Recover-a-Deleted-App-or/ta-p/2428385)
- 2024-03-26: the `admin.apps` scope was extended so tokens of OAuth bot accounts (M2M clients) get "non-interactive access to the personal and private resources end users in tenants can create and curate." Listed use cases include accessing orphaned content after a user leaves, moving ownership between personal spaces, publishing app content into shared/managed spaces, and extracting private app content from managed spaces (for example promoting it to base). It "is not available in Qlik Cloud graphical user interfaces," only via qlik-cli, qlik-api or REST. — [qlik.dev changelog 86](https://qlik.dev/changelog/86-m2m-access-personal-metadata/)
- "Managing personal and private content" tutorial (updated 2025-12-08): an OAuth M2M client with `admin.apps` + `admin_classic` scopes can list personal-space apps (`items.getItems({resourceType:"app", spaceType:"personal"})`), list private sheets (`app.getSheetList()`), publish a private sheet (`sheet.publish()` + `app.doSave()`), and duplicate a sheet then reassign it (`getFullPropertyTree` > `createObject` > `apps.updateAppObjectOwner(appId, objectId, {ownerId})`). The example was run on an app in a managed space. — [qlik.dev: Managing personal and private content](https://www.qlik.dev/manage/platform-operations/private-content-bots.md)
- A client-managed-to-cloud migration tutorial uses qlik-cli (PowerShell) plus Qlik Automate to import sheets, bookmarks and stories and reassign owners (not snapshots or ODAG links). — [qlik.dev: Migrate app objects](https://qlik.dev/manage/migrate/qlik-cli-app-objects-migrate/)
- Changing the app owner does not carry over private sheets. Qlik Support (Frank_S, 2024-12-04): "After testing this premise, I found that the private sheets are not saved unfortunately." Customer: private sheets "don't get transferred and are effectively lost." — [Qlik Community thread](https://community.qlik.com/t5/Move-to-Qlik-Cloud-Analytics/Anyone-ever-found-a-way-to-recover-private-sheets-that-belong-to/m-p/2496045)
- In the same thread, a customer reported that the CLI, API and automations "can ONLY change the owner of a sheet when that action is done by the current owner". After an MVP pointed to changelog 86 and the private-content-bot tutorial, the customer confirmed (2024-12-10): "I'm able to see/publish private sheets with that." — [Qlik Community thread](https://community.qlik.com/t5/Move-to-Qlik-Cloud-Analytics/Anyone-ever-found-a-way-to-recover-private-sheets-that-belong-to/m-p/2496045)
- Unofficial workaround (partner Chris Cammers, comment dated 2026-08-24, not official guidance): change the deleted/removed user's email through the Users API (Qlik Automate "Raw API Request" block or Postman on `users/{id}`), then log in with the new identity to inherit that profile's content. — [Qlik Support: orphaned apps article comments](https://community.qlik.com/t5/Official-Support-Articles/Qlik-Cloud-Analytics-Can-the-owner-of-orphaned-Apps-be-changed/ta-p/2484034)
- No Qlik Automate block exists to unpublish a sheet, and "a simple unpublish option cannot be done with the Qlik REST API." To transfer a published sheet's ownership it must first be unpublished. (Article 2025-05-19.) — [Qlik Support: Unpublish community sheets via Automate/REST?](https://community.qlik.com/t5/Official-Support-Articles/Qlik-Cloud-Analytics-Can-you-unpublish-community-sheets-with-a/ta-p/2518170)

### Inferences
- The "must own the object" restriction appears to be lifted in practice for an M2M bot token with `admin.apps`. That is how Qlik Support's orphaned-object procedure and the tutorial work, and an interactive admin user cannot do the same. This is inferred from the combination of sources; Qlik does not state it in one sentence.
- No first-party "transfer all content on delete" wizard was found for Qlik Cloud. Offboarding is a manual reassign-then-delete process, plus scripting for app objects.

### Gaps
- No Qlik-published Qlik Automate template specifically for reassigning orphaned sheets was found. There is a template to recover soft-deleted apps and one to alert about orphaned data connections.
- It is unconfirmed whether `change-owner` works directly on a published/community sheet or needs unpublishing first via the Engine API (`UnPublish`); the 2025 Support article implies unpublishing is required.

## Q3. Can community sheets of a deleted user still be viewed, duplicated or approved by others? Can private sheets be recovered by an admin?

### Takeaway
Approved (base) sheets belong to the app and are unaffected. Community sheets of a deleted user appear to remain in the app as orphaned objects; consumers who can view the space can likely still see them, and users with permissions can duplicate them into private copies. Nobody can unpublish, edit or delete them through the UI because only the owner can. Private sheets are invisible to everyone, including tenant admins in the UI, but an OAuth M2M bot with `admin.apps` can read, publish, duplicate or reassign them. This has been possible since March 2024.

### Cited Findings
- Base content: content public at publication time becomes app base content and "cannot be made private, but sheets and stories can be duplicated as private copies by users with sufficient permissions." Unpublishing a community sheet makes it private. "Private items are only visible to you." — [Qlik Help: Granting access to sheets, bookmarks, stories](https://help.qlik.com/en-us/cloud-services/Subsystems/Hub/Content/Sense_Hub/Share/make-public-or-private.htm)
- Approved (base) sheets "cannot be orphaned"; unapproved sheets of inactive users are often orphaned unless published. — [qlik.dev: Maintenance activities](https://www.qlik.dev/manage/oem/operate/maintenance/)
- "Duplicating a published sheet will create a private copy." Published sheets cannot be modified; they must be unpublished before deleting. — [Qlik Support: Unpublish community sheets](https://community.qlik.com/t5/Official-Support-Articles/Qlik-Cloud-Analytics-Can-you-unpublish-community-sheets-with-a/ta-p/2518170)
- Admin recovery of private sheets: an M2M bot can `getSheetList()`, `publish()` private sheets, or duplicate them and `updateAppObjectOwner`. — [qlik.dev: Managing personal and private content](https://www.qlik.dev/manage/platform-operations/private-content-bots.md); [qlik.dev changelog 86](https://qlik.dev/changelog/86-m2m-access-personal-metadata/)
- In the "New to Qlik Cloud" Q&A (August 2026), a Qlik panelist said users can take ownership of a departed colleague's never-published sheets, but the process is "script-based," "not a direct" UI process. — [Q&A with Qlik: New to Qlik Cloud, August 2026](https://community.qlik.com/t5/Video-Transcripts/Q-amp-A-with-Qlik-New-to-Qlik-Cloud-August-2026/ta-p/2554681)
- Feature request "allow tenant admins to change owners of all private sheets" (#442217) was filed by a customer after an older idea (idi-p/1736791, "Delete all user content and/or take ownership of…") was closed. — [Qlik Community: orphaned apps article comments](https://community.qlik.com/t5/Official-Support-Articles/Qlik-Cloud-Analytics-Can-the-owner-of-orphaned-Apps-be-changed/ta-p/2484034); [Qlik Community thread](https://community.qlik.com/t5/Move-to-Qlik-Cloud-Analytics/Anyone-ever-found-a-way-to-recover-private-sheets-that-belong-to/m-p/2496045)

### Inferences
- Whether consumers can still approve or unapprove an orphaned community sheet was not documented. Approving is a space-role action (manage/publish rights) rather than an owner action, so it plausibly still works, but this is unverified.
- The practical clean-up path for an orphaned community sheet is one of: (a) approve it so it becomes base content, which removes the orphan problem; (b) let a user duplicate it into a private copy, then re-publish; or (c) use an M2M bot to unpublish or reassign it.

### Gaps
- No Qlik test statement directly confirms the visibility of a deleted user's community sheets to consumers in managed spaces.
- No official statement on whether approve/unapprove works on orphaned community sheets.

## Q4. Is there an "orphaned" state or report, and how do admins find orphaned content?

### Takeaway
At the app level, yes: Administration > Content shows the owner as "Deleted User" and can be filtered on it. At the sheet/object level, no: there is no UI report, and the Support article warns that the object listing does not show current owners. Admins must script it with the Engine API (sheet list with owner metadata) and the Users API to check whether owners still exist.

### Cited Findings
- The Apps tab in Administration > Content can be filtered by Owner = "Deleted User". — [Qlik Support: orphaned apps](https://community.qlik.com/t5/Official-Support-Articles/Qlik-Cloud-Analytics-Can-the-owner-of-orphaned-Apps-be-changed/ta-p/2484034)
- `qlik app object ls` does not show object owners: "We currently don't show the current owner of each object." — [Qlik Support: Recover deleted app or sheet](https://community.qlik.com/t5/Official-Support-Articles/Qlik-Cloud-Analytics-Is-it-Possible-to-Recover-a-Deleted-App-or/ta-p/2428385)
- Recommended private-sheet hygiene: query all private sheets with the Engine API (the App Analyzer does not list sheets that were never accessed), find sheets with no access in 90+ days from Audits API data, check whether owners are still active, notify owners, then delete after a confirmation period. — [qlik.dev: Maintenance activities](https://www.qlik.dev/manage/oem/operate/maintenance/)
- A built-in template "Alert app owners and Tenant Admins about orphaned data connections" exists for orphaned data connections. — [qlik.dev: Maintenance activities](https://www.qlik.dev/manage/oem/operate/maintenance/)
- Admin Content section (2026): a Qlik panelist said a Content section in the admin console now lets admins "do bulk deletes or moves, or change owners." This came up in the context of data files/QVDs; whether it covers sheets was not stated. — [Q&A with Qlik: August 2026](https://community.qlik.com/t5/Video-Transcripts/Q-amp-A-with-Qlik-New-to-Qlik-Cloud-August-2026/ta-p/2554681)

### Inferences
- An admin can build an "orphaned sheets" report by joining Engine `GetObjects`/`getSheetList` owner IDs (`qMeta.owner`) against the Users API list. No out-of-the-box report exists.

### Gaps
- Not confirmed: whether the 2026 admin Content section shows or handles app objects (sheets) and their owners.

## Q5. License/entitlement implications

### Takeaway
Deleting an Active or Disabled user frees their entitlement. Disabling removes the entitlement and blocks access while keeping the user record and all owned content. Removing an entitlement alone does not affect owned resources, but dynamic assignment may re-grant it at the next login unless the user is disabled.

### Cited Findings
- "Deleting an active or disabled user frees up a user entitlement that can be assigned to another user." — [Qlik Help: Deleting users](https://help.qlik.com/en-US/cloud-services/Subsystems/Hub/Content/Sense_Hub/Admin/SaaS-delete-users.htm)
- "Removing a user's entitlement does not affect any resources owned by the user"; to stop dynamic re-assignment, "you can disable the user." — [Qlik Help: Managing user entitlements](https://help.qlik.com/en-US/cloud-services/Subsystems/Hub/Content/Sense_Hub/Admin/SaaS-user-allocations.htm)
- Disabled status: "The user entitlement is removed and the user cannot access their account or use the product. All alerts owned by the user will be disabled." (from a help.qlik.com search snippet; not re-verified) — [Qlik Help: Managing user entitlements (capacity)](https://help.qlik.com/en-US/cloud-services/Content/Sense_Hub/Admin/SaaS-user-entitlements-capacity-model.htm)
- If a license remains assigned to a user who is no longer visible, it can be removed with `qlik license assignment ls` / `qlik license assignment delete` (2023 Support article; older behavior). — [Qlik Support: license remains assigned to deleted user](https://community.qlik.com/t5/Official-Support-Articles/Qlik-Cloud-license-remains-assigned-to-deleted-user/ta-p/2051581)
- Re-login through the IdP after deletion may trigger automatic license assignment. — [Qlik Help: Deleting users](https://help.qlik.com/en-US/cloud-services/Subsystems/Hub/Content/Sense_Hub/Admin/SaaS-delete-users.htm)

### Inferences
- Under capacity-based subscriptions (Full/Basic users), a disabled user should not consume a Full User entitlement, so keeping departed users Disabled while content is triaged is cheap. This is inferred from "entitlement is removed", not stated in licensing terms.

### Gaps
- No source found on whether disabled users count against any capacity metric other than entitlements.

## Q6. Changes 2024-2026

### Takeaway
The main change is March 2024: OAuth M2M bots with `admin.apps` can access private and personal content, making departed users' private sheets recoverable by script. Before that, private sheets of departed users were effectively unrecoverable. Everything else (UI Change Owner for apps, spaces and connections; deletion semantics) has been stable. A 2026 admin Content section offers bulk move/delete/change owner, but sheet-level coverage is not confirmed.

### Cited Findings
- 2023-05-09: app object change-owner endpoint added (owner-only restriction). — [qlik.dev changelog 38](https://qlik.dev/changelog/38-api-updates-changeowner/)
- 2024-03-26: `admin.apps` extended for M2M access to personal/private resources; API/CLI only, not in the GUI. — [qlik.dev changelog 86](https://qlik.dev/changelog/86-m2m-access-personal-metadata/)
- 2024-09-27: Support article documents Administration > Content > filter "Deleted User" > Change Owner for apps. — [Qlik Support](https://community.qlik.com/t5/Official-Support-Articles/Qlik-Cloud-Analytics-Can-the-owner-of-orphaned-Apps-be-changed/ta-p/2484034)
- 2024-12: community thread confirms app owner change does not move private sheets, and that the M2M bot approach works. — [Qlik Community thread](https://community.qlik.com/t5/Move-to-Qlik-Cloud-Analytics/Anyone-ever-found-a-way-to-recover-private-sheets-that-belong-to/m-p/2496045)
- 2025-02: Support article author moved "Automations belonging to a deleted user" to the not-recoverable list (the article body as of 2026-09 still lists orphaned automations under recoverable, which is inconsistent; the help docs say automations are deleted with the user). — [Qlik Support: Recover deleted app or sheet](https://community.qlik.com/t5/Official-Support-Articles/Qlik-Cloud-Analytics-Is-it-Possible-to-Recover-a-Deleted-App-or/ta-p/2428385); [Qlik Help: Deleting users](https://help.qlik.com/en-US/cloud-services/Subsystems/Hub/Content/Sense_Hub/Admin/SaaS-delete-users.htm)
- 2025-12-08: private content bots tutorial updated. — [qlik.dev: Managing personal and private content](https://www.qlik.dev/manage/platform-operations/private-content-bots.md)
- August 2026: admin console Content section with bulk delete/move/change owner, mentioned in a Qlik Q&A; private sheet ownership still described as "script-based." — [Q&A with Qlik: August 2026](https://community.qlik.com/t5/Video-Transcripts/Q-amp-A-with-Qlik-New-to-Qlik-Cloud-August-2026/ta-p/2554681)

### Inferences
- Older forum claims that "admins cannot access private sheets in Qlik Cloud" (pre-March 2024) are outdated for API/bot access, but still true for the UI.

### Gaps
- No official "What's new" entry found for a user-deletion-with-content-transfer wizard in Qlik Cloud as of October 2026. Idea #442217 (admin change owner of all private sheets) has no confirmed delivery.
