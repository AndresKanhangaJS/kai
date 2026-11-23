"""Tabela de preços versionada e custo exacto (SPEC-004 §3.3, AC-004-07)."""

import json
import os
import re
from decimal import Decimal
from pathlib import Path

import pytest

from kai_ai_engine.llm.errors import PricingError
from kai_ai_engine.llm.gateway import ModelUsage, Usage
from kai_ai_engine.llm.pricing import CURRENT_VERSION, PRICING_DIR, format_usd, load_price_table


def _decimal_usd_pattern() -> str:
    contracts = Path(os.environ.get("KAI_CONTRACTS_DIR", "/contracts"))
    common = contracts / "schemas" / "common.v1.json"
    if not common.exists():
        common = Path(__file__).resolve().parents[3] / "packages" / "contracts" / "schemas" / "common.v1.json"
    pattern: str = json.loads(common.read_text(encoding="utf-8"))["$defs"]["decimal_usd"]["pattern"]
    return pattern


TABLE = load_price_table()


def test_custo_exacto_do_opus_5_5_com_cache() -> None:
    usage = Usage(
        by_model=(
            ModelUsage(
                model="claude-opus-5-5",
                input_tokens=10_000,
                output_tokens=15_000,
                cache_read_tokens=40_000,
                cache_write_tokens=2_000,
            ),
        )
    )
    # 10k*4 + 15k*20 + 40k*0.20 + 2k*5 = 0.04 + 0.30 + 0.008 + 0.01 (exemplo da página de preços + escrita)
    assert TABLE.cost(usage) == Decimal("0.358")


def test_o_fallback_e_cobrado_ao_preco_do_seu_modelo() -> None:
    usage = Usage(
        by_model=(
            ModelUsage(model="claude-opus-5-5", input_tokens=1_000_000),
            ModelUsage(model="claude-opus-5", input_tokens=1_000_000, output_tokens=1_000_000),
        )
    )
    assert TABLE.cost(usage) == Decimal(4 + 5 + 25)


def test_arredonda_para_cima_a_8_casas_e_respeita_decimal_usd() -> None:
    usage = Usage(by_model=(ModelUsage(model="claude-sonnet-5-5", cache_read_tokens=1),))
    cost = TABLE.cost(usage)
    assert cost == Decimal("0.00000010")
    pattern = _decimal_usd_pattern()
    for value in (cost, Decimal(0), Decimal("0.358"), Decimal("123.45000000")):
        assert re.fullmatch(pattern, format_usd(value)), format_usd(value)


def test_estimativa_maxima_soma_a_cadeia_de_fallback() -> None:
    only_primary = TABLE.estimate_max_cost(("claude-opus-5-5",), 1_000, 1_000)
    with_fallback = TABLE.estimate_max_cost(("claude-opus-5-5", "claude-opus-5"), 1_000, 1_000)
    assert only_primary == Decimal("0.024")
    # Cada tentativa é facturada: 0.024 (Opus 5.5, recusado a meio) + 0.03 (Opus 5).
    assert with_fallback == Decimal("0.054")


def test_custo_conservador_nunca_subestima() -> None:
    unknown = Usage(by_model=(ModelUsage(model="claude-desconhecido", input_tokens=1_000_000),))
    assert TABLE.cost_conservative(unknown) == Decimal(5)  # preço de entrada mais alto da tabela
    known = Usage(by_model=(ModelUsage(model="claude-opus-5-5", input_tokens=1_000_000),))
    assert TABLE.cost_conservative(known) == TABLE.cost(known) == Decimal(4)
    with_geo = Usage(by_model=known.by_model, modifiers=frozenset({"inference_geo"}))
    with pytest.raises(PricingError):
        TABLE.cost(with_geo)
    assert TABLE.cost_conservative(with_geo) == Decimal(8)


def test_negativo_modelo_sem_preco_e_recusado_nunca_custo_zero() -> None:
    with pytest.raises(PricingError):
        TABLE.cost(Usage(by_model=(ModelUsage(model="claude-desconhecido", input_tokens=1),)))
    with pytest.raises(PricingError):
        TABLE.estimate_max_cost(("claude-desconhecido",), 1, 1)


def test_a_tabela_actual_existe_e_e_coerente() -> None:
    assert (PRICING_DIR / f"{CURRENT_VERSION}.json").exists()
    assert TABLE.version == CURRENT_VERSION
    for price in TABLE.models.values():
        assert price.cache_read < price.input < price.cache_write < price.output
