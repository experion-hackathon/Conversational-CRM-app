from app.nlu.base import ExtractionResult, NLUClient
from app.nlu.rule_based_client import RuleBasedNLUClient


def get_nlu_client() -> NLUClient:
    from app.config import get_settings

    settings = get_settings()
    if settings.nlu_engine == "bedrock":
        from app.nlu.bedrock_client import BedrockNLUClient

        return BedrockNLUClient()
    return RuleBasedNLUClient()


__all__ = ["ExtractionResult", "NLUClient", "RuleBasedNLUClient", "get_nlu_client"]
