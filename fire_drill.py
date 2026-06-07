"""Fire drill — prove the PolicyGuard makes the right call.

Runs entirely in-process (no blockchain, no money). It sets the rules, then
throws five fake payments at the guard and prints whether it ALLOWED or BLOCKED
each one — so we can SEE the rulebook working before wiring it into real payments.

Run from the policy-guard/ folder:  .venv/bin/python fire_drill.py
"""
from algopy import UInt64, Asset
from algopy_testing import algopy_testing_context

from smart_contracts.policy_guard.contract import PolicyGuard, USDC_TESTNET_ASA_ID


def run() -> int:
    with algopy_testing_context() as ctx:
        guard = PolicyGuard()              # the owner is the account that "deploys" it
        agent = ctx.any.account()          # the robot's wallet
        shop = ctx.any.account()           # an APPROVED shop
        stranger = ctx.any.account()       # an UN-approved shop
        usdc = Asset(USDC_TESTNET_ASA_ID)  # the real coin
        other_coin = ctx.any.asset()       # some random other coin

        # The owner sets the rules: $1.00 cap for this agent, and approve the shop.
        guard.set_cap(agent, UInt64(1_000_000))   # 1 USDC = 1,000,000 units
        guard.allow_payee(shop)

        print("RULES:  $1.00 cap per agent  ·  approved shop only  ·  USDC only")
        print("-" * 64)

        def pay(label: str, payee, dollars: float, coin: Asset) -> None:
            units = int(dollars * 1_000_000)
            xfer = ctx.any.txn.asset_transfer(
                sender=agent,
                asset_receiver=payee,
                asset_amount=UInt64(units),
                xfer_asset=coin,
            )
            call = ctx.txn.defer_app_call(guard.enforce, xfer)
            try:
                with ctx.txn.create_group(gtxns=[xfer, call]):
                    call.submit()
                print(f"  ✅ ALLOWED   {label}")
            except Exception as e:  # an assert in the guard fired -> payment killed
                print(f"  ⛔ BLOCKED   {label}\n               → {e}")

        pay("$0.40 to approved shop (USDC)", shop, 0.40, usdc)
        pay("$0.40 to approved shop (USDC)   [running total $0.80]", shop, 0.40, usdc)
        pay("$0.40 to approved shop   [would hit $1.20 — OVER THE $1 CAP]", shop, 0.40, usdc)
        pay("$0.10 to a STRANGER shop (not approved)", stranger, 0.10, usdc)
        pay("$0.10 to approved shop, but in the WRONG coin", shop, 0.10, other_coin)

        print("-" * 64)
        print("fire drill complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
