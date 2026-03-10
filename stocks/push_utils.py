import json
import os

from cryptography.hazmat.primitives import serialization
from pywebpush import WebPushException, webpush


def _vapid_private_key():
    """
    Return VAPID private key as base64url-encoded DER (expected by pywebpush).
    Supports:
    - PEM key
    - base64-encoded PEM key
    - already base64url DER
    """
    import base64
    raw = os.getenv("VAPID_PRIVATE_KEY", "").strip()
    if not raw:
        return None

    maybe_pem = raw
    if "BEGIN" not in raw:
        try:
            decoded = base64.b64decode(raw + "==").decode("utf-8")
            if "BEGIN" in decoded:
                maybe_pem = decoded.strip()
        except Exception:
            pass

    if "BEGIN" in maybe_pem:
        key = serialization.load_pem_private_key(maybe_pem.encode("utf-8"), password=None)
        der_bytes = key.private_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        return base64.urlsafe_b64encode(der_bytes).decode("utf-8").rstrip("=")

    return raw


def send_push(subscription, title, body, url="/"):
    """Send a Web Push notification to a single PushSubscription model instance."""
    private_key = _vapid_private_key()
    if not private_key:
        return "keep"
    try:
        webpush(
            subscription_info={
                "endpoint": subscription.endpoint,
                "keys": {
                    "p256dh": subscription.p256dh,
                    "auth": subscription.auth,
                },
            },
            data=json.dumps({"title": title, "body": body, "url": url}),
            vapid_private_key=private_key,
            vapid_claims={"sub": f"mailto:{os.getenv('VAPID_CONTACT_EMAIL', 'jakeeb05@gmail.com')}"},
        )
        return "ok"
    except WebPushException as exc:
        print(f"[push] failed: {exc}")
        status_code = getattr(getattr(exc, "response", None), "status_code", None)
        if status_code in (404, 410):
            return "delete"
        return "keep"
    except Exception as exc:
        print(f"[push] failed: {exc}")
        return "keep"


def send_push_to_user(user, title, body, url="/"):
    """Send a push notification to all subscriptions for a user."""
    from .models import PushSubscription
    sent_count = 0
    dead = []
    kept = 0

    for sub in PushSubscription.objects.filter(user=user):
        outcome = send_push(sub, title, body, url)
        if outcome == "ok":
            sent_count += 1
        if outcome == "delete":
            dead.append(sub.pk)
        if outcome == "keep":
            kept += 1

    if dead:
        PushSubscription.objects.filter(pk__in=dead).delete()

    return {
        "sent": sent_count,
        "deleted": len(dead),
        "kept_failed": kept,
    }
