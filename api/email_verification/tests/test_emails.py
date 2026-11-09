from utils.emails import is_valid_email, mask_email, normalize_email


def test_normalize_strips_and_lowercases():
    assert normalize_email("  Asha@Example.COM ") == "asha@example.com"
    assert normalize_email(None) == ""


def test_non_string_input_normalises_to_empty_and_is_invalid():
    # JSON bodies can carry any type; a number or list must be a 400, not a crash.
    assert normalize_email(5) == ""
    assert normalize_email(["asha@example.com"]) == ""
    assert not is_valid_email({"email": "asha@example.com"})


def test_is_valid_email():
    assert is_valid_email("asha.nair+mu@example.co.in")
    assert not is_valid_email("asha")
    assert not is_valid_email("")
    assert not is_valid_email("a" * 190 + "@example.com")  # longer than user.email (200)


def test_mask_email_keeps_first_letter_and_domain():
    assert mask_email("Asha@Gmail.com") == "a•••@gmail.com"
    assert mask_email("not-an-email") == "•••"
