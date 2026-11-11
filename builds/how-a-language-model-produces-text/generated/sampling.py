import math
from collections import Counter


def softmax(scores, temperature=1.0):
    scores = list(scores)
    if not scores:
        raise ValueError("scores must be non-empty")
    if not temperature > 0:
        raise ValueError("temperature must be greater than 0")
    scaled = [s / temperature for s in scores]
    m = max(scaled)
    exps = [math.exp(s - m) for s in scaled]
    total = sum(exps)
    return [e / total for e in exps]


def empirical_distribution(answers):
    normalized = [a.strip().rstrip(".!?").lower() for a in answers]
    if not normalized:
        raise ValueError("no answers")
    n = len(normalized)
    counts = Counter(normalized)
    items = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return {k: v / n for k, v in items}


def entropy_bits(probabilities):
    if hasattr(probabilities, "values"):
        probs = list(probabilities.values())
    else:
        probs = list(probabilities)
    if any(p < 0 for p in probs):
        raise ValueError("negative probability")
    if abs(sum(probs) - 1) > 1e-6:
        raise ValueError("probabilities must sum to 1")
    h = sum(-p * math.log2(p) for p in probs if p > 0)
    return h + 0.0
