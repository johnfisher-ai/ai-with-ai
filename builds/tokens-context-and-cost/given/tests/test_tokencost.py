from types import SimpleNamespace

import pytest

from tokencost import (LONG_PROMPT_PRICES, PRICES, PRICES_AS_OF, call_cost, context_check, project_conversation,
                       prompt_tokens)


def test_prices_match_the_table():
    assert PRICES_AS_OF == "2026-11"
    assert PRICES["claude-sonnet-5-5"] == {"input": 2.00, "cache_write": 2.50, "cache_read": 0.10, "output": 10.00}
    assert PRICES["claude-opus-5-5"] == {"input": 4.00, "cache_write": 5.00, "cache_read": 0.20, "output": 20.00}
    assert PRICES["claude-haiku-5-5"] == {"input": 0.10, "cache_write": 0.125, "cache_read": 0.01, "output": 0.50}
    assert LONG_PROMPT_PRICES == {"claude-haiku-5-5": (100_000, {"input": 0.50, "cache_write": 0.625,
                                                                 "cache_read": 0.05, "output": 2.50})}


def test_prompt_tokens_adds_the_three_input_counts():
    usage = {"input_tokens": 120, "output_tokens": 40, "cache_read_input_tokens": 1000,
             "cache_creation_input_tokens": 30}
    assert prompt_tokens(usage) == 1150


def test_prompt_tokens_reads_attributes_and_treats_none_as_zero():
    usage = SimpleNamespace(input_tokens=57, output_tokens=12, cache_read_input_tokens=None,
                            cache_creation_input_tokens=None)
    assert prompt_tokens(usage) == 57


def test_prompt_tokens_treats_missing_fields_as_zero():
    assert prompt_tokens({"input_tokens": 9}) == 9
    assert prompt_tokens(SimpleNamespace(output_tokens=5)) == 0


def test_a_million_tokens_cost_the_listed_rate():
    assert call_cost({"input_tokens": 1_000_000}, "claude-sonnet-5-5") == pytest.approx(2.00)
    assert call_cost({"output_tokens": 1_000_000}, "claude-sonnet-5-5") == pytest.approx(10.00)


def test_call_cost_charges_each_count_at_its_rate():
    usage = {"input_tokens": 2_000, "output_tokens": 500, "cache_read_input_tokens": 10_000,
             "cache_creation_input_tokens": 1_000}
    expected = (2_000 * 4.00 + 500 * 20.00 + 10_000 * 0.20 + 1_000 * 5.00) / 1_000_000
    assert call_cost(usage, "claude-opus-5-5") == pytest.approx(expected)


def test_call_cost_reads_an_sdk_style_usage():
    usage = SimpleNamespace(input_tokens=66, output_tokens=24, cache_read_input_tokens=None,
                            cache_creation_input_tokens=None)
    assert call_cost(usage, "claude-sonnet-5-5") == pytest.approx((66 * 2.00 + 24 * 10.00) / 1_000_000)


def test_call_cost_is_not_rounded():
    assert call_cost({"input_tokens": 1}, "claude-haiku-5-5") == pytest.approx(1e-7)


def test_haiku_at_the_threshold_uses_the_standard_rates():
    usage = {"input_tokens": 100_000, "output_tokens": 1_000}
    assert call_cost(usage, "claude-haiku-5-5") == pytest.approx((100_000 * 0.10 + 1_000 * 0.50) / 1_000_000)


def test_haiku_over_the_threshold_charges_everything_at_the_long_rates():
    usage = {"input_tokens": 100_001, "output_tokens": 1_000}
    assert call_cost(usage, "claude-haiku-5-5") == pytest.approx((100_001 * 0.50 + 1_000 * 2.50) / 1_000_000)


def test_cache_reads_count_toward_the_haiku_threshold():
    usage = {"input_tokens": 99_000, "cache_read_input_tokens": 2_000, "output_tokens": 0}
    assert call_cost(usage, "claude-haiku-5-5") == pytest.approx((99_000 * 0.50 + 2_000 * 0.05) / 1_000_000)


def test_long_prompts_cost_the_standard_rate_on_sonnet():
    assert call_cost({"input_tokens": 900_000}, "claude-sonnet-5-5") == pytest.approx(1.80)


def test_call_cost_rejects_an_unknown_model():
    with pytest.raises(ValueError, match="claude-unknown"):
        call_cost({"input_tokens": 10}, "claude-unknown")


@pytest.mark.parametrize("usage", [{"input_tokens": -1}, {"output_tokens": -5},
                                   {"cache_read_input_tokens": -2}, {"cache_creation_input_tokens": -3}])
def test_negative_counts_are_rejected(usage):
    with pytest.raises(ValueError):
        call_cost(usage, "claude-sonnet-5-5")


@pytest.mark.parametrize("prompt, max_tokens, window, expected", [
    (50_000, 1_024, 1_000_000, "fits"),
    (998_976, 1_024, 1_000_000, "fits"),
    (998_977, 1_024, 1_000_000, "may stop early"),
    (1_000_000, 0, 1_000_000, "fits"),
    (1_000_000, 1, 1_000_000, "may stop early"),
    (1_000_001, 0, 1_000_000, "too long"),
    (150_000, 64_000, 200_000, "may stop early"),
])
def test_context_check(prompt, max_tokens, window, expected):
    assert context_check(prompt, max_tokens, window) == expected


def test_context_check_defaults_to_a_million_token_window():
    assert context_check(990_000, 10_000) == "fits"
    assert context_check(990_000, 10_001) == "may stop early"


@pytest.mark.parametrize("prompt, max_tokens, window", [(-1, 10, 100), (10, -1, 100), (10, 10, 0)])
def test_context_check_rejects_bad_input(prompt, max_tokens, window):
    with pytest.raises(ValueError):
        context_check(prompt, max_tokens, window)


def test_project_conversation_grows_by_the_same_amount_each_turn():
    turns = project_conversation(first_prompt=60, added_per_turn=150, output_per_turn=90, turns=4)
    assert turns == [{"input_tokens": 60, "output_tokens": 90}, {"input_tokens": 210, "output_tokens": 90},
                     {"input_tokens": 360, "output_tokens": 90}, {"input_tokens": 510, "output_tokens": 90}]


def test_projected_turns_can_be_priced():
    turns = project_conversation(100, 200, 50, 3)
    total = sum(call_cost(t, "claude-sonnet-5-5") for t in turns)
    assert total == pytest.approx(((100 + 300 + 500) * 2.00 + 150 * 10.00) / 1_000_000)


@pytest.mark.parametrize("args", [(100, 200, 50, 0), (-1, 200, 50, 3), (100, -1, 50, 3), (100, 200, -1, 3)])
def test_project_conversation_rejects_bad_input(args):
    with pytest.raises(ValueError):
        project_conversation(*args)
