from asc2mb.convert import combine_class_ids


def test_two_divisions():
    assert combine_class_ids(["G6_Science_A", "G6_Science_B"]) == "G6_Science_AB"


def test_three_divisions_with_numbers():
    assert (
        combine_class_ids(["G6_Math_A1", "G6_Math_A2", "G6_Math_B1"]) == "G6_Math_AB12"
    )


def test_single_id_is_unchanged():
    assert combine_class_ids(["G6_Art_A"]) == "G6_Art_A"


def test_different_lengths():
    assert combine_class_ids(["G6_A", "G6_AB"]) == "G6_AB"
