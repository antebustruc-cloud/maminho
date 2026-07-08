from rest_framework import serializers

from economy.models import lc_display

from .models import Club, ConstructionProject, Facility, Season, SeasonRegistration, SportLicense


class FacilitySerializer(serializers.ModelSerializer):
    facility_type_display = serializers.CharField(source="get_facility_type_display", read_only=True)
    is_usable = serializers.BooleanField(read_only=True)

    class Meta:
        model  = Facility
        fields = ["id", "facility_type", "facility_type_display", "level", "is_usable"]


class ConstructionProjectSerializer(serializers.ModelSerializer):
    facility_type = serializers.CharField(source="facility.facility_type", read_only=True)
    construction_price_display = serializers.SerializerMethodField()
    security_price_display     = serializers.SerializerMethodField()

    class Meta:
        model  = ConstructionProject
        fields = ["id", "facility", "facility_type", "from_level", "to_level", "status",
                  "started_at", "ends_at", "cost_kc", "required_workers",
                  "required_guards", "is_major", "construction_company",
                  "security_company", "construction_price_lc", "security_price_lc",
                  "construction_price_display", "security_price_display"]

    def get_construction_price_display(self, obj):
        return lc_display(obj.construction_price_lc)

    def get_security_price_display(self, obj):
        return lc_display(obj.security_price_lc)


class SeasonRegistrationSerializer(serializers.ModelSerializer):
    club_name = serializers.CharField(source="club.name", read_only=True)

    class Meta:
        model  = SeasonRegistration
        fields = ["id", "club", "club_name", "season", "sport", "registered_at"]


class SportLicenseSerializer(serializers.ModelSerializer):
    sport_display = serializers.CharField(source="get_sport_display", read_only=True)

    class Meta:
        model  = SportLicense
        fields = ["id", "sport", "sport_display", "purchased_at"]


class ClubSerializer(serializers.ModelSerializer):
    kc_balance_display = serializers.SerializerMethodField()

    def get_kc_balance_display(self, obj):
        return lc_display(obj.kc_balance)
    facilities    = FacilitySerializer(many=True, read_only=True)
    sport_licenses = SportLicenseSerializer(many=True, read_only=True)

    class Meta:
        model  = Club
        fields = ["id", "name", "country", "city", "kc_balance", "facilities", "sport_licenses", "kc_balance_display"]


class SeasonSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Season
        fields = ["id", "name", "sport", "status", "start_date", "end_date"]
