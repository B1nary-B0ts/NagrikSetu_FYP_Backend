from rest_framework import serializers
from users.serializers import UserSerializer
from users.models import User
from .models import (
    MunicipalCorporation,
    Ward,
    MunicipalCorpHead,
    WardHead
)

class MunicipalCorporationHeadSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        source="user",
        queryset=User.objects.filter(role="municipal_corp_head"),
        write_only=True
    )

    class Meta:
        model = MunicipalCorpHead
        fields = ["id", "municipal_corp", "user", "user_id"]

class WardHeadSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        source="user",
        queryset=User.objects.filter(role="ward_head"),
        write_only=True
    )

    class Meta:
        model = WardHead
        fields = ["id", "ward", "user", "user_id"]

class WardSerializer(serializers.ModelSerializer):
    head = WardHeadSerializer(read_only=True)

    class Meta:
        model = Ward
        fields = ["id", "name", "municipal_corp", "geometry", "head"]

class MunicipalCorporationSerializer(serializers.ModelSerializer):
    head = MunicipalCorporationHeadSerializer(read_only=True)
    wards = WardSerializer(many=True, read_only=True)

    class Meta:
        model = MunicipalCorporation
        fields = ["id", "name", "geometry", "head", "wards"]

class LocationResolveSerializer(serializers.Serializer):
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()

class WardLiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ward
        fields = ["id", "name"]

class MunicipalCorpLiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = MunicipalCorporation
        fields = ["id", "name"]
