"""De-risk the one tricky step of the Python x402 client:

The client holds the AGENT key only. The Airlock guard (a separate service, and
later the phone) holds the airlock key and returns just a raw 64-byte signature.
So the client must INSERT that raw signature into the 2-of-2 multisig WITHOUT ever
holding the airlock key, and the result must validate on-chain.

This proves that assembly works (and that withholding still blocks).
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

agent_sk, agent_addr = account.generate_account()
airlock_sk, airlock_addr = account.generate_account()
airlock_pk = encoding.decode_address(airlock_addr)
def fresh_msig():
    return Multisig(1, 2, [agent_addr, airlock_addr])
msig_addr = fresh_msig().address()

usdc = algorand.send.asset_create(AssetCreateParams(
    sender=dispenser.address, total=1_000_000_000, decimals=6,
    unit_name="tUSDC", asset_name="Test USDC", signer=dispenser.signer)).asset_id
algorand.send.payment(PaymentParams(sender=dispenser.address, receiver=msig_addr,
                                    amount=AlgoAmount(algo=1), signer=dispenser.signer))
_o = AssetTransferTxn(sender=msig_addr, sp=algod.suggested_params(), receiver=msig_addr, amt=0, index=usdc)
_m = MultisigTransaction(_o, fresh_msig()); _m.sign(agent_sk); _m.sign(airlock_sk)
wait_for_confirmation(algod, algod.send_raw_transaction(encoding.msgpack_encode(_m)), 4)
algorand.send.asset_transfer(AssetTransferParams(sender=dispenser.address, receiver=msig_addr,
                                                 asset_id=usdc, amount=100_000_000, signer=dispenser.signer))
shop = algorand.account.random()
algorand.account.ensure_funded(shop.address, dispenser.address, AlgoAmount(algo=1))
algorand.send.asset_opt_in(AssetOptInParams(sender=shop.address, asset_id=usdc, signer=shop.signer))
def shop_usdc():
    return algod.account_asset_info(shop.address, usdc)["asset-holding"]["amount"] / 1e6


def insert_airlock_sig(mtx, raw_sig):
    """Client inserts the guard's raw signature — without the airlock key."""
    for ss in mtx.multisig.subsigs:
        if ss.public_key == airlock_pk:
            ss.signature = raw_sig
    return mtx


pay = AssetTransferTxn(sender=msig_addr, sp=algod.suggested_params(),
                       receiver=shop.address, amt=3_000_000, index=usdc)
print(f"shop USDC before: ${shop_usdc():.2f}")

# what the guard returns on APPROVE (it has the key; client never sees it):
guard_raw_sig = pay.raw_sign(airlock_sk)

# CLIENT side: agent signs, then inserts the guard's raw sig (no airlock key here)
mtx = MultisigTransaction(pay, fresh_msig())
mtx.sign(agent_sk)
mtx = insert_airlock_sig(mtx, guard_raw_sig)
txid = algod.send_raw_transaction(encoding.msgpack_encode(mtx))
wait_for_confirmation(algod, txid, 4)
print(f"INSERTED guard sig (no key on client) -> SETTLED  (tx {txid[:14]}...)")
print(f"shop USDC after:  ${shop_usdc():.2f}")

# and confirm: agent alone (guard withheld) still fails
agent_only = MultisigTransaction(pay, fresh_msig())
agent_only.sign(agent_sk)
try:
    algod.send_raw_transaction(encoding.msgpack_encode(agent_only))
    print("UNEXPECTED: agent-only accepted")
except Exception as e:
    print(f"guard WITHHELD -> rejected ({str(e).splitlines()[0][:60]})")
print("-" * 60 + "\nClient-side assembly proven: raw-sig insertion validates on-chain.")
