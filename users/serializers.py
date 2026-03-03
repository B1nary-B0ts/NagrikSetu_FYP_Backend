from os import set_inheritable
from rest_framework import serializers
from .models import User, Citizen

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id", "name", "email", "phone",
            "role", "is_active", "is_staff"
        ]
        read_only_fields = ["is_active", "is_staff"]

class CitizenSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = Citizen
        fields = ["id", "user"]

class CitizenRegisterSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=10)
    password = serializers.CharField(write_only=True, min_length=8)
    otp = serializers.CharField(max_length=6, required=False)

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already exists")
        return value

    def validate_phone(self, value):
        if User.objects.filter(phone=value).exists():
            raise serializers.ValidationError("Phone already exists")
        return value

class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, min_length=8, required=True)
    