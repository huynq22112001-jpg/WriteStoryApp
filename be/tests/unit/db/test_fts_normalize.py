from writestory_be.infrastructure.db.fts import build_match_query, normalize_for_search


def test_vietnamese_search_normalization_and_fts_query_escaping() -> None:
    assert normalize_for_search("Nguyễn") == "nguyen"
    assert normalize_for_search("Ộc") == "oc"
    assert normalize_for_search("Đường") == "duong"
    assert build_match_query('Nguyễn "OR" (DROP)') == '"nguyen" AND "or" AND "drop"'
    assert build_match_query("nguyen van", prefix_last=True) == '"nguyen" AND "van"*'
    assert build_match_query("!@#") == ""
