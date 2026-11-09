import pytest

from api.integrations.futuremug import consent


@pytest.mark.parametrize("account_type", ["candidate", "company", "college"])
def test_every_account_type_has_a_complete_document(account_type):
    document = consent.document(account_type).as_dict()
    assert document["version"] == consent.CURRENT_VERSION == "fm-2026-10-12"
    assert document["title"] == "Connect Futuremug"
    assert "{terms}" in document["checkbox_label"] and "{privacy}" in document["checkbox_label"]
    assert [section["title"] for section in document["sections"]] == [
        "What Futuremug does with it", "Keeping it up to date", "Disconnecting and your rights"]
    assert document["terms_url"] == "https://futuremug.example/terms"


def test_companies_and_colleges_are_told_about_approval():
    assert any("approves" in note for note in consent.document("company").notes)
    assert any("Lead Enabler changes" in note for note in consent.document("college").notes)
    assert consent.document("candidate").notes == ()


def test_unknown_versions_are_refused():
    with pytest.raises(KeyError):
        consent.document("candidate", version="fm-1999-01-01")
