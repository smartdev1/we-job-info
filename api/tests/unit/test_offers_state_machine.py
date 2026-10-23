from app.offers.state_machine import is_allowed, allowed_targets, TRANSITIONS


def test_valid_transition():
    assert is_allowed("nouvelle", "selectionnee") is True


def test_invalid_transition():
    assert is_allowed("archivee", "nouvelle") is False


def test_allowed_targets():
    assert allowed_targets("publiee") == {"archivee"}