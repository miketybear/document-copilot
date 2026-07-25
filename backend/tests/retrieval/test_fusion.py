from app.retrieval.fusion import reciprocal_rank_fusion


def test_single_ranking_preserves_order():
    assert reciprocal_rank_fusion([["a", "b", "c"]]) == ["a", "b", "c"]


def test_agreement_across_lists_boosts_rank():
    # "b" is ranked lower in the first list but appears in both -> should end up first.
    result = reciprocal_rank_fusion(
        [
            ["a", "b", "c"],
            ["b", "d"],
        ]
    )
    assert result[0] == "b"


def test_item_only_in_one_list_is_still_included():
    result = reciprocal_rank_fusion([["a"], ["b"]])
    assert set(result) == {"a", "b"}


def test_empty_rankings_returns_empty():
    assert reciprocal_rank_fusion([]) == []
