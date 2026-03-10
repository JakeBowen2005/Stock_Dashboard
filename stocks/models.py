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