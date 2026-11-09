"""
Onboarding completeness.

Deliberately free of Django imports so the rule can be unit-tested without a
database (see utils/test_onboarding.py). The caller supplies the facts; this
module only decides.

Why this exists
---------------
Whether someone has finished onboarding was decided in the browser:

    if (!user.user_domains || user.user_domains.length === 0) {
        router.replace("/onboarding/interests");
    }

That has three problems, and "Sign in with muLearn" makes all three worse.

1. It is a CLIENT-side rule. The dashboard applies it; nothing else does. Once
   other apps can sign people in, every one of them would have to reimplement
   it from the same raw fields, and they would drift.
2. It conflates "has picked interests" with "has onboarded". Those are the same
   thing today by accident, not by design.
3. The company exemption is hardcoded in the dashboard, so a second client
   would send company users into an onboarding flow built for students.

Express signup makes this urgent rather than merely untidy: someone who signs
up through a partner app has NO interests by definition, so every consumer must
agree on what that means.

The rule itself is unchanged. It has moved, and it is now stated once.
"""

# Role titles exempt from interest selection. Companies onboard through their
# own verification flow and must never be routed into the student one.
EXEMPT_ROLES = frozenset({"Company"})

STATE_COMPLETE = "COMPLETE"
STATE_INCOMPLETE = "INCOMPLETE"

# Steps a consumer can be told to collect. Kept as constants so a client cannot
# match on a string that quietly changes shape later.
STEP_INTERESTS = "interests"


def onboarding_status(*, roles, domain_count):
    """
    Whether this member still has onboarding to do.

    :param roles: role titles held by the member, any iterable of str.
    :param domain_count: how many user_domains rows they have. An int, so the
        caller can pass a COUNT and avoid loading the rows.
    :returns: {"state": ..., "missing": [...], "exempt": bool}

    `missing` is ordered and safe to walk: it is what a client should ask for,
    in the order it should ask.
    """
    role_set = {str(r) for r in (roles or [])}
    exempt = bool(role_set & EXEMPT_ROLES)

    if exempt:
        # Not "complete" as a value judgement — exempt from THIS checklist.
        # Reported separately so a client can tell the two apart rather than
        # inferring the company case from an empty `missing` list.
        return {"state": STATE_COMPLETE, "missing": [], "exempt": True}

    missing = []
    if not domain_count:
        missing.append(STEP_INTERESTS)

    return {
        "state": STATE_COMPLETE if not missing else STATE_INCOMPLETE,
        "missing": missing,
        "exempt": False,
    }
