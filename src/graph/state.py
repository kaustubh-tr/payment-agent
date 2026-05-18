from typing import Annotated, Optional, Sequence
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    
    # 1. System/API Data
    session_status: str # "ACTIVE", "SUCCESS", "FAILURE"
    account_details: Optional[dict]
    is_verified: bool
    verification_attempts: int
    payment_attempts: int
    
    # 2. User Provided Data (Populated by Extractor Tool)
    account_id: Optional[str]
    full_name: Optional[str]
    dob: Optional[str]
    aadhaar_last4: Optional[str]
    pincode: Optional[str]
    
    # 3. Payment Details (Now included in state)
    payment_amount: Optional[float]
    card_number: Optional[str]
    expiry_month: Optional[int]
    expiry_year: Optional[int]
    cvv: Optional[str]
