from django.contrib import admin

from .models import Bid, ClubDeal, Contract, ManagerProfile, Player


@admin.register(ManagerProfile)
class ManagerProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "kc_balance")
    search_fields = ("user__username",)


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = (
        "name", "sport", "age", "talent_type", "is_free_agent",
        "current_manager", "current_club",
    )
    list_filter = ("sport", "is_free_agent", "talent_type")
    search_fields = ("name",)
    fieldsets = (
        (None, {"fields": ("name", "sport", "age", "country", "height_cm", "weight_kg")}),
        ("Hidden (admin only)", {"fields": ("talent_type",)}),
        ("Physical", {"fields": (
            "agility", "strength", "speed", "acceleration", "jump",
            "stamina", "injury_resistance", "flexibility",
        )}),
        ("Mental (hidden)", {"fields": (
            "aggression", "bravery", "composure", "work_rate", "team_spirit", "influence",
        )}),
        ("Football", {"fields": (
            "finishing", "passing", "dribbling", "first_touch", "crossing",
            "tackling", "marking", "positioning", "off_the_ball", "vision",
        )}),
        ("Ownership", {"fields": (
            "is_free_agent", "is_starter_player", "current_manager", "current_club",
        )}),
    )


@admin.register(Bid)
class BidAdmin(admin.ModelAdmin):
    list_display = ("player", "manager", "wage_offer", "contract_length_years", "status", "expires_at")
    list_filter = ("status",)


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = ("player", "manager", "wage", "start_date", "end_date", "is_active")
    list_filter = ("is_active",)


@admin.register(ClubDeal)
class ClubDealAdmin(admin.ModelAdmin):
    list_display = ("player", "club", "manager", "monthly_fee", "start_date", "is_active")
    list_filter = ("is_active",)
