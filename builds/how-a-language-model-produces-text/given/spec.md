# sampling.py

A small module for studying how a language model chooses its next token. It turns scores into
probabilities, turns a list of sampled answers into a distribution, and measures how spread out a
distribution is. Use only the Python standard library.

## softmax(scores, temperature=1.0)

`scores` is a non-empty sequence of numbers, one per candidate token. Return a list of probabilities,
in the same order, that sum to 1. Divide every score by `temperature` before exponentiating. A lower
temperature makes the highest score's share larger, and a higher one spreads the probability out.
Subtract the largest scaled score before exponentiating, so large scores don't overflow.

Raise `ValueError` if `scores` is empty or `temperature` is not greater than 0.

## empirical_distribution(answers)

`answers` is an iterable of strings, the replies a model gave to the same request. Normalize each one by
stripping surrounding whitespace, removing trailing `.`, `!` and `?`, and lowercasing it. Return a dict
from each distinct normalized answer to its share of all the answers. The shares sum to 1. Order the
dict by share, largest first, and alphabetically among equal shares.

Raise `ValueError` if there are no answers.

## entropy_bits(probabilities)

`probabilities` is either a sequence of probabilities or a mapping whose values are probabilities.
Return the Shannon entropy in bits: the sum of `-p * log2(p)` over every `p` greater than 0. A
distribution with one certain outcome has entropy 0.0, and two equally likely outcomes have 1.0.

Raise `ValueError` if a probability is negative or the probabilities don't sum to 1 within 1e-6.
