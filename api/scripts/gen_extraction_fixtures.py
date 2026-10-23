"""Generate diverse non-regression extraction fixtures.

Run: python scripts/gen_extraction_fixtures.py
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tests" / "fixtures" / "offers"
OUT.mkdir(parents=True, exist_ok=True)

# Each entry: (free-form text, expected dict). Missing fields -> None.
FIXTURES = [
    ("We are looking for a Backend Engineer at Acme in Paris, France. CDI contract. Apply before 2026-11-30 by sending your CV to jobs@acme.example.",
     {"title": "Backend Engineer", "company": "Acme", "location": "Paris, France", "contract_type": "CDI", "deadline": "2026-11-30", "how_to_apply": "Send CV to jobs@acme.example"}),
    ("Data Analyst — BetaCorp (Lyon, France). CDD. Deadline: 15/12/2026. Apply via https://beta.example/apply",
     {"title": "Data Analyst", "company": "BetaCorp", "location": "Lyon, France", "contract_type": "CDD", "deadline": "2026-12-15", "how_to_apply": "Apply via https://beta.example/apply"}),
    ("Product Manager @ Gamma, Remote, CDI. No deadline. Email pm@gamma.example to apply.",
     {"title": "Product Manager", "company": "Gamma", "location": "Remote", "contract_type": "CDI", "deadline": None, "how_to_apply": "Email pm@gamma.example"}),
    ("Offre : Développeur Full-Stack (H/F) — Société Étoile, Toulouse. CDI. Candidature avant le 31 janvier 2027 par mail à recrutement@etoile.fr.",
     {"title": "Développeur Full-Stack", "company": "Société Étoile", "location": "Toulouse", "contract_type": "CDI", "deadline": "2027-01-31", "how_to_apply": "Email recrutement@etoile.fr"}),
    ("QA Engineer needed at Delta Inc, Berlin or remote. Contract: freelance. Apply on our portal: https://delta.example/careers",
     {"title": "QA Engineer", "company": "Delta Inc", "location": "Berlin or remote", "contract_type": "freelance", "deadline": None, "how_to_apply": "https://delta.example/careers"}),
    ("Stage Marketing 6 mois — Kappa, Nantes. Candidature jusqu'au 2026-10-31. Envoyer CV + lettre à stage@kappa.example et via https://kappa.example/stage",
     {"title": "Stage Marketing", "company": "Kappa", "location": "Nantes", "contract_type": "Stage", "deadline": "2026-10-31", "how_to_apply": "Email stage@kappa.example and https://kappa.example/stage"}),
    ("DevOps Engineer, Epsilon (London, UK). Permanent. Closing date: 1st Feb 2027. Apply by emailing devops@epsilon.example with subject 'DevOps'.",
     {"title": "DevOps Engineer", "company": "Epsilon", "location": "London, UK", "contract_type": "Permanent", "deadline": "2027-02-01", "how_to_apply": "Email devops@epsilon.example"}),
    ("Data Scientist — Zeta, San Francisco. Full-time. No fixed deadline, rolling. Submit via https://zeta.example/apply and cc jobs@zeta.example",
     {"title": "Data Scientist", "company": "Zeta", "location": "San Francisco", "contract_type": "Full-time", "deadline": None, "how_to_apply": "https://zeta.example/apply and jobs@zeta.example"}),
    ("Ingénieur IA (H/F) chez Oméga, Paris 15e. CDI. Date limite : 2026-12-01. Postuler sur https://omega.example/jobs/ia",
     {"title": "Ingénieur IA", "company": "Oméga", "location": "Paris 15e", "contract_type": "CDI", "deadline": "2026-12-01", "how_to_apply": "https://omega.example/jobs/ia"}),
    ("Frontend React Developer at Lambda, Remote (EU). Contract type not specified. Deadline end of November 2026. Apply by emailing frontend@lambda.example",
     {"title": "Frontend React Developer", "company": "Lambda", "location": "Remote (EU)", "contract_type": None, "deadline": "2026-11-30", "how_to_apply": "Email frontend@lambda.example"}),
    ("Site Reliability Engineer, Mu Corp, Singapore. CDI. Apply before 2027-03-15 via portal https://mu.example/sre",
     {"title": "Site Reliability Engineer", "company": "Mu Corp", "location": "Singapore", "contract_type": "CDI", "deadline": "2027-03-15", "how_to_apply": "https://mu.example/sre"}),
    ("Chef de Projet IT — Nu SA, Bruxelles. CDD 12 mois. Candidature avant le 10/01/2027. Contact: projets@nu.example",
     {"title": "Chef de Projet IT", "company": "Nu SA", "location": "Bruxelles", "contract_type": "CDD", "deadline": "2027-01-10", "how_to_apply": "Email projets@nu.example"}),
    ("Machine Learning Engineer, Xi Ltd, London. Full-time. Deadline: 2026-11-15. Apply: https://xi.example/ml + ml@xi.example",
     {"title": "Machine Learning Engineer", "company": "Xi Ltd", "location": "London", "contract_type": "Full-time", "deadline": "2026-11-15", "how_to_apply": "https://xi.example/ml and ml@xi.example"}),
    ("Product Designer, Pi Studio, Amsterdam. Freelance. No deadline. Portfolio to design@pi.example",
     {"title": "Product Designer", "company": "Pi Studio", "location": "Amsterdam", "contract_type": "Freelance", "deadline": None, "how_to_apply": "Email design@pi.example"}),
    ("Analyste Cybersécurité, Rho, Montréal. CDI. Date limite 2026-12-20. Postuler via https://rho.example/cyber",
     {"title": "Analyste Cybersécurité", "company": "Rho", "location": "Montréal", "contract_type": "CDI", "deadline": "2026-12-20", "how_to_apply": "https://rho.example/cyber"}),
    ("Backend Python Developer at Sigma, Remote. Contract: CDI. Apply by 2027-01-05 at backend@sigma.example",
     {"title": "Backend Python Developer", "company": "Sigma", "location": "Remote", "contract_type": "CDI", "deadline": "2027-01-05", "how_to_apply": "Email backend@sigma.example"}),
    ("Data Engineer, Tau Inc, New York. Full-time. Rolling applications, no deadline. https://tau.example/de",
     {"title": "Data Engineer", "company": "Tau Inc", "location": "New York", "contract_type": "Full-time", "deadline": None, "how_to_apply": "https://tau.example/de"}),
    ("Responsable RH, Upsilon, Lyon. CDI. Candidature avant le 15/02/2027. Contact rh@upsilon.example",
     {"title": "Responsable RH", "company": "Upsilon", "location": "Lyon", "contract_type": "CDI", "deadline": "2027-02-15", "how_to_apply": "Email rh@upsilon.example"}),
    ("Cloud Architect, Phi Cloud, Paris. CDI. Deadline 2026-12-31. Apply via https://phi.example/cloud and cloud@phi.example",
     {"title": "Cloud Architect", "company": "Phi Cloud", "location": "Paris", "contract_type": "CDI", "deadline": "2026-12-31", "how_to_apply": "https://phi.example/cloud and cloud@phi.example"}),
    ("Mobile Developer (iOS/Android), Chi Mobile, Remote EU. Contract not specified. Apply by emailing mobile@chi.example. No deadline given.",
     {"title": "Mobile Developer", "company": "Chi Mobile", "location": "Remote EU", "contract_type": None, "deadline": None, "how_to_apply": "Email mobile@chi.example"}),
    ("Security Engineer, Psi Sec, Berlin. Permanent. Closing 2027-02-28. https://psi.example/sec",
     {"title": "Security Engineer", "company": "Psi Sec", "location": "Berlin", "contract_type": "Permanent", "deadline": "2027-02-28", "how_to_apply": "https://psi.example/sec"}),
    ("Ingénieur Réseau, Omega Net, Casablanca. CDI. Date limite 2027-03-01. Postuler à reseau@omega-net.example",
     {"title": "Ingénieur Réseau", "company": "Omega Net", "location": "Casablanca", "contract_type": "CDI", "deadline": "2027-03-01", "how_to_apply": "Email reseau@omega-net.example"}),
    ("Technical Writer, Iota Docs, Remote. Contract: freelance. No deadline. Apply: https://iota.example/tw",
     {"title": "Technical Writer", "company": "Iota Docs", "location": "Remote", "contract_type": "Freelance", "deadline": None, "how_to_apply": "https://iota.example/tw"}),
    ("Scrum Master, Kappa Agile, Paris/Lyon. CDI. Deadline 2026-11-20. Email scrum@kappa-agile.example",
     {"title": "Scrum Master", "company": "Kappa Agile", "location": "Paris/Lyon", "contract_type": "CDI", "deadline": "2026-11-20", "how_to_apply": "Email scrum@kappa-agile.example"}),
    ("Business Analyst, Lambda BA, Tunis. CDI. Candidature avant le 2027-01-31. https://lambda-ba.example/apply",
     {"title": "Business Analyst", "company": "Lambda BA", "location": "Tunis", "contract_type": "CDI", "deadline": "2027-01-31", "how_to_apply": "https://lambda-ba.example/apply"}),
    ("AI Researcher, Mu AI, Remote (Worldwide). Full-time. No deadline. research@mu-ai.example",
     {"title": "AI Researcher", "company": "Mu AI", "location": "Remote (Worldwide)", "contract_type": "Full-time", "deadline": None, "how_to_apply": "Email research@mu-ai.example"}),
    ("Sysadmin, Nu Infra, Dakar. CDI. Date limite 2027-04-15. Postuler via https://nu-infra.example/sysadmin",
     {"title": "Sysadmin", "company": "Nu Infra", "location": "Dakar", "contract_type": "CDI", "deadline": "2027-04-15", "how_to_apply": "https://nu-infra.example/sysadmin"}),
    ("UX Researcher, Xi UX, Paris. CDD. Deadline 2026-10-15. Apply at ux@xi-ux.example and https://xi-ux.example/ux",
     {"title": "UX Researcher", "company": "Xi UX", "location": "Paris", "contract_type": "CDD", "deadline": "2026-10-15", "how_to_apply": "Email ux@xi-ux.example and https://xi-ux.example/ux"}),
    ("Embedded Engineer, Pi Embedded, Grenoble. CDI. Apply before 2027-05-01 via https://pi-embedded.example/apply",
     {"title": "Embedded Engineer", "company": "Pi Embedded", "location": "Grenoble", "contract_type": "CDI", "deadline": "2027-05-01", "how_to_apply": "https://pi-embedded.example/apply"}),
    ("Chef de Cuisine, Rho Resto, Lyon. CDI. Pas de date limite. Envoyer CV à cuisine@rho-resto.example",
     {"title": "Chef de Cuisine", "company": "Rho Resto", "location": "Lyon", "contract_type": "CDI", "deadline": None, "how_to_apply": "Email cuisine@rho-resto.example"}),
]


def main() -> None:
    # clean old orphans
    for p in OUT.glob("offer_*.txt"):
        p.unlink()
    for p in OUT.glob("offer_*.expected.json"):
        p.unlink()
    count = 0
    for i, (text, expected) in enumerate(FIXTURES, start=1):
        slug = f"offer_{i:02d}"
        (OUT / f"{slug}.txt").write_text(text, encoding="utf-8")
        (OUT / f"{slug}.expected.json").write_text(
            json.dumps(expected, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        count += 1
    print(f"Generated {count} fixtures in {OUT}")


if __name__ == "__main__":
    main()
