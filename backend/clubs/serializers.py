from rest_framework import serializers

from .models import Club, ConstructionProject, Facility, Season, SeasonRegistration, SportLicense


class FacilitySerializer(serializers.ModelSerializer):
    facility_type_display = serializers.CharField(source="get_facility_type_display", read_only=True)
    is_usable = serializers.BooleanField(read_only=True)

    class Meta:
        model  = Facility
        fields = ["id", "facility_type", "facility_type_display", "level", "is_usable"]


class ConstructionProjectSerializer(serializers.ModelSerializer):
    facility_type = serializers.CharField(source="facility.facility_type", read_only=True)

    class Meta:
        model  = ConstructionProject
        fields = ["id", "facility", "facility_type", "from_level", "to_level", "status",
                  "started_at", "ends_at", "cost_kc", "required_workers",
                  "required_guards", "is_major"]


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
    facilities    = FacilitySerializer(many=True, read_only=True)
    sport_licenses = SportLicenseSerializer(many=True, read_only=True)

    class Meta:
        model  = Club
        fields = ["id", "name", "country", "city", "kc_balance", "facilities", "sport_licenses"]


class SeasonSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Season
        fields = ["id", "name", "sport", "status", "start_date", "end_date"]
