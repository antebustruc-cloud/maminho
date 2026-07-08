from rest_framework import serializers

from economy.models import lc_display

from .models import Company, Employee, ShareHolding, ShareTransferOffer


class ShareHoldingSerializer(serializers.ModelSerializer):
    holder_username = serializers.CharField(source="holder.username", read_only=True)

    class Meta:
        model  = ShareHolding
        fields = ["holder", "holder_username", "percent"]


class CompanySerializer(serializers.ModelSerializer):
    ceo_username       = serializers.CharField(source="ceo.username", read_only=True)
    kc_balance_display = serializers.SerializerMethodField()
    holdings           = ShareHoldingSerializer(many=True, read_only=True)
    active_employees   = serializers.SerializerMethodField()
    free_employees     = serializers.SerializerMethodField()

    class Meta:
        model  = Company
        fields = ["id", "name", "company_type", "ceo", "ceo_username", "kc_balance",
                  "kc_balance_display", "is_active", "created_at", "holdings",
                  "active_employees", "free_employees"]

    def get_kc_balance_display(self, obj):
        return lc_display(obj.kc_balance)

    def get_active_employees(self, obj):
        return obj.employees.filter(fired_at__isnull=True).count()

    def get_free_employees(self, obj):
        return obj.free_employees().count()


class CompanyListSerializer(serializers.ModelSerializer):
    """Slim listing used when picking companies for contracts."""
    free_employees = serializers.SerializerMethodField()

    class Meta:
        model  = Company
        fields = ["id", "name", "company_type", "is_active", "free_employees"]

    def get_free_employees(self, obj):
        return obj.free_employees().count()


class EmployeeSerializer(serializers.ModelSerializer):
    monthly_wage_display = serializers.SerializerMethodField()

    class Meta:
        model  = Employee
        fields = ["id", "worker_type", "monthly_wage_lc", "monthly_wage_display",
                  "hired_at", "fired_at", "current_project"]

    def get_monthly_wage_display(self, obj):
        return lc_display(obj.monthly_wage_lc)


class ShareTransferOfferSerializer(serializers.ModelSerializer):
    from_username = serializers.CharField(source="from_holder.username", read_only=True)
    to_username   = serializers.CharField(source="to_user.username", read_only=True)
    company_name  = serializers.CharField(source="company.name", read_only=True)

    class Meta:
        model  = ShareTransferOffer
        fields = ["id", "company", "company_name", "from_holder", "from_username",
                  "to_user", "to_username", "percent", "status", "created_at",
                  "expires_at", "resolved_at"]
