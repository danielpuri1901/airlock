"""Live demo on LocalNet: fire good + bad payments at the deployed PolicyGuard.

Each payment is a BUNDLE [USDC transfer + our enforce() check] submitted together.
The chain runs enforce(); if it fails, the whole bundle is rejected -> no payment.
"""
import json
from algosdk.encoding import decode_address
from algokit_utils import (
    AlgorandClient, AlgoAmount,
    AssetOptInParams, AssetTransferParams, AppClientMethodCallParams,
)

d = json.load(open(".deploy.json"))
APP, USDC = d["app_id"], d["usdc_id"]

algorand = AlgorandClient.default_localnet()
deployer = algorand.account.localnet_dispenser()
algorand.set_default_signer(deployer.signer)

app = algorand.client.get_app_client_by_id(
    app_spec=open("smart_contracts/policy_guard/PolicyGuard.arc56.json").read(),
    app_id=APP, default_sender=deployer.address, default_signer=deployer.signer)

def box(prefix, addr):
    return prefix + decode_address(addr)

# players
agent = algorand.account.random()
shop = algorand.account.random()
stranger = algorand.account.random()
for acct in (agent, shop, stranger):
    algorand.account.ensure_funded(acct.address, deployer.address, AlgoAmount(algo=5))
for acct in (agent, shop, stranger):                       # all opt in to hold USDC
    algorand.send.asset_opt_in(AssetOptInParams(sender=acct.address, asset_id=USDC, signer=acct.signer))
algorand.send.asset_transfer(AssetTransferParams(
    sender=deployer.address, receiver=agent.address, asset_id=USDC, amount=10_000_000))

# owner sets the rules
app.send.call(AppClientMethodCallParams(method="set_cap", args=[agent.address, 1_000_000],
                                        box_references=[box(b"cap_", agent.address)]))
app.send.call(AppClientMethodCallParams(method="allow_payee", args=[shop.address],
                                        box_references=[box(b"allow_", shop.address)]))
print("RULES:  $1.00 cap for the agent  .  the shop is approved")
print("-" * 64)

def pay(i, label, payee, dollars):
    units = int(dollars * 1_000_000)
    refs = [box(b"cap_", agent.address), box(b"spent_", agent.address), box(b"allow_", payee)]
    try:
        app.send.call(AppClientMethodCallParams(
            method="enforce",
            args=[AssetTransferParams(sender=agent.address, receiver=payee, asset_id=USDC,
                                      amount=units, signer=agent.signer, note=f"pay{i}".encode())],
            sender=agent.address, signer=agent.signer, box_references=refs,
            note=f"enforce{i}".encode()))
        print(f"  ALLOWED  {label}")
    except Exception as e:
        print(f"  BLOCKED  {label}\n             -> {str(e).splitlines()[0][:150]}")

pay(1, "$0.40 to approved shop", shop.address, 0.40)
pay(2, "$0.40 to approved shop   [running total $0.80]", shop.address, 0.40)
pay(3, "$0.40 to approved shop   [would hit $1.20 - OVER CAP]", shop.address, 0.40)
pay(4, "$0.10 to a STRANGER shop (not approved)", stranger.address, 0.10)
print("-" * 64)
print("demo complete.")
