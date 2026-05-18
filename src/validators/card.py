"""
Validators for card details, amounts, and dates.
All validation is pure Python — no external dependencies beyond stdlib.
These run BEFORE any API call to catch obvious problems early.
"""

from datetime import date
import re


def luhn_check(card_number: str) -> bool:
    """Return True if card_number passes the Luhn check."""
    digits = [int(d) for d in card_number if d.isdigit()]
    if len(digits) < 13 or len(digits) > 19:
        return False
    # Double every second digit from the right
    for i in range(len(digits) - 2, -1, -2):
        digits[i] *= 2
        if digits[i] > 9:
            digits[i] -= 9
    return sum(digits) % 10 == 0


def normalize_card_number(raw: str) -> str:
    """Strip spaces, dashes, and other separators; return digit-only string."""
    return re.sub(r"[\s\-]", "", raw)


def validate_card_number(card_number: str) -> tuple[bool, str]:
    """
    Returns (is_valid, error_message).
    Checks: digit-only, length 13-19, passes Luhn.
    """
    digits = normalize_card_number(card_number)
    if not digits.isdigit():
        return False, "Card number must contain only digits."
    if len(digits) < 13 or len(digits) > 19:
        return False, f"Card number must be 13–19 digits (got {len(digits)})."
    if not luhn_check(digits):
        return False, "Card number appears to be invalid. Please double-check it."
    return True, ""


def validate_cvv(cvv: str, card_number: str = "") -> tuple[bool, str]:
    """
    Standard cards: 3 digits. Amex (starts with 34 or 37): 4 digits.
    """
    if not cvv.isdigit():
        return False, "CVV must contain only digits."
    digits = normalize_card_number(card_number)
    is_amex = digits.startswith("34") or digits.startswith("37")
    expected_len = 4 if is_amex else 3
    if len(cvv) != expected_len:
        return False, f"CVV must be {expected_len} digits for this card type."
    return True, ""


def validate_expiry(month: int, year: int) -> tuple[bool, str]:
    """Return (is_valid, error_message). Card must not be expired."""
    if not (1 <= month <= 12):
        return False, "Expiry month must be between 1 and 12."
    # Normalise 2-digit year (e.g. 27 → 2027)
    if year < 100:
        year += 2000
    try:
        # Card is valid through the last day of the expiry month
        today = date.today()
        exp_date = date(year, month, 1)
        # Valid as long as expiry month/year >= current month/year
        if (exp_date.year, exp_date.month) < (today.year, today.month):
            return False, "This card has expired."
        return True, ""
    except ValueError as e:
        return False, f"Invalid expiry date: {e}"


def validate_amount(amount: float, balance: float) -> tuple[bool, str]:
    """
    Amount must be:
    - Positive
    - At most 2 decimal places
    - ≤ outstanding balance
    """
    if amount <= 0:
        return False, "Payment amount must be greater than zero."
    # Check decimal places
    if round(amount, 2) != amount:
        return False, "Amount must have at most 2 decimal places."
    if amount > balance:
        return False, f"Amount ₹{amount:.2f} exceeds your outstanding balance of ₹{balance:.2f}."
    return True, ""
