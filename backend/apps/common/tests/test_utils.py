from apps.common.utils import mask_phone


def test_mask_phone():
    assert mask_phone("9812345621") == "98XXXXXX21"
    assert mask_phone("+91 98123 45621") == "91XXXXXXXX21"
    assert mask_phone("") == ""
    assert mask_phone("123") == "XXX"
