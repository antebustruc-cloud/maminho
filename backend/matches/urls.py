from django.urls import path

from .views import FixtureDetailView, FixtureListView, LeagueTableView, SimulateFixtureView

urlpatterns = [
    path("",                              FixtureListView.as_view(),    name="fixture-list"),
    path("<int:pk>/",                     FixtureDetailView.as_view(),  name="fixture-detail"),
    path("<int:fixture_id>/simulate/",    SimulateFixtureView.as_view(), name="simulate-fixture"),
    path("standings/",                    LeagueTableView.as_view(),    name="league-table"),
]
