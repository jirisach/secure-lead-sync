from sls.core.normalize import normalize_email, normalize_phone, normalize_text


def test_normalize_email_lowercase_and_trim():
    assert normalize_email("  Jan.Novak@Example.com ") == "jan.novak@example.com"


def test_normalize_email_invalid():
    assert normalize_email("not-an-email") is None


def test_normalize_phone_plus_format():
    assert normalize_phone("+420 777 123 456") == "+420777123456"


def test_normalize_phone_00_prefix():
    assert normalize_phone("00420 777123456") == "+420777123456"


def test_normalize_text_blank_to_none():
    assert normalize_text("   ") is None