from rest_framework import generics, permissions, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from economy.models import InsufficientFundsError, Transaction, move_kc

from .models import Club, Facility, Season, SportLicense
from .serializers import ClubSerializer, SeasonSerializer


class IsClubOwner(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == User.Role.CLUB_OWNER


class MyClubView(generics.RetrieveAPIView):
    permission_classes = [IsClubOwner]
    serializer_class   = ClubSerializer

    def get_object(self):
        return self.request.user.club


class BuildFacilityView(APIView):
    permission_classes = [IsClubOwner]

    def post(self, request):
        club = request.user.club
        facility_type = request.data.get("facility_type")
        if facility_type not in Facility.FacilityType.values:
            raise ValidationError("Unknown facility_type.")
        if not Season.is_offseason():
            raise ValidationError("Cannot build facilities during an active season.")
        if club.facilities.filter(facility_type=facility_type).exists():
            raise ValidationError("Club already has this facility.")

        build_cost, _ = Facility.COSTS[facility_type]
        try:
            move_kc(from_holder=club, to_holder=None, amount=build_cost,
                     kind=Transaction.Kind.FACILITY_BUILD,
                     description=f"Built {facility_type}")
        except InsufficientFundsError as exc:
            raise ValidationError(str(exc))

        facility = Facility.objects.create(club=club, facility_type=facility_type, level=1)
        return Response({"id": facility.id, "facility_type": facility_type, "level": 1},
                        status=status.HTTP_201_CREATED)


class UpgradeFacilityView(APIView):
    permission_classes = [IsClubOwner]

    def post(self, request, facility_id):
        if not Season.is_offseason():
            raise ValidationError("Cannot upgrade facilities during an active season.")
        facility = Facility.objects.filter(id=facility_id, club=request.user.club).first()
        if not facility:
            raise PermissionDenied("Not your facility.")
        if facility.level >= 10:
            raise ValidationError("Facility already at max level (10).")

        cost = facility.upgrade_cost()
        try:
            move_kc(from_holder=facility.club, to_holder=None, amount=cost,
                     kind=Transaction.Kind.FACILITY_UPGRADE,
                     description=f"Upgraded {facility.facility_type} to level {facility.level + 1}")
        except InsufficientFundsError as exc:
            raise ValidationError(str(exc))

        facility.level += 1
        facility.full_clean()
        facility.save(update_fields=["level"])
        return Response({"id": facility.id, "level": facility.level})


class PurchaseSportLicenseView(APIView):
    permission_classes = [IsClubOwner]

    def post(self, request):
        club = request.user.club
        sport = request.data.get("sport")
        if sport not in SportLicense.Sport.values:
            raise ValidationError("Unknown sport.")
        if club.sport_licenses.filter(sport=sport).exists():
            raise ValidationError("Club already holds this license.")

        required = SportLicense.REQUIRED_FACILITY[sport]
        if not club.facilities.filter(facility_type=required).exists():
            raise ValidationError(f"Requires a {required} facility first.")

        cost = SportLicense.LICENSE_COSTS[sport]
        try:
            move_kc(from_holder=club, to_holder=None, amount=cost,
                     kind=Transaction.Kind.SPORT_LICENSE,
                     description=f"Purchased {sport} license")
        except InsufficientFundsError as exc:
            raise ValidationError(str(exc))

        lic = SportLicense.objects.create(club=club, sport=sport)
        return Response({"id": lic.id, "sport": sport}, status=status.HTTP_201_CREATED)


class CurrentSeasonView(APIView):
    """Public — anyone can check what season is running."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        sport  = request.query_params.get("sport", "football")
        season = Season.objects.filter(sport=sport, status=Season.Status.ACTIVE).first()
        if not season:
            offseason = Season.objects.filter(sport=sport, status=Season.Status.UPCOMING).order_by("start_date").first()
            if offseason:
                return Response({"status": "offseason", "next_season": SeasonSerializer(offseason).data})
            return Response({"status": "offseason", "next_season": None})
        return Response({"status": "active", "season": SeasonSerializer(season).data})
