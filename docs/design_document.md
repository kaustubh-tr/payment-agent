# System Design Document: Payment Collection Agent

## Authorship and AI Assistance Disclosure

The complete architecture, workflow, design decisions, and tradeoff analysis described in this document are my own work. AI agent assistance was used for code implementation support. Documentation formatting and automation scripts/tasks, including evaluator-style scripting, were written with agent assistance.

## 1. Architecture Overview

The payment collection agent orchestrates a natural language conversation to handle account lookup, identity verification, and payment processing. The architecture relies on an event-driven state machine using **LangGraph**, providing a hybrid approach that marries the adaptability of Large Language Models (LLMs) with the strict reliability of deterministic code.

### 1.1 Structural Layout

The system is constructed as a cyclic directed graph with the following primary vertices:

- **LLM Node (`agent_node`)**: Operates on OpenAI's configured model, defaulting to `gpt-5.4-mini`. It takes in the conversation history and a carefully tuned system prompt. Its job is to parse intent, formulate user-friendly responses, and map natural language variables to strongly-typed tool calls.
- **Tool Node (`tool_node`)**: A deterministic execution environment. When the LLM decides to execute an action, this node binds the LLM's JSON outputs to pure Python functions. It executes four primary tools: `save_extracted_info`, `lookup_account_tool`, `verify_identity_tool`, and `process_payment_tool`.
- **Central State (`AgentState`)**: The memory of the graph. Implemented via Python's `TypedDict`, this holds the immutable conversation history (`messages`), operational state (`session_status`, `is_verified`, retry counters), and structured properties provided by the user.

### 1.2 Data Flow

1.  User input hits the `Agent.next()` adapter.
2.  Input is routed to the `agent_node` acting as an orchestrator.
3.  If the input contains factual data (e.g. "My name is John"), the LLM binds to `save_extracted_info`, transitioning to `tool_node` to update `AgentState`.
4.  If criteria are met, the LLM calls business tools (e.g., `lookup_account_tool`).
5.  Control bounces between `agent_node` and `tool_node` until a terminal text response is generated, which is surfaced back to the user.

---

## 2. Key Decisions and Rationale

### 2.1 Hybrid Verification Strategy (LLM vs. Rule-Based)

- **Decision:** We restricted the LLM from making API calls directly or subjectively deciding if a user's verification matches the database.
- **Why:** LLMs can be prone to hallucination, sycophancy (agreeing with the user if they insist they are the account holder), and prompt injection. By limiting the LLM to merely _extracting_ strings and letting a strict Python module (`src/validators/identity.py`) perform equality checks against the API data, we guarantee the security of the verification process.
- **Tradeoff:** Strict validation is less forgiving. If the LLM extracts "Feb 29 1988" instead of "1988-02-29", the pure equality check will fail, frustrating the user. We mitigated this by introducing procedural extraction overrides within `agent_wrapper.py` for common date patterns.

### 2.2 Pre-flight Validation

- **Decision:** Card numbers, expiry dates, and transaction amounts are validated logically _before_ any API call is made to the payment processor.
- **Why:** Reduces unnecessary network traffic and speeds up the response loop. We implemented the Luhn algorithm locally alongside pure-Python datetime validations to catch obvious user errors immediately.
- **Tradeoff:** We have to maintain business logic code instead of solely relying on 4xx errors from the payment API.

### 2.3 Explicit State Extraction via Tool

- **Decision:** We force the LLM to call `save_extracted_info` to persist data onto `AgentState`, rather than just keeping the extracted entity in the conversational context window and passing it linearly.
- **Why:** It creates a deterministic, highly auditable execution trace. If payment fails, we can see exactly what `card_number` is saved in the state object at execution time, dramatically improving debuggability.
- **Tradeoff:** Increased LLM token cost and latency per interaction loop as the system must make multiple "hops" to extract, update state, and then formulate the subsequent API call.

---

## 3. Failure Handling & Context Management

### 3.1 Strict Retry Management

The system explicitly tracks `verification_attempts` and `payment_attempts` directly on the `AgentState`. If either hits the upper bound (3 attempts), the system state locks to `session_status = FAILURE`.

- **Enforcement:** The check is made at the adapter layer (`agent_wrapper.py`). Once locked, the graph is bypassed completely and returns a generic terminal statement. This makes the system immune to continued prompt injection or brute-force guessing attacks.

### 3.2 Error Surfacing

We wrap external HTTP requests via `httpx` using `tenacity` for resilience against transient networking blips (e.g., socket drops, temporary 5xxs). If the API fails with a 4xx error (e.g., `invalid_cvv`), the error code is mapped to a human-readable dictionary, passed to the LLM, and correctly relayed to the user.

---

## 4. Evaluation and Design Criteria Fulfillment

- **System Thinking:** The system uses clear pre-conditions (an account must be found before verification; verification must succeed before payment).
- **Context Handling:** The memory is tracked transparently by LangGraph's checkpointing system, preventing the LLM from losing track of what happened 5 turns ago.
- **Evaluation Design:** `test_agent.py` simulates real integration flows end-to-end, asserting that specific state transitions (like exhausting retries causing a lock-out) actually happen in practice.

---

## Tradeoffs

- **Extraction Brittleness vs. Fluidity:** We rely on the LLM to format data correctly before passing it to `save_extracted_info` (e.g., converting "Feb 29 1988" to "YYYY-MM-DD"). While this keeps the codebase clean of complex regex parsers, it introduces a reliance on the LLM's instruction-following capabilities.
- **Latency:** The "extract → tool call → re-prompt LLM" cycle means multiple network hops to the LLM provider for a single user turn.
- **Stateless Validators:** Validations (like Luhn checks) are done inside the tools rather than as a continuous active listener.

---

## 5. Potential Future Improvements (What to improve with more time)

1. **Secure UI Data Collection (Bypassing LLM for PII/PCI Data)**
   Currently, sensitive information like card numbers, CVVs, and account details are typed directly into the chat, exposing them to the LLM provider. In a production environment, when the agent requires sensitive info, it should trigger a secure pop-up UI/form on the frontend. The user enters data there, which is sent directly to the backend APIs/verification tools via tokenization—keeping the LLM entirely blind to the raw sensitive data.
2. **Asynchronous Architecture**
   The system currently relies on blocking, synchronous code (e.g., `httpx.Client`). To scale to multiple concurrent conversational sessions, the core agent graph and external API integrations need to be refactored to an async model (`async def`, `httpx.AsyncClient`).

3. **Streaming Responses for Better UX**
   There is currently no streaming; the user waits for the entire LLM-Tool-LLM cycle to finish before seeing a response. Implementing streaming via Server-Sent Events (SSE) would allow the agent's text to appear chunk-by-chunk in real-time, drastically reducing the perceived latency and vastly improving the user experience.

4. **Persistent Database for State & Workflow**
   Relying on an in-memory `MemorySaver` checkpointer means all session states disappear on server restart. We need a persistent database (like PostgreSQL or Redis via `PostgresSaver`) to store the `AgentState`. This allows the application to reliably track exactly which workflow stage a transaction is in across distributed worker nodes.

5. **Explicit Thread/Conversation Management**
   Building on the DB persistence, the system should strictly enforce `thread_id` (conversation ID) management at the API/websocket level. Every frontend interaction must pass this ID, ensuring the agent retrieves the correct historical checkpoint and context safely from the persistent database.

6. **Scalability and Human Handoff (Based on the Above)**
   Once the system is Async, securely decoupled via UI bounds, and strictly maintaining conversational threads in a DB, further horizontal scaling becomes trivial. Additionally, we could implement a seamless "Human Support Handoff"—if the workflow stage gets stuck (e.g., exhausting verification attempts), the exact unified thread state can be instantly surfaced to a human agent dashboard without losing context.
