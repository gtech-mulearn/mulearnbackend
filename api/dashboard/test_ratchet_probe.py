# Probe for PR #3417: a new failing legacy test must turn ci / legacy red. Reverted in the next commit.
def test_ratchet_probe():
    assert False, "probe"
