from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from accounts.models import Profile, CustomUser
from mobile.serializers import UserViewProfileSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from accounts.serializers.user_serializers import OTPRequestSerializer, OTPVerifySerializer, SetNewPasswordSerializer
from django.utils import timezone
from datetime import timedelta
import random
from hmac import compare_digest
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from accounts.views.user_views import send_otp_email

class UserViewProfileView(RetrieveAPIView):
    serializer_class = UserViewProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        # Returns the profile of the currently logged-in user
        return get_object_or_404(Profile, user=self.request.user)


class OnboardingView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [SessionAuthentication, JWTAuthentication]

    def post(self, request):
        user = request.user
        user.legal_update_required = False
        user.save(update_fields=["legal_update_required"])

        return Response({"message": "Onboarding completed successfully."}, status=status.HTTP_200_OK)
    

@api_view(['POST'])
@permission_classes([AllowAny])
def otp_request_api(request):
    """
    API endpoint to request OTP for password reset.
    
    Expected payload:
    {
        "email": "user@example.com"
    }
    """
    serializer = OTPRequestSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response({
            "success": False,
            "errors": serializer.errors
        }, status=400)
    
    email = serializer.validated_data['email']
    user = User.objects.filter(email=email).first()
    
    # Check if user exists
    if not user:
        return Response({
            "success": False,
            "message": "Email is not registered."
        }, status=404)
    
    # Check for cooldown (prevent OTP spam)
    otp_lifetime = timedelta(minutes=10)
    cooldown_time = timedelta(minutes=1)
    if user.otp_created_at:
        if timezone_now() - user.otp_created_at < cooldown_time:
            next_allowed = user.otp_created_at + cooldown_time
            resend_in = max(0, int((next_allowed - timezone_now()).total_seconds()))
            return Response({
                "success": False,
                "message": "You have recently requested an OTP. Please wait before trying again.",
                "resend_in": resend_in,
                "next_resend_allowed_at": next_allowed.isoformat(),
            }, status=429)

    # Generate OTP & store with timestamp
    otp = str(random.randint(100000, 999999))
    user.otp = otp
    user.otp_created_at = timezone_now()
    user.save()

    # Send OTP via email
    try:
        send_otp_email(email, otp)
    except Exception as e:
        return Response({
            "success": False,
            "message": "Failed to send OTP email. Please try again later."
        }, status=500)

    expires_at = user.otp_created_at + otp_lifetime
    next_allowed = user.otp_created_at + cooldown_time
    return Response({
        "success": True,
        "message": "An OTP has been sent to your email.",
        "expires_in": int(otp_lifetime.total_seconds()),
        "expires_at": expires_at.isoformat(),
        "resend_in": int(cooldown_time.total_seconds()),
        "next_resend_allowed_at": next_allowed.isoformat(),
    }, status=200)



@api_view(['POST'])
@permission_classes([AllowAny])
def otp_verify_api(request):
    """
    API endpoint to verify OTP.
    
    Expected payload:
    {
        "email": "user@example.com",
        "otp": "123456"
    }
    """
    serializer = OTPVerifySerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response({
            "success": False,
            "errors": serializer.errors
        }, status=400)
    
    email = serializer.validated_data['email']
    entered_otp = serializer.validated_data['otp']
    
    user = User.objects.filter(email=email).first()
    
    if not user:
        return Response({
            "success": False,
            "message": "Invalid email address."
        }, status=404)
    
    stored_otp = user.otp
    otp_created_at = user.otp_created_at
    
    # Check if OTP exists
    if not stored_otp:
        return Response({
            "success": False,
            "message": "No OTP found. Please request a new one."
        }, status=400)
    
    # Check if OTP has expired
    otp_lifetime = timedelta(minutes=10)
    if otp_created_at and timezone_now() - otp_created_at > otp_lifetime:
        return Response({
            "success": False,
            "message": "OTP has expired. Please request a new one."
        }, status=400)
    
    # Secure OTP comparison to prevent timing attacks
    if compare_digest(stored_otp, entered_otp):
        expires_at = otp_created_at + otp_lifetime
        expires_in = max(0, int((expires_at - timezone_now()).total_seconds()))

        # Clear OTP and timestamp after successful verification
        user.otp = None
        user.otp_created_at = None
        user.save()

        return Response({
            "success": True,
            "message": "OTP verified successfully. You can now set a new password.",
            "expires_at": expires_at.isoformat(),
            "expires_in": expires_in,
        }, status=200)
    
    return Response({
        "success": False,
        "message": "Invalid OTP. Please try again."
    }, status=400)


@api_view(['POST'])
@permission_classes([AllowAny])
def set_new_password_api(request):
    """
    API endpoint to set a new password for password reset.
    
    Expected payload:
    {
        "email": "user@example.com",
        "password": "newpassword123",
    }
    """
    serializer = SetNewPasswordSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response({
            "success": False,
            "errors": serializer.errors
        }, status=400)
    
    email = serializer.validated_data['email']
    password = serializer.validated_data['password']
    
    # Get user by email
    user = User.objects.filter(email=email).first()
    
    if not user:
        return Response({
            "success": False,
            "message": "Invalid email address."
        }, status=404)
    
    # Validate password using Django's built-in validators
    try:
        validate_password(password, user)
    except ValidationError as e:
        return Response({
            "success": False,
            "errors": {"password": list(e.messages)}
        }, status=400)
    
    # Save new password and clear OTP
    user.set_password(password)
    user.otp = None
    user.otp_created_at = None
    user.save()
    
    return Response({
        "success": True,
        "message": "Password reset successful. You can now log in."
    }, status=200)
