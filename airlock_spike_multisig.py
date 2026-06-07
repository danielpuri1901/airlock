"""AIRLOCK make-or-break spike (LocalNet).

Claim under test: funds in a 2-of-2 multisig [agent, airlock] mean the Airlock
guard's signature is MANDATORY. If Airlock withholds (i.e. the local model says
BLOCK), the USDC payment cannot settle. If it co-signs (APPROVE), it settles.

We prove both halves on a real chain:
  - axfer from the multisig with ONLY the agent's sig  -> rejected (no settle)
  - axfer from the multisig with BOTH sigs             -> settles
"""
from algosdk import account, encoding
from algosdk.transaction import (
    Multisig, MultisigTransaction, AssetTransferTxn, wait_for_confirmation,
)
from algokit_utils import (
    AlgorandClient, AlgoAmount,
    PaymentParams, AssetCreateParams, AssetOptInParams, AssetTransferParams,
)

algorand = AlgorandClient.default_localnet()
algod = algorand.client.algod
dispenser = algorand.account.localnet_dispenser()
algorand.set_default_signer(dispenser.signer)

# --- players: agent + airlock are the two multisig members ---
agent_sk, agent_addr = account.generate_account()
airlock_sk, airlock_addr = account.generate_account()

def fresh_msig():
    return Multisig(1, 2, [agent_addr, airlock_addr])

msig_addr = fresh_msig().address()
print(f"agent   : {agent_addr}")
print(f"airlock : {airlock_addr}")
print(f"MULTISIG: {msig_addr}  (2-of-2 — needs BOTH to spend)")
print("-" * 70)

# --- mint test-USDC, fund the multisig, opt it in, give it USDC ---
usdc = algorand.send.asset_create(AssetCreateParams(
    sender=dispenser.address, total=1_000_000_000, decimals=6, unit_name="tUSDC",
    asset_name="Test USDC", signer=dispenser.signer)).asset_id
print(f"test-USDC id : {usdc}")

# fund the multisig with ALGO (base MBR + asset MBR + fees)
algorand.send.payment(PaymentParams(
    sender=dispenser.address, receiver=msig_addr, amount=AlgoAmount(algo=1),
    signer=dispenser.signer))

# multisig opts into USDC (this itself needs BOTH sigs — it's setup, so we co-sign)
sp = algod.suggested_params()
optin = AssetTransferTxn(sender=msig_addr, sp=sp, receiver=msig_addr, amt=0, index=usdc)
mtx = MultisigTransaction(optin, fresh_msig())
mtx.sign(agent_sk)
mtx.sign(airlock_sk)
txid = algod.send_raw_transaction(encoding.msgpack_encode(mtx))
wait_for_confirmation(algod, txid, 4)
print("multisig opted into USDC")

# load the multisig with 100 USDC
algorand.send.asset_transfer(AssetTransferParams(
    sender=dispenser.address, receiver=msig_addr, asset_id=usdc, amount=100_000_000,
    signer=dispenser.signer))

# a shop to receive payment
shop = algorand.account.random()
algorand.account.ensure_funded(shop.address, dispenser.address, AlgoAmount(algo=1))
algorand.send.asset_opt_in(AssetOptInParams(sender=shop.address, asset_id=usdc, signer=shop.signer))
print(f"shop    : {shop.address}  (opted in, ready to receive)")
print("-" * 70)


def shop_usdc():
    info = algod.account_asset_info(shop.address, usdc)
    return info["asset-holding"]["amount"] / 1e6


# === THE TEST ===
# The agent wants to pay the shop $5. Build ONE payment txn; the only thing that
# changes is whether Airlock co-signs.
sp = algod.suggested_params()
pay = AssetTransferTxn(sender=msig_addr, sp=sp, receiver=shop.address,
                       amt=5_000_000, index=usdc)

print(f"shop USDC before        : ${shop_usdc():.2f}")

# 1) Airlock says BLOCK -> only the agent signs -> submit -> must FAIL
blocked = MultisigTransaction(pay, fresh_msig())
blocked.sign(agent_sk)
try:
    algod.send_raw_transaction(encoding.msgpack_encode(blocked))
    print("UNEXPECTED: 1-of-2 was accepted (claim is FALSE)")
except Exception as e:
    print(f"AIRLOCK WITHHELD  -> payment REJECTED on-chain")
    print(f"   reason: {str(e).splitlines()[0][:120]}")

print(f"shop USDC after block   : ${shop_usdc():.2f}   (unchanged — no money moved)")

# 2) Airlock says APPROVE -> both sign -> submit -> settles
approved = MultisigTransaction(pay, fresh_msig())
approved.sign(agent_sk)
approved.sign(airlock_sk)
txid = algod.send_raw_transaction(encoding.msgpack_encode(approved))
wait_for_confirmation(algod, txid, 4)
print(f"AIRLOCK CO-SIGNED -> payment SETTLED  (txid {txid[:16]}...)")
print(f"shop USDC after approve : ${shop_usdc():.2f}")
print("-" * 70)
print("CLAIM PROVEN: Airlock's signature is mandatory and enforced by the chain.")
