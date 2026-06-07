"""Deploy PolicyGuard to LocalNet, mint a test-USDC, and switch the guard on.

Run from policy-guard/:  .venv/bin/python deploy_local.py
Saves the live IDs to .deploy.json for the demo script to use.
"""
import json
from algokit_utils import (
    AlgorandClient,
    AlgoAmount,
    AssetCreateParams,
    PaymentParams,
    AppClientMethodCallParams,
)

# 1) Connect to YOUR local chain + grab the pre-funded account (no faucet!)
algorand = AlgorandClient.default_localnet()
deployer = algorand.account.localnet_dispenser()
algorand.set_default_signer(deployer.signer)
print("deployer       :", deployer.address)

# 2) Mint a local test-USDC (6 decimals, just like real USDC)
res = algorand.send.asset_create(AssetCreateParams(
    sender=deployer.address,
    total=1_000_000_000_000,   # 1,000,000 USDC of supply
    decimals=6,
    unit_name="tUSDC",
    asset_name="Test USDC",
))
usdc_id = getattr(res, "asset_id", None) or res.confirmation["asset-index"]
print("test-USDC id   :", usdc_id)

# 3) Deploy the guard from its compiled spec
app_spec = open("smart_contracts/policy_guard/PolicyGuard.arc56.json").read()
factory = algorand.client.get_app_factory(app_spec=app_spec, default_sender=deployer.address)
deployed = factory.deploy()
app_client = deployed[0] if isinstance(deployed, tuple) else deployed
print("guard app id   :", app_client.app_id)
print("guard app addr :", app_client.app_address)

# 4) Fund the app account so it can store boxes (MBR)
algorand.send.payment(PaymentParams(
    sender=deployer.address,
    receiver=app_client.app_address,
    amount=AlgoAmount(algo=1),
))

# 5) Tell the guard which coin counts as USDC
app_client.send.call(AppClientMethodCallParams(method="set_usdc", args=[usdc_id]))
print("\n✅ PolicyGuard is LIVE on LocalNet — coin set to", usdc_id)

json.dump(
    {
        "app_id": int(app_client.app_id),
        "app_address": str(app_client.app_address),
        "usdc_id": int(usdc_id),
        "deployer": deployer.address,
    },
    open(".deploy.json", "w"),
    indent=2,
)
print("(IDs saved to .deploy.json for the demo)")
