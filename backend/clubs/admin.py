from django.contrib import admin

from .models import Club, Facility, Season, SportLicense


class FacilityInline(admin.TabularInline):
    model = Facility
    extra = 0


class SportLicenseInline(admin.TabularInline):
    model = SportLicense
    extra = 0
    readonly_fields = ("purchased_at",)


@admin.register(Club)
class ClubAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "country", "city", "kc_balance")
    search_fields = ("name", "owner__username")
    inlines = [FacilityInline, SportLicenseInline]


@admin.register(Season)
class SeasonAdmin(admin.ModelAdmin):
    list_display = ("name", "sport", "status", "start_date", "end_date")
    list_filter  = ("sport", "status")
    list_editable = ("status",)
