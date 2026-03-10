import base64
import json
import os

from pywebpush import WebPushException, webpush


def _vapid_private_key():
    raw = os.getenv("VAPID_PRIVATE_KEY", "")
    if not raw:
        return None
    # The key is stored as base64-encoded PEM
    return base64.b64decode(raw).decode("utf-8")


def send_push(subscription, title, body, url="/"):
    """Send a Web Push notification to a single PushSubscription model instance."""
    private_key = _vapid_private_key()
    if not private_key:
        return False
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
        return True
    except WebPushException as exc:
        print(f"[push] failed: {exc}")
        return False


def send_push_to_user(user, title, body, url="/"):
    """Send a push notification to all subscriptions for a user."""
    from .models import PushSubscription
    dead = []
    for sub in PushSubscription.objects.filter(user=user):
        ok = send_push(sub, title, body, url)
        if not ok:
            dead.append(sub.pk)
    if dead:
        PushSubscription.objects.filter(pk__in=dead).delete()
