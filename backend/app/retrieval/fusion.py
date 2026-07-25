DEFAULT_RRF_K = 60


def reciprocal_rank_fusion(rankings: list[list[str]], k: int = DEFAULT_RRF_K) -> list[str]:
    """Merges multiple ranked ID lists into one, by summing 1/(k + rank) across lists.

    Standard RRF: https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf
    """
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, item_id in enumerate(ranking):
            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank + 1)

    return sorted(scores, key=lambda item_id: scores[item_id], reverse=True)
