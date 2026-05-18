from typing import Annotated
from langchain_core.tools import tool
from langchain_core.messages import ToolMessage
from langchain_core.tools.base import InjectedToolCallId
from langgraph.prebuilt import InjectedState
from langgraph.types import Command
from src.graph.state import AgentState
from src.validators.identity import validate_date_string, validate_aadhaar_last4, validate_pincode

@tool
def verify_identity_tool(
    state: Annotated[AgentState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """
    Verify the user's identity. 
    Call this immediately after saving the full_name, and call it AGAIN after saving a secondary factor.
    """
    real_data = state.get("account_details")
    if not real_data:
        return Command(update={
            "messages": [ToolMessage(content="No account_details in state. Call lookup_account_tool first.", tool_call_id=tool_call_id)]
        })
        
    full_name = state.get("full_name")
    if not full_name:
        return Command(update={
            "messages": [ToolMessage(content="Missing full_name in state. Save it before verifying.", tool_call_id=tool_call_id)]
        })
        
    name_match = full_name.strip().lower() == real_data.get("full_name", "").strip().lower()
    
    sec_match = False
    provided_sec = False
    validation_errors = []
    
    # Check if a secondary factor is present
    if state.get("dob"):
        provided_sec = True
        ok, err = validate_date_string(state.get("dob"))
        if not ok: validation_errors.append(err)
        elif state.get("dob") == real_data.get("dob"): sec_match = True
            
    elif state.get("aadhaar_last4"):
        provided_sec = True
        ok, err = validate_aadhaar_last4(state.get("aadhaar_last4"))
        if not ok: validation_errors.append(err)
        elif state.get("aadhaar_last4") == real_data.get("aadhaar_last4"): sec_match = True
            
    elif state.get("pincode"):
        provided_sec = True
        ok, err = validate_pincode(state.get("pincode"))
        if not ok: validation_errors.append(err)
        elif state.get("pincode") == real_data.get("pincode"): sec_match = True

    # PARTIAL VERIFICATION (NAME ONLY)
    if not provided_sec:
        if name_match:
            return Command(update={
                "messages": [ToolMessage(content="Full name matches perfectly. Now ask the user for ONE secondary factor (DOB, Aadhaar, or Pincode).", tool_call_id=tool_call_id)]
            })
        else:
            attempts = state.get("verification_attempts", 0) + 1
            return Command(update={
                "verification_attempts": attempts,
                "messages": [ToolMessage(content=f"Verification failed: Full name does not match our records. Attempt {attempts}/3.", tool_call_id=tool_call_id)]
            })

    # FULL VERIFICATION (NAME + SECONDARY)
    attempts = state.get("verification_attempts", 0) + 1
    
    if name_match and sec_match:
        return Command(
            update={
                "is_verified": True,
                "messages": [ToolMessage(content=f"Verification successful! Outstanding balance is {real_data.get('balance', 0):.2f}. Ask for payment amount and card details.", tool_call_id=tool_call_id)]
            }
        )
        
    reasons = []
    if validation_errors:
        reasons.extend(validation_errors)
    else:
        if not name_match: reasons.append("Full name does not match")
        if not sec_match: reasons.append("Secondary factor does not match")
        
    reason_str = ". ".join(reasons) + "."
        
    return Command(
        update={
            "verification_attempts": attempts,
            "messages": [ToolMessage(content=f"Verification failed: {reason_str} Attempt {attempts}/3.", tool_call_id=tool_call_id)]
        }
    )