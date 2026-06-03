
import os
import json
import time
import uuid
import subprocess
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Tuple

import requests
from flask import Flask, request, jsonify, render_template_string
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

MPP_DOCS_LINKS = {
    "mpp_site": "https://mpp.dev/",
    "stripe_mpp": "https://docs.stripe.com/payments/machine/mpp",
    "tempo_docs": "https://docs.tempo.xyz/guide/machine-payments",
    "parallel_mpp": "https://docs.parallel.ai/integrations/agentic-payments",
}

BUDGET = float(os.getenv("DEMO_BUDGET_USD", "20.00"))

@dataclass
class ProviderOption:
    id: str
    name: str
    kind: str
    task: str
    price_usd: float
    latency_sec: float
    quality: int
    reliability: float
    real_provider: bool
    notes: str

CATALOG = [
    ProviderOption(
        id="parallel_mpp_search",
        name="Parallel MPP Search",
        kind="research",
        task="paid market and technical research",
        price_usd=0.25,
        latency_sec=4,
        quality=8,
        reliability=0.96,
        real_provider=True,
        notes="Real MPP-native research if ENABLE_PARALLEL_MPP=1 and mppx is configured.",
    ),
    ProviderOption(
        id="exa_search",
        name="Exa Search",
        kind="research",
        task="agentic web search",
        price_usd=0.12,
        latency_sec=3,
        quality=8,
        reliability=0.95,
        real_provider=True,
        notes="Real API if EXA_API_KEY is set; otherwise simulated.",
    ),
    ProviderOption(
        id="tavily_search",
        name="Tavily Search",
        kind="research",
        task="web search and source discovery",
        price_usd=0.10,
        latency_sec=3,
        quality=7,
        reliability=0.94,
        real_provider=True,
        notes="Real API if TAVILY_API_KEY is set; otherwise simulated.",
    ),
    ProviderOption(
        id="together_cheap",
        name="Together AI",
        kind="inference",
        task="cheap centralized inference baseline",
        price_usd=0.60,
        latency_sec=8,
        quality=7,
        reliability=0.97,
        real_provider=True,
        notes="Real API if TOGETHER_API_KEY is set; otherwise simulated.",
    ),
    ProviderOption(
        id="fireworks_fast",
        name="Fireworks AI",
        kind="inference",
        task="fast centralized inference baseline",
        price_usd=0.75,
        latency_sec=6,
        quality=7,
        reliability=0.97,
        real_provider=True,
        notes="Real API if FIREWORKS_API_KEY is set; otherwise simulated.",
    ),
    ProviderOption(
        id="vast_gpu_quote",
        name="Vast.ai GPU Marketplace",
        kind="gpu_market",
        task="rented GPU marketplace quotes",
        price_usd=0.00,
        latency_sec=2,
        quality=8,
        reliability=0.91,
        real_provider=True,
        notes="Real Vast marketplace quotes if VAST_API_KEY is set; no GPU is rented by default.",
    ),
    ProviderOption(
        id="runpod_job",
        name="RunPod Serverless",
        kind="serverless_gpu",
        task="serverless GPU batch benchmark",
        price_usd=1.40,
        latency_sec=80,
        quality=8,
        reliability=0.95,
        real_provider=True,
        notes="Real job if RUNPOD_API_KEY and RUNPOD_ENDPOINT_ID are set; otherwise simulated.",
    ),
    ProviderOption(
        id="decentralized_compute_probe",
        name="Decentralized Compute Probe",
        kind="decentralized",
        task="decentralized compute reliability probe",
        price_usd=0.80,
        latency_sec=45,
        quality=6,
        reliability=0.82,
        real_provider=False,
        notes="Simulated decentralized compute probe; placeholder for Akash, io.net, Gensyn, Bittensor-style routes.",
    ),
    ProviderOption(
        id="strong_synthesis",
        name="Strong Synthesis Model",
        kind="synthesis",
        task="final route selection and economic synthesis",
        price_usd=0.90,
        latency_sec=7,
        quality=9,
        reliability=0.98,
        real_provider=False,
        notes="Simulated premium synthesis step.",
    ),
]

def make_402_challenge(option: ProviderOption) -> Dict[str, Any]:
    challenge_id = "chal_" + uuid.uuid4().hex[:12]
    return {
        "status": 402,
        "title": "Payment Required",
        "why_this_happened": "The agent requested a paid resource. The provider did not return the resource yet. It returned machine-readable payment terms first.",
        "challenge_id": challenge_id,
        "http_header_example": (
            f'WWW-Authenticate: Payment id="{challenge_id}", intent="charge", '
            f'amount="{option.price_usd:.2f}", currency="USD", provider="{option.name}"'
        ),
        "payment": {
            "amount_usd": option.price_usd,
            "currency": "USD",
            "accepted_rails": ["tempo-usdc", "visa-mpp-card", "stripe"],
            "resource": option.task,
            "provider": option.name,
            "estimated_latency_sec": option.latency_sec,
            "quality_score": option.quality,
            "reliability": option.reliability,
        },
    }

def authorize_payment(option: ProviderOption, budget_remaining: float, reason: str) -> Tuple[bool, Dict[str, Any]]:
    if option.price_usd <= budget_remaining:
        rail = "tempo-usdc" if option.kind in ["gpu_market", "serverless_gpu", "decentralized", "research"] else "visa-mpp-card"
        return True, {
            "step": "Agent payment decision",
            "approved": True,
            "credential": "pay_" + uuid.uuid4().hex,
            "reason": reason,
            "amount_usd": option.price_usd,
            "selected_rail": rail,
            "what_mpp_adds": "The rail funds the payment; MPP standardizes the quote, decision, authorization, retry, and receipt flow.",
        }
    return False, {
        "step": "Agent payment decision",
        "approved": False,
        "reason": f"Rejected: price ${option.price_usd:.2f} exceeds remaining budget ${budget_remaining:.2f}.",
        "what_mpp_adds": "Even rejected purchases are legible: the agent saw a machine-readable price and made a policy decision.",
    }

def receipt_for(option: ProviderOption, credential: str) -> Dict[str, Any]:
    return {
        "receipt_id": "rcpt_" + uuid.uuid4().hex[:12],
        "provider": option.name,
        "resource": option.task,
        "amount_usd": option.price_usd,
        "credential_tail": credential[-8:],
        "timestamp": int(time.time()),
        "status": "paid" if option.price_usd > 0 else "free_or_quote",
        "why_it_matters": "This receipt ties the payment to the exact resource the agent bought, not just to a merchant-level charge.",
    }

def call_parallel_mpp(query: str) -> Dict[str, Any]:
    if os.getenv("ENABLE_PARALLEL_MPP", "0") != "1":
        return {
            "mode": "simulated",
            "summary": "Simulated Parallel MPP research: inference cost depends heavily on batch size, model size, latency target, and provider utilization.",
        }
    cmd = [
        "npx", "mppx",
        "https://parallelmpp.dev/api/search",
        "--method", "POST",
        "-J", json.dumps({"query": query, "mode": "fast"}),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return {"mode": "real_parallel_mpp", "stdout": result.stdout[-5000:], "stderr": result.stderr[-1000:], "returncode": result.returncode}
    except Exception as e:
        return {"mode": "parallel_mpp_error", "error": str(e)}

def call_exa(query: str) -> Dict[str, Any]:
    key = os.getenv("EXA_API_KEY")
    if not key:
        return {"mode": "simulated", "results": ["Simulated Exa: recent inference providers expose per-token APIs; GPU marketplaces can win at high volume."]}
    try:
        r = requests.post(
            "https://api.exa.ai/search",
            headers={"x-api-key": key, "Content-Type": "application/json"},
            json={"query": query, "numResults": 5, "contents": {"text": True}},
            timeout=30,
        )
        return {"mode": "real_exa", "status_code": r.status_code, "data": r.json()}
    except Exception as e:
        return {"mode": "exa_error", "error": str(e)}

def call_tavily(query: str) -> Dict[str, Any]:
    key = os.getenv("TAVILY_API_KEY")
    if not key:
        return {"mode": "simulated", "results": ["Simulated Tavily: serverless GPU reduces ops overhead; rented GPU wins only if utilization is high."]}
    try:
        r = requests.post(
            "https://api.tavily.com/search",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"query": query, "search_depth": "basic", "max_results": 5},
            timeout=30,
        )
        return {"mode": "real_tavily", "status_code": r.status_code, "data": r.json()}
    except Exception as e:
        return {"mode": "tavily_error", "error": str(e)}

def call_together(prompt: str) -> Dict[str, Any]:
    key = os.getenv("TOGETHER_API_KEY")
    if not key:
        return {
            "mode": "simulated",
            "output": "Simulated Together inference: good for quick baseline estimates and low-latency centralized inference, but large jobs may hit token-cost ceilings.",
            "estimated_route": {"route": "centralized inference API", "relative_cost": "medium", "reliability": "high", "setup_time": "low"},
        }
    try:
        r = requests.post(
            "https://api.together.xyz/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "model": "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 350,
            },
            timeout=60,
        )
        return {"mode": "real_together", "status_code": r.status_code, "data": r.json()}
    except Exception as e:
        return {"mode": "together_error", "error": str(e)}

def call_fireworks(prompt: str) -> Dict[str, Any]:
    key = os.getenv("FIREWORKS_API_KEY")
    if not key:
        return {
            "mode": "simulated",
            "output": "Simulated Fireworks inference: fast hosted inference is useful for benchmarking, but not always cheapest for 100,000 jobs.",
            "estimated_route": {"route": "fast centralized inference API", "relative_cost": "medium", "reliability": "high", "setup_time": "low"},
        }
    try:
        r = requests.post(
            "https://api.fireworks.ai/inference/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "model": "accounts/fireworks/models/llama-v3p1-8b-instruct",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 350,
            },
            timeout=60,
        )
        return {"mode": "real_fireworks", "status_code": r.status_code, "data": r.json()}
    except Exception as e:
        return {"mode": "fireworks_error", "error": str(e)}

def call_vast_quotes() -> Dict[str, Any]:
    key = os.getenv("VAST_API_KEY")
    if not key:
        return {
            "mode": "simulated",
            "offers": [
                {"gpu_name": "RTX 4090", "num_gpus": 1, "dph": 0.34, "reliability": 0.991, "country": "US", "fit": "cheap if job can tolerate setup and queue time"},
                {"gpu_name": "A100", "num_gpus": 1, "dph": 0.85, "reliability": 0.995, "country": "CA", "fit": "strong price/performance for batch inference"},
                {"gpu_name": "H100", "num_gpus": 1, "dph": 2.05, "reliability": 0.998, "country": "US", "fit": "best for high-throughput jobs if fully utilized"},
            ],
        }
    try:
        r = requests.post(
            "https://console.vast.ai/api/v0/bundles/",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "num_gpus": {"gte": 1},
                "gpu_ram": {"gte": 16},
                "reliability": {"gte": 0.98},
                "rentable": {"eq": True},
                "type": "ondemand",
                "limit": 6,
            },
            timeout=30,
        )
        return {"mode": "real_vast_quotes", "status_code": r.status_code, "data": r.json()}
    except Exception as e:
        return {"mode": "vast_error", "error": str(e)}

def call_runpod_job(task: str) -> Dict[str, Any]:
    key = os.getenv("RUNPOD_API_KEY")
    endpoint_id = os.getenv("RUNPOD_ENDPOINT_ID")
    if not key or not endpoint_id:
        return {
            "mode": "simulated",
            "job": "Simulated RunPod serverless inference benchmark",
            "latency_sec": 78,
            "estimated_reliability": 0.95,
            "fit": "Good middle ground: less ops than renting, more batch-friendly than pure API inference.",
        }
    try:
        url = f"https://api.runpod.ai/v2/{endpoint_id}/runsync"
        r = requests.post(
            url,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"input": {"task": task, "jobs": 100000}},
            timeout=120,
        )
        return {"mode": "real_runpod", "status_code": r.status_code, "data": r.json()}
    except Exception as e:
        return {"mode": "runpod_error", "error": str(e)}

def execute_provider(option_id: str, task: str) -> Dict[str, Any]:
    if option_id == "parallel_mpp_search":
        return call_parallel_mpp(task)
    if option_id == "exa_search":
        return call_exa(task)
    if option_id == "tavily_search":
        return call_tavily(task)
    if option_id == "together_cheap":
        return call_together("Estimate centralized inference economics for: " + task)
    if option_id == "fireworks_fast":
        return call_fireworks("Estimate fast hosted inference economics for: " + task)
    if option_id == "vast_gpu_quote":
        return call_vast_quotes()
    if option_id == "runpod_job":
        return call_runpod_job(task)
    if option_id == "decentralized_compute_probe":
        return {
            "mode": "simulated",
            "output": "Decentralized compute route is attractive if supply is deep and verification exists, but current reliability and latency are weaker than centralized/serverless options.",
            "estimated_route": {"relative_cost": "potentially low", "reliability": "variable", "latency": "variable", "risk": "provider verification and job completion uncertainty"},
        }
    if option_id == "strong_synthesis":
        return {
            "mode": "simulated",
            "output": "Winning route: use centralized inference APIs for baseline tests, serverless GPU for medium batch execution, and rented GPU if utilization is high enough. Decentralized compute is worth monitoring but rejected for reliability-sensitive production until verification/reputation improves.",
        }
    return {"error": "unknown provider"}

def choose_option(kind: str, min_quality: int, max_price: Optional[float] = None) -> ProviderOption:
    candidates = [o for o in CATALOG if o.kind == kind and o.quality >= min_quality]
    if max_price is not None:
        candidates = [o for o in candidates if o.price_usd <= max_price]
    candidates.sort(key=lambda o: (o.price_usd, o.latency_sec, -o.quality))
    return candidates[0]

def mpp_call(option: ProviderOption, task: str, budget_remaining: float, reason: str, educational_step: str) -> Dict[str, Any]:
    challenge = make_402_challenge(option)
    approved, auth = authorize_payment(option, budget_remaining, reason)

    event = {
        "step_title": educational_step,
        "provider": asdict(option),
        "mpp_stage_1_request": {
            "description": "Agent requests a resource from the provider.",
            "example": f"POST /mpp/{option.id}",
            "resource_requested": option.task,
        },
        "mpp_stage_2_challenge": challenge,
        "mpp_stage_3_agent_decision": auth,
        "mpp_stage_4_retry": None,
        "mpp_stage_5_result": None,
        "receipt": None,
    }

    if not approved:
        return event

    event["mpp_stage_4_retry"] = {
        "description": "Agent retries the same resource request, now attaching the payment credential.",
        "example": f"POST /mpp/{option.id}\nAuthorization: Payment {auth['credential'][:18]}...",
    }
    result = execute_provider(option.id, task)
    event["mpp_stage_5_result"] = {
        "description": "Provider verifies payment and returns the paid resource.",
        "result_preview": result,
    }
    event["receipt"] = receipt_for(option, auth["credential"])
    return event

def run_agent(task: str, budget: float) -> Dict[str, Any]:
    spend = 0.0
    events = []
    decisions = []

    plan = [
        "Clarify objective: find the cheapest reliable route for 100,000 inference jobs.",
        "Research current inference and GPU market options.",
        "Get centralized inference baseline.",
        "Check rented GPU marketplace economics.",
        "Probe serverless GPU economics.",
        "Probe decentralized compute risk/reliability.",
        "Reject expensive benchmark if it does not fit the budget.",
        "Synthesize the winning route and spend ledger.",
    ]

    research = choose_option("research", min_quality=8)
    ev = mpp_call(
        research,
        task,
        budget - spend,
        "Approved: research is cheap and helps avoid choosing the wrong compute route.",
        "Step 1: Buy minimum viable research",
    )
    events.append(ev)
    if ev.get("mpp_stage_3_agent_decision", {}).get("approved"):
        spend += research.price_usd
        decisions.append({"decision": f"Bought {research.name}", "amount": research.price_usd, "why": "Need market context before pricing 100,000 jobs."})

    inference = choose_option("inference", min_quality=7, max_price=0.75)
    ev = mpp_call(
        inference,
        task,
        budget - spend,
        "Approved: centralized inference gives the baseline cost and reliability route.",
        "Step 2: Price centralized inference API",
    )
    events.append(ev)
    if ev.get("mpp_stage_3_agent_decision", {}).get("approved"):
        spend += inference.price_usd
        decisions.append({"decision": f"Bought {inference.name}", "amount": inference.price_usd, "why": "Baseline for hosted inference cost, latency, and reliability."})

    vast = next(o for o in CATALOG if o.id == "vast_gpu_quote")
    ev = mpp_call(
        vast,
        task,
        budget - spend,
        "Approved: GPU quotes are free and essential for comparing rented GPU economics.",
        "Step 3: Check rented GPU marketplace",
    )
    events.append(ev)
    decisions.append({"decision": "Checked Vast.ai quotes", "amount": 0.0, "why": "Rented GPU can win if utilization is high enough."})

    runpod = next(o for o in CATALOG if o.id == "runpod_job")
    ev = mpp_call(
        runpod,
        task,
        budget - spend,
        "Approved: serverless GPU is a realistic middle path for high-volume inference without managing machines.",
        "Step 4: Buy serverless GPU benchmark",
    )
    events.append(ev)
    if ev.get("mpp_stage_3_agent_decision", {}).get("approved"):
        spend += runpod.price_usd
        decisions.append({"decision": f"Bought {runpod.name}", "amount": runpod.price_usd, "why": "Need a batch-compute benchmark route."})

    decentral = next(o for o in CATALOG if o.id == "decentralized_compute_probe")
    ev = mpp_call(
        decentral,
        task,
        budget - spend,
        "Approved: decentralized compute is relevant to compare, but only a small probe is justified.",
        "Step 5: Probe decentralized compute route",
    )
    events.append(ev)
    if ev.get("mpp_stage_3_agent_decision", {}).get("approved"):
        spend += decentral.price_usd
        decisions.append({"decision": "Bought decentralized compute probe", "amount": decentral.price_usd, "why": "Useful comparison, but reliability risk is higher."})

    premium = ProviderOption(
        id="premium_full_benchmark",
        name="Premium Full Benchmark Suite",
        kind="benchmark",
        task="full multi-provider benchmark suite",
        price_usd=35.00,
        latency_sec=300,
        quality=10,
        reliability=0.99,
        real_provider=False,
        notes="Simulated expensive option to show rejection.",
    )
    ev = mpp_call(
        premium,
        task,
        budget - spend,
        "Rejected: too expensive for a $20 exploration budget.",
        "Step 6: Reject overpriced option",
    )
    events.append(ev)
    decisions.append({"decision": "Rejected Premium Full Benchmark Suite", "amount": 0.0, "why": "High quality, but too expensive for the budget and not needed for a first route estimate."})

    synth = next(o for o in CATALOG if o.id == "strong_synthesis")
    ev = mpp_call(
        synth,
        task,
        budget - spend,
        "Approved: one final synthesis call is worth it to choose the route and explain tradeoffs.",
        "Step 7: Buy final synthesis",
    )
    events.append(ev)
    if ev.get("mpp_stage_3_agent_decision", {}).get("approved"):
        spend += synth.price_usd
        decisions.append({"decision": "Bought final synthesis", "amount": synth.price_usd, "why": "Need a clean final route recommendation."})

    winning_route = {
        "route": "Serverless GPU first, rented GPU if utilization is predictable, centralized API for baseline and burst traffic",
        "why": "For 100,000 inference jobs, pure API inference is simplest but may be expensive. Rented GPUs can be cheapest if fully utilized, but add setup and reliability risk. Serverless GPU is the practical middle route.",
        "rejected_routes": [
            {"route": "Only centralized inference APIs", "reason": "High reliability and low setup, but likely weaker unit economics at 100,000 jobs."},
            {"route": "Only rented GPUs", "reason": "Can be cheapest, but only if utilization is high and ops overhead is acceptable."},
            {"route": "Only decentralized compute", "reason": "Potentially cheap, but reliability, verification, and latency risks are too high for production-sensitive work."},
            {"route": "Premium full benchmark", "reason": "Rejected because it exceeds the $20 exploration budget."},
        ],
    }

    report = {
        "recommendation": winning_route["route"],
        "why": winning_route["why"],
        "budget_usd": budget,
        "spent_usd": round(spend, 2),
        "remaining_usd": round(budget - spend, 2),
        "decisions": decisions,
        "rejected_routes": winning_route["rejected_routes"],
        "mpp_takeaway": "MPP is the checkout layer: each provider quotes a price through 402, the agent applies a spending policy, pays through an accepted rail, retries, and receives the result plus a receipt.",
    }

    return {"task": task, "plan": plan, "catalog": [asdict(o) for o in CATALOG], "events": events, "report": report}

HTML = """
<!doctype html>
<html>
<head>
  <title>Agentic Costco</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    :root {
      --bg: #070A12;
      --panel: rgba(255,255,255,0.075);
      --panel2: rgba(255,255,255,0.105);
      --border: rgba(255,255,255,0.14);
      --text: #F4F7FB;
      --muted: #A7B1C2;
      --green: #79F2B0;
      --red: #FF8C8C;
      --blue: #9BC8FF;
      --yellow: #FFE08A;
      --purple: #C8A7FF;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background:
        radial-gradient(circle at 10% 0%, rgba(88, 166, 255, 0.28), transparent 34%),
        radial-gradient(circle at 90% 10%, rgba(196, 126, 255, 0.23), transparent 32%),
        radial-gradient(circle at 40% 100%, rgba(67, 220, 160, 0.16), transparent 32%),
        var(--bg);
      color: var(--text);
      font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
      min-height: 100vh;
    }
    .wrap { max-width: 1360px; margin: 0 auto; padding: 34px; }
    .hero {
      border: 1px solid var(--border);
      background: linear-gradient(135deg, rgba(255,255,255,0.11), rgba(255,255,255,0.055));
      box-shadow: 0 24px 90px rgba(0,0,0,0.35);
      border-radius: 28px;
      padding: 28px;
      overflow: hidden;
      position: relative;
    }
    .hero:after {
      content: "";
      position: absolute;
      right: -140px;
      top: -140px;
      width: 360px;
      height: 360px;
      border-radius: 999px;
      background: rgba(121,242,176,0.11);
      filter: blur(3px);
    }
    .kicker { color: var(--green); font-weight: 700; letter-spacing: .08em; text-transform: uppercase; font-size: 12px; }
    .topnav { display:flex; justify-content:space-between; align-items:center; gap:16px; position:relative; z-index:2; }
    .topnav a { color: var(--muted); text-decoration:none; margin-left:14px; font-size:13px; border:1px solid var(--border); padding:7px 10px; border-radius:999px; background:rgba(255,255,255,.045); }
    .topnav a:hover { color: var(--text); background:rgba(255,255,255,.09); }
    h1 { margin: 10px 0 8px; font-size: 48px; line-height: 1.02; }
    h2, h3 { margin-top: 0; }
    p { color: var(--muted); line-height: 1.55; }
    .hero p { max-width: 850px; font-size: 16px; }
    .pitchline {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 12px;
      margin-top: 22px;
    }
    .pillcard {
      border: 1px solid var(--border);
      background: rgba(10, 16, 28, 0.72);
      border-radius: 18px;
      padding: 14px;
      min-height: 92px;
    }
    .pillcard b { display: block; margin-bottom: 6px; }
    .pillcard span { color: var(--muted); font-size: 13px; line-height: 1.35; }
    .inputbar {
      margin-top: 18px;
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 12px;
    }
    textarea {
      width: 100%;
      min-height: 104px;
      resize: vertical;
      background: rgba(5, 8, 14, 0.78);
      color: white;
      border: 1px solid var(--border);
      border-radius: 18px;
      padding: 16px;
      font-size: 15px;
      outline: none;
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.05);
    }
    button {
      min-width: 150px;
      border: 0;
      border-radius: 18px;
      padding: 16px 20px;
      color: #06110B;
      background: linear-gradient(135deg, #79F2B0, #9BC8FF);
      font-weight: 800;
      cursor: pointer;
      box-shadow: 0 14px 36px rgba(121,242,176,0.2);
      font-size: 15px;
    }
    .grid { display: grid; grid-template-columns: 0.88fr 1.12fr; gap: 16px; margin-top: 16px; }
    .card {
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 22px;
      padding: 18px;
      backdrop-filter: blur(14px);
      box-shadow: 0 12px 50px rgba(0,0,0,0.22);
    }
    .small { font-size: 13px; color: var(--muted); }
    .statrow { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin: 12px 0; }
    .stat { background: rgba(255,255,255,0.075); border: 1px solid var(--border); border-radius: 16px; padding: 12px; }
    .stat .num { font-size: 22px; font-weight: 800; }
    .stat .label { color: var(--muted); font-size: 12px; margin-top: 3px; }
    table { width: 100%; border-collapse: collapse; font-size: 13px; }
    td, th { border-bottom: 1px solid rgba(255,255,255,0.09); padding: 9px 7px; text-align: left; vertical-align: top; }
    th { color: #DCE7F5; font-size: 12px; text-transform: uppercase; letter-spacing: .04em; }
    .tag { display:inline-block; border:1px solid var(--border); border-radius:999px; padding:4px 8px; font-size:12px; color:var(--muted); background:rgba(255,255,255,0.055); }
    .tag.green { color: var(--green); border-color: rgba(121,242,176,.35); }
    .tag.red { color: var(--red); border-color: rgba(255,140,140,.35); }
    .steps { display: grid; gap: 14px; }
    .event {
      border: 1px solid var(--border);
      background: rgba(8, 13, 24, 0.76);
      border-radius: 20px;
      overflow: hidden;
    }
    .eventHead {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: flex-start;
      padding: 16px;
      background: linear-gradient(90deg, rgba(155,200,255,0.13), rgba(255,255,255,0.035));
      border-bottom: 1px solid rgba(255,255,255,0.1);
    }
    .eventHead b { font-size: 15px; }
    .flow {
      display: grid;
      grid-template-columns: repeat(5, 1fr);
      gap: 10px;
      padding: 14px;
    }
    .flowbox {
      border: 1px solid rgba(255,255,255,0.1);
      background: rgba(255,255,255,0.055);
      border-radius: 14px;
      padding: 12px;
      min-height: 150px;
    }
    .flowbox .title { font-weight: 800; font-size: 12px; margin-bottom: 8px; color: var(--blue); text-transform: uppercase; letter-spacing: .04em; }
    .flowbox p { font-size: 12px; margin: 0 0 8px; }
    code, pre {
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
    }
    pre {
      white-space: pre-wrap;
      word-break: break-word;
      background: rgba(0,0,0,0.35);
      border: 1px solid rgba(255,255,255,0.09);
      padding: 10px;
      border-radius: 12px;
      max-height: 240px;
      overflow: auto;
      color: #DDE7F4;
      font-size: 11px;
      margin: 0;
    }
    .planlist { counter-reset: step; display: grid; gap: 8px; }
    .planitem {
      display: grid;
      grid-template-columns: 28px 1fr;
      gap: 10px;
      align-items: start;
      color: var(--muted);
      font-size: 13px;
    }
    .planitem:before {
      counter-increment: step;
      content: counter(step);
      width: 26px; height: 26px;
      display: grid; place-items: center;
      border-radius: 999px;
      background: rgba(155,200,255,0.15);
      color: var(--blue);
      font-weight: 800;
    }
    .route { color: var(--text); font-size: 17px; line-height: 1.45; }
    .hidden { display: none; }
    .loader {
      display: inline-block;
      width: 14px; height: 14px;
      border: 2px solid rgba(255,255,255,.25);
      border-top-color: var(--green);
      border-radius: 50%;
      animation: spin 1s linear infinite;
      margin-right: 8px;
      vertical-align: middle;
    }
    @keyframes spin { to { transform: rotate(360deg); } }
    @media (max-width: 1050px) {
      .grid, .pitchline, .flow, .inputbar { grid-template-columns: 1fr; }
      h1 { font-size: 38px; }
    }
  </style>
</head>
<body>
<div class="wrap">
  <section class="hero">
    <div class="topnav"><div class="kicker">Agentic Costco</div><div><a href="/">Demo</a><a href="/idea">Idea</a><a href="https://mpp.dev/" target="_blank">MPP Docs</a></div></div>
    <h1>Where AI agents shop for compute</h1>
    <p>
      This demo shows an agent turning a task into a procurement problem. It compares search, inference APIs,
      rented GPUs, serverless GPU, and decentralized compute, then uses an MPP-style payment flow to buy only
      the resources that improve the answer.
    </p>
    <div class="pitchline">
      <div class="pillcard"><b>1. Decompose</b><span>The agent breaks one big task into research, pricing, benchmarking, and synthesis.</span></div>
      <div class="pillcard"><b>2. Shop</b><span>It compares provider type, cost, latency, quality, and reliability.</span></div>
      <div class="pillcard"><b>3. Pay via MPP</b><span>Providers return 402 price quotes; the agent decides and retries with a payment credential.</span></div>
      <div class="pillcard"><b>4. Audit</b><span>The final answer includes spend, receipts, rejected routes, and why.</span></div>
    </div>
    <div class="inputbar">
      <textarea id="task">Find the cheapest reliable way to run 100,000 AI inference jobs today. Budget: $20. Compare centralized inference APIs, serverless GPU providers, rented GPUs, and decentralized compute networks. Buy only the resources needed to estimate real cost, latency, and reliability. Return the winning route, rejected routes, and a spend ledger.</textarea>
      <button onclick="run()">Run demo</button>
    </div>
  </section>

  <div id="loading" class="card hidden" style="margin-top:16px;"><span class="loader"></span> Running Agentic Costco...</div>

  <div class="grid">
    <div>
      <div class="card" style="margin-top:16px;">
        <h3>Provider marketplace</h3>
        <p class="small">These are the real provider categories the agent can route work to. If API keys are configured, some calls become real. Otherwise they stay simulated for safe demo mode.</p>
        <div id="catalog" class="small">Run the demo to load providers.</div>
      </div>

      <div class="card" style="margin-top:16px;">
        <h3>Agent plan</h3>
        <div id="plan" class="small">Run the demo to see the task decomposition.</div>
      </div>

      <div class="card" style="margin-top:16px;">
        <h3>What MPP is doing</h3>
        <p class="small">
          MPP is not the money itself. It is the machine-readable checkout flow:
          request resource, receive <code>402 Payment Required</code>, read price and terms,
          approve or reject, retry with payment credential, receive result and receipt.
        </p>
      </div>
    </div>

    <div>
      <div class="card" style="margin-top:16px;">
        <h3>Final route recommendation</h3>
        <div id="report" class="small">Waiting.</div>
      </div>

      <div class="card" style="margin-top:16px;">
        <h3>Spend ledger</h3>
        <div id="ledger" class="small">Waiting.</div>
      </div>
    </div>
  </div>

  <div class="card" style="margin-top:16px;">
    <h3>MPP Trace</h3>
    <p class="small">Each row shows where MPP is used: the provider's 402 quote, the agent's payment decision, the retry, the result, and the receipt.</p>
    <div id="events" class="steps small">Waiting.</div>
  </div>
</div>

<script>
function money(x) { return "$" + Number(x || 0).toFixed(2); }
function esc(obj) { return JSON.stringify(obj, null, 2); }

async function run() {
  const task = document.getElementById("task").value;
  document.getElementById("loading").classList.remove("hidden");
  document.getElementById("events").innerHTML = "Running...";
  document.getElementById("report").innerHTML = "Waiting.";
  document.getElementById("ledger").innerHTML = "Waiting.";

  const res = await fetch("/api/run", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({task})
  });
  const data = await res.json();
  document.getElementById("loading").classList.add("hidden");

  document.getElementById("catalog").innerHTML = `
    <table>
      <tr><th>Provider</th><th>Type</th><th>Price</th><th>Latency</th><th>Quality</th><th>Real?</th></tr>
      ${data.catalog.map(p => `<tr>
        <td><b>${p.name}</b><br><span class="small">${p.notes}</span></td>
        <td><span class="tag">${p.kind}</span></td>
        <td>${money(p.price_usd)}</td>
        <td>${p.latency_sec}s</td>
        <td>${p.quality}/10</td>
        <td>${p.real_provider ? '<span class="tag green">adapter</span>' : '<span class="tag">sim</span>'}</td>
      </tr>`).join("")}
    </table>
  `;

  document.getElementById("plan").innerHTML = `
    <div class="planlist">
      ${data.plan.map(p => `<div class="planitem">${p}</div>`).join("")}
    </div>
  `;

  document.getElementById("report").innerHTML = `
    <div class="statrow">
      <div class="stat"><div class="num">${money(data.report.budget_usd)}</div><div class="label">Budget</div></div>
      <div class="stat"><div class="num">${money(data.report.spent_usd)}</div><div class="label">Spent</div></div>
      <div class="stat"><div class="num">${money(data.report.remaining_usd)}</div><div class="label">Remaining</div></div>
    </div>
    <div class="route"><b>Winning route:</b> ${data.report.recommendation}</div>
    <p>${data.report.why}</p>
    <p><b>MPP takeaway:</b> ${data.report.mpp_takeaway}</p>
    <h4>Rejected routes</h4>
    <table>
      <tr><th>Route</th><th>Reason</th></tr>
      ${data.report.rejected_routes.map(r => `<tr><td>${r.route}</td><td>${r.reason}</td></tr>`).join("")}
    </table>
  `;

  document.getElementById("ledger").innerHTML = `
    <table>
      <tr><th>Decision</th><th>Amount</th><th>Why</th></tr>
      ${data.report.decisions.map(d => `<tr><td>${d.decision}</td><td>${money(d.amount)}</td><td>${d.why}</td></tr>`).join("")}
    </table>
  `;

  document.getElementById("events").innerHTML = data.events.map((e, i) => {
    const approved = e.mpp_stage_3_agent_decision && e.mpp_stage_3_agent_decision.approved;
    const status = approved ? `<span class="tag green">paid or authorized</span>` : `<span class="tag red">rejected</span>`;
    const retry = e.mpp_stage_4_retry ? e.mpp_stage_4_retry : {description: "No retry. The agent rejected this resource.", example: "No Authorization header sent."};
    const result = e.mpp_stage_5_result ? e.mpp_stage_5_result : {description: "No result returned because the agent did not pay.", result_preview: null};
    return `
      <div class="event">
        <div class="eventHead">
          <div>
            <b>${i + 1}. ${e.step_title}</b>
            <div class="small">${e.provider.name} · ${e.provider.task}</div>
          </div>
          ${status}
        </div>
        <div class="flow">
          <div class="flowbox">
            <div class="title">1. Request</div>
            <p>${e.mpp_stage_1_request.description}</p>
            <pre>${e.mpp_stage_1_request.example}</pre>
          </div>
          <div class="flowbox">
            <div class="title">2. 402 quote</div>
            <p>${e.mpp_stage_2_challenge.why_this_happened}</p>
            <pre>${esc(e.mpp_stage_2_challenge.payment)}</pre>
          </div>
          <div class="flowbox">
            <div class="title">3. Decision</div>
            <p>${approved ? "Agent approves the purchase under budget/policy." : "Agent rejects the purchase under budget/policy."}</p>
            <pre>${esc(e.mpp_stage_3_agent_decision)}</pre>
          </div>
          <div class="flowbox">
            <div class="title">4. Retry</div>
            <p>${retry.description}</p>
            <pre>${retry.example}</pre>
          </div>
          <div class="flowbox">
            <div class="title">5. Result + receipt</div>
            <p>${result.description}</p>
            <pre>${esc({result: result.result_preview, receipt: e.receipt})}</pre>
          </div>
        </div>
      </div>
    `;
  }).join("");
}
</script>
</body>
</html>
"""


IDEA_HTML = """
<!doctype html>
<html>
<head>
  <title>Agentic Costco · Idea</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    :root {
      --bg: #070A12;
      --panel: rgba(255,255,255,0.075);
      --border: rgba(255,255,255,0.14);
      --text: #F4F7FB;
      --muted: #A7B1C2;
      --green: #79F2B0;
      --red: #FF8C8C;
      --blue: #9BC8FF;
      --yellow: #FFE08A;
      --purple: #C8A7FF;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background:
        radial-gradient(circle at 8% 0%, rgba(88, 166, 255, 0.28), transparent 34%),
        radial-gradient(circle at 92% 8%, rgba(196, 126, 255, 0.23), transparent 32%),
        radial-gradient(circle at 45% 100%, rgba(67, 220, 160, 0.16), transparent 32%),
        var(--bg);
      color: var(--text);
      font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
      min-height: 100vh;
    }
    .wrap { max-width: 1180px; margin: 0 auto; padding: 34px; }
    .hero, .card {
      border: 1px solid var(--border);
      background: linear-gradient(135deg, rgba(255,255,255,0.10), rgba(255,255,255,0.055));
      box-shadow: 0 24px 90px rgba(0,0,0,0.28);
      border-radius: 26px;
      padding: 26px;
      backdrop-filter: blur(14px);
    }
    .hero { position: relative; overflow: hidden; }
    .hero:after {
      content:"";
      position:absolute;
      width:420px; height:420px; border-radius:999px;
      background:rgba(121,242,176,.10);
      right:-170px; top:-170px;
    }
    .topnav { display:flex; justify-content:space-between; align-items:center; gap:16px; position:relative; z-index:2; }
    .kicker { color: var(--green); font-weight: 800; letter-spacing: .08em; text-transform: uppercase; font-size: 12px; }
    .topnav a { color: var(--muted); text-decoration:none; margin-left:14px; font-size:13px; border:1px solid var(--border); padding:7px 10px; border-radius:999px; background:rgba(255,255,255,.045); }
    .topnav a:hover { color: var(--text); background:rgba(255,255,255,.09); }
    h1 { margin: 18px 0 10px; font-size: 48px; line-height:1.02; position:relative; z-index:2; }
    h2 { margin: 0 0 12px; font-size: 24px; }
    h3 { margin: 16px 0 8px; }
    p, li { color: var(--muted); line-height: 1.58; font-size: 15px; }
    .lead { font-size: 18px; max-width: 900px; position:relative; z-index:2; }
    .grid { display:grid; grid-template-columns: repeat(2, 1fr); gap:16px; margin-top:16px; }
    .three { display:grid; grid-template-columns: repeat(3, 1fr); gap:16px; margin-top:16px; }
    .highlight { background: linear-gradient(135deg, rgba(121,242,176,.13), rgba(155,200,255,.09)); }
    .warn { background: linear-gradient(135deg, rgba(255,224,138,.12), rgba(255,255,255,.05)); }
    .number {
      width:32px; height:32px; border-radius:999px; display:grid; place-items:center;
      background:rgba(155,200,255,.15); color:var(--blue); font-weight:900; margin-bottom:10px;
    }
    .flow { display:grid; grid-template-columns: repeat(5, 1fr); gap:10px; margin-top:14px; }
    .flowbox {
      background: rgba(5,8,14,.58); border: 1px solid rgba(255,255,255,.12);
      border-radius: 16px; padding: 14px; min-height: 150px;
    }
    .flowbox b { display:block; color:var(--blue); font-size:13px; margin-bottom:8px; }
    .flowbox span { color:var(--muted); font-size:13px; line-height:1.42; }
    .tag { display:inline-block; border:1px solid var(--border); border-radius:999px; padding:5px 9px; font-size:12px; color:var(--muted); background:rgba(255,255,255,0.055); margin: 0 6px 6px 0; }
    .tag.green { color: var(--green); border-color: rgba(121,242,176,.35); }
    .tag.blue { color: var(--blue); border-color: rgba(155,200,255,.35); }
    .tag.yellow { color: var(--yellow); border-color: rgba(255,224,138,.35); }
    table { width:100%; border-collapse: collapse; font-size:14px; }
    td, th { border-bottom:1px solid rgba(255,255,255,.10); padding:10px 8px; text-align:left; vertical-align:top; }
    th { color:#DCE7F5; font-size:12px; text-transform:uppercase; letter-spacing:.04em; }
    code, pre { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace; }
    pre {
      white-space: pre-wrap; background:rgba(0,0,0,.35); border:1px solid rgba(255,255,255,.10);
      border-radius:14px; padding:14px; color:#DDE7F4; font-size:13px; overflow:auto;
    }
    .cta {
      display:inline-block; margin-top:12px; color:#06110B; text-decoration:none;
      background:linear-gradient(135deg, #79F2B0, #9BC8FF);
      font-weight:900; padding:12px 16px; border-radius:14px;
    }
    .linklist a { color: var(--blue); text-decoration:none; display:block; margin:8px 0; }
    .linklist a:hover { text-decoration:underline; }
    @media (max-width: 980px) {
      .grid, .three, .flow { grid-template-columns:1fr; }
      h1 { font-size: 38px; }
      .topnav { align-items:flex-start; flex-direction:column; }
      .topnav a { margin-left:0; margin-right:8px; }
    }
  </style>
</head>
<body>
<div class="wrap">
  <section class="hero">
    <div class="topnav">
      <div class="kicker">Agentic Costco</div>
      <div>
        <a href="/">Demo</a>
        <a href="/idea">Idea</a>
        <a href="https://mpp.dev/" target="_blank">MPP Docs</a>
      </div>
    </div>
    <h1>Agents become buyers</h1>
    <p class="lead">
      Agentic Costco is a prototype of the MPP gateway/router layer that lets agents buy compute and data
      from existing providers as if every provider were a machine-payable endpoint.
    </p>
  </section>

  <div class="grid">
    <div class="card highlight">
      <h2>Is this a good idea?</h2>
      <p>
        Yes, if we pitch it honestly: this is a future-facing demo of agentic procurement, not a claim
        that every GPU provider already supports MPP natively.
      </p>
      <p>
        The strong thesis is that agents will become procurement engines. MPP and x402-style protocols
        make APIs economically addressable. The first useful markets are likely paid digital resources:
        search, inference, GPU compute, scraping, datasets, verification, and storage.
      </p>
      <a class="cta" href="/">Run the demo</a>
    </div>

    <div class="card warn">
      <h2>The honest caveat</h2>
      <p>
        Most GPU and inference providers do not natively support MPP today. Parallel is a strong MPP-native
        reference for paid agentic research. For Vast, RunPod, Together, Fireworks, Exa, and similar providers,
        the realistic architecture is an MPP gateway wrapper.
      </p>
      <pre>Agent
  -> MPP Gateway
    -> Vast.ai API
    -> RunPod API
    -> Together / Fireworks
    -> Exa / Tavily
    -> Parallel MPP</pre>
    </div>
  </div>

  <div class="card" style="margin-top:16px;">
    <h2>What is MPP?</h2>
    <p>
      MPP means Machine Payments Protocol. It is a machine-readable payment flow for paid internet resources.
      A provider can quote a price inside the HTTP flow. The agent can decide whether to pay, pay through an
      accepted rail, retry the request, and receive the resource plus a receipt.
    </p>
    <div>
      <span class="tag green">HTTP-native</span>
      <span class="tag blue">Agent-readable prices</span>
      <span class="tag yellow">Cards or stablecoins underneath</span>
      <span class="tag">Receipts per resource</span>
    </div>
    <div class="flow">
      <div class="flowbox"><b>1. Request</b><span>Agent asks for a paid resource, like a GPU benchmark or search result.</span></div>
      <div class="flowbox"><b>2. 402 quote</b><span>Provider returns <code>402 Payment Required</code> with price and terms.</span></div>
      <div class="flowbox"><b>3. Decide</b><span>Agent checks budget, value, latency, and reliability.</span></div>
      <div class="flowbox"><b>4. Pay + retry</b><span>Agent pays through an accepted rail and retries with a payment credential.</span></div>
      <div class="flowbox"><b>5. Result</b><span>Provider returns the resource and a receipt tied to that exact purchase.</span></div>
    </div>
  </div>

  <div class="grid">
    <div class="card">
      <h2>Why not just give the agent a card?</h2>
      <p>You can. The card is only the funding source. MPP is the checkout protocol.</p>
      <table>
        <tr><th>Normal card flow</th><th>MPP flow</th></tr>
        <tr><td>Create account, add card, choose plan, manage API key, handle invoices.</td><td>Request resource, receive price quote, approve or reject, pay, retry, receive receipt.</td></tr>
        <tr><td>Merchant-level payment.</td><td>Resource-level payment.</td></tr>
        <tr><td>Each provider has a different integration.</td><td>Providers expose a common HTTP payment pattern.</td></tr>
      </table>
      <p>A card can be one rail inside MPP. Stablecoins can be another. MPP is the common interface above those rails.</p>
    </div>

    <div class="card">
      <h2>Why the compute angle works</h2>
      <p>
        The GPU/inference problem is already metered, digital, price-sensitive, and API-driven. An agent can
        realistically compare centralized inference APIs, serverless GPU, rented GPUs, and decentralized compute.
      </p>
      <p>
        The demo task is deliberately concrete:
      </p>
      <pre>Find the cheapest reliable way to run
100,000 AI inference jobs today.

Budget: $20
Return: winning route, rejected routes, spend ledger</pre>
    </div>
  </div>

  <div class="three">
    <div class="card">
      <div class="number">1</div>
      <h3>Cost optimization</h3>
      <p>For small jobs, API inference may be cheapest. For large jobs, serverless or rented GPU may win. The agent should choose dynamically.</p>
    </div>
    <div class="card">
      <div class="number">2</div>
      <h3>Reliability-aware routing</h3>
      <p>The cheapest provider is not always best. The agent should compare price with latency, quality, uptime, and verification.</p>
    </div>
    <div class="card">
      <div class="number">3</div>
      <h3>Auditable spending</h3>
      <p>The final output should include not only the answer, but what the agent bought, what it rejected, and why.</p>
    </div>
  </div>

  <div class="card" style="margin-top:16px;">
    <h2>Documentation links</h2>
    <p>Use these if someone wants to verify the protocol category or continue building.</p>
    <div class="linklist">
      <a href="https://mpp.dev/" target="_blank">MPP official site</a>
      <a href="https://docs.stripe.com/payments/machine/mpp" target="_blank">Stripe MPP documentation</a>
      <a href="https://docs.tempo.xyz/guide/machine-payments" target="_blank">Tempo machine payments guide</a>
      <a href="https://docs.parallel.ai/integrations/agentic-payments" target="_blank">Parallel agentic payments integration</a>
      <a href="https://docs.cdp.coinbase.com/x402/welcome" target="_blank">Coinbase x402 documentation</a>
      <a href="https://blog.cloudflare.com/x402/" target="_blank">Cloudflare x402 writeup</a>
    </div>
  </div>
</div>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/idea")
def idea():
    return render_template_string(IDEA_HTML)

@app.route("/api/run", methods=["POST"])
def api_run():
    payload = request.get_json(force=True)
    task = payload.get("task", "")
    result = run_agent(task, BUDGET)
    return jsonify(result)

@app.route("/api/catalog")
def api_catalog():
    return jsonify([asdict(o) for o in CATALOG])

if __name__ == "__main__":
    print("Open http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=True)
