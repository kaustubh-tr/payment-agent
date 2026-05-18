from typing import Annotated
from langchain_core.tools import tool
from langchain_core.messages import ToolMessage
from langchain_core.tools.base import InjectedToolCallId
from langgraph.prebuilt import InjectedState
from langgraph.types import Command
from src.graph.state import AgentState
from src.api.client import lookup_account, get_lookup_error_message

@tool
def lookup_account_tool(
    state: Annotated[AgentState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """
    Look up the account.
    Call this after you have saved the account_id into the state.
    """
    account_id = state.get("account_id")
    if not account_id:
        return Command(
            update={
                "messages": [ToolMessage(content="No account_id found in state. Please save it first.", tool_call_id=tool_call_id)]
            }
        )
        
    result = lookup_account(account_id)
    if "error_code" in result:
        msg = get_lookup_error_message(result["error_code"])
        return Command(
            update={
                "messages": [ToolMessage(content=msg, tool_call_id=tool_call_id)]
            }
        )
    
    return Command(
        update={
            "account_details": result,
            "messages": [ToolMessage(content="Account found. Please verify the user's identity.", tool_call_id=tool_call_id)]
        }
    )
