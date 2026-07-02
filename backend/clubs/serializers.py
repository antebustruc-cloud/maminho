from rest_framework import serializers

from .models import Club, Facility, Season, SportLicense


class FacilitySerializer(serializers.ModelSerializer):
    facility_type_display = serializers.CharField(source="get_facility_type_display", read_only=True)

    class Meta:
        model  = Facility
        fields = ["id", "facility_type", "facility_type_display", "level"]


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
