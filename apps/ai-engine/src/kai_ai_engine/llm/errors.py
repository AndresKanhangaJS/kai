"""Erros do gateway no formato do `safe_error` (common.v1): código estável e mensagem segura.

Nunca levam a mensagem nem o corpo do fornecedor, que podem ecoar conteúdo do pedido.
"""

from typing import override


class LlmError(Exception):
    """Base. `code` segue `^[a-z][a-z0-9_]*$`; a mensagem não tem conteúdo nem segredos."""

    retryable: bool = False

    def __init__(self, code: str, message: str, *, status: int | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status
        # O adaptador marca-o: depois do primeiro delta, nem um transitório se repete (AC-004-09).
        self.after_first_delta = False

    @override
    def __repr__(self) -> str:
        return f"{type(self).__name__}(code={self.code!r}, status={self.status!r})"


def detached[E: LlmError](error: E, *, after_first_delta: bool) -> E:
    """Erro pronto a levantar sem a excepção original encadeada.

    `raise ... from None` só esconde o contexto; o `__context__` continuava a apontar para a
    excepção do SDK, que guarda o pedido (cabeçalho com a chave) e o corpo (pode ecoar conteúdo).
    """
    error.__cause__ = None
    error.__context__ = None
    error.__suppress_context__ = True
    error.after_first_delta = after_first_delta
    return error


class ProviderUnavailableError(LlmError):
    """Transitório (429, 529 e outros 5xx, ligação, timeout): pode repetir antes do 1.º delta."""

    retryable = True


class ProviderError(LlmError):
    """Permanente (restantes 4xx, recusa do modelo): nunca se repete."""


class PricingError(LlmError):
    """Modelo sem preço na tabela: recusa por omissão, nunca custo 0."""
