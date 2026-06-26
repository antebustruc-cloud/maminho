from django.db import transaction
from rest_framework import serializers
from rest_framework.authtoken.models import Token

from clubs.models import Club
from players.models import ManagerProfile

from .models import User


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    # Only club_owner/manager can self-register; admin accounts are created
    # via createsuperuser or the Django admin.
    role = serializers.ChoiceField(choices=[User.Role.CLUB_OWNER, User.Role.MANAGER])
    club_name = serializers.CharField(required=False, allow_blank=True)
    country = serializers.CharField(required=False, allow_blank=True)
    city = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ["username", "email", "password", "role", "club_name", "country", "city"]

    def validate(self, attrs):
        if attrs["role"] == User.Role.CLUB_OWNER and not attrs.get("club_name"):
            raise serializers.ValidationError("club_name is required when registering as a club owner.")
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        club_name = validated_data.pop("club_name", "")
        country = validated_data.pop("country", "")
        city = validated_data.pop("city", "")
        password = validated_data.pop("password")

        user = User(**validated_data)
        user.set_password(password)
        user.save()

        if user.role == User.Role.CLUB_OWNER:
            Club.objects.create(owner=user, name=club_name, country=country, city=city)
        else:
            ManagerProfile.objects.create(user=user)

        Token.objects.create(user=user)
        return user


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "role"]
