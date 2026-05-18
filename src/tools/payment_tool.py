from typing import Annotated
from langchain_core.tools import tool
from langchain_core.messages import ToolMessage
from langchain_core.tools.base import InjectedToolCallId
from langgraph.prebuilt import InjectedState
from langgraph.types import Command
from src.graph.state import AgentState
from src.api.client import process_payment, get_payment_error_message
from src.validators.card import validate_card_number, validate_cvv, validate_expiry, validate_amount

@tool
def process_payment_tool(
    state: Annotated[AgentState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """
    Process the card payment.
    Call this after the user is verified, and you have saved the payment_amount, card_number, cvv, expiry_month, and expiry_year into the state.
    """
    if not state.get("is_verified"):
        return Command(update={
            "messages": [ToolMessage(content="User not verified.", tool_call_id=tool_call_id)]
        })
        
    account_id = state.get("account_id")
    amount = state.get("payment_amount")
    card_number = state.get("card_number")
    cvv = state.get("cvv")
    expiry_month = state.get("expiry_month")
    expiry_year = state.get("expiry_year")
    
    if not all([account_id, amount, card_number, cvv, expiry_month, expiry_year]):
        return Command(update={
            "messages": [ToolMessage(content="Missing payment details in state. Please extract them first.", tool_call_id=tool_call_id)]
        })
        
    real_data = state.get("account_details", {})
    balance = real_data.get("balance", 0.0)
    
    ok, err = validate_amount(amount, balance)
    if not ok: 
        return Command(update={"messages": [ToolMessage(content=err, tool_call_id=tool_call_id)]})
    
    ok, err = validate_card_number(card_number)
    if not ok: 
        return Command(update={"messages": [ToolMessage(content=err, tool_call_id=tool_call_id)]})
    
    ok, err = validate_expiry(expiry_month, expiry_year)
    if not ok: 
        return Command(update={"messages": [ToolMessage(content=err, tool_call_id=tool_call_id)]})
    
    ok, err = validate_cvv(cvv, card_number)
    if not ok: 
        return Command(update={"messages": [ToolMessage(content=err, tool_call_id=tool_call_id)]})
    
    attempts = state.get("payment_attempts", 0) + 1
    
    try:
        result = process_payment(account_id, amount, card_number, cvv, expiry_month, expiry_year, state.get("full_name", ""))
    except Exception as e:
        return Command(update={
            "payment_attempts": attempts,
            "messages": [ToolMessage(content=f"Network error: {str(e)}", tool_call_id=tool_call_id)]
        })
        
    if result.get("success"):
        return Command(
            update={
                "session_status": "SUCCESS",
                "messages": [ToolMessage(content=f"Payment Successful! Txn: {result.get('transaction_id')}. Close session.", tool_call_id=tool_call_id)]
            }
        )
        
    err_msg = get_payment_error_message(result.get("error_code"))
    return Command(
        update={
            "payment_attempts": attempts,
            "card_number": None,
            "cvv": None,
            "messages": [ToolMessage(content=f"Payment API failed: {err_msg}. Attempt {attempts}/3.", tool_call_id=tool_call_id)]
        }
    )
