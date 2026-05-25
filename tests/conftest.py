import pytest

from backend.schemas.enums import QueryType
from backend.schemas.investigation import InvestigationRequest


@pytest.fixture
def sample_investigation_request() -> InvestigationRequest:
    return InvestigationRequest(query="CVE-2024-3094", query_type=QueryType.CVE)
