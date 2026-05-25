from backend.agents.research_agent import ResearchAgent
from backend.core.config import Settings
from backend.services.http_client import ResilientHttpClient
from backend.services.providers.cisa_provider import CisaKevProvider
from backend.services.providers.nvd_provider import NvdProvider


def build_research_agent(http: ResilientHttpClient, settings: Settings) -> ResearchAgent:
    providers = [
        NvdProvider(http, settings),
        CisaKevProvider(http, settings),
    ]
    return ResearchAgent(providers=providers)
