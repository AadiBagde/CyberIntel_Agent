import json
from backend.core.logging import get_logger
from backend.schemas.research import ThreatResearch, ThreatAssessment
from backend.services.llm.base_llm import BaseLLMProvider, LLMValidationError

logger = get_logger(__name__)


class ThreatAnalysisAgent:
    """
    Threat Analysis Agent that reasons over ThreatResearch data to produce a ThreatAssessment.
    """

    def __init__(self, llm_provider: BaseLLMProvider, max_retries: int = 3) -> None:
        """
        Initialize the Threat Analysis Agent.

        Args:
            llm_provider: The LLM provider instance to use.
            max_retries: Maximum number of attempts to generate a valid structured response.
        """
        self._llm_provider = llm_provider
        self._max_retries = max_retries

    async def analyze(self, research: ThreatResearch) -> ThreatAssessment:
        """
        Analyze a ThreatResearch payload and generate a validated ThreatAssessment.

        Args:
            research: The ThreatResearch payload to analyze.

        Returns:
            A validated ThreatAssessment instance.

        Raises:
            LLMValidationError: If max_retries is reached and LLM validation/decoding fails.
            LLMProviderError: If the LLM provider fails due to client or transient errors.
        """
        logger.info("analysis_agent_start cve=%s", research.cve_id)

        system_instruction = (
            "You are an expert Cyber Threat Intelligence (CTI) analyst.\n"
            "Your task is to analyze the provided threat research data and produce a structured threat assessment."
        )

        research_data = research.model_dump(mode="json")
        prompt = (
            f"Analyze the following threat research data and generate a structured threat assessment:\n\n"
            f"{json.dumps(research_data, indent=2)}\n\n"
            f"Requirements:\n"
            f"- Ground your assessment strictly in the provided research data.\n"
            f"- Detail the potential attack paths, mitigation steps, and highlight any uncertainties/data gaps."
        )

        attempts = 0
        while True:
            attempts += 1
            try:
                assessment = await self._llm_provider.generate(
                    prompt=prompt,
                    system_instruction=system_instruction,
                    temperature=0.0,
                    response_schema=ThreatAssessment,
                )

                if not isinstance(assessment, ThreatAssessment):
                    raise LLMValidationError(
                        "Response was not parsed into a ThreatAssessment instance"
                    )

                logger.info(
                    "analysis_agent_complete cve=%s severity=%s confidence=%d attempts=%d",
                    research.cve_id,
                    assessment.severity,
                    assessment.confidence,
                    attempts,
                )
                return assessment

            except LLMValidationError as exc:
                if attempts >= self._max_retries:
                    logger.error(
                        "analysis_agent_failed cve=%s attempts=%d error=%s",
                        research.cve_id,
                        attempts,
                        exc,
                    )
                    raise

                logger.warning(
                    "analysis_agent_retry cve=%s attempt=%d error=%s",
                    research.cve_id,
                    attempts,
                    str(exc),
                )
