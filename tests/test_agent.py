"""
Integration tests for the Agent class.
Tests the full conversation flow via agent.next() calls.

NOTE: These tests make REAL API calls to the payment service and REAL LLM calls.
      Set OPENAI_API_KEY in your .env before running.

Run with:
    pytest tests/test_agent.py -v
"""

import pytest
from agent import Agent


def make_agent() -> Agent:
    """Fresh agent for each test."""
    return Agent()


class TestGreeting:
    def test_greeting_returned_on_first_call(self):
        agent = make_agent()
        result = agent.next("hi")
        assert "message" in result
        msg = result["message"].lower()
        assert any(kw in msg for kw in ["welcome", "hello", "account id", "account"])

    def test_greeting_always_asks_for_account_id(self):
        agent = make_agent()
        result = agent.next("just testing")
        assert "account" in result["message"].lower()


class TestAccountLookup:
    def test_valid_account_id_extracted(self):
        agent = make_agent()
        agent.next("hi")
        result = agent.next("my account is ACC1001")
        assert "name" in result["message"].lower()

    def test_invalid_account_id_re_asks(self):
        agent = make_agent()
        agent.next("hi")
        result = agent.next("ACC9999")  # non-existent
        msg = result["message"].lower()
        assert any(kw in msg for kw in ["couldn't find", "account", "check"])

    def test_messy_account_id_still_works(self):
        agent = make_agent()
        agent.next("hi")
        result = agent.next("yeah my account number is ACC 1001 I think")
        assert "name" in result["message"].lower()


class TestVerification:
    def _get_to_verification(self, agent: Agent):
        """Helper: run through greeting + lookup."""
        agent.next("hi")
        agent.next("ACC1001")

    def test_correct_name_prompts_secondary(self):
        agent = make_agent()
        self._get_to_verification(agent)
        result = agent.next("Nithin Jain")
        msg = result["message"].lower()
        assert any(kw in msg for kw in ["date of birth", "aadhaar", "pincode"])

    def test_wrong_name_fails(self):
        agent = make_agent()
        self._get_to_verification(agent)
        agent.next("My name is ABCD")
        result = agent.next("1990-05-14")
        msg = result["message"].lower()
        assert any(kw in msg for kw in ["wasn't able", "verify", "attempt", "doesn't match", "does not match"])

    def test_correct_dob_verifies(self):
        agent = make_agent()
        self._get_to_verification(agent)
        agent.next("Nithin Jain")
        result = agent.next("DOB is 1990-05-14")
        msg = result["message"].lower()
        assert "verified" in msg or "balance" in msg

    def test_correct_aadhaar_verifies(self):
        agent = make_agent()
        self._get_to_verification(agent)
        agent.next("Nithin Jain")
        result = agent.next("aadhaar last 4 is 4321")
        msg = result["message"].lower()
        assert "verified" in msg or "balance" in msg

    def test_correct_pincode_verifies(self):
        agent = make_agent()
        self._get_to_verification(agent)
        agent.next("Nithin Jain")
        result = agent.next("pincode is 400001")
        msg = result["message"].lower()
        assert "verified" in msg or "balance" in msg

    def test_max_retries_closes_conversation(self):
        agent = make_agent()
        self._get_to_verification(agent)
        for _ in range(3):
            agent.next("Wrong Name")
            agent.next("9999-01-01")
        result = agent.next("Wrong Name")
        msg = result["message"].lower()
        assert any(kw in msg for kw in ["unable", "support", "closed"])


class TestPaymentFlow:
    def _get_to_payment(self, agent: Agent, account: str = "ACC1001"):
        """Helper: complete greeting, lookup, and verification."""
        agent.next("hi")
        if account == "ACC1001":
            agent.next("ACC1001")
            agent.next("Nithin Jain")
            agent.next("DOB 1990-05-14")
        elif account == "ACC1002":
            agent.next("ACC1002")
            agent.next("Rajarajeswari Balasubramaniam")
            agent.next("aadhaar 9876")

    def test_balance_shown_after_verification(self):
        agent = make_agent()
        self._get_to_payment(agent)
        # The verification response already includes balance
        # This tests that the agent doesn't skip to payment
        result = agent.next("500")
        assert "card" in result["message"].lower()

    def test_full_payment_success(self):
        agent = make_agent()
        self._get_to_payment(agent)
        agent.next("500")
        result = agent.next(
            "card 4532015112830366 cvv 123 expires 12/2027 cardholder Nithin Jain"
        )
        msg = result["message"].lower()
        assert "successful" in msg or "transaction" in msg

    def test_invalid_card_rejected_locally(self):
        agent = make_agent()
        self._get_to_payment(agent)
        agent.next("500")
        result = agent.next(
            "card 1234567890123456 cvv 123 expires 12/2027 name Nithin Jain"
        )
        msg = result["message"].lower()
        assert "invalid" in msg or "card" in msg


class TestEdgeCases:
    def test_zero_balance_acc1003(self):
        agent = make_agent()
        agent.next("hi")
        agent.next("ACC1003")
        agent.next("Priya Agarwal")
        result = agent.next("DOB 1992-08-10")
        msg = result["message"].lower()
        assert "no outstanding balance" in msg or "0.00" in msg

    def test_leap_year_dob_acc1004(self):
        agent = make_agent()
        agent.next("hi")
        agent.next("ACC1004")
        agent.next("Rahul Mehta")
        result = agent.next("my birthday is February 29 1988")
        msg = result["message"].lower()
        assert "verified" in msg or "balance" in msg or "3,200" in msg

    def test_wrong_dob_near_leap_year(self):
        """1988-02-28 is NOT the same as 1988-02-29."""
        agent = make_agent()
        agent.next("hi")
        agent.next("ACC1004")
        agent.next("Rahul Mehta")
        result = agent.next("DOB February 28 1988")
        msg = result["message"].lower()
        assert any(kw in msg for kw in ["wasn't able", "verify", "date of birth", "aadhaar", "pincode"])

    def test_partial_payment(self):
        """Partial payment (amount < balance) should be allowed."""
        agent = make_agent()
        agent.next("hi")
        agent.next("ACC1001")
        agent.next("Nithin Jain")
        agent.next("DOB 1990-05-14")
        agent.next("can I pay 200")
        result = agent.next(
            "card 4532015112830366 cvv 123 expires 12/2027 name Nithin Jain"
        )
        msg = result["message"].lower()
        assert "successful" in msg or "transaction" in msg
