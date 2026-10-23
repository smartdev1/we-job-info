"""Source connectors package."""

from app.sources.connector import register
from app.sources.eclozion import EclozionConnector
from app.sources.educarriere import EducarriereConnector
from app.sources.emploi_ci import EmploiCiConnector
from app.sources.emploiivoire import EmploiIvoireConnector
from app.sources.jobivoire import JobIvoireConnector

register("eclozion", EclozionConnector)
register("educarriere", EducarriereConnector)
register("emploi_ci", EmploiCiConnector)
register("emploiivoire", EmploiIvoireConnector)
register("jobivoire", JobIvoireConnector)
