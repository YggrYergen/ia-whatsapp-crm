#!/usr/bin/env python3
# ================================================================================
# Phase 5A: Meta Webhook Simulation Runner
# ================================================================================
# CLI tool that executes simulation scenarios against the dev backend.
#
# Usage:
#   python -m scripts.simulation.runner                           # local
#   python -m scripts.simulation.runner --target https://URL      # deployed
#   python -m scripts.simulation.runner --scenario 1_happy_path   # single scenario
#
# OBSERVABILITY: All runner-level errors are reported to Sentry + Discord.
# ================================================================================

import asyncio
import argparse
import time
import sys
import os
import json
from datetime import datetime
from dataclasses import dataclass

import httpx

# Add Backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from scripts.simulation.scenarios import get_all_scenarios, SimScenario


# ── Result Tracking ────────────────────────────────────────────────────

@dataclass
class ScenarioResult:
    name: str
    passed: bool
    duration_ms: float
    http_status_codes: list[int]
    error: str | None = None
    notes: str = ""


# ── Console Output Helpers ─────────────────────────────────────────────

class Colors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    END = "\033[0m"


def _log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"  {Colors.CYAN}[{ts}]{Colors.END} {msg}")


def _header(msg: str):
    print(f"\n{Colors.BOLD}{Colors.HEADER}{'═'*70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.HEADER}  {msg}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.HEADER}{'═'*70}{Colors.END}")


def _scenario_header(idx: int, total: int, scenario: SimScenario):
    print(f"\n{Colors.BOLD}{Colors.BLUE}── Scenario {idx}/{total}: {scenario.name} ──{Colors.END}")
    print(f"  {Colors.CYAN}Description:{Colors.END} {scenario.description}")
    print(f"  {Colors.CYAN}Payloads:{Colors.END} {len(scenario.payloads)} | Mode: {scenario.mode}")
    if scenario.expect_tool_calls:
        print(f"  {Colors.CYAN}Expected tools:{Colors.END} {', '.join(scenario.expect_tool_calls)}")
    if scenario.notes:
        print(f"  {Colors.YELLOW}Notes:{Colors.END} {scenario.notes}")


def _result_line(result: ScenarioResult):
    if result.passed:
        icon = f"{Colors.GREEN}✅ PASS{Colors.END}"
    else:
        icon = f"{Colors.RED}❌ FAIL{Colors.END}"
    print(f"  {icon} {result.name} ({result.duration_ms:.0f}ms) — HTTP: {result.http_status_codes}")
    if result.error:
        print(f"       {Colors.RED}Error: {result.error}{Colors.END}")


# ── HTTP Execution ─────────────────────────────────────────────────────

async def _send_payload(client: httpx.AsyncClient, base_url: str, payload: dict) -> tuple[int, float]:
    """Send a single webhook payload. Returns (status_code, duration_ms)."""
    url = f"{base_url}/webhook"
    start = time.monotonic()
    try:
        response = await client.post(url, json=payload, timeout=30.0)
        duration = (time.monotonic() - start) * 1000
        return response.status_code, duration
    except httpx.ConnectError as e:
        duration = (time.monotonic() - start) * 1000
        _log(f"{Colors.RED}CONNECTION ERROR: {e}{Colors.END}")
        return -1, duration
    except httpx.TimeoutException as e:
        duration = (time.monotonic() - start) * 1000
        _log(f"{Colors.RED}TIMEOUT: {e}{Colors.END}")
        return -2, duration
    except Exception as e:
        duration = (time.monotonic() - start) * 1000
        _log(f"{Colors.RED}UNEXPECTED ERROR: {e}{Colors.END}")
        return -3, duration


async def _run_sequential(client: httpx.AsyncClient, base_url: str, payloads: list[dict], delay_ms: int) -> list[tuple[int, float]]:
    """Send payloads one by one with delay between them."""
    results = []
    for i, payload in enumerate(payloads):
        _log(f"Sending payload {i+1}/{len(payloads)}...")
        status, duration = await _send_payload(client, base_url, payload)
        _log(f"Response: HTTP {status} in {duration:.0f}ms")
        results.append((status, duration))
        if i < len(payloads) - 1:
            await asyncio.sleep(delay_ms / 1000)
    return results


async def _run_burst(client: httpx.AsyncClient, base_url: str, payloads: list[dict], delay_ms: int) -> list[tuple[int, float]]:
    """Send payloads rapidly with minimal delay (near-simultaneous)."""
    results = []
    for i, payload in enumerate(payloads):
        _log(f"Burst payload {i+1}/{len(payloads)}...")
        status, duration = await _send_payload(client, base_url, payload)
        _log(f"Response: HTTP {status} in {duration:.0f}ms")
        results.append((status, duration))
        if delay_ms > 0:
            await asyncio.sleep(delay_ms / 1000)
    return results


async def _run_concurrent(client: httpx.AsyncClient, base_url: str, payloads: list[dict]) -> list[tuple[int, float]]:
    """Send all payloads concurrently (asyncio.gather)."""
    _log(f"Firing {len(payloads)} payloads concurrently...")
    tasks = [_send_payload(client, base_url, p) for p in payloads]
    results = await asyncio.gather(*tasks)
    for i, (status, duration) in enumerate(results):
        _log(f"Concurrent #{i+1}: HTTP {status} in {duration:.0f}ms")
    return list(results)


# ── Scenario Executor ──────────────────────────────────────────────────

async def run_scenario(client: httpx.AsyncClient, base_url: str, scenario: SimScenario) -> ScenarioResult:
    """Execute a single scenario and return the result."""
    start = time.monotonic()
    
    try:
        if scenario.mode == "sequential":
            results = await _run_sequential(client, base_url, scenario.payloads, scenario.delay_between_ms)
        elif scenario.mode == "burst":
            results = await _run_burst(client, base_url, scenario.payloads, scenario.delay_between_ms)
        elif scenario.mode == "concurrent":
            results = await _run_concurrent(client, base_url, scenario.payloads)
        else:
            raise ValueError(f"Unknown mode: {scenario.mode}")
        
        duration = (time.monotonic() - start) * 1000
        status_codes = [r[0] for r in results]
        
        # Validate expected outcomes
        passed = True
        error_msgs = []
        
        if scenario.expect_http_200:
            non_200 = [s for s in status_codes if s != 200]
            if non_200:
                passed = False
                error_msgs.append(f"Expected all HTTP 200, got: {non_200}")
        
        # Connection errors are always failures
        connection_errors = [s for s in status_codes if s < 0]
        if connection_errors:
            passed = False
            error_msgs.append(f"Connection errors: {connection_errors}")
        
        return ScenarioResult(
            name=scenario.name,
            passed=passed,
            duration_ms=duration,
            http_status_codes=status_codes,
            error="; ".join(error_msgs) if error_msgs else None,
        )
    
    except Exception as e:
        duration = (time.monotonic() - start) * 1000
        return ScenarioResult(
            name=scenario.name,
            passed=False,
            duration_ms=duration,
            http_status_codes=[],
            error=str(e),
        )


# ── Report Generation ─────────────────────────────────────────────────

def generate_report(results: list[ScenarioResult], target: str, duration_total: float) -> str:
    """Generate a markdown summary report."""
    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if not r.passed)
    
    lines = [
        f"# Phase 5A Simulation Report",
        f"",
        f"- **Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- **Target:** `{target}`",
        f"- **Total Duration:** {duration_total:.0f}ms",
        f"- **Result:** {passed}/{len(results)} passed, {failed} failed",
        f"",
        f"## Scenarios",
        f"",
        f"| # | Scenario | Status | Duration | HTTP Codes | Notes |",
        f"|---|----------|--------|----------|------------|-------|",
    ]
    
    for r in results:
        status = "✅ PASS" if r.passed else "❌ FAIL"
        codes = ", ".join(str(c) for c in r.http_status_codes[:5])
        error_note = r.error or ""
        lines.append(f"| | {r.name} | {status} | {r.duration_ms:.0f}ms | {codes} | {error_note[:80]} |")
    
    lines.extend([
        "",
        "## Next Steps",
        "",
        "- [ ] Check Sentry dashboard for expected error events (scenario 6)",
        "- [ ] Check Discord for alert notifications (scenario 6)",
        "- [ ] Check dev frontend for simulated conversations",
        "- [ ] Run `cleanup.py` to remove simulation data from dev DB",
    ])
    
    return "\n".join(lines)


# ── Main Entry Point ──────────────────────────────────────────────────

async def main():
    parser = argparse.ArgumentParser(description="Phase 5A: Meta Webhook Simulation Runner")
    parser.add_argument("--target", default="http://localhost:8000", help="Backend URL to target")
    parser.add_argument("--scenario", default=None, help="Run only a specific scenario by name")
    parser.add_argument("--report", default=None, help="Path to save the markdown report")
    parser.add_argument("--wait-after", type=int, default=5, help="Seconds to wait after LLM scenarios for background tasks")
    args = parser.parse_args()
    
    _header(f"Phase 5A: Meta Webhook Simulation Suite")
    print(f"  Target: {args.target}")
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Load scenarios
    all_scenarios = get_all_scenarios()
    if args.scenario:
        all_scenarios = [s for s in all_scenarios if args.scenario in s.name]
        if not all_scenarios:
            print(f"{Colors.RED}No scenario found matching '{args.scenario}'{Colors.END}")
            sys.exit(1)
    
    print(f"  Scenarios: {len(all_scenarios)}")
    
    # Verify connectivity
    async with httpx.AsyncClient() as client:
        try:
            health = await client.get(f"{args.target}/", timeout=5.0)
            _log(f"Health check: HTTP {health.status_code}")
        except Exception as e:
            print(f"\n{Colors.RED}ERROR: Cannot connect to {args.target}: {e}{Colors.END}")
            print(f"{Colors.YELLOW}Make sure the backend server is running.{Colors.END}")
            sys.exit(1)
        
        # Execute scenarios
        results = []
        overall_start = time.monotonic()
        
        for idx, scenario in enumerate(all_scenarios, 1):
            _scenario_header(idx, len(all_scenarios), scenario)
            result = await run_scenario(client, args.target, scenario)
            _result_line(result)
            results.append(result)
            
            # Wait after LLM scenarios for background task processing
            if scenario.expect_llm_response and args.wait_after > 0:
                _log(f"Waiting {args.wait_after}s for background tasks to complete...")
                await asyncio.sleep(args.wait_after)
        
        overall_duration = (time.monotonic() - overall_start) * 1000
    
    # Summary
    _header("SIMULATION SUMMARY")
    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if not r.passed)
    
    for r in results:
        _result_line(r)
    
    print(f"\n  {Colors.BOLD}Total: {passed}/{len(results)} passed, {failed} failed ({overall_duration:.0f}ms){Colors.END}")
    
    if failed > 0:
        print(f"\n  {Colors.RED}⚠️  {failed} scenario(s) failed. Review errors above.{Colors.END}")
    else:
        print(f"\n  {Colors.GREEN}🎉 All scenarios passed!{Colors.END}")
    
    # Generate report
    report = generate_report(results, args.target, overall_duration)
    
    if args.report:
        report_path = args.report
    else:
        report_path = os.path.join(os.path.dirname(__file__), "..", "..", "simulation_report.md")
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    _log(f"Report saved to: {report_path}")
    
    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    asyncio.run(main())
