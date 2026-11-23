"""Escolhe o adaptador a partir da configuração (por omissão, o `fake`)."""

from kai_ai_engine.llm.anthropic_adapter import AnthropicGateway
from kai_ai_engine.llm.fake import FakeGateway
from kai_ai_engine.llm.gateway import LLMGateway
from kai_ai_engine.llm.ollama_adapter import OllamaGateway
from kai_ai_engine.settings import LlmSettings


def build_gateway(settings: LlmSettings) -> LLMGateway:
    if settings.provider == "anthropic" and settings.anthropic is not None:
        return AnthropicGateway(settings.anthropic)
    if settings.provider == "ollama" and settings.ollama is not None:
        return OllamaGateway(settings.ollama)
    if settings.provider == "fake":
        return FakeGateway(settings.fake)
    # Nunca cair no fake em silêncio por configuração incompleta.
    raise ValueError("configuração do fornecedor LLM incompleta")
