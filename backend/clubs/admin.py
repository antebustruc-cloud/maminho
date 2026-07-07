from django.contrib import admin

from .models import Club, ConstructionProject, Facility, Season, SeasonRegistration, SportLicense


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
    actions = ["generate_fixtures"]

    def generate_fixtures(self, request, queryset):
        from matches.fixtures import generate_round_robin_fixtures
        for season in queryset:
            try:
                created = generate_round_robin_fixtures(season)
                self.message_user(request, f"{season.name}: created {created} fixtures "
                                           "from registered clubs.")
            except ValueError as exc:
                self.message_user(request, f"{season.name}: {exc}", level="warning")
    generate_fixtures.short_description = "Generate fixtures (registered clubs only)"


@admin.register(ConstructionProject)
class ConstructionProjectAdmin(admin.ModelAdmin):
    list_display = ("facility", "from_level", "to_level", "status", "is_major",
                    "started_at", "ends_at", "cost_kc")
    list_filter  = ("status", "is_major", "facility__facility_type")


@admin.register(SeasonRegistration)
class SeasonRegistrationAdmin(admin.ModelAdmin):
    list_display = ("club", "season", "sport", "registered_at")
    list_filter  = ("sport", "season")
