from django.contrib import admin

from .models import WatchList, WatchListItem

@admin.register(WatchList)
class WatchListAdmin(admin.ModelAdmin):
    list_display = ("user", "created_at", "updated_at")
    search_fields = ("user__username", "user__email")


@admin.register(WatchListItem)
class WatchListItemAdmin(admin.ModelAdmin):
    list_display = ("watchlist", "ticker", "created_at")
    search_fields = ("ticker", "watchlist__user__username")
    list_filter = ("created_at",)
