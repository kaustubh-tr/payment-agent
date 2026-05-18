"""
Automated evaluation runner for the Payment Collection AI Agent.

Runs scripted conversation scenarios through agent.next() and scores each step.
Produces a detailed pass/fail table per scenario.

Run with:
    python evaluate.py
"""

import sys
import time
from dataclasses import dataclass, field
from rich.console import Console
from rich.table import Table
from rich.rule import Rule
from rich import print as rprint

from agent import Agent

console = Console()

@dataclass
class Turn:
    user_input: str
    expect_contains: list[str] = field(default_factory=list)
    expect_not_contains: list[str] = field(default_factory=list)
    label: str = ""


@dataclass
class Scenario:
    name: str
    turns: list[Turn]
    description: str = ""


SCENARIOS: list[Scenario] = [
    # 1. Happy path — full payment
    Scenario(
        name="Happy Path — Full Payment (ACC1001, DOB)",
        description="Successful end-to-end payment using DOB verification.",
        turns=[
            Turn("hi", ["account id", "account"], label="Greeting"),
            Turn("my account is ACC1001", ["full name", "name"], label="Account lookup"),
            Turn("Nithin Jain", ["date of birth", "aadhaar", "pincode"], label="Name collected"),
            Turn("DOB is 1990-05-14", ["1250", "balance", "pay"], label="Verified + balance shown"),
            Turn("I want to pay 500", ["card", "card number"], label="Amount collected"),
            Turn(
                "card number 4532015112830366 CVV 123 expires 12/2027 name Nithin Jain",
                ["successful", "transaction"],
                label="Payment processed",
            ),
        ],
    ),

    # 2. Happy path — Aadhaar verification + pay in full
    Scenario(
        name="Happy Path — Aadhaar + Full Amount (ACC1002)",
        description="Verify with Aadhaar last 4, pay full balance.",
        turns=[
            Turn("hello", ["account id"], label="Greeting"),
            Turn("ACC1002", ["full name", "name"], label="Account lookup"),
            Turn("Rajarajeswari Balasubramaniam", ["date of birth", "aadhaar", "pincode"], label="Name collected"),
            Turn("my aadhaar last 4 is 9876", ["540", "balance"], label="Verified"),
            Turn("just clear the full amount", ["card", "card number"], label="Full amount"),
            Turn(
                "4532015112830366 cvv 123 expires 12/2027 cardholder Rajarajeswari Balasubramaniam",
                ["successful", "transaction"],
                label="Payment processed",
            ),
        ],
    ),

    # 3. Verification failure — exhausts retries
    Scenario(
        name="Verification Failure — Exhausts Retries",
        description="User provides wrong identity details 3 times.",
        turns=[
            Turn("hi", ["account id"], label="Greeting"),
            Turn("ACC1001", ["full name"], label="Lookup"),
            Turn("Wrong Name", ["name", "match"], label="Fail 1 — wrong name"),
            Turn("1990-05-14", ["name", "match"], label="Fail 1 — wrong secondary"),
            Turn("Still Wrong", ["closed", "attempt"], label="Fail 2 — wrong name"),
            Turn("1990-05-14", ["closed"], label="Fail 2 — wrong secondary"),
            Turn("Bad Name Again", ["closed"], label="Fail 3 — wrong name"),
            Turn("1990-05-14", ["closed"], label="Locked out"),
        ],
    ),

    # 4. Payment failure — invalid card
    Scenario(
        name="Payment Failure — Invalid Card Number",
        description="User provides a card number that fails Luhn check.",
        turns=[
            Turn("hi", ["account id"], label="Greeting"),
            Turn("ACC1001", ["full name"], label="Lookup"),
            Turn("Nithin Jain", ["date of birth", "aadhaar", "pincode"], label="Name"),
            Turn("pincode 400001", ["1250", "balance"], label="Verified"),
            Turn("500", ["card"], label="Amount"),
            Turn(
                "card 1234567890123456 cvv 123 expires 12/2027 name Nithin Jain",
                ["invalid", "card number"],
                label="Invalid card rejected locally",
            ),
        ],
    ),

    # 5. Zero balance account
    Scenario(
        name="Edge Case — Zero Balance (ACC1003)",
        description="Account with no outstanding balance closes cleanly.",
        turns=[
            Turn("hi", ["account id"], label="Greeting"),
            Turn("ACC1003", ["full name"], label="Lookup"),
            Turn("Priya Agarwal", ["date of birth", "aadhaar", "pincode"], label="Name"),
            Turn("DOB 1992-08-10", ["0.00"], label="Zero balance"),
        ],
    ),

    # 6. Leap year DOB (ACC1004)
    Scenario(
        name="Edge Case — Leap Year DOB (ACC1004)",
        description="Rahul Mehta's DOB is 1988-02-29 — valid leap year date.",
        turns=[
            Turn("hi", ["account id"], label="Greeting"),
            Turn("ACC1004", ["full name"], label="Lookup"),
            Turn("Rahul Mehta", ["date of birth", "aadhaar", "pincode"], label="Name"),
            Turn("my DOB is February 29 1988", ["3200", "balance"], label="Leap year DOB verified"),
            Turn("pay 1000", ["card"], label="Amount"),
            Turn(
                "card 4532015112830366 cvv 123 expires 12/2027 cardholder Rahul Mehta",
                ["successful", "transaction"],
                label="Payment processed",
            ),
        ],
    ),

    # 7. Messy / free-form input handling
    Scenario(
        name="Edge Case — Messy Input Throughout",
        description="Every input is in a non-standard, conversational format.",
        turns=[
            Turn("hey there I need help", ["account id"], label="Greeting"),
            Turn("yeah my account number is ACC 1001 I think", ["full name"], label="Messy account ID"),
            Turn("it's Nithin, Nithin Jain", ["date of birth", "aadhaar", "pincode"], label="Messy name"),
            Turn("last four of my Aadhaar is 4321", ["1250", "balance"], label="Messy Aadhaar"),
            Turn("I want to pay a thousand rupees", ["card"], label="Messy amount"),
            Turn(
                "the card number is 4532 0151 1283 0366 and CVV is one two three expires December 2027 name Nithin Jain",
                ["successful", "transaction"],
                label="Messy card details",
            ),
        ],
    ),

    # 8. Card details across multiple turns
    Scenario(
        name="Multi-Turn Card Collection",
        description="User provides card details piecemeal across 3 turns.",
        turns=[
            Turn("hi", ["account id"], label="Greeting"),
            Turn("ACC1001", ["full name"], label="Lookup"),
            Turn("Nithin Jain", ["date of birth", "aadhaar", "pincode"], label="Name"),
            Turn("dob 14-05-1990", ["balance"], label="Verified"),
            Turn("500", ["card"], label="Amount"),
            Turn("card number is 4532015112830366", ["cvv", "expiry", "name"], label="Card only"),
            Turn("cvv 123", ["expiry", "name"], label="CVV"),
            Turn("expires 12/2027 cardholder Nithin Jain", ["successful", "transaction"], label="Remaining → payment"),
        ],
    ),
]


# Evaluation engine

def evaluate_turn(response: str, turn: Turn) -> tuple[bool, list[str]]:
    """Returns (passed, list_of_failures)."""
    failures = []
    lower = response.lower()

    for kw in turn.expect_contains:
        if kw.lower() not in lower:
            failures.append(f"Missing: '{kw}'")

    for kw in turn.expect_not_contains:
        if kw.lower() in lower:
            failures.append(f"Should NOT contain: '{kw}'")

    return len(failures) == 0, failures


def run_scenario(scenario: Scenario) -> dict:
    """Run one scenario and return results."""
    agent = Agent()
    results = []
    total_turns = len(scenario.turns)
    passed_turns = 0

    greeting_result = agent.next("__init__")

    agent = Agent()

    for i, turn in enumerate(scenario.turns):
        try:
            if i == 0:
                # First call fires the greeting; we expect greeting-like response
                result = agent.next(turn.user_input)
            else:
                result = agent.next(turn.user_input)

            response = result["message"]
            passed, failures = evaluate_turn(response, turn)
            if passed:
                passed_turns += 1

            results.append({
                "turn": i + 1,
                "label": turn.label,
                "user_input": turn.user_input[:60] + ("..." if len(turn.user_input) > 60 else ""),
                "response_snippet": response[:80] + ("..." if len(response) > 80 else ""),
                "passed": passed,
                "failures": failures,
            })
        except Exception as e:
            results.append({
                "turn": i + 1,
                "label": turn.label,
                "user_input": turn.user_input[:60],
                "response_snippet": f"ERROR: {e}",
                "passed": False,
                "failures": [str(e)],
            })

    return {
        "scenario": scenario.name,
        "passed_turns": passed_turns,
        "total_turns": total_turns,
        "score": f"{passed_turns}/{total_turns}",
        "pass_rate": passed_turns / total_turns if total_turns else 0,
        "turns": results,
    }


# Reporter

def print_scenario_result(result: dict):
    passed = result["passed_turns"]
    total = result["total_turns"]
    color = "green" if passed == total else ("yellow" if passed >= total * 0.7 else "red")

    console.print(Rule(f"[bold]{result['scenario']}[/bold]"))
    console.print(f"Score: [{color}]{result['score']}[/{color}] turns passed")
    console.print()

    table = Table(show_header=True, header_style="bold cyan", expand=True)
    table.add_column("#", width=3)
    table.add_column("Label", width=22)
    table.add_column("User Input", width=35)
    table.add_column("Response Snippet", width=45)
    table.add_column("Pass", width=5)

    for t in result["turns"]:
        status = "[green]✓[/green]" if t["passed"] else "[red]✗[/red]"
        table.add_row(
            str(t["turn"]),
            t["label"],
            t["user_input"],
            t["response_snippet"],
            status,
        )
        if not t["passed"]:
            for f in t["failures"]:
                table.add_row("", "", "", f"  [red]↳ {f}[/red]", "")

    console.print(table)
    console.print()


def print_summary(all_results: list[dict]):
    console.print(Rule("[bold]EVALUATION SUMMARY[/bold]"))

    table = Table(show_header=True, header_style="bold white", expand=True)
    table.add_column("Scenario", width=45)
    table.add_column("Score", width=8)
    table.add_column("Pass Rate", width=10)
    table.add_column("Status", width=8)

    total_turns_all = 0
    passed_turns_all = 0

    for r in all_results:
        pct = r["pass_rate"] * 100
        color = "green" if pct == 100 else ("yellow" if pct >= 70 else "red")
        status = "✅ PASS" if pct == 100 else ("⚠️  PART" if pct >= 70 else "❌ FAIL")
        table.add_row(
            r["scenario"],
            r["score"],
            f"[{color}]{pct:.0f}%[/{color}]",
            status,
        )
        total_turns_all += r["total_turns"]
        passed_turns_all += r["passed_turns"]

    console.print(table)
    overall = (passed_turns_all / total_turns_all * 100) if total_turns_all else 0
    console.print()
    console.print(
        f"[bold]Overall:[/bold] {passed_turns_all}/{total_turns_all} turns passed "
        f"([bold {'green' if overall >= 80 else 'red'}]{overall:.1f}%[/bold {'green' if overall >= 80 else 'red'}])"
    )


def main():
    console.print()
    console.print("[bold cyan]Payment Agent — Automated Evaluation[/bold cyan]")
    console.print(f"Running {len(SCENARIOS)} scenarios...\n")

    all_results = []
    start = time.time()

    for scenario in SCENARIOS:
        console.print(f"[dim]Running: {scenario.name}...[/dim]")
        try:
            result = run_scenario(scenario)
        except Exception as e:
            console.print(f"[red]Scenario crashed: {e}[/red]")
            result = {
                "scenario": scenario.name,
                "passed_turns": 0,
                "total_turns": len(scenario.turns),
                "score": f"0/{len(scenario.turns)}",
                "pass_rate": 0,
                "turns": [],
            }
        all_results.append(result)

    elapsed = time.time() - start
    console.print()

    for result in all_results:
        print_scenario_result(result)

    print_summary(all_results)
    console.print(f"\n[dim]Total time: {elapsed:.1f}s[/dim]")


if __name__ == "__main__":
    main()
