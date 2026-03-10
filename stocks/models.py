from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
# Create your models here.

class WatchList(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL,
                                on_delete=models.CASCADE,
                                related_name="watchlist")
    created_at =  models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Watchlist"


class WatchListItem(models.Model):
    watchlist = models.ForeignKey(WatchList,
                                  on_delete=models.CASCADE,
                                  related_name="items")
    ticker = models.CharField(max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["watchlist", "ticker"],
                name="unique_ticker_per_watchlist"
            )
        ]
        ordering = ["ticker"]

    def save(self, *args, **kwargs):
        self.ticker = self.ticker.strip().upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.watchlist.user.username} - {self.ticker}"


class StockAlert(models.Model):
    PRICE = "price"
    PCT = "pct"
    TYPE_CHOICES = [(PRICE, "Price"), (PCT, "% Change from set price")]

    ABOVE = "above"
    BELOW = "below"
    DIR_CHOICES = [(ABOVE, "Goes above"), (BELOW, "Goes below")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="alerts")
    ticker = models.CharField(max_length=10)
    alert_type = models.CharField(max_length=5, choices=TYPE_CHOICES)
    direction = models.CharField(max_length=5, choices=DIR_CHOICES)
    threshold = models.DecimalField(max_digits=14, decimal_places=4)
    baseline_price = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    triggered = models.BooleanField(default=False)
    rearm_ready = models.BooleanField(default=True)
    last_notified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["ticker", "created_at"]

    def __str__(self):
        return f"{self.user.username} - {self.ticker} {self.direction} {self.threshold}"


class PushSubscription(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="push_subscriptions")
    endpoint = models.TextField(unique=True)
    p256dh = models.TextField()
    auth = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} push sub"
