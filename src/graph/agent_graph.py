from typing import Literal

from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode

from src.graph.state import AgentState
from src.graph.prompts import SYSTEM_PROMPT
from src.config import MAX_VERIFICATION_ATTEMPTS, MAX_PAYMENT_ATTEMPTS, OPENAI_MODEL_NAME

from src.tools.extractor_tool import save_extracted_info
from src.tools.lookup_tool import lookup_account_tool
from src.tools.verify_tool import verify_identity_tool
from src.tools.payment_tool import process_payment_tool


def build_graph():
    llm = ChatOpenAI(model=OPENAI_MODEL_NAME, temperature=0)
    tools = [save_extracted_info, lookup_account_tool, verify_identity_tool, process_payment_tool]
    llm_with_tools = llm.bind_tools(tools)

    def should_continue(state: AgentState) -> Literal["tool_node", END]:
        messages = state["messages"]
        last_message = messages[-1]
        
        if last_message.tool_calls:
            return "tool_node"
            
        return END

    def agent_node(state: AgentState):
        sys_msg = SystemMessage(content=SYSTEM_PROMPT.format(
            is_verified=state.get("is_verified", False),
            verification_attempts=state.get("verification_attempts", 0),
            max_v=MAX_VERIFICATION_ATTEMPTS,
            payment_attempts=state.get("payment_attempts", 0),
            max_p=MAX_PAYMENT_ATTEMPTS
        ))
        
        messages = [sys_msg] + list(state["messages"])
        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}

    workflow = StateGraph(AgentState)
    
    workflow.add_node("agent_node", agent_node)
    workflow.add_node("tool_node", ToolNode(tools))
    
    workflow.add_edge(START, "agent_node")
    workflow.add_conditional_edges("agent_node", should_continue, ["tool_node", END])
    workflow.add_edge("tool_node", "agent_node")
    
    memory = MemorySaver()
    graph = workflow.compile(checkpointer=memory)
    
    return graph, memory
