from django.urls import path

from .views import (
    BuildFacilityView,
    CurrentSeasonView,
    MyClubView,
    PurchaseSportLicenseView,
    UpgradeFacilityView,
)

urlpatterns = [
    path("me/",                              MyClubView.as_view(),             name="my-club"),
    path("facilities/build/",               BuildFacilityView.as_view(),      name="build-facility"),
    path("facilities/<int:facility_id>/upgrade/", UpgradeFacilityView.as_view(), name="upgrade-facility"),
    path("licenses/purchase/",              PurchaseSportLicenseView.as_view(), name="purchase-license"),
    path("season/",                         CurrentSeasonView.as_view(),       name="current-season"),
]
