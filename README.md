# Payment Collection AI Agent

A conversational AI agent for an end-to-end payment collection flow. The agent chats with a user, extracts messy natural-language inputs, looks up the account, verifies identity with strict rules, collects payment details, processes the payment, and closes the conversation with a clear outcome.

The implementation combines a LangGraph workflow, OpenAI structured extraction, deterministic Python validators, and the provided payment API.

## Overall Idea

The agent is designed as a controlled payment workflow, not an open-ended chatbot:

1. Greet the user and ask for an account ID.
2. Look up the account through the payment API.
3. Collect the user's exact full name.
4. Collect one secondary verification field: DOB, Aadhaar last 4, or pincode.
5. Verify identity with deterministic equality checks.
6. Show the outstanding balance only after verification.
7. Collect amount and card details.
8. Validate payment inputs locally where possible.
9. Process the payment through the API.
10. Return success, failure reason, or retry guidance.

The LLM is used for natural-language extraction and response generation. Security-sensitive decisions, identity matching, retry limits, card validation, and amount validation are handled by deterministic code.

## Repository Layout

```text
.
├── README.md                       # Setup, run instructions, and project overview
├── agent.py                        # Root Agent export
├── cli.py                          # Interactive terminal chat
├── evaluate.py                     # Automated scenario evaluator
├── requirements.txt                # Python dependencies
├── sample_conversation.ipynb       # Example conversation walkthrough
├── test.ipynb                      # Notebook scratch/test runner
├── docs/
│   ├── design_document.md          # Architecture, workflow, tradeoffs, improvements
│   └── problem_statement.md        # Original assignment prompt
├── src/
│   ├── config.py                   # Environment configuration
│   ├── agent/
│   │   └── agent_wrapper.py        # Agent wrapper and session handling
│   ├── api/
│   │   └── client.py               # Payment API client
│   ├── graph/
│   │   ├── agent_graph.py          # LangGraph construction
│   │   ├── prompts.py              # Agent prompt instructions
│   │   └── state.py                # Graph state schema
│   ├── tools/
│   │   ├── extractor_tool.py       # Structured data extraction tool
│   │   ├── lookup_tool.py          # Account lookup tool
│   │   ├── payment_tool.py         # Payment processing tool
│   │   └── verify_tool.py          # Identity verification tool
│   └── validators/
│       ├── card.py                 # Card, CVV, expiry, and amount validators
│       └── identity.py             # DOB, Aadhaar, and pincode validators
└── tests/
    ├── test_agent.py               # Agent flow tests
    └── test_validators.py          # Validator unit tests
```

## Setup

### 1. Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

On Windows:

```bash
.venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
cp .env.example .env
```

Then edit `.env`:

```bash
OPENAI_API_KEY=your_openai_api_key
PAYMENT_API_BASE_URL=https://se-payment-verification-api...
OPENAI_MODEL_NAME=gpt-5.4-mini
MAX_VERIFICATION_ATTEMPTS=3
MAX_PAYMENT_ATTEMPTS=3
```

`OPENAI_API_KEY` and `PAYMENT_API_BASE_URL` are required for the full agent flow.

## Run

### Interactive CLI

```bash
python cli.py
```

Start chatting with the agent. Use `quit`, `exit`, `bye`, or `q` to end the session.

### Automated Evaluation

```bash
python evaluate.py
```

This runs scripted conversations covering happy paths, verification failures, invalid cards, zero balance, leap-year DOB handling, messy inputs, and multi-turn card collection.

### Tests

Run validator tests:

```bash
python -m pytest tests/test_validators.py -v
```

Run the full test suite:

```bash
python -m pytest tests/ -v
```

The full suite requires the environment variables above because integration-style agent tests may call the LLM and payment API.

## Programmatic Usage

```python
from agent import Agent

agent = Agent()

print(agent.next("hi")["message"])
print(agent.next("my account id is ACC1001")["message"])
print(agent.next("Nithin Jain")["message"])
print(agent.next("DOB is 1990-05-14")["message"])
print(agent.next("I want to pay 500")["message"])
print(agent.next("card 4532015112830366 cvv 123 expires 12/2027 name Nithin Jain")["message"])
```

## Test Accounts

| Account ID | Full Name | DOB | Aadhaar Last 4 | Pincode | Balance |
| --- | --- | --- | --- | --- | --- |
| ACC1001 | Nithin Jain | 1990-05-14 | 4321 | 400001 | Rs. 1,250.75 |
| ACC1002 | Rajarajeswari Balasubramaniam | 1985-11-23 | 9876 | 400002 | Rs. 540.00 |
| ACC1003 | Priya Agarwal | 1992-08-10 | 2468 | 400003 | Rs. 0.00 |
| ACC1004 | Rahul Mehta | 1988-02-29 | 1357 | 400004 | Rs. 3,200.50 |

`ACC1004` is included to verify leap-year date handling. `1988-02-29` should pass; `1988-02-28` should not.

## Verification Rules

- Full name matching is exact and case-sensitive.
- At least one secondary field must match exactly.
- Partial inputs do not count as failed verification attempts.
- The session locks after the configured retry limit.
- DOB, Aadhaar, pincode, and card data are not echoed back to the user.

## Documentation

- [Design document](docs/design_document.md): architecture, workflow, key decisions, tradeoffs, and future improvements.
- [Problem statement](docs/problem_statement.md): original assignment requirements and API reference.

## AI Assistance Disclosure

The complete architecture, workflow design, design decisions, and tradeoff analysis are my own work. AI agent assistance was used for code implementation support. Documentation formatting and automation scripts/tasks, including evaluator-style scripting, were written with agent assistance.
