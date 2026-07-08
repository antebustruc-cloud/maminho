from datetime import date

from django.db import transaction
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from economy.models import InsufficientFundsError, Transaction, move_kc

from .models import Bid, ClubDeal, Player
from .serializers import (
    BidSerializer,
    ClubDealSerializer,
    ManagerProfileSerializer,
    PlayerOwnedSerializer,
    PlayerPublicSerializer,
)


class IsManager(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == User.Role.MANAGER


class FreeAgentListView(generics.ListAPIView):
    """Anyone authenticated can browse the free-agent pool to scout."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PlayerPublicSerializer
    queryset = Player.objects.filter(is_free_agent=True).order_by("-id")
    filterset_fields = []

    def get_queryset(self):
        qs = super().get_queryset()
        sport = self.request.query_params.get("sport")
        if sport:
            qs = qs.filter(sport=sport)
        return qs


class ManagerMeView(generics.RetrieveAPIView):
    permission_classes = [IsManager]
    serializer_class = ManagerProfileSerializer

    def get_object(self):
        return self.request.user.manager_profile


class MyPlayersView(generics.ListAPIView):
    """A manager's currently-owned squad."""

    permission_classes = [IsManager]
    serializer_class = PlayerOwnedSerializer

    def get_queryset(self):
        return Player.objects.filter(current_manager=self.request.user.manager_profile)


class PlaceBidView(APIView):
    """
    POST {"wage_offer": 120, "contract_length_years": 2} to /players/<id>/bid/

    Opens a 24h window on the player's first bid; any bid placed while a
    window is open just adds to it (does NOT reset the 24h clock -- this is
    deliberate, so a last-second sniper can't perpetually extend the
    window and lock everyone else out).
    """

    permission_classes = [IsManager]

    @transaction.atomic
    def post(self, request, player_id):
        player = Player.objects.select_for_update().filter(id=player_id, is_free_agent=True).first()
        if not player:
            raise ValidationError("Player is not a free agent (already contracted, or doesn't exist).")

        wage_offer = request.data.get("wage_offer")
        contract_length = request.data.get("contract_length_years")
        if not wage_offer or not contract_length:
            raise ValidationError("wage_offer and contract_length_years are required.")

        manager = request.user.manager_profile
        open_bid = Bid.objects.filter(player=player, status=Bid.Status.OPEN).order_by("created_at").first()

        if open_bid:
            highest = Bid.objects.filter(player=player, status=Bid.Status.OPEN).order_by("-wage_offer").first()
            if int(wage_offer) <= highest.wage_offer:
                raise ValidationError(f"Must beat the current highest bid of {highest.wage_offer} KC.")
            expires_at = open_bid.expires_at
        else:
            expires_at = timezone.now() + timezone.timedelta(hours=24)

        bid = Bid.objects.create(
            player=player, manager=manager, wage_offer=wage_offer,
            contract_length_years=contract_length, expires_at=expires_at,
        )
        return Response(BidSerializer(bid).data, status=status.HTTP_201_CREATED)


class ClubDealCreateView(APIView):
    """
    POST {"player": id, "club": id, "monthly_fee": int, "signing_bonus": int,
    "length_years": int} -- records a manager<->club agreement reached off-platform
    (Discord, for the MVP). Caller must be the manager who owns the player.
    Signing bonus, if any, is paid immediately club -> manager.
    """

    permission_classes = [IsManager]

    @transaction.atomic
    def post(self, request):
        manager = request.user.manager_profile
        player = Player.objects.filter(id=request.data.get("player"), current_manager=manager).first()
        if not player:
            raise PermissionDenied("You don't manage this player.")

        from clubs.models import Club
        club = Club.objects.filter(id=request.data.get("club")).first()
        if not club:
            raise ValidationError("Club not found.")

        from maminho import limits
        if club.squad.count() >= limits.MAX_ROSTER_PER_CLUB:
            raise ValidationError(
                f"{club.name} roster is full (max {limits.MAX_ROSTER_PER_CLUB} players).")

        monthly_fee = request.data.get("monthly_fee")
        signing_bonus = request.data.get("signing_bonus", 0)
        length_years = request.data.get("length_years")
        if not monthly_fee or not length_years:
            raise ValidationError("monthly_fee and length_years are required.")

        if signing_bonus:
            try:
                move_kc(
                    from_holder=club, to_holder=manager, amount=int(signing_bonus),
                    kind=Transaction.Kind.SIGNING_BONUS,
                    description=f"Signing bonus for {player.name}",
                )
            except InsufficientFundsError as exc:
                raise ValidationError(str(exc))

        deal = ClubDeal.objects.create(
            club=club, manager=manager, player=player,
            monthly_fee=monthly_fee, signing_bonus=signing_bonus or 0,
            length_years=length_years, start_date=date.today(),
        )
        player.current_club = club
        player.save(update_fields=["current_club"])

        return Response(ClubDealSerializer(deal).data, status=status.HTTP_201_CREATED)
