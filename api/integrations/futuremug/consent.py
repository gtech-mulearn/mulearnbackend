"""
Futuremug consent text (spec B §3.3). Versions are append-only: when the text
changes, add a new builder and bump CURRENT_VERSION; never edit an old one,
so we can always show exactly what someone agreed to.
"""
from django.conf import settings

from api.integrations.partner_sso.consent import ConsentDocument, ConsentSection

CURRENT_VERSION = "fm-2026-10-12"

_APPROVAL_NOTE = "Futuremug reviews new company and college accounts. You can sign in once Futuremug approves yours."


def _fm_2026_10_12(account_type):
    subtitles = {
        "candidate": "Take assessments and AI or expert interviews on Futuremug.",
        "company": "Assess and interview candidates on Futuremug.",
        "college": "Run assessments and interviews for your students on Futuremug.",
    }
    notes = {
        "candidate": (),
        "company": (_APPROVAL_NOTE, "Only the company owner can connect and open Futuremug from µLearn."),
        "college": (_APPROVAL_NOTE,
                    "If your college's Lead Enabler changes, the new Lead Enabler can take over this "
                    "Futuremug account, and you will no longer be able to sign in to it."),
    }
    return ConsentDocument(
        version="fm-2026-10-12",
        title="Connect Futuremug",
        subtitle=subtitles[account_type],
        purpose="µLearn shares these details only to create your Futuremug account and sign you in to it from µLearn.",
        sections=(
            ConsentSection("What Futuremug does with it",
                           "Futuremug uses these details to run your account and its services: assessments, "
                           "AI interviews and expert interviews. Futuremug is responsible for the data you add "
                           "or create on Futuremug, under its own Terms and Privacy Policy."),
            ConsentSection("Keeping it up to date",
                           "If you change your name, email or phone on µLearn, we update Futuremug the next "
                           "time you open it from µLearn."),
            ConsentSection("Disconnecting and your rights",
                           "You can disconnect at any time from this card. µLearn then stops sharing your "
                           "details and stops signing you in. Your Futuremug account is not deleted: to delete "
                           "it or its data, contact Futuremug. Questions or complaints about how µLearn handles "
                           "your data: info@mulearn.org."),
        ),
        notes=notes[account_type],
        checkbox_label=("I agree to share these details with Futuremug and accept Futuremug's {terms} "
                        "and {privacy}. I can disconnect anytime."),
        terms_url=settings.FUTUREMUG_TERMS_URL,
        privacy_url=settings.FUTUREMUG_PRIVACY_URL,
    )


_VERSIONS = {"fm-2026-10-12": _fm_2026_10_12}


def document(account_type, version=CURRENT_VERSION):
    return _VERSIONS[version](account_type)
