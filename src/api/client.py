"""
Synchronous HTTP wrappers for the payment collection API.
Uses httpx for blocking calls.
Retry logic (tenacity) handles transient network failures.
"""

import os
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from src.config import PAYMENT_API_BASE_URL

BASE_URL = PAYMENT_API_BASE_URL.rstrip("/")

TIMEOUT = httpx.Timeout(15.0, connect=5.0)


retryable = retry(
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
    reraise=True,
)

@retryable
def lookup_account(account_id: str) -> dict:
    """
    POST /api/lookup-account

    Returns:
        On success (200): full account dict with balance, dob, aadhaar_last4, etc.
        On failure: {"error_code": "account_not_found", "message": "..."}
        On network error: raises httpx.HTTPError
    """
    url = f"{BASE_URL}/api/lookup-account"
    with httpx.Client(timeout=TIMEOUT) as client:
        try:
            resp = client.post(url, json={"account_id": account_id})
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 404:
                return resp.json()
            else:
                resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            return {
                "error_code": "server_error",
                "message": f"Unexpected server response: {e.response.status_code}",
            }


@retryable
def process_payment(
    account_id: str,
    amount: float,
    card_number: str,
    cvv: str,
    expiry_month: int,
    expiry_year: int,
    cardholder_name: str,
) -> dict:
    """
    POST /api/process-payment

    Returns:
        On success (200): {"success": true, "transaction_id": "txn_..."}
        On failure (422): {"success": false, "error_code": "..."}
        On network error: raises httpx.HTTPError
    """
    payload = {
        "account_id": account_id,
        "amount": amount,
        "payment_method": {
            "type": "card",
            "card": {
                "cardholder_name": cardholder_name,
                "card_number": card_number,
                "cvv": cvv,
                "expiry_month": expiry_month,
                "expiry_year": expiry_year,
            },
        },
    }
    url = f"{BASE_URL}/api/process-payment"
    with httpx.Client(timeout=TIMEOUT) as client:
        try:
            resp = client.post(url, json=payload)
            if resp.status_code in (200, 422):
                return resp.json()
            else:
                resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            return {
                "success": False,
                "error_code": "server_error",
                "message": f"Unexpected server response: {e.response.status_code}",
            }


PAYMENT_ERROR_MESSAGES: dict[str, str] = {
    "invalid_amount": "The payment amount is invalid. Please enter a positive amount with up to 2 decimal places.",
    "insufficient_balance": "That amount exceeds your outstanding balance. Please enter a lower amount.",
    "invalid_card": "Your card number appears to be invalid. Please re-enter your card number carefully.",
    "invalid_cvv": "The CVV you entered is incorrect. Please check the 3 (or 4) digit code on your card.",
    "invalid_expiry": "Your card expiry date is invalid or the card has expired. Please check and re-enter.",
    "server_error": "We're experiencing a technical issue on our end. Please try again in a moment.",
}

LOOKUP_ERROR_MESSAGES: dict[str, str] = {
    "account_not_found": "I couldn't find an account with that ID. Could you double-check it?",
    "server_error": "We're having trouble looking up your account right now. Please try again.",
}

def get_payment_error_message(error_code: str) -> str:
    """Returns user_message."""
    return PAYMENT_ERROR_MESSAGES.get(
        error_code,
        "An unexpected error occurred while processing your payment.",
    )

def get_lookup_error_message(error_code: str) -> str:
    return LOOKUP_ERROR_MESSAGES.get(
        error_code,
        "An unexpected error occurred. Please try again.",
    )
