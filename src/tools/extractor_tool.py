from typing import Annotated
from langchain_core.tools import tool
from langchain_core.messages import ToolMessage
from langchain_core.tools.base import InjectedToolCallId
from langgraph.types import Command

@tool
def save_extracted_info(
    tool_call_id: Annotated[str, InjectedToolCallId],
    account_id: str = None,
    full_name: str = None,
    dob: str = None,
    aadhaar_last4: str = None,
    pincode: str = None,
    payment_amount: float = None,
    card_number: str = None,
    expiry_month: int = None,
    expiry_year: int = None,
    cvv: str = None
) -> Command:
    """
    Call this tool whenever the user provides ANY piece of information.
    
    CRITICAL FORMATTING RULES:
    1. DOB MUST be converted to strict YYYY-MM-DD format before saving (e.g., 'February 29 1988' becomes '1988-02-29').
    2. Strip all spaces, dashes, and special characters from card_number, aadhaar_last4, and pincode.
    """
    kwargs = {
        "account_id": account_id,
        "full_name": full_name,
        "dob": dob,
        "aadhaar_last4": aadhaar_last4,
        "pincode": pincode,
        "payment_amount": payment_amount,
        "card_number": card_number,
        "expiry_month": expiry_month,
        "expiry_year": expiry_year,
        "cvv": cvv
    }
    
    updates = {k: v for k, v in kwargs.items() if v is not None}
    
    updates["messages"] = [
        ToolMessage(content="Information saved to state.", tool_call_id=tool_call_id)
    ]

    return Command(update=updates)