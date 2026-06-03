# Agentic Costco

**Where AI agents shop for compute.**

Agentic Costco is a demo of an AI agent that turns a task into a procurement problem. The agent compares search, inference APIs, rented GPUs, serverless GPU, and decentralized compute, then uses an MPP-style payment flow to buy only the resources that improve the answer.

The important framing: this is a future-facing demo of agentic procurement, not a claim that every GPU provider already supports MPP natively.

---

## Thesis

Agents will become procurement engines.

MPP and x402-style protocols make APIs economically addressable. The first useful markets are likely paid digital resources:

- search
- inference
- GPU compute
- scraping
- datasets
- verification
- storage
- API access

Agentic Costco prototypes the MPP gateway/router layer that lets agents buy compute and data from existing providers as if every provider were a machine-payable endpoint.

---

## The honest caveat

Most GPU and inference providers do not natively support MPP today.

Parallel is a strong MPP-native reference for paid agentic research. For providers like Vast, RunPod, Together, Fireworks, Exa, and Tavily, the realistic architecture is an MPP gateway wrapper:

```text
Agent
  -> MPP Gateway
    -> Vast.ai API
    -> RunPod API
    -> Together / Fireworks
    -> Exa / Tavily
    -> Parallel MPP
```

That is still a useful architecture. The gateway handles the `402 Payment Required` challenge, payment terms, payment credential verification, provider API call, receipt creation, and spend ledger.

---

## What is MPP?

MPP means Machine Payments Protocol.

The flow is:

```text
1. Agent requests a paid resource.
2. Provider returns HTTP 402 Payment Required.
3. Provider includes price, currency, accepted rails, resource, and terms.
4. Agent decides whether the purchase is worth it.
5. Agent pays through an accepted rail.
6. Agent retries the request with Authorization: Payment <credential>.
7. Provider returns the resource plus receipt.
```

MPP is not the money itself. It is the machine-readable checkout flow. A card can be one rail inside MPP. Stablecoins can be another.

```text
Credit card = funding source
MPP = machine-readable checkout protocol
```

---

## Demo task

The current demo prompt is:

```text
Find the cheapest reliable way to run 100,000 AI inference jobs today. Budget: $20. Compare centralized inference APIs, serverless GPU providers, rented GPUs, and decentralized compute networks. Buy only the resources needed to estimate real cost, latency, and reliability. Return the winning route, rejected routes, and a spend ledger.
```

This is stronger than a generic diligence copilot because the agent is acting as a live compute procurement engine.

The agent asks:

- Should I buy API inference?
- Should I rent a GPU?
- Should I use serverless GPU?
- Should I route some work to decentralized compute?
- What is the cheapest reliable path for 100,000 jobs?
- Which options should I reject because they are too slow, expensive, or unreliable?

---

## Run from GitHub

Replace `<YOUR_GITHUB_REPO_URL>` with the repo URL after you push it.

```bash
git clone <YOUR_GITHUB_REPO_URL>
cd agentic-costco

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env

python app.py
```

Open:

```bash
http://127.0.0.1:5000
```

Idea page:

```bash
http://127.0.0.1:5000/idea
```

---

## Run from a downloaded zip

```bash
unzip agentic-costco.zip
cd agentic-costco

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env

python app.py
```

Open:

```bash
http://127.0.0.1:5000
```

---

## Optional real provider setup

The demo works without keys. To make provider calls real, edit `.env`.

```bash
ENABLE_PARALLEL_MPP=0
EXA_API_KEY=
TAVILY_API_KEY=
TOGETHER_API_KEY=
FIREWORKS_API_KEY=
VAST_API_KEY=
RUNPOD_API_KEY=
RUNPOD_ENDPOINT_ID=
DEMO_BUDGET_USD=20.00
```

### Parallel MPP

Install `mppx`:

```bash
npm install -g mppx
```

Create and fund an account:

```bash
npx mppx account create
npx mppx account fund
```

Then set:

```bash
ENABLE_PARALLEL_MPP=1
```

### Vast.ai

Set:

```bash
VAST_API_KEY=your_key_here
```

The demo queries GPU marketplace-style offers. It does not rent a GPU by default.

### RunPod

Create a RunPod serverless endpoint first, then set:

```bash
RUNPOD_API_KEY=your_key_here
RUNPOD_ENDPOINT_ID=your_endpoint_id_here
```

If these are not set, RunPod runs in simulation mode.

---

## Website pages

### `/`

The main demo page. It shows:

- provider marketplace
- agent plan
- final route recommendation
- spend ledger
- MPP trace for each provider interaction

### `/idea`

Presentation page. It explains:

- the goal of Agentic Costco
- whether this is actually a good idea
- what MPP is
- the honest caveat that most GPU providers do not support MPP natively today
- why an MPP gateway wrapper is the realistic architecture
- why MPP is different from just giving an agent a card
- links to MPP, Stripe, Tempo, Parallel, Coinbase x402, and Cloudflare x402 documentation

---

## One-line pitch

Agentic Costco is an AI agent that turns a task into a procurement problem, shops across compute and data providers, pays through an MPP-style flow, and returns the completed work with an auditable spend ledger.

---

## Useful documentation

- MPP official site: https://mpp.dev/
- Stripe MPP docs: https://docs.stripe.com/payments/machine/mpp
- Tempo machine payments guide: https://docs.tempo.xyz/guide/machine-payments
- Parallel agentic payments docs: https://docs.parallel.ai/integrations/agentic-payments
- Coinbase x402 docs: https://docs.cdp.coinbase.com/x402/welcome
- Cloudflare x402 writeup: https://blog.cloudflare.com/x402/
