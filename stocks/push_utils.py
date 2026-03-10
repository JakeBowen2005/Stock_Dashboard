import json
import os

from pywebpush import WebPushException, webpush


def _vapid_private_key():
    """
    Return VAPID private key for pywebpush.
    Supports PEM strings, base64-encoded PEM, and raw base64url DER.
    pywebpush accepts PEM directly when the string contains '-----'.
    """
    import base64
    raw = os.getenv("VAPID_PRIVATE_KEY", "").strip()
    if not raw:
        return None

    # If it looks like base64-encoded PEM, decode it first.
    if not raw.startswith("-----"):
        try:
            decoded = base64.b64decode(raw + "==").decode("utf-8")
            if "-----" in decoded:
                return decoded.strip()
        except Exception:
            pass

    # Return PEM as-is (pywebpush handles it natively) or raw base64url DER.
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
    dead = []
    for sub in PushSubscription.objects.filter(user=user):
        outcome = send_push(sub, title, body, url)
        if outcome == "delete":
            dead.append(sub.pk)
    if dead:
        PushSubscription.objects.filter(pk__in=dead).delete()
