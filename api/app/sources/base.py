"""Shared base for HTTP source connectors.

Provides fetching with User-Agent, timeout, robots.txt awareness and a
small ``Offer`` value object. Concrete connectors only implement parsing.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional
from urllib.parse import quote_plus, urljoin, urlparse
from urllib.robotparser import RobotFileParser
import logging
import re
import time
import urllib.request

from .detail import OfferDetail, fold


logger = logging.getLogger(__name__)

USER_AGENT = "we-info-jobs-bot/1.0 (+respectful; contact: admin@example.com)"
DEFAULT_TIMEOUT = 15


# Editorial theme of the chain: software development, data/AI and cyber security.
#
# This list is shared by every connector on purpose. It used to be duplicated
# per connector, which had drifted into five different variants and produced
# both false negatives and false positives.
#
# Keywords shorter than 5 characters are matched on word boundaries, longer
# ones as substrings. That distinction matters: "soc" must not match "société"
# and "ia" must not match "recherche", while "développeur" must still match
# the plural "développeurs".
#
# The bare words "web", "ia", "data" and "securite" are NOT keywords: they
# matched "Community Manager & Gestionnaire de site web", "Création & IA",
# "Ingenieur Securite Ferroviaire" and "100% Téléravail Strasbourg France".
# The compounds are listed instead.
THEME_KEYWORDS: tuple[str, ...] = (
    # -- Data / AI (the specific compounds come first: the first match wins)
    "data analyst",
    "data scientist",
    "data engineer",
    "analyste de donnees",
    "analyste data",
    "big data",
    "power bi",
    "power query",
    "tableau de bord",
    "data warehouse",
    "science des donnees",
    "ingenieur donnees",
    "business intelligence",
    "intelligence artificielle",
    "machine learning",
    "deep learning",
    "nlp",
    "computer vision",
    "generative ai",
    "chatgpt",
    "data & ia",
    "ia & data",
    # -- Cyber / security
    "cyber",
    "cybersecurite",
    "pentest",
    "osint",
    "soc",
    "ssi",
    "securite informatique",
    "securite des systemes",
    "securite numerique",
    "securite web",
    "securite des donnees",
    "analyste securite",
    "test d'intrusion",
    "ethical hacker",
    "reverse engineering",
    "forensic",
    "vulnerabilite",
    "hacking",
    "ceh",
    # -- Development
    "developpeur",
    "devops",
    "dev front",
    "dev back",
    "dev web",
    "fullstack",
    "full stack",
    "frontend",
    "front-end",
    "backend",
    "back-end",
    "webdesigner",
    "web designer",
    "webdesign",
    "react",
    "angular",
    "vue.js",
    "php",
    "laravel",
    "symfony",
    "django",
    "flask",
    "fastapi",
    "python",
    "java",
    "kotlin",
    "golang",
    "rust",
    "wordpress",
    "docker",
    "kubernetes",
    "gitlab",
    "ci/cd",
    "javascript",
    "typescript",
    "node.js",
    "html5",
    "css3",
    "integrateur web",
    "administrateur de base de donnees",
    "base de donnees",
    "mysql",
    "postgresql",
    "mongodb",
    "api rest",
    "restfull",
    "microservice",
    "devsecops",
    # -- IT
    "informaticien",
    "informatique",
    # -- Generic data (last: it is the loosest keyword of the list)
    "data",
)


# Titles that carry a theme keyword but describe another job.
#
# In Côte d'Ivoire "développeur" is also a sales title ("Business Développeur",
# "Développeur Commercial", "Développeur Immobilier") and "sécurité" is often
# physical ("Agent de sécurité"). Those offers are not for the channel.

THEME_EXCLUDES: tuple[str, ...] = (
    # -- Business development / commerce
    "business developpeur",
    "business developer",
    "business development",
    "developpeur d affaires",
    "developpeur commercial",
    "developpement commercial",
    "commercial terrain",
    "ingenieur commercial",
    "technico commercial",
    "representant commercial",
    "prospection commerciale",
    "charge d affaires",

    # -- Immobilier / construction / urbanisme
    "developpeur immobilier",
    "promotion immobiliere",
    "promoteur immobilier",
    "developpement immobilier",
    "developpeur foncier",
    "amenagement foncier",
    "developpement urbain",
    "genie civil",
    "developpement territorial",

    # -- Reseaux commerciaux et distribution
    "developpeur de reseau",
    "developpement de reseau commercial",
    "reseau de distribution",
    "reseau de franchises",
    "franchise commerciale",
    "demarcheur informatique",
    "demarcheur commercial",

    # -- Materiel / maintenance non logicielle
    "materiel informatique",
    "vente de materiel informatique",
    "technicien informatique",
    "maintenance informatique",
    "reparation ordinateur",
    "reparation informatique",
    "maintenance industrielle",
    "technicien de maintenance",
    "support informatique",
    "help desk",
    "centre de reparation",

    # -- Saisie / traitement administratif des donnees
    "data entry",
    "data entry clerk",
    "saisie de donnees",
    "operateur de saisie",
    "agent de saisie",
    "saisie informatique",
    "traitement administratif des donnees",
    "transcription audio",
    "transcription de documents",

    # -- Securite non informatique
    "agent de securite",
    "agent de securite incendie",
    "securite ferroviaire",
    "securite civile",
    "securite physique",
    "securite alimentaire",
    "securite environnementale",
    "securite routiere",
    "securite au travail",
    "sante securite au travail",
    "prevention des risques professionnels",
    "gardiennage",
    "surveillance humaine",
    "agent de surveillance",
    "securite des personnes",
    "securite des biens",

    # -- Community management / marketing / communication
    "community manager",
    "community management",
    "social media manager",
    "gestionnaire de communaute",
    "charge de communication",
    "communication digitale",
    "marketing digital",
    "marketing de contenu",
    "redacteur web",
    "copywriter",
    "referencement naturel",
    "specialiste seo",
    "publicite en ligne",
    "media buying",
    "influenceur",

    # -- Gestion de site / administration non technique
    "gestionnaire de site web",
    "administrateur de site web",
    "gestion de contenu web",
    "webmaster editorial",
    "mise a jour de site web",
    "publication de contenu",
    "gestionnaire de contenu",
    "saisie de contenu web",

    # -- Developpement personnel / autres sens de developpement
    "developpement personnel",
    "developpement durable",
    "developpement economique",
    "developpement communautaire",
    "developpement social",
    "developpement humain",
    "developpement agricole",
    "developpement rural",
    "developpement organisationnel",

    # -- Autres homonymes de data / intelligence artificielle
    "data entry operator",
    "data entry job",
    "intelligence economique",
    "intelligence emotionnelle",
    "agent de renseignement humain",
)



def _matches(haystack: str, keyword: str) -> bool:
    """Case-insensitive match of ``keyword`` inside ``haystack``.

    Short keywords are anchored on word boundaries to avoid false hits
    ("soc" in "société", "ia" in "recherche"); longer ones match as
    substrings so that plurals are still caught.
    """
    if len(keyword) < 5:
        return re.search(rf"(?<!\w){re.escape(keyword)}(?!\w)", haystack) is not None
    return keyword in haystack


# The keywords are compared in their folded form (no accent, lower case), so
# that "Sécurité informatique" is matched by the keyword "securite informatique".
_FOLDED_THEME_KEYWORDS: tuple[str, ...] = tuple(fold(k) for k in THEME_KEYWORDS)
_FOLDED_THEME_EXCLUDES: tuple[str, ...] = tuple(fold(e) for e in THEME_EXCLUDES)


def match_theme(title: str) -> str | None:
    """Return the theme keyword that ``title`` matches, or None.

    Matching is applied to the job *title* only. Applying it to a whole
    listing card also matched the card description, which let unrelated
    jobs through (a "commercial" ad whose description mentioned a website
    was classified as a web job).

    The comparison is accent-insensitive: the platforms write "Développeur",
    "Developpeur" and "DEVELOPPEUR" in the same listing.
    """
    low = fold(title or "")
    for keyword in _FOLDED_THEME_KEYWORDS:
        if _matches(low, keyword):
            return keyword
    return None


def exclusion_reason(title: str) -> str | None:
    """Return the exclusion that rules ``title`` out, or None.

    A title can carry a theme keyword and still describe another job: in
    Côte d'Ivoire "Développeur" is also a sales title and "Sécurité" is
    often physical. Those are excluded explicitly.
    """
    low = fold(title or "")
    for exclusion in _FOLDED_THEME_EXCLUDES:
        if _matches(low, exclusion):
            return exclusion
    return None


def is_themed(title: str) -> bool:
    """True when the job title belongs to the channel's editorial theme."""
    if exclusion_reason(title) is not None:
        return False
    return match_theme(title) is not None


# Coarse sector derived from the theme keyword that matched, so that the
# scoring engine (which rewards the "informatique", "data" and
# "cybersecurite" sectors) can rank collected offers before the LLM has
# extracted anything.
#
# The keys are folded: the keyword returned by ``match_theme`` is folded too.
_SECTOR_BY_KEYWORD = {
    # -- Data / AI
    "data": "data",
    "big data": "data",
    "data analyst": "data",
    "data scientist": "data",
    "data engineer": "data",
    "analytics engineer": "data",
    "analyste de donnees": "data",
    "analyste data": "data",
    "ingenieur donnees": "data",
    "science des donnees": "data",
    "analyse de donnees": "data",
    "analyse statistique": "data",
    "power bi": "data",
    "power query": "data",
    "tableau de bord": "data",
    "tableau software": "data",
    "looker studio": "data",
    "business intelligence": "data",
    "visualisation de donnees": "data",
    "etl": "data",
    "elt": "data",
    "data warehouse": "data",
    "data lake": "data",
    "dbt": "data",
    "apache spark": "data",
    "airflow": "data",
    "gouvernance des donnees": "data",
    "qualite des donnees": "data",
    "sql analytics": "data",

    # -- Intelligence artificielle
    "intelligence artificielle": "data",
    "ia generative": "data",
    "generative ai": "data",
    "machine learning": "data",
    "deep learning": "data",
    "ingenieur machine learning": "data",
    "ingenieur ia": "data",
    "ingenieur en intelligence artificielle": "data",
    "ai engineer": "data",
    "nlp": "data",
    "traitement du langage naturel": "data",
    "computer vision": "data",
    "llm": "data",
    "large language model": "data",
    "rag": "data",
    "fine tuning": "data",
    "prompt engineering": "data",
    "agents ia": "data",
    "agents autonomes": "data",
    "automatisation ia": "data",
    "evaluation llm": "data",
    "inference llm": "data",
    "vector database": "data",
    "langchain": "data",
    "llamaindex": "data",
    "chatgpt": "data",
    "openai api": "data",
    "data & ia": "data",
    "ia & data": "data",

    # -- Cyber / security
    "cyber": "cybersecurite",
    "cybersecurite": "cybersecurite",
    "pentest": "cybersecurite",
    "pentesting": "cybersecurite",
    "osint": "cybersecurite",
    "ssi": "cybersecurite",
    "securite informatique": "cybersecurite",
    "securite des systemes": "cybersecurite",
    "securite numerique": "cybersecurite",
    "securite web": "cybersecurite",
    "securite des donnees": "cybersecurite",
    "analyste securite": "cybersecurite",
    "analyste soc": "cybersecurite",
    "soc analyst": "cybersecurite",
    "test d'intrusion": "cybersecurite",
    "ethical hacker": "cybersecurite",
    "hacker ethique": "cybersecurite",
    "reverse engineering": "cybersecurite",
    "forensic": "cybersecurite",
    "forensic numerique": "cybersecurite",
    "vulnerabilite": "cybersecurite",
    "gestion des vulnerabilites": "cybersecurite",
    "hacking": "cybersecurite",
    "ceh": "cybersecurite",
    "red team": "cybersecurite",
    "blue team": "cybersecurite",
    "application security": "cybersecurite",
    "appsec": "cybersecurite",
    "devsecops": "cybersecurite",
    "securite cloud": "cybersecurite",
    "securite reseau": "cybersecurite",
    "securite des api": "cybersecurite",
    "incident response": "cybersecurite",
    "threat intelligence": "cybersecurite",
    "zero trust": "cybersecurite",
    "owasp": "cybersecurite",
    "bug bounty": "cybersecurite",
    "cryptographie": "cybersecurite",
    "iso 27001": "cybersecurite",
    "audit de securite": "cybersecurite",
    "identity and access management": "cybersecurite",

    # -- Developpement logiciel
    "developpeur": "developpement",
    "developpeur logiciel": "developpement",
    "software engineer": "developpement",
    "ingenieur logiciel": "developpement",
    "programmation": "developpement",
    "coding": "developpement",
    "code review": "developpement",
    "architecture logicielle": "developpement",
    "api rest": "developpement",
    "microservices": "developpement",
    "developpeur python": "developpement",
    "developpeur javascript": "developpement",
    "developpeur java": "developpement",
    "developpeur php": "developpement",
    "developpeur nodejs": "developpement",
    "developpeur dotnet": "developpement",
    "developpeur jeux video": "developpement",
    "game developer": "developpement",
    "open source": "developpement",

    # -- Developpement web
    "developpeur web": "web",
    "dev web": "web",
    "full stack": "web",
    "frontend": "web",
    "front end": "web",
    "backend": "web",
    "back end": "web",
    "developpeur react": "web",
    "developpeur laravel": "web",
    "developpeur wordpress": "web",
    "wordpress": "web",
    "woocommerce": "web",
    "shopify": "web",
    "webflow": "web",
    "prestashop": "web",
    "creation de site web": "web",
    "ecommerce": "web",
    "accessibilite web": "web",
    "performance web": "web",

    # -- Developpement mobile
    "developpeur mobile": "mobile",
    "developpeur android": "mobile",
    "developpeur ios": "mobile",
    "flutter": "mobile",
    "react native": "mobile",
    "kotlin android": "mobile",
    "swift ios": "mobile",

    # -- DevOps / Cloud / Infrastructure
    "devops": "devops",
    "ingenieur devops": "devops",
    "ingenieur cloud": "cloud",
    "cloud computing": "cloud",
    "aws": "cloud",
    "azure": "cloud",
    "google cloud": "cloud",
    "docker": "devops",
    "kubernetes": "devops",
    "ci cd": "devops",
    "integration continue": "devops",
    "deploiement continu": "devops",
    "terraform": "devops",
    "infrastructure as code": "devops",
    "observabilite": "devops",
    "site reliability engineering": "devops",
    "platform engineering": "devops",
    "administrateur systeme": "systemes_reseaux",
    "administrateur reseau": "systemes_reseaux",
    "linux": "systemes_reseaux",
    "reseaux informatiques": "systemes_reseaux",
    "ingenieur reseau": "systemes_reseaux",
    "telecommunications": "systemes_reseaux",

    # -- Design / Creation numerique
    "ux design": "design",
    "ui design": "design",
    "ux ui": "design",
    "product designer": "design",
    "web designer": "design",
    "webdesign": "design",
    "motion design": "design",
    "motion designer": "design",
    "animation 2d": "design",
    "animation 3d": "design",
    "design graphique": "design",
    "graphic designer": "design",
    "figma": "design",
    "design system": "design",
    "prototypage": "design",
    "montage video": "creation_numerique",
    "video editing": "creation_numerique",
    "creation de contenu": "creation_numerique",
    "creative coding": "creation_numerique",
    "generative design": "design",

    # -- QA / Tests logiciels
    "qa engineer": "qa",
    "quality assurance": "qa",
    "testeur logiciel": "qa",
    "automatisation des tests": "qa",
    "software testing": "qa",
    "tests logiciels": "qa",
    "tests automatises": "qa",

    # -- Produit / Gestion de projet
    "product manager": "produit",
    "product owner": "produit",
    "business analyst": "produit",
    "chef de projet informatique": "gestion_projet",
    "gestion de projet agile": "gestion_projet",
    "scrum master": "gestion_projet",
    "developpement agile": "gestion_projet",
    "consultant informatique": "conseil",

    # -- Reseaux / IoT / Embarque
    "iot": "iot_embarque",
    "internet des objets": "iot_embarque",
    "systemes embarques": "iot_embarque",
    "robotique": "iot_embarque",
    "arduino": "iot_embarque",
    "raspberry pi": "iot_embarque",
    "electronique": "iot_embarque",
    "edge computing": "iot_embarque",

    # -- Blockchain / Fintech
    "fintech": "fintech",
    "blockchain": "blockchain",
    "web3": "blockchain",
    "smart contracts": "blockchain",
    "solidity": "blockchain",
    "paiement numerique": "fintech",
    "mobile money": "fintech",

    # -- Formation / Emploi / Communaute
    "formation informatique": "formation_tech",
    "apprentissage programmation": "formation_tech",
    "bootcamp coding": "formation_tech",
    "carriere tech": "emploi_tech",
    "emploi informatique": "emploi_tech",
    "recrutement tech": "emploi_tech",
    "freelance informatique": "emploi_tech",
    "portfolio developpeur": "emploi_tech",
    "hackathon": "communaute_tech",
    "communaute tech": "communaute_tech",
    "conference tech": "communaute_tech",
    "veille technologique": "communaute_tech",
}


def sector_for_title(title: str) -> str | None:
    """Coarse sector for a job title, or None when it is off-theme."""
    keyword = match_theme(title)
    if keyword is None:
        return None
    return _SECTOR_BY_KEYWORD.get(keyword, "informatique")


@dataclass
class Offer:
    url: str
    title: str
    date: str | None = None


# The terms sent to the platforms' own search.
#
# The search of a platform matches the whole text of a posting, not only its
# title: it brings noise, which the theme gate then removes. It is used to
# reach the offers the platforms do not show on their first page, not to
# decide whether an offer is on-theme.
EDITORIAL_SEARCH_TERMS: tuple[str, ...] = (
    # Developpement logiciel
    "developpeur",
    "developpeur logiciel",
    "developpeur web",
    "dev web",
    "full stack",
    "frontend",
    "front end",
    "backend",
    "back end",
    "developpeur mobile",
    "developpeur android",
    "developpeur ios",
    "developpeur python",
    "developpeur javascript",
    "developpeur java",
    "developpeur php",
    "developpeur react",
    "developpeur nodejs",
    "developpeur flutter",
    "developpeur laravel",
    "developpeur dotnet",
    "developpeur jeux video",
    "game developer",
    "software engineer",
    "ingenieur logiciel",
    "programmation",
    "coding",
    "code review",
    "architecture logicielle",
    "api rest",
    "microservices",
    "bases de donnees",
    "sql",
    "postgresql",
    "mongodb",

    # DevOps, cloud et infrastructure
    "devops",
    "ingenieur devops",
    "ingenieur cloud",
    "cloud computing",
    "aws",
    "azure",
    "google cloud",
    "docker",
    "kubernetes",
    "ci cd",
    "integration continue",
    "deploiement continu",
    "administrateur systeme",
    "administrateur reseau",
    "linux",
    "infrastructure as code",
    "terraform",
    "observabilite",
    "site reliability engineering",
    "platform engineering",

    # CMS et outils web
    "wordpress",
    "developpeur wordpress",
    "woocommerce",
    "shopify",
    "webflow",
    "prestashop",
    "creation de site web",
    "ecommerce",
    "no code",
    "low code",

    # Data et Business Intelligence
    "data analyst",
    "data scientist",
    "data engineer",
    "analytics engineer",
    "business intelligence",
    "power bi",
    "tableau software",
    "looker studio",
    "excel avance",
    "sql analytics",
    "big data",
    "data warehouse",
    "data lake",
    "etl",
    "elt",
    "dbt",
    "apache spark",
    "airflow",
    "analyse de donnees",
    "visualisation de donnees",
    "gouvernance des donnees",
    "qualite des donnees",
    "machine learning",
    "deep learning",
    "ingenieur machine learning",
    "computer vision",
    "traitement du langage naturel",
    "nlp",
    "statistiques",

    # Intelligence artificielle et IA generative
    "intelligence artificielle",
    "ia generative",
    "generative ai",
    "llm",
    "large language model",
    "prompt engineering",
    "ingenieur ia",
    "ingenieur en intelligence artificielle",
    "ai engineer",
    "rag",
    "agents ia",
    "agents autonomes",
    "automatisation ia",
    "fine tuning",
    "inference llm",
    "mcp",
    "vector database",
    "langchain",
    "llamaindex",
    "openai api",
    "computer use",
    "ai coding assistant",
    "evaluation llm",
    "ethique ia",
    "ai safety",

    # Cybersecurite
    "cybersecurite",
    "securite informatique",
    "pentest",
    "pentesting",
    "ethical hacking",
    "hacker ethique",
    "analyste soc",
    "soc analyst",
    "red team",
    "blue team",
    "application security",
    "appsec",
    "securite applicative",
    "securite cloud",
    "securite reseau",
    "securite des api",
    "owasp",
    "bug bounty",
    "incident response",
    "forensic numerique",
    "threat intelligence",
    "gestion des vulnerabilites",
    "identity and access management",
    "iam",
    "zero trust",
    "devsecops",
    "iso 27001",
    "rgpd",
    "audit de securite",

    # Reseaux, systemes et electronique
    "reseaux informatiques",
    "telecommunications",
    "ingenieur reseau",
    "iot",
    "internet des objets",
    "systemes embarques",
    "robotique",
    "arduino",
    "raspberry pi",
    "electronique",
    "edge computing",

    # Design numerique et creation
    "ux design",
    "ui design",
    "ux ui",
    "product designer",
    "web designer",
    "webdesign",
    "motion design",
    "motion designer",
    "animation 2d",
    "animation 3d",
    "design graphique",
    "graphic designer",
    "figma",
    "design system",
    "prototypage",
    "video editing",
    "montage video",
    "creation de contenu",
    "creative coding",
    "generative design",

    # Produit, gestion et qualite
    "product manager",
    "product owner",
    "chef de projet informatique",
    "gestion de projet agile",
    "scrum master",
    "business analyst",
    "consultant informatique",
    "qa engineer",
    "testeur logiciel",
    "automatisation des tests",
    "quality assurance",
    "software testing",
    "accessibilite web",
    "performance web",
    "open source",
    "github",
    "git",
    "developpement agile",

    # Fintech, blockchain et technologies emergentes
    "fintech",
    "blockchain",
    "web3",
    "smart contracts",
    "solidity",
    "cryptographie",
    "paiement numerique",
    "mobile money",
    "digitalisation",
    "transformation numerique",

    # Formation et insertion professionnelle
    "formation informatique",
    "apprentissage programmation",
    "bootcamp coding",
    "carriere tech",
    "emploi informatique",
    "recrutement tech",
    "freelance informatique",
    "portfolio developpeur",
    "hackathon",
    "communaute tech",
    "conference tech",
    "veille technologique",
)


Fetcher = Callable[[str], str]


class BaseHttpConnector:
    """Common HTTP behaviour for source connectors."""

    source_id: str = ""
    base_url: str = ""
    listing_path: str = "/"

    # Search terms sent to the platform's own search. An empty tuple means the
    # platform is read without a keyword, through its listing pages only.
    search_terms: tuple[str, ...] = ()
    # Path of the platform's search page, when it has one.
    search_path: str = ""
    # Maximum number of listing pages read per search term. The pagination
    # stops earlier on its own as soon as a page brings nothing new.
    max_pages: int = 1
    # Number of unfiltered listing pages read besides the searched ones.
    unfiltered_pages: int = 0
    # Query parameter carrying the page number.
    page_param: str = "page"
    # Delay between two listing requests, in seconds.
    request_delay: float = 0.4

    def __init__(
        self,
        fetcher: Optional[Fetcher] = None,
        base_url: Optional[str] = None,
        check_robots: bool = True,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        self.fetcher = fetcher
        self.base_url = base_url or self.base_url
        self.check_robots = check_robots
        self.timeout = timeout
        self._robots: RobotFileParser | None = None

    def _fetch(self, url: str) -> str:
        if self.fetcher is not None:
            return self.fetcher(url)
        if self.check_robots and not self._robots_allowed(url):
            raise PermissionError(f"robots.txt disallows {url}")
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            charset = resp.headers.get_content_charset() or "utf-8"
            return resp.read().decode(charset, errors="replace")

    def _robots_allowed(self, url: str) -> bool:
        if self._robots is None:
            parsed = urlparse(self.base_url)
            robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
            rp = RobotFileParser()
            try:
                rp.set_url(robots_url)
                # fetch robots via same mechanism but without recursion
                req = urllib.request.Request(robots_url, headers={"User-Agent": USER_AGENT})
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    charset = resp.headers.get_content_charset() or "utf-8"
                    body = resp.read().decode(charset, errors="replace")
                # RobotFileParser.read_file() no longer exists in the supported
                # Python versions, and the AttributeError it raised was being
                # swallowed below, which silently disabled the robots check.
                rp.parse(body.splitlines())
            except Exception:  # noqa: BLE001 - best effort; allow on failure
                return True
            self._robots = rp
        return self._robots.can_fetch(USER_AGENT, url)

    def lister(self) -> list[Offer]:
        """Jobs matching the channel theme."""
        html = self._fetch(self.base_url + self.listing_path)
        return self.parse_listing(html)

    def lister_candidates(self) -> list[Offer]:
        """Every job advertised by the source, across every search term.

        The catalogue is meant to hold what the sources publish; whether an
        offer is worth publishing is decided later, by the theme gate and the
        scoring engine, not by a keyword on the title.

        The platforms do not advertise how many pages they have, so the
        pagination stops on its own as soon as a page brings no new job. A
        listing page that fails is logged and skipped: one broken page must
        not lose the rest of the catalogue.
        """
        offers: list[Offer] = []
        seen: set[str] = set()
        errors: list[str] = []
        for group in self.listing_pages():
            for url in group:
                try:
                    html = self._fetch(url)
                except Exception as exc:  # noqa: BLE001 - one broken page must not stop the run
                    logger.warning("listing %s failed: %s", url, exc)
                    errors.append(f"{url}: {exc}")
                    break
                fresh = [o for o in self.parse_candidates(html) if o.url not in seen]
                for offer in fresh:
                    seen.add(offer.url)
                    offers.append(offer)
                if not fresh:
                    # No new job on this page: the pagination is over.
                    break
                time.sleep(self.request_delay)
        if errors and not offers:
            raise RuntimeError(f"{self.source_id}: no listing page could be read ({errors[0]})")
        return offers

    def listing_pages(self) -> list[list[str]]:
        """The listing pages to read, grouped by search term.

        A platform is read through its own search, once per editorial term
        and once per page: reading a single unfiltered listing page used to
        cap the catalogue at what that single page showed.

        The unfiltered listing is read too, for a few pages only: the search
        of a platform matches the whole text of a posting, so it finds the
        offers of the first pages, but not the ones whose text mentions none
        of the editorial terms.
        """
        groups: list[list[str]] = []
        if not self.search_terms:
            base = self.base_url + self.listing_path
            groups.append(
                [self._with_page(base, page) for page in range(1, self.max_pages + 1)]
            )
            return groups

        if self.unfiltered_pages:
            base = self.base_url + self.listing_path
            groups.append(
                [
                    self._with_page(base, page)
                    for page in range(1, self.unfiltered_pages + 1)
                ]
            )
        for term in self.search_terms:
            base = self.search_url(term)
            groups.append(
                [self._with_page(base, page) for page in range(1, self.max_pages + 1)]
            )
        return groups

    def search_url(self, term: str) -> str:
        """URL of the search page for ``term``."""
        if not term:
            return self.base_url + self.listing_path
        if not self.search_path:
            raise NotImplementedError(
                f"{self.source_id} declares search terms but no search path"
            )
        return f"{self.base_url}{self.search_path}?q={quote_plus(term)}"

    def _with_page(self, url: str, page: int) -> str:
        """Append the page number to a listing URL."""
        if page <= 1:
            return url
        separator = "&" if "?" in url else "?"
        return f"{url}{separator}{self.page_param}={page}"

    def recuperer(self, item: Offer | str) -> str:
        url = item.url if isinstance(item, Offer) else str(item)
        return self._fetch(url)

    def sante(self) -> dict:
        """Report source health.

        ``candidates`` counts every job found on the listing page and ``items``
        counts the ones matching the channel theme. Keeping both apart is what
        makes "the site changed its markup" distinguishable from "the site
        currently has no job of interest".

        The probe reads a single listing page: a health check must stay fast
        even when a source is read through twelve search terms.
        """
        pages = self.listing_pages()
        url = pages[0][0] if pages and pages[0] else self.base_url + self.listing_path
        html = self._fetch(url)
        candidates = self.parse_candidates(html)
        return {
            "status": "ok",
            "items": len([o for o in candidates if is_themed(o.title)]),
            "candidates": len(candidates),
        }

    def parse_candidates(self, html: str) -> list[Offer]:
        """Extract every job advertised on the listing page.

        Implementations must scope the title to the job title itself, not to
        the whole card, so that the theme filter never sees the description.
        """
        raise NotImplementedError

    def parse_listing(self, html: str) -> list[Offer]:
        """Return the candidates whose title matches the channel theme."""
        return [o for o in self.parse_candidates(html) if is_themed(o.title)]

    def parse_detail(self, html: str) -> "OfferDetail":
        """Extract the structured fields of a job detail page.

        Implementations return an :class:`~app.sources.detail.OfferDetail`
        whose unset fields stay ``None``: a page that does not expose a value
        must not be filled with a guess.
        """
        raise NotImplementedError

    @staticmethod
    def _abs(base: str, href: str) -> str:
        return urljoin(base, href)

    @staticmethod
    def _dedupe_by_url(offers: list[Offer]) -> list[Offer]:
        """Drop repeated URLs, keeping the first occurrence."""
        seen: set[str] = set()
        out: list[Offer] = []
        for offer in offers:
            if offer.url in seen:
                continue
            seen.add(offer.url)
            out.append(offer)
        return out
