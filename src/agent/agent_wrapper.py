from langchain_core.messages import HumanMessage
from src.graph.agent_graph import build_graph


class Agent:
    def __init__(self, thread_id: str = "user123"):
        self._graph, self._checkpointer = build_graph()
        self._thread_id = thread_id
        self._config = {"configurable": {"thread_id": self._thread_id}}
        
        # Initialize state with default values
        self._graph.update_state(
            self._config,
            {
                "messages": [],
                "session_status": "ACTIVE",
                "account_details": None,
                "is_verified": False,
                "verification_attempts": 0,
                "payment_attempts": 0,
                "account_id": None,
                "full_name": None,
                "dob": None,
                "aadhaar_last4": None,
                "pincode": None,
                "payment_amount": None,
                "card_number": None,
                "expiry_month": None,
                "expiry_year": None,
                "cvv": None
            }
        )
        self._initialized = False

    def next(self, user_input: str) -> dict:
        """
        Process one turn of the conversation.
        """
        if not self._initialized:
            self._initialized = True
            result_state = self._graph.invoke(
                {"messages": [HumanMessage(content="Hello")]}, 
                config=self._config
            )
        else:
            current_state = self._graph.get_state(self._config).values
            session_status = current_state.get("session_status", "ACTIVE")
            v_attempts = current_state.get("verification_attempts", 0)
            p_attempts = current_state.get("payment_attempts", 0)
            
            if session_status != "ACTIVE" or v_attempts >= 3 or p_attempts >= 3:
                return {"message": "This session has been closed. If you need further assistance, please start a new session."}
                
            result_state = self._graph.invoke(
                {"messages": [HumanMessage(content=user_input)]}, 
                config=self._config
            )
            
        messages = result_state["messages"]
        final_message = messages[-1].content
        
        return {"message": final_message}

    def get_state(self) -> dict:
        """
        Returns the current state of the agent.
        """
        if not self._initialized:
            return {}
        return self._graph.get_state(self._config).values
