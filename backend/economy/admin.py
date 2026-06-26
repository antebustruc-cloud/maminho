from django.contrib import admin

from .models import Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("created_at", "kind", "from_user", "to_user", "amount")
    list_filter = ("kind",)
    search_fields = ("from_user__username", "to_user__username", "description")
    readonly_fields = [f.name for f in Transaction._meta.fields]
    ordering = ("-created_at",)
