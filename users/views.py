from django.shortcuts import render
from django.db import transaction
from django.conf import settings
from django.template.context_processors import request
from django.utils.text import phone2numeric
from django.contrib.auth import authenticate
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from rest_framework import status, request, response
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken, BlacklistedToken

from .models import User, Citizen
from .serializers import CitizenRegisterSerializer, UserSerializer, UserLoginSerializer
from .utils.otp import generate_otp, store_otp, verify_otp
from django.core.mail import send_mail

# Create your views here.
class RegisterView(APIView):
    permission_classes = []

    def post(self, request):
        serializer = CitizenRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        email = data["email"]

        if "otp" not in data:
            otp = generate_otp()
            store_otp(email, otp)

            send_mail(
                subject="Your OTP Verification Code",
                message=f"Your OTP for registering to Nagrik Setu {otp}",
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[email],
                fail_silently=False
            )

            return Response(
                {"message": "OTP sent successfully"},
                status=status.HTTP_200_OK
            )

        if not verify_otp(email, data["otp"]):
            return Response(
                {"error": "Invalid or expired OTP"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if User.objects.filter(email=data["email"]).exists():
            raise ValidationError("Email already registered")

        if User.objects.filter(phone=data["phone"]).exists():
            raise ValidationError("Phone already registered")

        with transaction.atomic():
            user = User.objects.create_user(
                username=email,
                email=email,
                password=data["password"],
                name=data["name"],
                phone=data["phone"],
                role="citizen",
                is_active=True,
            )
            Citizen.objects.create(user=user)

        refresh = RefreshToken.for_user(user)

        response = Response(
            {
                "message": "Registration successful",
                "user": UserSerializer(user).data,
            },
            status=status.HTTP_201_CREATED
        )

        response.set_cookie(
            key="access_token",
            value=str(refresh.access_token),
            httponly=True,
            secure=not settings.DEBUG,
            samesite="Lax"
        )
        response.set_cookie(
            key="refresh_token",
            value=str(refresh),
            httponly=True,
            secure=not settings.DEBUG,
            samesite="Lax",
        )

        return response

class LoginView(APIView):
    permission_classes = []

    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        email = data["email"]
        password = data["password"]

        user = authenticate(request, username=email, password=password)

        if user is None:
            raise AuthenticationFailed("Invalid login credentials")

        refresh = RefreshToken.for_user(user)

        response = Response(
            {
                "message": "Login successful",
                "user": UserSerializer(user).data,  # role comes from DB
            },
            status=status.HTTP_200_OK
        )
        response.set_cookie(
            key="access_token",
            value=str(refresh.access_token),
            httponly=True,
            secure=not settings.DEBUG,
            samesite="Lax",
            max_age=15 * 60,
        )
        response.set_cookie(
            key="refresh_token",
            value=str(refresh),
            httponly=True,
            secure=not settings.DEBUG,
            samesite="Lax",
            max_age=7 * 24 * 60 * 60,
        )

        return response

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.COOKIES.get("refresh_token")

        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except Exception:
                pass
        response = Response(
            {"message": "Logged out successfully"},
            status=status.HTTP_200_OK
        )
        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")

        return response

