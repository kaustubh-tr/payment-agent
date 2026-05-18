from datetime import datetime


def validate_date_string(dob: str) -> tuple[bool, str]:
    """
    Validate that a YYYY-MM-DD string is a real calendar date.
    Correctly handles leap years (e.g. 1988-02-29 is valid).
    """
    try:
        datetime.strptime(dob, "%Y-%m-%d")
        return True, ""
    except ValueError:
        return False, f"'{dob}' is not a valid calendar date format (YYYY-MM-DD)."

def validate_aadhaar_last4(value: str) -> tuple[bool, str]:
    """Must be exactly 4 digits."""
    if not value.isdigit() or len(value) != 4:
        return False, "Aadhaar last 4 must be exactly 4 digits."
    return True, ""

def validate_pincode(value: str) -> tuple[bool, str]:
    """Indian pincode: exactly 6 digits."""
    cleaned = value.replace(" ", "")
    if not cleaned.isdigit() or len(cleaned) != 6:
        return False, "Pincode must be exactly 6 digits."
    return True, ""
