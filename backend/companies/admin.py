from django.contrib import admin

from .models import Company, Employee, ShareHolding, ShareTransferOffer


class ShareHoldingInline(admin.TabularInline):
    model = ShareHolding
    extra = 0


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display  = ("name", "company_type", "ceo", "kc_balance", "is_active", "created_at")
    list_filter   = ("company_type", "is_active")
    search_fields = ("name", "ceo__username")
    inlines       = [ShareHoldingInline]


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("company", "worker_type", "monthly_wage_lc", "hired_at", "fired_at", "current_project")
    list_filter  = ("worker_type", "company")


@admin.register(ShareTransferOffer)
class ShareTransferOfferAdmin(admin.ModelAdmin):
    list_display = ("company", "from_holder", "to_user", "percent", "status", "expires_at")
    list_filter  = ("status",)
