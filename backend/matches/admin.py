from django.contrib import admin

from .models import Fixture, LeagueStanding, MatchEvent


class MatchEventInline(admin.TabularInline):
    model     = MatchEvent
    extra     = 0
    readonly_fields = ("minute", "event_type", "club", "description")


@admin.register(Fixture)
class FixtureAdmin(admin.ModelAdmin):
    list_display   = ("__str__", "season", "scheduled_at", "status", "home_score", "away_score")
    list_filter    = ("status", "season")
    list_editable  = ("status",)
    inlines        = [MatchEventInline]
    actions        = ["simulate_selected"]

    def simulate_selected(self, request, queryset):
        from .simulation import simulate_fixture
        done = 0
        for fixture in queryset.filter(status__in=["scheduled", "in_progress"]):
            simulate_fixture(fixture)
            done += 1
        self.message_user(request, f"Simulated {done} fixture(s).")
    simulate_selected.short_description = "Simulate selected fixtures"


@admin.register(LeagueStanding)
class LeagueStandingAdmin(admin.ModelAdmin):
    list_display = ("club", "season", "played", "won", "drawn", "lost", "gf", "ga", "points")
    list_filter  = ("season",)
