from rest_framework import serializers

from economy.models import lc_display

from .models import Bid, ClubDeal, Contract, ManagerProfile, Player

# Hidden mental attributes + talent_type are intentionally left off the
# public serializer per the design doc -- managers/club owners scout based
# on visible attributes only.
PUBLIC_FIELDS = [
    "id", "name", "sport", "age", "height_cm", "weight_kg", "country",
    "agility", "strength", "speed", "acceleration", "jump", "stamina",
    "injury_resistance", "flexibility",
    "finishing", "passing", "dribbling", "first_touch", "crossing",
    "tackling", "marking", "positioning", "off_the_ball", "vision",
    "is_free_agent",
]


class PlayerPublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Player
        fields = PUBLIC_FIELDS


class PlayerOwnedSerializer(serializers.ModelSerializer):
    """Fuller view for a manager looking at their own roster -- still hides talent_type."""

    class Meta:
        model = Player
        fields = PUBLIC_FIELDS + [
            "aggression", "bravery", "composure", "work_rate", "team_spirit", "influence",
        ]


class ManagerProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = ManagerProfile
        fields = ["id", "username", "kc_balance", "kc_balance_display"]

    kc_balance_display = serializers.SerializerMethodField()

    def get_kc_balance_display(self, obj):
        return lc_display(obj.kc_balance)


class BidSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bid
        fields = ["id", "player", "wage_offer", "wage_offer_display", "contract_length_years", "status", "created_at", "expires_at"]

    wage_offer_display = serializers.SerializerMethodField()

    def get_wage_offer_display(self, obj):
        return lc_display(obj.wage_offer)
        read_only_fields = ["status", "created_at", "expires_at"]


class ContractSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contract
        fields = ["id", "player", "wage", "length_years", "start_date", "end_date", "is_active"]


class ClubDealSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClubDeal
        fields = [
            "id", "club", "manager", "player", "monthly_fee", "signing_bonus",
            "length_years", "start_date", "is_active",
        ]
