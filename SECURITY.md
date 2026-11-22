# Security policy

## Reporting a vulnerability

**Report security problems privately, never in a public issue, pull request, discussion or chat.** That includes anything that could expose another user's data, let someone act as another user or gain a role, change karma or money, or reach an endpoint their roles shouldn't allow.

1. Open the repository's **Security** tab and choose **Report a vulnerability** ([direct link](https://github.com/gtech-mulearn/mulearnbackend/security/advisories/new)). Only the maintainers can read the report.
2. Say what you found, where (the endpoint, the request, or the file), how to reproduce it, and what an attacker could do with it.
3. Don't test against other people's accounts or data, and don't run anything against production that you wouldn't run as an ordinary user. Use the local environment in [DEVELOPMENT.md](DEVELOPMENT.md).

If the problem is in the dashboard rather than the API, report it in [mulearn-dashboard](https://github.com/gtech-mulearn/mulearn-dashboard/security/advisories/new) the same way. If you're not sure which repository it belongs to, either is fine.

## What happens next

- A maintainer acknowledges the report, normally within 5 working days, and may ask you questions in the private advisory.
- The fix is prepared privately and released before the advisory is published. You're credited in the advisory unless you ask not to be.

## Supported versions

Only the current production release receives security fixes.
