from algopy import (
    ARC4Contract,
    Account,
    BoxMap,
    Global,
    Txn,
    UInt64,
    gtxn,
)
from algopy.arc4 import abimethod

# USDC asset IDs per network — the owner picks the right one via set_usdc():
#   TestNet USDC = 10458941   ·   MainNet USDC = 31566704
#   LocalNet: we mint our own test-USDC and pass its id.
USDC_TESTNET_ASA_ID = 10458941


class PolicyGuard(ARC4Contract):
    """The on-chain spending rulebook for x402 agent payments.

    Every payment bundles a call to `enforce` right next to its USDC transfer.
    The blockchain runs `enforce`; if any check fails, the WHOLE bundle is
    rejected, so the payment cannot settle. Only the owner (whoever deployed
    this contract) can change the rules.
    """

    def __init__(self) -> None:
        # Which coin counts as "USDC" — the owner sets this per network (set_usdc).
        self.usdc_id = UInt64(0)
        # How much each payer has spent so far (USDC base units).
        self.spent = BoxMap(Account, UInt64, key_prefix="spent_")
        # Each payer's cap (USDC base units). Default 0 => blocked until the owner sets one.
        self.cap = BoxMap(Account, UInt64, key_prefix="cap_")
        # The allow-list of payees. If an address is in here, it's allowed.
        self.allowed = BoxMap(Account, UInt64, key_prefix="allow_")

    # ---------- owner-only: set the rules ----------
    @abimethod
    def set_usdc(self, usdc_id: UInt64) -> None:
        assert Txn.sender == Global.creator_address, "only the owner can set the coin"
        self.usdc_id = usdc_id

    @abimethod
    def set_cap(self, payer: Account, cap: UInt64) -> None:
        assert Txn.sender == Global.creator_address, "only the owner can set the cap"
        self.cap[payer] = cap

    @abimethod
    def allow_payee(self, payee: Account) -> None:
        assert Txn.sender == Global.creator_address, "only the owner can edit the allow-list"
        self.allowed[payee] = UInt64(1)

    # ---------- the gate: runs on EVERY payment ----------
    @abimethod
    def enforce(self, xfer: gtxn.AssetTransferTransaction) -> None:
        # 1) It must be the coin the owner approved (our USDC).
        assert xfer.xfer_asset.id == self.usdc_id, "wrong coin"
        payer = xfer.sender
        payee = xfer.asset_receiver
        amount = xfer.asset_amount
        # 2) The recipient must be on the owner's allow-list.
        assert payee in self.allowed, "payee is not allow-listed"
        # 3) This payment must keep the payer under their cap.
        prior = self.spent.get(payer, default=UInt64(0))
        cap = self.cap.get(payer, default=UInt64(0))
        assert prior + amount <= cap, "over the spending cap"
        # Record the spend. This only sticks if the whole bundle commits.
        self.spent[payer] = prior + amount
