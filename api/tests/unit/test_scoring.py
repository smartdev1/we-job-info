from app.services.scoring import compute_score
from app.services.suspicion import check_suspicion


def test_score_complete_offer_high():
    offer = {
        "title": "Dev", "company": "ACME", "city": "Abidjan", "sector": "informatique",
        "contract_type": "CDI", "education_level": "Bac+3", "experience": "2 ans",
        "description": "desc", "how_to_apply": "apply", "contact_email": "a@b.com",
        "deadline": "2026-12-01", "created_at": None,
    }
    assert compute_score(offer) >= 0.7


def test_score_empty_offer_low():
    assert compute_score({}) <= 0.3


def test_suspicion_payment_request():
    offer = {"description": "Paiement de frais requis", "company": "X"}
    suspect, reasons = check_suspicion(offer)
    assert suspect
    assert "demande de paiement" in reasons


def test_score_bounds():
    assert 0.0 <= compute_score({}) <= 1.0
    big = {"title": "x", "company": "y", "city": "z", "sector": "informatique",
           "contract_type": "CDI", "education_level": "Bac", "experience": "1",
           "description": "d", "how_to_apply": "a", "contact_email": "e@f.com",
           "deadline": "2026-12-01"}
    assert 0.0 <= compute_score(big) <= 1.0


def test_suspicion_all_rules():
    from app.services.suspicion import RULES
    # payment
    assert check_suspicion({"description": "Frais de dossier"})[0]
    # no company
    assert check_suspicion({"title": "x"})[0]
    # urgency
    assert check_suspicion({"title": "Urgent recrutement", "company": "X"})[0]

def test_score_future_date_no_boost():
    from datetime import datetime, timedelta, timezone
    future = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()
    offer = {"title": "x", "created_at": future}
    s = compute_score(offer)
    assert 0.0 <= s <= 1.0


def test_suspicion_all_six_rules():
    cases = [
        ({"description": "Frais de dossier", "company": "X"}, "demande de paiement"),
        ({"contact_email": "a@gmail.com", "company": "BigCo"}, "email gratuit pour grande entreprise"),
        ({"description": "Salaire 12345678 FCFA", "company": "X"}, "salaire irréaliste"),
        ({"title": "x"}, "aucune entreprise identifiable"),
        ({"how_to_apply": "WhatsApp only", "company": "X"}, "contact uniquement par messagerie privée"),
        ({"title": "Urgent poste", "company": "X"}, "urgence excessive"),
    ]
    for offer, expected in cases:
        suspect, reasons = check_suspicion(offer)
        assert suspect, offer
        assert expected in reasons, (offer, reasons)
