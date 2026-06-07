"""Airlock TestNet setup: create the [agent, airlock] 2-of-2 multisig, fund it
from the existing wallet, and opt the multisig + shop into USDC. Then you fund
the multisig with TestNet USDC from the Circle faucet (the one manual step).

Saves everything to .airlock_testnet.json for the x402 client to use.
"""
import json
import pathlib

from algosdk import account, encoding, mnemonic
from algosdk.v2client import algod
from algosdk.transaction import (
    Multisig, MultisigTransaction, AssetTransferTxn, PaymentTxn, wait_for_confirmation,
)

USDC_TESTNET = 10458941
ALGOD = algod.AlgodClient("", "https://testnet-api.algonode.cloud",
                          headers={"User-Agent": "airlock/1.0"})
HERE = pathlib.Path(__file__).parent
CONFIG = HERE / ".airlock_testnet.json"


def deployer_key():
    for line in (HERE / ".env.deploy").read_text().splitlines():
        if line.startswith("DEPLOYER_MNEMONIC="):
            return mnemonic.to_private_key(line.split("=", 1)[1].strip().strip('"').strip())
    raise SystemExit("DEPLOYER_MNEMONIC not found in .env.deploy")


def send(txn, sk):
    txid = ALGOD.send_transaction(txn.sign(sk))
    wait_for_confirmation(ALGOD, txid, 6)
    return txid


def send_msig(txn, msig, *sks):
    mtx = MultisigTransaction(txn, msig)
    for sk in sks:
        mtx.sign(sk)
    txid = ALGOD.send_raw_transaction(encoding.msgpack_encode(mtx))
    wait_for_confirmation(ALGOD, txid, 6)
    return txid


def main():
    deployer_sk = deployer_key()
    deployer_addr = account.address_from_private_key(deployer_sk)
    bal = ALGOD.account_info(deployer_addr)["amount"] / 1e6
    print(f"funder: {deployer_addr}  ({bal:.2f} ALGO)")

    agent_sk, agent_addr = account.generate_account()
    airlock_sk, airlock_addr = account.generate_account()
    shop_sk, shop_addr = account.generate_account()
    msig = Multisig(1, 2, [agent_addr, airlock_addr])
    msig_addr = msig.address()
    print(f"agent  : {agent_addr}\nairlock: {airlock_addr}")
    print(f"MULTISIG (payer): {msig_addr}")
    print(f"shop (payTo)    : {shop_addr}")

    sp = ALGOD.suggested_params()
    print("funding multisig + shop with ALGO ...")
    send(PaymentTxn(deployer_addr, sp, msig_addr, 500_000), deployer_sk)  # 0.5 ALGO
    send(PaymentTxn(deployer_addr, sp, shop_addr, 300_000), deployer_sk)  # 0.3 ALGO

    print("opting multisig + shop into USDC ...")
    sp = ALGOD.suggested_params()
    send_msig(AssetTransferTxn(msig_addr, sp, msig_addr, 0, USDC_TESTNET), msig, agent_sk, airlock_sk)
    send(AssetTransferTxn(shop_addr, sp, shop_addr, 0, USDC_TESTNET), shop_sk)

    cfg = {
        "network_caip2": "algorand:SGO1GKSzyE7IEPItTxCByw9x8FmnrCDexi9/cOUJOiI=",
        "algod": "https://testnet-api.algonode.cloud",
        "usdc_id": USDC_TESTNET,
        "agent_sk": agent_sk, "agent_addr": agent_addr,
        "airlock_sk": airlock_sk, "airlock_addr": airlock_addr,
        "msig_addr": msig_addr,
        "shop_sk": shop_sk, "shop_addr": shop_addr,
    }
    CONFIG.write_text(json.dumps(cfg, indent=2))
    print("-" * 72)
    print(f"saved -> {CONFIG.name}")
    print("\n>>> ONE MANUAL STEP: fund the MULTISIG with TestNet USDC")
    print("    faucet.circle.com -> Algorand TestNet -> paste this address:")
    print(f"    {msig_addr}")
    print("    (get ~$1-2 USDC; that's plenty for the demo)")
    print(f"\n    verify with: explorer / lora.algokit.io/testnet/account/{msig_addr}")


if __name__ == "__main__":
    main()
