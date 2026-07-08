from django.urls import path

from .views import (
    AcceptShareOfferView,
    CompanyDetailView,
    CompanyListView,
    CreateShareOfferView,
    DeclineShareOfferView,
    FireEmployeeView,
    FoundCompanyView,
    FoundingFeesView,
    HireEmployeesView,
    MyCompanyView,
    MyShareOffersView,
    PayDividendView,
)

urlpatterns = [
    path("found/",                    FoundCompanyView.as_view(),   name="found-company"),
    path("founding-fees/",            FoundingFeesView.as_view(),   name="founding-fees"),
    path("mine/",                     MyCompanyView.as_view(),      name="my-company"),
    path("",                          CompanyListView.as_view(),    name="company-list"),
    path("<int:pk>/",                 CompanyDetailView.as_view(),  name="company-detail"),
    path("<int:company_id>/hire/",    HireEmployeesView.as_view(),  name="hire-employees"),
    path("<int:company_id>/employees/<int:employee_id>/fire/", FireEmployeeView.as_view(), name="fire-employee"),
    path("<int:company_id>/dividend/", PayDividendView.as_view(),   name="pay-dividend"),
    path("<int:company_id>/share-offers/", CreateShareOfferView.as_view(), name="create-share-offer"),
    path("share-offers/mine/",        MyShareOffersView.as_view(),  name="my-share-offers"),
    path("share-offers/<int:offer_id>/accept/",  AcceptShareOfferView.as_view(),  name="accept-share-offer"),
    path("share-offers/<int:offer_id>/decline/", DeclineShareOfferView.as_view(), name="decline-share-offer"),
]
