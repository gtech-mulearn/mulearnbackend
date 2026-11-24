# Module catalogue

The business modules of the target architecture, plus `building_blocks`. At `dev` 7fd66060 none of them exists yet: their tables are mapped in the legacy `db/` app. A module is created, with `python manage.py new_module <name>`, when its first table moves. The generator accepts only names listed in this table.

Each page lists what the module owns, who writes its tables today (from an AST scan of 7fd66060), its public API, its events, and the issues that build it.

| Module | Kind | Owns (summary) | Status at 7fd66060 | Phase |
|---|---|---|---|---|
| [building_blocks](building_blocks.md) | Plumbing | outbox, inbox, dead letters, idempotency, flags, schedule runs, service clients, audit | not started | 1, 3, 4 |
| [contributions](contributions.md) | Core | submissions (`karma_activity_log`), the karma ledger, `wallet.karma` | not started | 4 |
| [gamification](gamification.md) | Core | levels, achievements, period totals, boards | not started | 6 |
| [identity_access](identity_access.md) | Supporting | roles, scoped grants | not started | 5 (μCoin tickets in 3) |
| [people](people.md) | Supporting | profiles, settings, socials, consent | not started | 7 (first event in 3) |
| [organizations](organizations.md) | Supporting | organisations, colleges, geography, chapters | not started | later |
| [communities](communities.md) | Supporting | interest groups, learning circles, channels | not started | later |
| [learning](learning.md) | Supporting | tasks, task types, skills | not started | later |
| [rewards](rewards.md) | Supporting | vouchers, coupons, referrals; coin tables frozen | not started | 8 |
| [events](events.md) | Supporting | events, hackathons | not started | later |
| [mentorship](mentorship.md) | Supporting | mentor applications, sessions | not started | later |
| [careers](careers.md) | Supporting | companies, jobs, applications | not started | later |
| [interns](interns.md) | Supporting | intern tasks, timesheets, reviews | not started | later (karma writes in 4) |
| [media](media.md) | Supporting | comics, media content | not started | later |
| [projects](projects.md) | Supporting | projects, impact projects | not started | later |
| [notifications](notifications.md) | Generic | in-app, push and email delivery | not started | 6 |
| [integrations](integrations.md) | Generic | Discord and partner integrations | not started | 4 |
| [payments](payments.md) | Generic | donations, provider webhooks | not started | later |
| [administration](administration.md) | Generic | platform settings, URL shortener | not started | later |
| [analytics](analytics.md) | Generic (deferred) | nothing until its trigger | deferred | trigger |

The rules every module follows are in [04-module-rules.md](../04-module-rules.md).
