"""The required-setting helper runs without importing Django settings (#3302)."""
import mulearnbackend.required as required


def test_two_missing_names_are_both_reported(monkeypatch):
    required.MISSING.clear()
    seen = []

    def fake_config(name, default=None, **kwargs):
        seen.append((name, default, kwargs))
        return default

    monkeypatch.setattr(required, "decouple_config", fake_config)
    assert required.required("FIRST_MISSING") is None
    assert required.required("SECOND_MISSING") is None
    assert required.MISSING == {"FIRST_MISSING", "SECOND_MISSING"}
    # Every read used default=None, so a missing value never raises in decouple.
    assert all(default is None for _, default, _ in seen)
    required.MISSING.clear()


def test_present_value_is_not_recorded_and_cast_is_kept(monkeypatch):
    required.MISSING.clear()
    monkeypatch.setattr(
        required, "decouple_config",
        lambda name, default=None, **kwargs: kwargs["cast"](default) if default is not None else "ok",
    )
    assert required.required("PRESENT_SETTING") == "ok"
    assert required.MISSING == set()
