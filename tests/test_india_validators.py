import pytest

from app.utils.validators import (
    validate_aadhaar,
    validate_gstin,
    validate_ifsc,
    validate_indian_state,
    validate_mobile,
    validate_pan,
    validate_pincode,
    validate_uan,
)


def test_validate_pan_ok():
    assert validate_pan("ABCDE1234F") == "ABCDE1234F"


def test_validate_pan_invalid():
    with pytest.raises(ValueError):
        validate_pan("INVALID")


def test_validate_aadhaar_ok():
    assert validate_aadhaar("234567890123") == "234567890123"


def test_validate_aadhaar_rejects_leading_zero():
    with pytest.raises(ValueError):
        validate_aadhaar("123456789012")


def test_validate_mobile_ok():
    assert validate_mobile("+919876543210") == "+919876543210"
    assert validate_mobile("9876543210") == "9876543210"


def test_validate_gstin_ok():
    assert validate_gstin("27AABCO1234A1Z5") == "27AABCO1234A1Z5"


def test_validate_pincode_ok():
    assert validate_pincode("400001") == "400001"


def test_validate_ifsc_ok():
    assert validate_ifsc("HDFC0001234") == "HDFC0001234"


def test_validate_indian_state_ok():
    assert validate_indian_state("Maharashtra") == "Maharashtra"


def test_validate_indian_state_invalid():
    with pytest.raises(ValueError):
        validate_indian_state("California")


def test_validate_uan_ok():
    assert validate_uan("100123456789") == "100123456789"
