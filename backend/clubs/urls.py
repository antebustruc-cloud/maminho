from django.urls import path

from .views import (
    BuildFacilityView,
    CurrentSeasonView,
    FacilityLevelConfigView,
    MyClubView,
    MyConstructionProjectsView,
    PurchaseSportLicenseView,
    RegisterForSeasonView,
    SeasonRegistrationsView,
    StartConstructionView,
    UpgradeFacilityView,
)

urlpatterns = [
    path("me/",                              MyClubView.as_view(),             name="my-club"),
    path("facilities/build/",               BuildFacilityView.as_view(),      name="build-facility"),
    path("facilities/<int:facility_id>/upgrade/", UpgradeFacilityView.as_view(), name="upgrade-facility"),
    path("facilities/level-config/",        FacilityLevelConfigView.as_view(), name="facility-level-config"),
    path("facilities/construction/start/",  StartConstructionView.as_view(),  name="start-construction"),
    path("facilities/construction/",        MyConstructionProjectsView.as_view(), name="my-construction-projects"),
    path("licenses/purchase/",              PurchaseSportLicenseView.as_view(), name="purchase-license"),
    path("season/",                         CurrentSeasonView.as_view(),       name="current-season"),
    path("seasons/<int:season_id>/register/",      RegisterForSeasonView.as_view(),   name="register-for-season"),
    path("seasons/<int:season_id>/registrations/", SeasonRegistrationsView.as_view(), name="season-registrations"),
]
