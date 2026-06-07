"""AIRLOCK phone — the air-gapped guard. Mic + speaker only; no network.

Run this in one terminal (ideally on the phone; here it stands in on the laptop).
It listens for payment requests over sound, judges the intent with the on-device
model, and chirps back a 64-byte signature ONLY for clean payments.
"""
from airlock_sound import listen, play, phone_guard, request_decode


def main():
    print("AIRLOCK phone — air-gapped guard (mic + speaker only).")
    print("Put me in airplane mode; I never touch a network. Listening...\n")
    while True:
        req = listen(timeout_s=3600)
        if req is None:
            continue
        try:
            payee, amount, _, _, intent = request_decode(req.decode())
        except Exception:
            continue  # not a payment request
        print(f"heard a payment request: {amount} USDC-units -> {payee[:10]}...")
        print(f"  intent: {intent!r}")
        sig, verdict, score = phone_guard(req)
        print(f"  on-device verdict: {verdict}  ({score:.2f})")
        if sig is None:
            print("  BLOCKED — withholding signature. The payment cannot settle.\n")
        else:
            print("  APPROVED — chirping the 64-byte signature back...\n")
            play(sig)


if __name__ == "__main__":
    main()
