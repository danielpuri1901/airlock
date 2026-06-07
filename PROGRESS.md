# PolicyGuard — BUILD STATE / HANDOFF (single source of truth)
**What:** an on-chain spending guard for x402 AI-agent payments on Algorand. Hackathon: Algorand "Agentic Commerce x402" Berlin, Jun 6–7 2026. **Track 2 Infrastructure, NEW project, solo.**

## ✅ WORKING RIGHT NOW (verified on LocalNet)
A real payment = an atomic group **[USDC transfer + `enforce()` app-call]**. The CHAIN runs `enforce`; if it fails, the whole group is rejected → no payment. Demonstrated live:
```
RULES: $1.00 cap for agent · shop approved
✅ ALLOWED  $0.40 to shop
✅ ALLOWED  $0.40 to shop   [total $0.80]
⛔ BLOCKED  $0.40 to shop   → "over the spending cap"   (cumulative budget!)
⛔ BLOCKED  $0.10 to stranger → "payee is not allow-listed"
```
Blocks come from `Runtime error executing PolicyGuard (appId)` = **the chain enforces it, not a server** (byzantine-proof). This is the core + the "shock" demo.

## WHERE EVERYTHING IS  (root: ~/Desktop/Projects/x402-demo/)
- `policy-guard/smart_contracts/policy_guard/contract.py` — **the guard** (PolicyGuard). Methods: `set_usdc`, `set_cap`, `allow_payee`, `enforce`. Boxes: `usdc_id`(global), `spent`/`cap`/`allowed`(BoxMaps). Coin is CONFIGURABLE (set_usdc).
- `policy-guard/fire_drill.py` — in-process unit test (passes: cap/cumulative/allowlist/asset).
- `policy-guard/deploy_local.py` — deploys to LocalNet + mints test-USDC + set_usdc. Writes `.deploy.json` (app_id, usdc_id, app_address, deployer).
- `policy-guard/demo_local.py` — the live good/bad payment demo (WORKS).
- `policy-guard/.deploy.json` — last: app_id 1002, usdc_id 1001 (regenerate by re-running deploy).
- `policy-guard/.env.deploy` — TestNet wallet (gitignored, addr OFXC7P4L…, funded ALGO). SET ASIDE (we pivoted to LocalNet).
- Demo we build on (reused, decluttered): `x402-basic-tutorial/client/index.ts` (robot), `.../server/index.ts` (shop), `x402-examples/facilitator/basic/index.ts` (cashier), `x402-examples/client/custom/index.ts` (fallback). npm-installed.

## ENV / HOW TO RUN  (CRITICAL — non-obvious)
- **System Python is 3.14 (too new for Algorand tools).** Use the **3.12 venv** at `policy-guard/.venv` (made via `python3.12 -m venv .venv`). It has: puyapy, algorand-python, algorand-python-testing, py-algorand-sdk, algokit-utils.
- **AlgoKit** installed via `uv tool install algokit --python 3.12` (NOT brew — no brew formula; `pipx` also works). Version 2.10.2.
- **Compile contract:** `cd policy-guard && .venv/bin/puyapy smart_contracts/policy_guard/contract.py` → PolicyGuard.approval.teal + .arc56.json.
- **LocalNet:** `algokit localnet start` (Docker). algod = localhost:4001. Reliable, no faucet (uses `algorand.account.localnet_dispenser()`).
- **Run:** `.venv/bin/python deploy_local.py` then `.venv/bin/python demo_local.py`.
- **Box refs gotcha:** any call touching a box MUST pass `box_references` (name = prefix bytes + `decode_address(addr)`), e.g. `b"cap_"+pk`, `b"spent_"+pk`, `b"allow_"+pk`.
- **Method-call gotcha:** use the **AppClient** (`algorand.client.get_app_client_by_id(...)` → `app.send.call(AppClientMethodCallParams(method="...", args=[...], box_references=[...], sender=, signer=))`) — passing a raw method string to `algorand.send.app_call_method_call` fails (needs an ABI Method object).
- **Txn-as-arg:** to pass the USDC transfer to `enforce`, put `AssetTransferParams(...)` directly in `args=[...]` — AppClient bundles it. Give each a unique `note=` or identical payments collide ("transaction already in ledger").
- **⚠️ TESTNET node is flaky:** algonode (`testnet-api.algonode.cloud`) returns intermittent **403 / "quota exceeded"** — needs a `User-Agent` header AND likely an API key. THIS is why we build/demo on LocalNet. Do TestNet deploy LAST, with a key.

## KEY DECISIONS
- **Berlin = WIN (Algorand). NO LangChain in the core** — LangChain/LangSmith/deep-agents = separate, post-Berlin / Jun-12 interview prep. AI "scam-scan" = optional bonus only.
- **Harder version chosen:** the CHAIN enforces (not the facilitator) → byzantine-proof. DONE on LocalNet.
- **Configurable coin** (set_usdc) so same contract works localnet/testnet/mainnet.
- LocalNet for reliable build + live demo; TestNet at the very end for the public Lora link.

## ▶️ NEXT STEPS (in order)
1. **Wrap in the real x402 flow** (IN PROGRESS): subclass `ExactAvmScheme` (from `@x402/avm/exact/client`) in a TS client; override `createPaymentPayload` to inject our `enforce` app-call (appId + the axfer as ABI arg + box refs) into the x402 payment group, so a real x402 402→pay→settle gets guarded. Demo uses `@x402/*` `^2.11.0`. Point client/server/facilitator at LocalNet (or hosted, but our guard must be on that network).
2. **Deploy to TestNet** (with a working node/API key) for the public Lora link = the 50/50 milestone artifact.
3. **Stage demo:** "hijacked agent → chain blocks the drain." Silence algokit_utils' verbose error logging for clean output.
4. **README** (threat model, the gap = empty `onBeforeSettle` / x402 issue #2299, byzantine demo, Lora links) + an eval number.

## PITCH (honest)
"x402's facilitator settles any valid payment with NO policy layer — the `onBeforeSettle` hook ships empty (x402 issue #2299 names this). We fill it natively on Algorand, enforced ON-CHAIN: spend cap + cumulative budget + payee allowlist, in the settlement group. Even a compromised facilitator can't drain you." 
**Don't overclaim:** on-chain box = auditable/durable, not "more secure" than an off-chain cap; NOT first to the idea (presidio-hardened-x402, PaySentry exist on EVM); pre-volume on Algorand; the Grok $174k drain was on Base, NOT x402 (it motivates the threat class only). Real proof for the gap: x402 SDK CVE (GHSA-qr2g-p6q7-w82m), arXiv 2605.11781 + 2605.30998, Halborn x402 guide (recommends exactly spend-limits+allowlists).

## Reference docs (~/Desktop/Learning/05-ai-engineering/)
BUILD-PLAN-confirmed.md · GAP-AND-ALGORAND-WIN.md · PLAN-v2-VALIDATED.md · BUILD-REUSE-MAP.md · frontier-techniques-shortlist.md · hackathon-resource-guide.md · EXPLAINER-langchain-langgraph-recursion.md · START-HERE-explainer.html (+ explainer-animation.html)

## WRAP PLAN (x402 flow) — exact, ready to implement
**Override target:** `ExactAvmScheme.createPaymentPayload(x402Version, paymentRequirements): Promise<PaymentPayloadResult>` from `@x402/avm/exact/client`. It internally builds `[optional feePayer + USDC axfer]` via algokit-utils TransactionComposer and returns an ENCODED, signed group; `getAlgorandClient`/`getAssetId` are private (can't hook mid-build).
**Approach:** start from `x402-examples/client/custom/index.ts` (it assembles the group manually = cleaner than subclassing), OR subclass + reimplement `createPaymentPayload`. Inject our `enforce` app-call into the SAME group: appId from `.deploy.json`, the axfer as the ABI arg, `box_references` = `[b"cap_"+agentpk, b"spent_"+agentpk, b"allow_"+payeepk]`, a unique `note`. Client signs BOTH the axfer + the app-call (this is what makes it byzantine-proof).
**Network:** the guard must be deployed on the SAME chain the facilitator uses. For end-to-end on LocalNet, run the demo's server + facilitator pointed at LocalNet (the hosted goplausible server is TestNet-only). Then: a good x402 payment settles; a bad one → facilitator `/settle` fails because the chain rejects the group → 402.
**Reuse** demo_local.py's box-ref + unique-note logic. After it works on LocalNet → deploy guard to TestNet (reliable node / API key) → public Lora link.
