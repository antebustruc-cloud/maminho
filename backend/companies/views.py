from django.db.models import Q
from rest_framework import generics, permissions, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from economy.models import lc_display

from .models import FOUNDING_FEES_LC, Company, Employee, ShareTransferOffer
from .serializers import (
    CompanyListSerializer,
    CompanySerializer,
    EmployeeSerializer,
    ShareTransferOfferSerializer,
)
from .services import (
    accept_share_offer,
    create_share_offer,
    fire_employee,
    found_company,
    hire_employees,
    pay_dividend,
)


def _get_company_or_404(company_id):
    company = Company.objects.filter(id=company_id).first()
    if not company:
        raise ValidationError("Unknown company.")
    return company


class FoundCompanyView(APIView):
    """POST {name, company_type} — manager founds a company (pays fee, becomes
    CEO with 100%)."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        company = found_company(request.user, request.data.get("name"),
                                request.data.get("company_type"))
        return Response(CompanySerializer(company).data, status=status.HTTP_201_CREATED)


class FoundingFeesView(APIView):
    """Read-only founding fee listing per company type."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response({t: {"fee_lc": fee, "fee_display": lc_display(fee)}
                         for t, fee in FOUNDING_FEES_LC.items()})


class CompanyListView(generics.ListAPIView):
    """All companies (filter: ?company_type=construction). Used to pick
    contractors for construction projects."""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class   = CompanyListSerializer

    def get_queryset(self):
        qs = Company.objects.all().order_by("name")
        ctype = self.request.query_params.get("company_type")
        if ctype:
            qs = qs.filter(company_type=ctype)
        return qs


class CompanyDetailView(generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class   = CompanySerializer
    queryset           = Company.objects.all()


class MyCompanyView(APIView):
    """The company the requester is CEO of, with employees."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        company = Company.objects.filter(ceo=request.user).first()
        if not company:
            return Response({"company": None})
        data = CompanySerializer(company).data
        data["employees"] = EmployeeSerializer(
            company.employees.filter(fired_at__isnull=True), many=True).data
        return Response({"company": data})


class HireEmployeesView(APIView):
    """POST {count} — CEO hires N NPC workers instantly."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, company_id):
        company = _get_company_or_404(company_id)
        count, worker_type = hire_employees(company, request.user,
                                            request.data.get("count", 0))
        return Response({"hired": count, "worker_type": worker_type},
                        status=status.HTTP_201_CREATED)


class FireEmployeeView(APIView):
    """POST — CEO fires one employee (only after 1 full month employed)."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, company_id, employee_id):
        company = _get_company_or_404(company_id)
        employee = fire_employee(company, request.user, employee_id)
        return Response(EmployeeSerializer(employee).data)


class PayDividendView(APIView):
    """POST {amount_lc} — CEO splits a payout among holders by percent."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, company_id):
        company = _get_company_or_404(company_id)
        payouts = pay_dividend(company, request.user, request.data.get("amount_lc", 0))
        return Response({"payouts": [
            {"holder": username, "amount_lc": share, "amount_display": lc_display(share)}
            for username, share in payouts
        ]})


class CreateShareOfferView(APIView):
    """POST {to_username, percent} — offer part/all of your holding."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, company_id):
        company = _get_company_or_404(company_id)
        offer = create_share_offer(company, request.user,
                                   request.data.get("to_username"),
                                   request.data.get("percent", 0))
        return Response(ShareTransferOfferSerializer(offer).data,
                        status=status.HTTP_201_CREATED)


class MyShareOffersView(generics.ListAPIView):
    """Offers involving me (made or received)."""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class   = ShareTransferOfferSerializer

    def get_queryset(self):
        return (ShareTransferOffer.objects
                .filter(Q(from_holder=self.request.user) | Q(to_user=self.request.user))
                .order_by("-created_at"))


class AcceptShareOfferView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, offer_id):
        offer = ShareTransferOffer.objects.filter(id=offer_id).first()
        if not offer:
            raise ValidationError("Unknown offer.")
        offer = accept_share_offer(offer, request.user)
        return Response(ShareTransferOfferSerializer(offer).data)


class DeclineShareOfferView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, offer_id):
        from django.utils import timezone
        offer = ShareTransferOffer.objects.filter(id=offer_id).first()
        if not offer:
            raise ValidationError("Unknown offer.")
        if request.user not in (offer.to_user, offer.from_holder):
            raise ValidationError("Not your offer.")
        if offer.status != ShareTransferOffer.Status.PENDING:
            raise ValidationError(f"Offer is {offer.status}.")
        offer.status = (ShareTransferOffer.Status.DECLINED
                        if request.user == offer.to_user
                        else ShareTransferOffer.Status.CANCELLED)
        offer.resolved_at = timezone.now()
        offer.save(update_fields=["status", "resolved_at"])
        return Response(ShareTransferOfferSerializer(offer).data)
