"""Tabela de preços versionada (SPEC-004 §3.3, AC-004-07): custo exacto em `Decimal`.

A versão é o nome do ficheiro em `pricing/`. Mudar um preço é um ficheiro novo, nunca uma
edição: o custo registado tem de ser reprodutível.
"""

import json
from dataclasses import dataclass
from decimal import ROUND_CEILING, Decimal
from pathlib import Path

from kai_ai_engine.llm.errors import PricingError
from kai_ai_engine.llm.gateway import ModelUsage, Usage

PRICING_DIR = Path(__file__).parent / "pricing"
CURRENT_VERSION = "2026-11-23"
MILLION = Decimal(1_000_000)
# `decimal_usd` (common.v1) aceita até 8 casas; arredonda-se para cima (nunca subestimar).
QUANTUM = Decimal("0.00000001")
MODIFIER_UPPER_BOUND = Decimal(2)


@dataclass(frozen=True)
class ModelPrice:
    input: Decimal
    output: Decimal
    cache_read: Decimal
    cache_write: Decimal


@dataclass(frozen=True)
class PriceTable:
    version: str
    models: dict[str, ModelPrice]

    def price(self, model: str) -> ModelPrice:
        try:
            return self.models[model]
        except KeyError:
            raise PricingError("unpriced_model", "modelo sem preço na tabela") from None

    def cost(self, usage: Usage) -> Decimal:
        """Custo exacto. Modelo sem preço ou modificador desconhecido: `PricingError`."""
        if usage.modifiers:
            raise PricingError("unpriced_modifier", "modificador de preço fora da tabela")
        return quantize_usd(sum((self._cost_one(u, self.price(u.model)) for u in usage.by_model), Decimal(0)))

    def cost_conservative(self, usage: Usage) -> Decimal:
        """Custo nunca subestimado, para quando `cost` falha depois de a chamada já ter custado.

        Um modelo sem preço paga ao preço mais alto da tabela; com modificadores, tudo x2
        (cobre fast mode x2, geografia x1,1 e a escrita de cache de 1 h).
        """
        worst = self._worst_price()
        total = sum((self._cost_one(u, self.models.get(u.model, worst)) for u in usage.by_model), Decimal(0))
        return quantize_usd(total * (MODIFIER_UPPER_BOUND if usage.modifiers else 1))

    def _worst_price(self) -> ModelPrice:
        prices = list(self.models.values())
        return ModelPrice(
            input=max(p.input for p in prices),
            output=max(p.output for p in prices),
            cache_read=max(p.cache_read for p in prices),
            cache_write=max(p.cache_write for p in prices),
        )

    @staticmethod
    def _cost_one(u: ModelUsage, p: ModelPrice) -> Decimal:
        return (
            u.input_tokens * p.input
            + u.output_tokens * p.output
            + u.cache_read_tokens * p.cache_read
            + u.cache_write_tokens * p.cache_write
        ) / MILLION

    def estimate_max_cost(
        self, models: tuple[str, ...], input_tokens: int, max_output_tokens: int
    ) -> Decimal:
        """Tecto antes da chamada: a cadeia inteira (modelo e fallbacks).

        Com o fallback do lado do servidor, cada tentativa é facturada: a entrada paga-se em
        cada modelo, e uma tentativa recusada a meio pode ter gerado até `max_tokens`.
        """
        if not models:
            raise PricingError("unpriced_model", "nenhum modelo para estimar")
        total = sum(
            (
                (input_tokens * self.price(m).input + max_output_tokens * self.price(m).output) / MILLION
                for m in models
            ),
            Decimal(0),
        )
        return quantize_usd(total)


def quantize_usd(value: Decimal) -> Decimal:
    """8 casas, sempre para cima (`decimal_usd`): nunca subestima."""
    return value.quantize(QUANTUM, rounding=ROUND_CEILING)


def load_price_table(version: str = CURRENT_VERSION) -> PriceTable:
    raw = json.loads((PRICING_DIR / f"{version}.json").read_text(encoding="utf-8"))
    if raw.get("version") != version or raw.get("currency") != "USD":
        raise PricingError("invalid_price_table", "tabela de preços inconsistente")
    models = {
        name: ModelPrice(
            input=Decimal(p["input"]),
            output=Decimal(p["output"]),
            cache_read=Decimal(p["cache_read"]),
            cache_write=Decimal(p["cache_write"]),
        )
        for name, p in raw["models"].items()
    }
    return PriceTable(version=version, models=models)


def format_usd(value: Decimal) -> str:
    """Formato `decimal_usd`: sem notação científica nem zeros à direita."""
    text = format(value.normalize(), "f")
    return text if text != "-0" else "0"
