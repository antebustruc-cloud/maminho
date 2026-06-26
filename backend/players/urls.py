from django.urls import path

from .views import ClubDealCreateView, FreeAgentListView, ManagerMeView, MyPlayersView, PlaceBidView

urlpatterns = [
    path("manager/me/", ManagerMeView.as_view(), name="manager-me"),
    path("free-agents/", FreeAgentListView.as_view(), name="free-agents"),
    path("mine/", MyPlayersView.as_view(), name="my-players"),
    path("<int:player_id>/bid/", PlaceBidView.as_view(), name="place-bid"),
    path("club-deals/", ClubDealCreateView.as_view(), name="create-club-deal"),
]
