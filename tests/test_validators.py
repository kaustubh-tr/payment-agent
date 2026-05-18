"""
Unit tests for validators/card.py.
Tests Luhn check, card number validation, CVV, expiry, amount, date, Aadhaar, pincode.
"""

import pytest
from src.validators.card import (
    luhn_check,
    validate_card_number,
    validate_cvv,
    validate_expiry,
    validate_amount,
)
from src.validators.identity import (
    validate_date_string,
    validate_aadhaar_last4,
    validate_pincode,
)

class TestLuhn:
    def test_valid_visa(self):
        assert luhn_check("4532015112830366") is True

    def test_valid_mastercard(self):
        assert luhn_check("5425233430109903") is True

    def test_invalid_card(self):
        assert luhn_check("1234567890123456") is False

    def test_too_short(self):
        assert luhn_check("123456789012") is False


class TestCardNumber:
    def test_valid_card(self):
        ok, err = validate_card_number("4532015112830366")
        assert ok is True

    def test_spaces_stripped(self):
        ok, err = validate_card_number("4532 0151 1283 0366")
        assert ok is True

    def test_invalid_luhn(self):
        ok, err = validate_card_number("1234567890123456")
        assert ok is False
        assert "invalid" in err.lower()

    def test_too_short(self):
        ok, err = validate_card_number("123456789012")
        assert ok is False

    def test_non_digits(self):
        ok, err = validate_card_number("4532-ABCD-1283-0366")
        assert ok is False


class TestCVV:
    def test_valid_3_digit(self):
        ok, err = validate_cvv("123", "4532015112830366")
        assert ok is True

    def test_invalid_2_digit(self):
        ok, err = validate_cvv("12", "4532015112830366")
        assert ok is False

    def test_amex_4_digit_valid(self):
        # Amex starts with 34 or 37
        ok, err = validate_cvv("1234", "371449635398431")
        assert ok is True

    def test_amex_3_digit_invalid(self):
        ok, err = validate_cvv("123", "371449635398431")
        assert ok is False


class TestExpiry:
    def test_future_date(self):
        ok, err = validate_expiry(12, 2030)
        assert ok is True

    def test_past_date(self):
        ok, err = validate_expiry(1, 2020)
        assert ok is False
        assert "expired" in err.lower()

    def test_invalid_month(self):
        ok, err = validate_expiry(13, 2030)
        assert ok is False

    def test_two_digit_year(self):
        ok, err = validate_expiry(12, 27)  # 27 → 2027
        assert ok is True

    def test_month_zero_invalid(self):
        ok, err = validate_expiry(0, 2030)
        assert ok is False


class TestAmount:
    def test_valid_amount(self):
        ok, err = validate_amount(500.0, 1250.75)
        assert ok is True

    def test_full_balance(self):
        ok, err = validate_amount(1250.75, 1250.75)
        assert ok is True

    def test_exceeds_balance(self):
        ok, err = validate_amount(1300.0, 1250.75)
        assert ok is False
        assert "exceeds" in err.lower()

    def test_zero_amount(self):
        ok, err = validate_amount(0.0, 1250.75)
        assert ok is False

    def test_negative_amount(self):
        ok, err = validate_amount(-100.0, 1250.75)
        assert ok is False

    def test_too_many_decimals(self):
        ok, err = validate_amount(100.123, 1250.75)
        assert ok is False


class TestDateString:
    def test_valid_date(self):
        ok, err = validate_date_string("1990-05-14")
        assert ok is True

    def test_leap_year_valid(self):
        ok, err = validate_date_string("1988-02-29")
        assert ok is True

    def test_non_leap_year_invalid(self):
        ok, err = validate_date_string("1989-02-29")
        assert ok is False

    def test_invalid_month(self):
        ok, err = validate_date_string("1990-13-01")
        assert ok is False

    def test_invalid_day(self):
        ok, err = validate_date_string("1990-04-31")
        assert ok is False


class TestAadhaarLast4:
    def test_valid(self):
        ok, err = validate_aadhaar_last4("4321")
        assert ok is True

    def test_too_short(self):
        ok, err = validate_aadhaar_last4("432")
        assert ok is False

    def test_non_digits(self):
        ok, err = validate_aadhaar_last4("43AB")
        assert ok is False


class TestPincode:
    def test_valid(self):
        ok, err = validate_pincode("400001")
        assert ok is True

    def test_space_separated(self):
        ok, err = validate_pincode("4 0 0 0 0 1")
        assert ok is True

    def test_too_short(self):
        ok, err = validate_pincode("40000")
        assert ok is False

    def test_non_digits(self):
        ok, err = validate_pincode("4000AB")
        assert ok is False
