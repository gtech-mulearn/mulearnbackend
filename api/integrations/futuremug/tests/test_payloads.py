"""Spec B §3.5: µLearn data → Futuremug fields, and the preview equals what is sent."""
from types import SimpleNamespace

import pytest

from api.integrations.futuremug import payloads
from api.integrations.partner_sso.adapter import ContactChange
from api.integrations.partner_sso.errors import PartnerError
from api.integrations.partner_sso.subjects import Resolution, SubjectKind


def person(full_name="Asha Nair", email="Asha.Nair@Example.com", mobile="+91 98765-43210"):
    return SimpleNamespace(full_name=full_name, email=email, mobile=mobile)


def resolution(kind=SubjectKind.LEARNER, name=None, **who):
    return Resolution(kind, subject_type="user", subject_id="s-1", subject_name=name,
                      manager=person(**who), can_manage=True)


def preview(contact):
    return {row.label: (row.value, row.note) for row in contact.preview}


class TestNames:
    def test_first_word_then_the_rest(self):
        assert payloads.split_name("Asha") == ("Asha", None, False)
        assert payloads.split_name("Asha Mary  Nair") == ("Asha", "Mary Nair", False)

    def test_long_names_are_cut_to_25_and_flagged(self):
        first, last, shortened = payloads.split_name("Muhammed Shafeeq Abdul Rahiman Kunnath")
        assert (first, last, shortened) == ("Muhammed", "Shafeeq Abdul Rahiman Kun", True)

    def test_unicode_names_are_kept_as_typed(self):
        assert payloads.split_name("Ánh Nguyễn") == ("Ánh", "Nguyễn", False)
        assert payloads.split_name("അനു കൃഷ്ണ") == ("അനു", "കൃഷ്ണ", False)


class TestEmail:
    def test_lowercased(self):
        assert payloads.futuremug_email(" Asha@Example.COM ") == "asha@example.com"

    @pytest.mark.parametrize("email", ["a" * 50 + "@example.com", "o'brien@example.com"])
    def test_unsupported_addresses_say_how_to_fix_them(self, email):
        with pytest.raises(PartnerError) as error:
            payloads.futuremug_email(email)
        assert error.value.code == "email_not_supported"
        assert "60 characters" in error.value.text("Futuremug")


class TestPhone:
    def test_formatting_is_stripped(self):
        assert payloads.futuremug_phone("+91 98765-43210") == ("919876543210", None)

    def test_unsendable_numbers_are_left_out_with_a_reason(self):
        assert payloads.futuremug_phone("12345") == (None, "Format not supported")
        assert payloads.futuremug_phone(None) == (None, "Not on your profile")


class TestContact:
    def test_candidate_preview_matches_the_payload(self):
        contact = payloads.build_contact("candidate", resolution())
        body = payloads.session_payload("candidate", contact)
        assert body == {"account_type": "candidate", "email": "asha.nair@example.com",
                        "first_name": "Asha", "last_name": "Nair", "phone": "919876543210"}
        assert preview(contact) == {
            "Name": ("Asha Nair", None),
            "Email": ("asha.nair@example.com", None),
            "Phone": ("919876543210", None),
            "Account type": ("Candidate", None),
        }

    def test_a_long_company_name_is_cut_and_shown_exactly(self):
        long_name = "Acme Technologies and Consulting Services Private Limited India"  # 63 characters
        contact = payloads.build_contact("company", resolution(SubjectKind.COMPANY, name=long_name))
        body = payloads.session_payload("company", contact)
        assert len(body["company_name"]) <= 60
        assert preview(contact)["Company name"] == (body["company_name"], payloads.SHORTENED)

    def test_the_college_contact_is_the_lead_enabler(self):
        contact = payloads.build_contact("college", resolution(SubjectKind.COLLEGE, name="St Xavier's College"))
        assert payloads.session_payload("college", contact)["college_name"] == "St Xavier's College"
        assert preview(contact)["Contact (TPO)"] == ("Asha Nair", "You, as Lead Enabler")

    def test_a_missing_phone_is_not_sent(self):
        contact = payloads.build_contact("candidate", resolution(mobile=None))
        assert "phone" not in payloads.session_payload("candidate", contact)
        assert preview(contact)["Phone"] == ("Not shared", "Not on your profile")

    def test_a_blank_name_cannot_be_sent(self):
        with pytest.raises(PartnerError) as error:
            payloads.build_contact("candidate", resolution(full_name="   "))
        assert error.value.code == "partner_rejected_field"


class TestUpdateContactPayload:
    def test_only_what_changed_and_last_name_only_with_first_name(self):
        assert payloads.update_contact_payload("candidate", "old@example.com", ContactChange(new_phone="9123456780")) == \
            {"account_type": "candidate", "email": "old@example.com", "new_phone": "9123456780"}
        change = ContactChange(new_email="tpo@example.com", new_first_name="Anil", new_last_name="Kumar", replace_contact=True)
        assert payloads.update_contact_payload("college", "old@example.com", change) == {
            "account_type": "college", "email": "old@example.com", "new_email": "tpo@example.com",
            "new_first_name": "Anil", "new_last_name": "Kumar", "replace_contact": True,
        }
