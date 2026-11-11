import math

import pytest

from sampling import empirical_distribution, entropy_bits, softmax


def test_softmax_sums_to_one_and_keeps_order():
    probs = softmax([2.0, 1.0, 0.1])
    assert math.isclose(sum(probs), 1.0)
    assert probs[0] > probs[1] > probs[2]


def test_softmax_matches_the_formula():
    probs = softmax([1.0, 0.0])
    assert math.isclose(probs[0], math.e / (math.e + 1))


def test_lower_temperature_sharpens_and_higher_flattens():
    scores = [2.0, 1.0, 0.1]
    assert softmax(scores, temperature=0.5)[0] > softmax(scores)[0] > softmax(scores, temperature=2.0)[0]


def test_equal_scores_give_equal_probabilities():
    assert softmax([3.0, 3.0, 3.0, 3.0]) == pytest.approx([0.25] * 4)


def test_large_scores_do_not_overflow():
    probs = softmax([1000.0, 999.0])
    assert probs == pytest.approx([1 / (1 + math.exp(-1)), math.exp(-1) / (1 + math.exp(-1))])


@pytest.mark.parametrize("scores, temperature", [([], 1.0), ([1.0], 0.0), ([1.0], -1.0)])
def test_softmax_rejects_bad_input(scores, temperature):
    with pytest.raises(ValueError):
        softmax(scores, temperature)


def test_empirical_distribution_normalizes_and_orders():
    dist = empirical_distribution([" Apple.", "apple", "Mango!", "APPLE", "kiwi?"])
    assert list(dist) == ["apple", "kiwi", "mango"]
    assert dist == pytest.approx({"apple": 0.6, "kiwi": 0.2, "mango": 0.2})


def test_empirical_distribution_rejects_no_answers():
    with pytest.raises(ValueError):
        empirical_distribution([])


def test_entropy_of_certain_and_even_distributions():
    assert entropy_bits([1.0]) == 0.0
    assert math.isclose(entropy_bits([0.5, 0.5]), 1.0)
    assert math.isclose(entropy_bits({"a": 0.25, "b": 0.25, "c": 0.25, "d": 0.25}), 2.0)


def test_entropy_ignores_zero_probabilities():
    assert math.isclose(entropy_bits([0.5, 0.5, 0.0]), 1.0)


@pytest.mark.parametrize("probs", [[0.5, 0.6], [1.2, -0.2]])
def test_entropy_rejects_invalid_distributions(probs):
    with pytest.raises(ValueError):
        entropy_bits(probs)
