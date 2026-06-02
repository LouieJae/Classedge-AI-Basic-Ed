import logging

from django.shortcuts import render,redirect, get_object_or_404
from accounts.models import CustomUser, Profile, DisplayImage, LoginHistory, UserLegalConsent, LegalDocument

logger = logging.getLogger(__name__)


def _pending_legal_doc_types(user):
    active_ids = set(
        LegalDocument.objects.filter(is_active=True).values_list("id", flat=True)
    )
    accepted_ids = set(
        UserLegalConsent.objects.filter(user=user).values_list("document_id", flat=True)
    )
    missing_ids = active_ids - accepted_ids
    return list(
        LegalDocument.objects.filter(id__in=missing_ids).values_list("doc_type", flat=True)
    )


from mobile.models import Attachment
from accounts.serializers import CustomUserSerializer, OTPRequestSerializer, OTPVerifySerializer, SetNewPasswordSerializer, ProfileSerializer, UserLegalConsentSerializer
from accounts.utils import CustomPagination
from accounts.forms import RegistrationForm, StudentUpdateForm, CustomLoginForm, SetPasswordForm, profileForm, registrarProfileForm, ProgramHeadCreateForm
from course.models import StudentInvite
from subject.models import SubjectCollaborator, SDG
from allauth.socialaccount.models import SocialAccount, SocialToken
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.filters import SearchFilter
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework import status
from accounts.serializers import LoginSerializer
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import permission_required
from django.contrib.auth import get_user_model
from django.conf import settings
from django.contrib.auth import logout as auth_logout, authenticate, login, get_backends
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from datetime import timedelta
from django.utils.timezone import now
import random
from django.core.mail import send_mail
from django.contrib import messages
from django.db.models import Q
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.hashers import make_password
from django.contrib.messages import get_messages
from accounts.utils import validate_image_file
from accounts.utils.security_utils import custom_ratelimit, log_security_event, get_client_ip
from django.urls import reverse
from datetime import date
from roles.models import Role
User = get_user_model()
from django.utils import timezone
from rest_framework.permissions import BasePermission
from django.core.cache import cache
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.authentication import SessionAuthentication
from social_media.models import Friend
from datetime import datetime
from accounts.utils import paginate_queryset, search_queryset, get_pagination_context
from accounts.utils.powersync_utils import generate_powersync_token
import re
from hmac import compare_digest
from django.utils.timezone import now as timezone_now
from accounts.utils import validate_microsoft_token
from django.http import Http404, HttpResponseForbidden, JsonResponse
from gamification.models import StudentBadge, StudentGamification, BadgeDefinition


class IsSuperUser(BasePermission):
    """
    Global permission check for superuser.
    """

    def has_permission(self, request, view):
        return request.user and request.user.is_superuser

class CustomUserViewSet(ModelViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer
    pagination_class = CustomPagination
    filter_backends = [SearchFilter]
    search_fields = ['username', 'email', 'last_name', 'first_name']
    permission_classes = [IsAuthenticated, IsSuperUser]

    def get_queryset(self):
        return self.queryset
    
def _mask(s: str, keep: int = 4):
    if not s:
        return s
    s = str(s)
    return s if len(s) <= keep * 2 else f"{s[:keep]}...{s[-keep:]}"


@custom_ratelimit(rate='5/h', method='POST')
def register_user(request):
    if request.method == 'POST':
        log_security_event('USER_REGISTRATION_ATTEMPT', request)
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)

            user.set_password(form.cleaned_data['password'])

            invite_email = request.session.get('invite_email')
            student_invite_email = request.session.get('student_invite_email')
            student_invite_token = request.session.get('student_invite_token')

            collab_invite = None
            student_invite = None

            if invite_email:
                collab_invite = SubjectCollaborator.objects.filter(
                    email=invite_email, user__isnull=True, accepted=False
                ).first()

            if student_invite_token:
                student_invite = StudentInvite.objects.filter(
                    token=student_invite_token,
                    accepted=False
                ).first()

            if not collab_invite and not student_invite:
                messages.error(request, "Invalid or expired student/collaborator invite.")
                return redirect('register_user')

            if student_invite:
                assigned_role = Role.objects.get(name__iexact='Student')
            elif collab_invite:
                assigned_role = Role.objects.get(name__iexact='Teacher')
            else:
                messages.error(request, "Could not determine role from invite.")
                return redirect('register_user')

            user.save()

            profile, created = Profile.objects.get_or_create(
                user=user,
                defaults={
                    'role': assigned_role,
                    'is_coil_user': True,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                }
            )
            if created:
                profile.role = assigned_role
                profile.is_coil_user = True
                profile.first_name = user.first_name
                profile.last_name = user.last_name
                profile.save()

            if collab_invite:
                collab_invite.user = user
                collab_invite.accepted = True
                collab_invite.save()
                collab_invite.subject.collaborators.add(user)

            if student_invite:
                student_invite.accepted = True
                student_invite.save()

                now = timezone.localtime(timezone.now()).date()
                current_semester = Semester.objects.filter(
                    start_date__lte=now, end_date__gte=now
                ).first()

                if current_semester:
                    se_obj, se_created = SubjectEnrollment.objects.get_or_create(
                        student=user,
                        subject=student_invite.subject,
                        semester=current_semester,
                        defaults={'status': 'enrolled'}
                    )

            backend = get_backends()[0]
            user.backend = f"{backend.__module__}.{backend.__class__.__name__}"
            login(request, user)

            messages.success(request, "Registration successful.")
            return redirect('dashboard')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = RegistrationForm()

    return render(request, 'accounts/interface/user_registration.html', {'form': form})



class User_Profile(ModelViewSet):
    serializer_class = ProfileSerializer
    authentication_classes = [SessionAuthentication, JWTAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = None  

    def get_queryset(self):
        return Profile.objects.select_related('user', 'role', 'course', 'department_fields').filter(user=self.request.user)

    def get_object(self):
        return get_object_or_404(
            Profile.objects.select_related('user', 'role', 'course', 'department_fields'),
            user=self.request.user
        )

    def list(self, request, *args, **kwargs):
        obj = self.get_object()
        serializer = self.get_serializer(obj)
        return Response(serializer.data)
    
    def handle_exception(self, exc):
        if isinstance(exc, Http404):
            return Response({"message": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        if isinstance(exc, MethodNotAllowed):
            return Response({"message": "Method not allowed"}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
        if isinstance(exc, Profile.DoesNotExist):
            return Response({"message": "Profile not found"}, status=status.HTTP_404_NOT_FOUND)
        return super().handle_exception(exc)

@custom_ratelimit(rate='100/h', method='POST')
def admin_login_view(request):
    """Handle login form submission (OTP disabled): validate captcha, authenticate, and login."""
    if request.user.is_authenticated:
        return redirect('dashboard')

    login_error = False
    failed_attempts_context = {'failed_count': 0, 'remaining_attempts': 5}
    
    # Check if there's an email in session (from failed login redirect)
    failed_email = request.session.get('failed_login_email')
    if failed_email:
        try:
            user = CustomUser.objects.get(email=failed_email)
            failed_count = user.failed_login_count or 0
            remaining_attempts = max(0, 5 - failed_count)
            failed_attempts_context = {
                'failed_count': failed_count,
                'remaining_attempts': remaining_attempts
            }
        except CustomUser.DoesNotExist:
            pass
    
    if request.method == 'POST':
        # Clear any existing login credentials from previous attempts
        if 'login_email' in request.session:
            del request.session['login_email']
        if 'login_password' in request.session:
            del request.session['login_password']
        if 'login_attempt_time' in request.session:
            del request.session['login_attempt_time']
        if 'pending_user_id' in request.session:
            del request.session['pending_user_id']
        # Clear failed_login_email when submitting new attempt
        if 'failed_login_email' in request.session:
            del request.session['failed_login_email']
        
        form = CustomLoginForm(request.POST)
        
        if not form.is_valid():
            logger.debug("Login form errors: %s", form.errors)
        
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']

            # OTP disabled: authenticate and login immediately
            try:
                user_obj = CustomUser.objects.get(email=email)
                username = user_obj.username
                user = authenticate(request, username=username, password=password)
            except CustomUser.DoesNotExist:
                user = None

            if user is None:
                try:
                    failed_user = CustomUser.objects.get(email=email)
                    failed_user.failed_login_count = (failed_user.failed_login_count or 0) + 1
                    failed_user.save()

                    failed_count = failed_user.failed_login_count
                    remaining_attempts = max(0, 5 - failed_count)

                    request.session['failed_login_email'] = email

                    if remaining_attempts > 0:
                        messages.error(request, 'Invalid email or password.')
                    else:
                        messages.error(request, 'Account locked due to too many failed attempts. Please contact support.')
                        # Lock the account
                        failed_user.otp_blocked_until = timezone.now() + timedelta(hours=1)
                        failed_user.save()

                    login_error = True
                except CustomUser.DoesNotExist:
                    messages.error(request, 'Invalid email or password. Please try again.')
                    login_error = True
            else:
                backend = get_backends()[0]
                login(request, user, backend=backend.__class__.__module__ + '.' + backend.__class__.__name__)

                ip_address = get_client_ip(request)
                user_agent = request.META.get('HTTP_USER_AGENT', '')
                LoginHistory.objects.create(user=user, ip_address=ip_address, user_agent=user_agent)

                user.failed_login_count = 0
                user.save()

                if 'failed_login_email' in request.session:
                    del request.session['failed_login_email']

                messages.success(request, 'Login successful! Welcome back.')
                return redirect('dashboard')
        else:
            if 'captcha' in form.errors:
                messages.error(request, 'Please complete the reCAPTCHA verification.')
            else:
                messages.error(request, 'Form data is invalid. Please check your input.')
            login_error = True
    else:
        form = CustomLoginForm()

    carousel_images = DisplayImage.objects.filter(is_displayed=True)
    return render(request, 'accounts/interface/login.html', {
        'form': form,
        'login_error': login_error,
        'carousel_images': carousel_images,
        **failed_attempts_context
    })


@custom_ratelimit(rate='10/h', method='POST')
def verify_login_otp(request):
    """Handle authentication and OTP verification."""
    email = request.session.get('login_email')
    password = request.session.get('login_password')
    
    user_id = request.session.get('pending_user_id')
    
    if not email and not user_id:
        messages.error(request, "Session expired. Please login again.")
        return redirect('admin_login_view')
    
    if email and password and not user_id:
        try:
            user_obj = CustomUser.objects.get(email=email)
            username = user_obj.username
            user = authenticate(request, username=username, password=password)
        except CustomUser.DoesNotExist:
            user = None
        
        if user is None:
            try:
                failed_user = CustomUser.objects.get(email=email)
                failed_user.failed_login_count = (failed_user.failed_login_count or 0) + 1
                failed_user.save()
                
                failed_count = failed_user.failed_login_count
                remaining_attempts = max(0, 5 - failed_count)
                
                request.session['failed_login_email'] = email
                
                del request.session['login_email']
                del request.session['login_password']
                if 'login_attempt_time' in request.session:
                    del request.session['login_attempt_time']
                
                if remaining_attempts > 0:
                    messages.error(request, 'Invalid email or password.')
                else:
                    messages.error(request, 'Account locked due to too many failed attempts. Please contact support.')
                    # Lock the account
                    failed_user.otp_blocked_until = timezone.now() + timedelta(hours=1)
                    failed_user.save()
                
                return redirect('admin_login_view')
            except CustomUser.DoesNotExist:
                del request.session['login_email']
                del request.session['login_password']
                if 'login_attempt_time' in request.session:
                    del request.session['login_attempt_time']
                messages.error(request, 'Invalid email or password. Please try again.')
                return redirect('admin_login_view')
        
        now = timezone.now()
        
        user.failed_login_count = 0
        user.save()
        
        if user.otp_blocked_until and now < user.otp_blocked_until:
            remaining = int((user.otp_blocked_until - now).total_seconds() / 60)
            messages.error(request, f"Too many OTP requests. Try again in {remaining} minutes.")
            del request.session['login_email']
            del request.session['login_password']
            if 'login_attempt_time' in request.session:
                del request.session['login_attempt_time']
            return redirect('admin_login_view')
        
        if user.account_locked_permanent:
            messages.error(request, "This account is permanently locked. Contact support.")
            del request.session['login_email']
            del request.session['login_password']
            if 'login_attempt_time' in request.session:
                del request.session['login_attempt_time']
            return redirect('admin_login_view')
        
        if user.otp_created_at and now - user.otp_created_at < timedelta(minutes=1):
            messages.warning(request, "Please wait 1 minute before requesting another OTP.")
            request.session['pending_user_id'] = user.id
            del request.session['login_email']
            del request.session['login_password']
            if 'login_attempt_time' in request.session:
                del request.session['login_attempt_time']
            # Render OTP page
            remaining_attempts = max(0, 5 - user.failed_otp_count)
            return render(request, 'accounts/interface/verify_login_otp.html', {
                'email': user.email,
                'remaining_attempts': remaining_attempts,
                'failed_count': user.failed_otp_count
            })
        
        if user.otp_attempts >= 5:
            user.otp_blocked_until = now + timedelta(minutes=15)
            user.otp_attempts = 0
            user.save()
            messages.error(request, "Too many OTP requests. Please try again in 15 minutes.")
            del request.session['login_email']
            del request.session['login_password']
            if 'login_attempt_time' in request.session:
                del request.session['login_attempt_time']
            return redirect('admin_login_view')
        
        otp = str(random.randint(100000, 999999))
        user.otp = otp
        user.otp_created_at = now
        user.otp_attempts += 1
        user.save()
        
        send_otp_email(user.email, otp, purpose='login', expiry_minutes=5)
        
        request.session['pending_user_id'] = user.id
        del request.session['login_email']
        del request.session['login_password']
        if 'login_attempt_time' in request.session:
            del request.session['login_attempt_time']
        
        messages.info(request, f'An OTP has been sent to {user.email}. Please verify to continue.')
        remaining_attempts = max(0, 5 - user.failed_otp_count)
        return render(request, 'accounts/interface/verify_login_otp.html', {
            'email': user.email,
            'remaining_attempts': remaining_attempts,
            'failed_count': user.failed_otp_count
        })
    
    if not user_id:
        messages.error(request, "Session expired. Please login again.")
        return redirect('admin_login_view')
    
    user = CustomUser.objects.get(id=user_id)
    
    # If account permanently locked, refuse
    if user.account_locked_permanent:
        messages.error(request, "This account is permanently locked. Contact support.")
        return redirect('admin_login_view')
    
    # If currently blocked by otp_blocked_until, show remaining time
    now = timezone.now()
    if user.otp_blocked_until and now < user.otp_blocked_until:
        remaining_seconds = int((user.otp_blocked_until - now).total_seconds())
        minutes = remaining_seconds // 60
        messages.error(request, f"Too many failed attempts. Try again in {minutes} minute(s).")
        return redirect('admin_login_view')
    
    if request.method == 'POST':
        entered_otp = request.POST.get('otp')
        # guard if otp_created_at missing
        if not user.otp_created_at:
            messages.error(request, "No OTP was issued. Please login again.")
            return redirect('admin_login_view')

        # check expiry (5 minutes)
        if timezone.now() - user.otp_created_at > timedelta(minutes=5):
            # expired - treat as failed attempt
            user.failed_otp_count += 1
            user.save()
            messages.error(request, "OTP expired. Please request a new OTP.")
            # handle escalation below (fall through)
        elif user.otp == entered_otp:
            # Correct OTP: finalize login and reset counters
            backend = get_backends()[0]
            login(request, user, backend=backend.__class__.__module__ + '.' + backend.__class__.__name__)

            # record login history (IP/user agent)
            ip_address = get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            LoginHistory.objects.create(user=user, ip_address=ip_address, user_agent=user_agent)

            # reset both OTP and login-related fields
            del request.session['pending_user_id']
            # Clear any remaining login credentials from session
            if 'login_email' in request.session:
                del request.session['login_email']
            if 'login_password' in request.session:
                del request.session['login_password']
            if 'login_attempt_time' in request.session:
                del request.session['login_attempt_time']
            
            user.otp = None
            user.otp_created_at = None
            user.failed_otp_count = 0
            user.failed_login_count = 0  # Reset login attempts on successful login
            user.otp_blocked_until = None
            user.save()

            messages.success(request, 'Login successful! Welcome back.')
            return redirect('dashboard')

        else:
            # wrong OTP
            user.failed_otp_count += 1
            user.save()
            messages.error(request, "Invalid OTP. Please try again.")

        # AFTER incrementing failed_otp_count, apply escalation rules:
        # - >=15 -> permanent lock
        # - >=10 -> 24-hour block
        # - >=5  -> 1-hour block
        if user.failed_otp_count >= 15:
            user.account_locked_permanent = True
            user.otp_blocked_until = None
            user.save()
            # Optionally deactivate user account:
            user.is_active = False
            user.save()
            # Log and notify admin if needed
            messages.error(request, "Account permanently locked due to repeated failed attempts. Contact support.")
            return redirect('admin_login_view')

        if user.failed_otp_count >= 10:
            # set 24 hour block
            user.otp_blocked_until = timezone.now() + timedelta(hours=24)
            user.save()
            messages.error(request, "Too many failed attempts. Account blocked for 24 hours.")
            return redirect('admin_login_view')

        if user.failed_otp_count >= 5:
            # set 1 hour block
            user.otp_blocked_until = timezone.now() + timedelta(hours=1)
            user.save()
            messages.error(request, "Too many failed attempts. Please try again in 1 hour.")
            return redirect('admin_login_view')

    # Calculate remaining attempts before lockout
    remaining_attempts = max(0, 5 - user.failed_otp_count)
    return render(request, 'accounts/interface/verify_login_otp.html', {
        'email': user.email,
        'remaining_attempts': remaining_attempts,
        'failed_count': user.failed_otp_count
    })


@custom_ratelimit(rate='5/h', method='POST')
def resend_login_otp(request):
    user_id = request.session.get('pending_user_id')
    if not user_id:
        return redirect('admin_login_view')

    user = CustomUser.objects.get(id=user_id)
    now = timezone.now()

    # ⏳ Cooldown check
    if user.otp_created_at and now - user.otp_created_at < timedelta(minutes=1):
        messages.warning(request, "Please wait 1 minute before requesting another OTP.")
        return redirect('verify_login_otp')

    # 🚨 Attempt limit
    if user.otp_attempts >= 5:
        user.otp_blocked_until = now + timedelta(minutes=15)
        user.otp_attempts = 0
        user.save()
        messages.error(request, "Too many OTP requests. Please try again in 15 minutes.")
        return redirect('admin_login_view')

    # ✅ Generate new OTP
    otp = str(random.randint(100000, 999999))
    user.otp = otp
    user.otp_created_at = now
    user.otp_attempts += 1
    user.save()

    send_mail(
        subject='Your Login OTP Code',
        message=f'Your One-Time Password is {otp}. It will expire in 5 minutes.',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )

    messages.info(request, f'New OTP sent to {user.email}.')
    return redirect('verify_login_otp')



# Handle API Login
class LoginAPIView(APIView):
    permission_classes = [AllowAny]
    serializer_class = LoginSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        username = serializer.validated_data['username']
        password = serializer.validated_data['password']
        
        user = authenticate(username=username, password=password)
        
        if user is None:
            return Response({
                'message': 'Invalid username or password'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        if not user.is_active:
            return Response({
                'message': 'User account is disabled'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Create JWT tokens
        refresh = RefreshToken.for_user(user)
        
        refresh['role'] = user.profile.role.name
        refresh['needs_password_setup'] = user.needs_password_setup
        refresh['needs_onboarding'] = user.needs_onboarding
        
        # Add custom claims to access token as well
        access_token = refresh.access_token
        access_token['role'] = user.profile.role.name
        
        needs_password_setup = user.needs_password_setup
        needs_onboarding = user.needs_onboarding
        
        access_token['needs_password_setup'] = needs_password_setup
        access_token['needs_onboarding'] = needs_onboarding

        # Generate PowerSync token using shared helper
        try:
            powersync_token = generate_powersync_token(user_id=user.id, request=request)
        except Exception as exc:
            return Response(
                {
                    'message': 'Failed to generate PowerSync token',
                    'error': str(exc)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Log the login
        LoginHistory.objects.create(user=user)
        
        return Response({
            'refresh_token': str(refresh),
            'access_token': str(access_token),
            'powersync_token': powersync_token,
        }, status=status.HTTP_200_OK)


class PowerSyncTokenRefreshView(TokenRefreshView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as exc:
            raise InvalidToken(exc.args[0])

        # Get the NEW refresh token from validated data (important for token rotation)
        response_data = serializer.validated_data
        new_refresh_token = response_data.get('refresh')
        
        if not new_refresh_token:
            return Response(
                {'detail': 'Failed to generate new refresh token.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        try:
            # Use the NEW refresh token to get user_id
            refresh_obj = RefreshToken(new_refresh_token)
            user_id = refresh_obj['user_id']
        except Exception:
            return Response(
                {'detail': 'Invalid refresh token.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            powersync_token = generate_powersync_token(user_id=user_id, request=request)
        except Exception as exc:
            return Response(
                {
                    'message': 'Failed to generate PowerSync token',
                    'error': str(exc)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        response_payload = {
            'refresh_token': response_data.get('refresh'),
            'access_token': response_data.get('access'),
            'powersync_token': powersync_token,
        }

        return Response(response_payload, status=status.HTTP_200_OK)


# Program head ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@login_required
@permission_required('accounts.view_profile', raise_exception=True)
def program_head_list(request):
    search_query = request.GET.get('search', '').strip()

    # Get base queryset
    program_head = Profile.objects.filter(role__name__iexact='program head').select_related('user', 'role')

    # Apply search using reusable function
    search_fields = ['first_name', 'last_name', 'user__email', 'id_number', 'department_fields__name']
    program_head = search_queryset(program_head, search_query, search_fields)

    # Apply pagination using reusable function
    page_obj, paginator = paginate_queryset(program_head, request, items_per_page=10)
    
    # Get pagination context
    pagination_context = get_pagination_context(page_obj, request)

    role = request.user.profile.role.name

    context = {
        'program_head': page_obj,
        'role': role,
        'search_query': search_query,
    }
    
    # Merge pagination context
    context.update(pagination_context)

    return render(request, 'accounts/user_list/program_head_list.html', context)


# User level ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━





@login_required
@permission_required('accounts.view_profile', raise_exception=True)
def view_student_profile(request, pk):
    # Send the requester to their own gamified profile if they target themself.
    if pk == request.user.id:
        return redirect('account_profile', pk=request.user.id)

    admin_roles = {'admin', 'registrar', 'program head', 'academic director', 'super admin'}
    is_admin_view = request.user.is_superuser or request.user.role_name in admin_roles

    try:
        profile = get_object_or_404(
            Profile.objects.select_related('user', 'role', 'course', 'department_fields').prefetch_related('certificates'),
            user__id=pk
        )
    except Http404:
        try:
            profile = get_object_or_404(
                Profile.objects.select_related('user', 'role', 'course', 'department_fields').prefetch_related('certificates'),
                id=pk
            )
        except Http404:
            raise 

    certificates = profile.certificates.all() 

    target_user = profile.user
    current_user = request.user
    
    friend_status = None
    is_request_sender = False  # Track if current user sent the friend request
    friend_request_id = None
    if current_user != target_user:
        friend_request = Friend.objects.filter(
            (Q(from_user=current_user) & Q(to_user=target_user)) |
            (Q(from_user=target_user) & Q(to_user=current_user))
        ).first()

        if friend_request:
            friend_request_id = friend_request.id
            friend_status = friend_request.status
            # Check if current user is the one who sent the request
            is_request_sender = (friend_request.from_user == current_user)
        else:
            friend_status = 'none' 
    sdg = SDG.objects.all()
    from gamification.models import StudentBadge, StudentGamification
    earned_badges = StudentBadge.objects.filter(
        student=target_user, is_featured=True,
    ).select_related('badge').order_by('-earned_at')
    try:
        target_gamification = target_user.gamification
    except StudentGamification.DoesNotExist:
        target_gamification = None
    context = {
        'profile': profile,
        'certificates': certificates,
        'sdg': sdg,
        'friend_status': friend_status,
        'is_request_sender': is_request_sender,
        'target_user': target_user,
        'can_add_friend': current_user != target_user,
        'earned_badges': earned_badges,
        'is_admin_view': is_admin_view,
        'friend_request_id': friend_request_id,
        'target_gamification': target_gamification,
    }
    return render(request, 'accounts/user_level/view_student_profile.html', context)



@login_required
def update_profile(request, user_id):
    profile = get_object_or_404(Profile, user_id=user_id)

    if profile.user != request.user and not request.user.has_perm('accounts.change_profile'):
        return HttpResponseForbidden("You are not allowed to edit this profile.")

    profile_url = reverse('account_profile', kwargs={'pk': profile.user.id})
    is_xhr = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if request.method != 'POST':
        return redirect(profile_url)

    def fail(errors):
        if is_xhr:
            return JsonResponse({'ok': False, 'errors': errors}, status=400)
        for msgs in errors.values():
            for err in (msgs if isinstance(msgs, (list, tuple)) else [msgs]):
                messages.error(request, err, extra_tags='profile_edit')
        return redirect(f"{profile_url}?edit=1")

    image_errs = validate_image_file(request.FILES.get('student_photo'))
    if image_errs:
        return fail({'student_photo': image_errs})

    form = StudentUpdateForm(request.POST, request.FILES, instance=profile)
    if not form.is_valid():
        return fail(form.errors)

    dob = form.cleaned_data.get('date_of_birth')
    if dob and dob > date.today():
        return fail({'date_of_birth': ['Birthday cannot be in the future.']})

    updated_profile = form.save()
    if form.cleaned_data.get('student_photo'):
        Attachment.objects.create(profile=updated_profile, file=updated_profile.student_photo)

    if is_xhr:
        return JsonResponse({'ok': True, 'redirect': profile_url}, status=200)
    messages.success(request, 'Profile updated successfully.')
    return redirect(profile_url)


# Admin side
#--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

@login_required
@permission_required('accounts.change_profile', raise_exception=True)
def admin_update_student_profile(request, pk):
    profile = get_object_or_404(
        Profile.objects.select_related('user', 'role', 'course', 'department_fields'),
        pk=pk
    )
    if request.method == 'POST':
        form = profileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, f"Student profile has been updated successfully!")
            return redirect('student-list')
    else:
        form = profileForm(instance=profile)
    
    return render(request, 'accounts/admin_update/update-profile-student.html', {
        'form': form,
        'profile': profile
    })


@login_required
@permission_required('accounts.change_profile', raise_exception=True)
def admin_update_teacher_profile(request, pk):
    profile = get_object_or_404(
        Profile.objects.select_related('user', 'role', 'course', 'department_fields'),
        pk=pk
    )
    if request.method == 'POST':
        form = profileForm(request.POST,request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, f"Teacher profile for has been updated successfully!")
            return redirect('teacher-list')
    else:
        form = profileForm(instance=profile)
    return render(request, 'accounts/admin_update/update-profile-teacher.html', {
        'form': form,
        'profile': profile
    })


@login_required
@permission_required('accounts.change_profile', raise_exception=True)
def admin_update_program_head_profile(request, pk):
    profile = get_object_or_404(
        Profile.objects.select_related('user', 'role', 'course', 'department_fields'),
        pk=pk
    )
    if request.method == 'POST':
        form = profileForm(request.POST,request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, f"Program head profile for has been updated successfully!")
            return redirect('program-head-list')
    else:
        form = profileForm(instance=profile)
    return render(request, 'accounts/admin_update/update-profile-program-head.html', {
        'form': form,
        'profile': profile
    })


@login_required
@permission_required('accounts.change_profile', raise_exception=True)
def admin_update_admin_and_staff_profile(request, pk):
    profile = get_object_or_404(
        Profile.objects.select_related('user', 'role', 'course', 'department_fields'),
        pk=pk
    )
    if request.method == 'POST':
        form = profileForm(request.POST,request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, f"Staff profile for has been updated successfully!")
            return redirect('admin-and-staff-list')
    else:
        form = profileForm(instance=profile)
    return render(request, 'accounts/admin_update/update-profile-staff.html', {
        'form': form,
        'profile': profile
    })

# Registrar Side --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

@login_required
def update_student_profile(request, pk):
    profile = get_object_or_404(Profile, pk=pk)
    
    if request.method == 'POST':
        form = registrarProfileForm(request.POST, request.FILES, instance=profile)
        
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('student-list')  
        else:
            messages.error(request, 'There were errors updating the profile. Please review the form below.')
    else:
        form = registrarProfileForm(instance=profile)

    return render(request, 'accounts/registrar_update/update-student-profile.html', {'form': form, 'profile': profile})


@login_required
def update_teacher_profile(request, pk):
    profile = get_object_or_404(Profile, pk=pk)
    
    if request.method == 'POST':
        form = registrarProfileForm(request.POST, request.FILES, instance=profile)
        
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('teacher-list')  
        else:
            messages.error(request, 'There were errors updating the profile. Please review the form below.')
    else:
        form = registrarProfileForm(instance=profile)

    return render(request, 'accounts/registrar_update/update-teacher-profile.html', {'form': form, 'profile': profile})


@login_required
def update_admin_and_staff_profile(request, pk):
    profile = get_object_or_404(Profile, pk=pk)
    
    if request.method == 'POST':
        form = registrarProfileForm(request.POST, request.FILES, instance=profile)
        
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('admin-and-staff-list')  
        else:
            messages.error(request, 'There were errors updating the profile. Please review the form below.')
    else:
        form = registrarProfileForm(instance=profile)

    return render(request, 'accounts/registrar_update/update-admin-and-staff-profile.html', {'form': form, 'profile': profile})


@login_required
def update_program_head_profile(request, pk):
    profile = get_object_or_404(Profile, pk=pk)
    
    if request.method == 'POST':
        form = registrarProfileForm(request.POST, request.FILES, instance=profile)
        
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('program-head-list')  
        else:
            messages.error(request, 'There were errors updating the profile. Please review the form below.')
    else:
        form = registrarProfileForm(instance=profile)

    return render(request, 'accounts/registrar_update/update-program-head-profile.html', {'form': form, 'profile': profile})

@login_required
def sign_out(request):
    auth_logout(request)
    
    is_office365_user = request.session.get('is_office365_user', False)
    
    request.session.flush()
    
    if is_office365_user:
        microsoft_logout_url = 'https://login.microsoftonline.com/common/oauth2/v2.0/logout'
        post_logout_redirect_uri = request.build_absolute_uri(reverse('admin_login_view'))
        params = urlencode({'post_logout_redirect_uri': post_logout_redirect_uri})
        full_logout_url = f"{microsoft_logout_url}?{params}"
        
        return redirect(full_logout_url)
    
    return redirect('admin_login_view')

@custom_ratelimit(rate='5/h', method='POST')
def otp_reset_request(request):
    if request.method == "POST":
        email = request.POST.get("email")

        try:
            validate_email(email)
        except ValidationError:
            messages.error(request, "Please enter a valid email address.")
            return redirect("otp_reset")

        user = User.objects.filter(email=email).first()

        if not user or not hasattr(user, "profile"):
            messages.error(request, "Email is not registered.")
            return redirect("otp_reset")
        if user.otp_created_at:
            cooldown_time = timedelta(minutes=1)
            if now() - user.otp_created_at < cooldown_time:
                messages.error(request, "You have recently requested an OTP. Please wait a few minutes before trying again.")
                return redirect("otp_reset")

        otp = str(random.randint(100000, 999999))  
        user.otp = otp
        user.otp_created_at = now()  
        user.save()

        send_otp_email(email, otp)

        messages.success(request, "An OTP has been sent to your email.")
        return redirect("otp_verify", email=email)

    return render(request, "forget_password/otp_reset_request.html")

@custom_ratelimit(rate='10/h', method='POST')
def otp_verify(request, email):
    user = User.objects.filter(email=email).first()

    if not user or not hasattr(user, 'profile'):
        messages.error(request, "Invalid email address.")
        return redirect("otp_reset")

    storage = get_messages(request)
    list(storage)  

    if request.method == "POST":
        entered_otp = request.POST.get("otp")
        if not entered_otp:
            messages.error(request, "OTP cannot be empty. Please enter a valid OTP.")
            return redirect("otp_verify", email=email)

        if not re.match(r"^\d{6}$", entered_otp):
            messages.error(request, "Invalid OTP format. Please enter a 6-digit code.")
            return redirect("otp_verify", email=email)

        stored_otp = user.otp if user else None
        otp_created_at = user.otp_created_at if user else None

        otp_lifetime = timedelta(minutes=10)  
        if otp_created_at and now() - otp_created_at > otp_lifetime:
            messages.error(request, "OTP has expired. Please request a new one.")
            return redirect("otp_reset")
        
        if stored_otp and compare_digest(stored_otp, entered_otp):
            user.otp = None
            user.otp_created_at = None
            user.save()

            return redirect("set_new_password", email=email)

        messages.error(request, "Invalid OTP. Please try again.")
        return redirect("otp_verify", email=email)

    return render(request, "forget_password/otp_verify.html", {"email": email})

def send_otp_email(email, otp, purpose='password reset', expiry_minutes=10):
    """Send OTP email with consistent formatting."""
    subject = f"🔐 Classedge {purpose.title()} OTP Code"
    
    message = f"""Hi there,

        We received a request to {purpose} for your Classedge account.

        🔐 Your OTP code: {otp}

        This code will expire in {expiry_minutes} minutes and can only be used once.

        Security Notice:
        If you didn't request this {purpose}, please ignore this message or contact our support team immediately.

        — The Classify Team"""
    
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [email],
        fail_silently=False,
    )

@custom_ratelimit(rate='5/h', method='POST')
def set_new_password(request, email):
    user = User.objects.filter(email=email).first()

    if not user or not hasattr(user, 'profile'):
        messages.error(request, "Invalid email address.")
        return redirect("otp_reset")

    storage = get_messages(request)
    list(storage)  

    if request.method == "POST":
        password1 = request.POST.get("password1")
        password2 = request.POST.get("password2")

        if password1 != password2:
            messages.error(request, "Passwords do not match.")
            return redirect("set_new_password", email=email)
        try:
            validate_password(password1, user)
        except ValidationError as e:
            for error in e.messages:
                messages.error(request, error)
            return redirect("set_new_password", email=email)

        user.set_password(password1)
        user.save()

        user.otp = None
        user.save()

        messages.success(request, "Password reset successful. You can now log in.")
        return redirect("admin_login_view")

    return render(request, "forget_password/set_new_password.html", {"email": email})


def error(request):
    return render(request, '404.html')


RESET_LIMIT = timedelta(minutes=30)

@custom_ratelimit(rate='10/h', method='POST')
def setup_password(request):
    show_password_fields = False
    
    # Rate limiting: 5 attempts per hour per IP
    client_ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', ''))
    if client_ip:
        # If there are multiple IPs (proxy chain), take the first one
        client_ip = client_ip.split(',')[0].strip()
    
    rate_limit_key = f"setup_password_attempts_{client_ip}"
    
    # Check current attempt count
    attempt_count = cache.get(rate_limit_key, 0)
    
    if attempt_count >= 5:
        messages.error(request, "Too many password setup attempts. Please try again in an hour.")
        return render(request, 'accounts/interface/setup_password.html', {
            'form': SetPasswordForm(),
            'show_password_fields': False,
            'rate_limited': True
        })

    if request.method == 'POST':
        cache.set(rate_limit_key, attempt_count + 1, 3600)  
        form = SetPasswordForm(request.POST)

        if form.is_valid():
            email = form.cleaned_data.get('email')
            id_number = form.cleaned_data.get('id_number')
            user = CustomUser.objects.filter(email=email).first()

            if user and user.last_password_reset:
                messages.error(request, "You have already set up your password. Please use 'Forgot Password' instead.")
                return redirect('admin_login_view')

            if user and user.profile.id_number == id_number:
                show_password_fields = True

                if form.cleaned_data.get("password"):
                    password = form.cleaned_data.get("password")
                    confirm_password = form.cleaned_data.get("confirm_password")

                    if password != confirm_password:
                        messages.error(request, "Passwords do not match.")
                        return render(request, 'accounts/interface/setup_password.html', {'form': form})

                    try:
                        validate_password(password, user)
                    except ValidationError as e:
                        for error in e.messages:
                            messages.error(request, error)
                        return render(request, 'accounts/interface/setup_password.html', {'form': form})

                    user.password = make_password(password)
                    user.last_password_reset = now()
                    user.save()
                    user.save()
                    
                    if client_ip:
                        cache.delete(rate_limit_key)

                    messages.success(request, "Password has been set successfully. You can now log in.")
                    return redirect('admin_login_view')
            else:
                messages.error(request, "Email or ID number does not match our records.")
    else:
        form = SetPasswordForm()

    return render(request, 'accounts/interface/setup_password.html', {
        'form': form,
        'show_password_fields': show_password_fields
    })

@login_required
@permission_required('accounts.view_profile', raise_exception=True)
def import_and_export_user_page(request):
    from accounts.utils.pagination_utils import (
        paginate_queryset,
        search_queryset,
        get_pagination_context,
    )

    search_query = request.GET.get('search', '').strip()

    users = Profile.objects.all()

    # Search
    search_fields = [
        'first_name',
        'last_name',
        'email',
        'id_number',
    ]
    users = search_queryset(users, search_query, search_fields)

    # Pagination
    page_obj, paginator = paginate_queryset(users, request, items_per_page=10)
    pagination_context = get_pagination_context(page_obj, request)

    role = request.user.profile.role.name

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'role': role,
        'MEDIA_URL': settings.MEDIA_URL,
    }
    context.update(pagination_context)

    return render(request, 'accounts/interface/import_and_export_user_page.html', context)


# ==================== API ENDPOINTS FOR OTP PASSWORD RESET ====================

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
        logger.debug("OTP verify validation errors: %s", serializer.errors)
        return Response({
            "success": False,
            "errors": serializer.errors
        }, status=400)

    email = serializer.validated_data['email']
    entered_otp = serializer.validated_data['otp']
    logger.info("OTP verify attempt for %s", email)

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
        logger.debug("set_new_password_api validation errors: %s", serializer.errors)
        return Response({
            "success": False,
            "errors": serializer.errors
        }, status=400)

    email = serializer.validated_data['email']
    password = serializer.validated_data['password']

    user = User.objects.filter(email=email).first()
    if not user:
        logger.info("set_new_password_api: user not found for %s", email)
        return Response({
            "success": False,
            "message": "Invalid email address."
        }, status=404)

    try:
        validate_password(password, user)
    except ValidationError as e:
        logger.debug("set_new_password_api validators rejected password for %s", email)
        return Response({
            "success": False,
            "errors": {"password": list(e.messages)}
        }, status=400)

    user.set_password(password)
    user.otp = None
    user.otp_created_at = None
    user.save()
    logger.info("Password reset successful for %s", email)
    
    return Response({
        "success": True,
        "message": "Password reset successful. You can now log in."
    }, status=200)



class MicrosoftLoginAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = [] 

    def get(self, request):
        auth_header = request.headers.get("Authorization", "")

        if not auth_header.startswith("Bearer "):
            return Response({"message": "Missing or invalid Microsoft token"}, status=status.HTTP_400_BAD_REQUEST)

        ms_token = auth_header.split(" ", 1)[1]

        try:
            # 1) Validate token & read payload
            payload = validate_microsoft_token(ms_token)
            email = payload.get("preferred_username") or payload.get("upn")
            given = payload.get("given_name", "")
            family = payload.get("family_name", "")

            if not email:
                return Response({"message": "No email found in Microsoft token"}, status=status.HTTP_400_BAD_REQUEST)

            # 2) Ensure user exists (auto-create if needed)
            user_created = False
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                user = User.objects.create_user(
                    username=email,
                    email=email,
                    password=User.objects.make_random_password()
                )
                user_created = True
            
            # Update user names from Microsoft data (always, not just on creation)
            user.first_name = given
            user.last_name = family
            user.save()
            
            # Get or create profile and update names (matches web OAuth behavior)
            profile, profile_created = Profile.objects.get_or_create(user=user)
            profile.first_name = given
            profile.last_name = family
            profile.save()
            
            # Create/update SocialAccount to link Microsoft account (matches web OAuth)
            from allauth.socialaccount.models import SocialAccount, SocialToken, SocialApp
            microsoft_uid = payload.get("oid") or payload.get("sub")  # Microsoft user ID
            
            if microsoft_uid:
                social_account, sa_created = SocialAccount.objects.get_or_create(
                    user=user,
                    provider='microsoft',
                    uid=microsoft_uid,
                    defaults={'extra_data': payload}
                )
                if not sa_created:
                    # Update extra_data on existing account
                    social_account.extra_data = payload
                    social_account.save()
                
                # Store the Microsoft token (optional but matches web OAuth)
                try:
                    social_app = SocialApp.objects.filter(provider='microsoft').first()
                    if social_app:
                        social_token, st_created = SocialToken.objects.get_or_create(
                            account=social_account,
                            app=social_app,
                            defaults={'token': ms_token}
                        )
                        if not st_created:
                            social_token.token = ms_token
                            social_token.save()
                except Exception:
                    logger.exception("Could not save SocialToken")

            # 3) Issue your own JWT (SimpleJWT)
            refresh = RefreshToken.for_user(user)

            role = None
            try:
                role = getattr(user.profile.role, "name", None) if hasattr(user, "profile") else None
            except Exception:
                logger.exception("Failed to read role for user %s", user.pk)

            refresh["role"] = role if role else None
            refresh["needs_password_setup"] = user.needs_password_setup
            refresh["needs_onboarding"] = user.needs_onboarding
            access = refresh.access_token
            access["role"] = refresh["role"]
            access["needs_password_setup"] = user.needs_password_setup
            access["needs_onboarding"] = user.needs_onboarding

            try:
                powersync_token = generate_powersync_token(user_id=user.id, request=request)
            except Exception as exc:
                return Response(
                    {
                        'message': 'Failed to generate PowerSync token',
                        'error': str(exc)
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            return Response({
                "refresh_token": str(refresh),
                "access_token": str(access),
                "powersync_token": powersync_token,
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"message": f"Invalid Microsoft token: {str(e)}"}, status=status.HTTP_401_UNAUTHORIZED)
    

class SetupPasswordView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [SessionAuthentication, JWTAuthentication]

    def patch(self, request):
        password = request.data.get("password")
        user = request.user
        
        try:
            validate_password(password, user)
        except ValidationError as e:
            return Response({
                "message": "Password validation failed.",
                "errors": list(e.messages)
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Set password and update user
        user.set_password(password)
        user.needs_password_setup = False
        user.save()
        
        # Generate new JWT tokens
        refresh = RefreshToken.for_user(user)
        
        # Add custom claims to refresh token
        refresh['role'] = [user.profile.role.name]
        refresh['needs_password_setup'] = False 
        refresh['needs_onboarding'] = user.needs_onboarding
        
        # Add custom claims to access token
        access_token = refresh.access_token
        access_token['role'] = [user.profile.role.name]
        access_token['needs_password_setup'] = False
        access_token['needs_onboarding'] = user.needs_onboarding
        
        # Calculate token expiry times
        access_lifetime = getattr(settings, 'SIMPLE_JWT', {}).get('ACCESS_TOKEN_LIFETIME', timedelta(minutes=60))
        refresh_lifetime = getattr(settings, 'SIMPLE_JWT', {}).get('REFRESH_TOKEN_LIFETIME', timedelta(days=1))
        
        access_expiry = datetime.now() + access_lifetime
        refresh_expiry = datetime.now() + refresh_lifetime
        
        # Log the activity (optional)
        LoginHistory.objects.create(user=user)

        try:
            powersync_token = generate_powersync_token(user_id=user.id, request=request)
        except Exception as exc:
            return Response(
                {
                    'message': 'Failed to generate PowerSync token',
                    'error': str(exc)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response({
            "message": "Password set successfully.",
            "refresh_token": str(refresh),
            "access_token": str(access_token),
            "powersync_token": powersync_token,
            "access_expiry": int(access_expiry.timestamp()),
            "refresh_expiry": int(refresh_expiry.timestamp()),
        }, status=status.HTTP_200_OK)
    
    
class OnboardingView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [SessionAuthentication, JWTAuthentication]

    def post(self, request):
        user = request.user
        eula_version = request.data.get('eula_version')
        privacy_policy_version = request.data.get('privacy_policy_version')
        
        if not eula_version or not privacy_policy_version:
            return Response({
                "error": "Both EULA version and Privacy Policy version are required."
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if user has already accepted this exact version combination
        existing_consent = UserLegalConsent.objects.filter(
            user=user,
            eula_version=eula_version,
            privacy_policy_version=privacy_policy_version,
            is_accepted=True
        ).first()
        
        if existing_consent:
            # User already accepted this version combination
            return Response({
                "message": "You have already accepted this agreement version.",
                "needs_term_agreement": False
            }, status=status.HTTP_200_OK)
        
        # Create new consent record
        UserLegalConsent.objects.create(
            user=user,
            eula_version=eula_version,
            privacy_policy_version=privacy_policy_version,
            is_accepted=True
        )
        
        # Mark onboarding as complete
        user.needs_onboarding = False
        user.save()

        return Response({
            "message": "Onboarding completed successfully.",
            "needs_term_agreement": True
        }, status=status.HTTP_200_OK)


class UserLegalConsentViewSet(ModelViewSet):
    """
    ViewSet for managing user legal consents (EULA and Privacy Policy).
    
    - List: GET /api/legal-consents/ - Get all consents for authenticated user
    - Retrieve: GET /api/legal-consents/{id}/ - Get specific consent
    - Create: POST /api/legal-consents/ - Create new consent
    - Update: PUT/PATCH /api/legal-consents/{id}/ - Update consent
    - Delete: DELETE /api/legal-consents/{id}/ - Delete consent
    """
    serializer_class = UserLegalConsentSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [SessionAuthentication, JWTAuthentication]
    pagination_class = CustomPagination
    
    def get_queryset(self):
        """Return consents for the authenticated user only."""
        user = self.request.user
        
        # Admin/staff can see all consents
        if user.is_staff or user.is_superuser:
            return UserLegalConsent.objects.all().select_related('user').order_by('-consent_timestamp')
        
        # Regular users can only see their own consents
        return UserLegalConsent.objects.filter(user=user).order_by('-consent_timestamp')
    
    def perform_create(self, serializer):
        """Automatically set the user to the authenticated user."""
        serializer.save(user=self.request.user)
    
    def list(self, request, *args, **kwargs):
        """List all consents with additional metadata."""
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'count': queryset.count(),
            'results': serializer.data
        })
    
    def retrieve(self, request, *args, **kwargs):
        """Retrieve a specific consent record."""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    def create(self, request, *args, **kwargs):
        """Create a new consent record."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        # Mark onboarding as complete
        user = request.user
        user.needs_onboarding = False
        user.save(update_fields=['needs_onboarding'])
        
        return Response({
            'message': 'Legal consent recorded successfully.',
            'data': serializer.data
        }, status=status.HTTP_201_CREATED)
    
    def update(self, request, *args, **kwargs):
        """Update an existing consent record."""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        return Response({
            'message': 'Legal consent updated successfully.',
            'data': serializer.data
        })
    
    def destroy(self, request, *args, **kwargs):
        """Delete a consent record (admin only)."""
        if not request.user.is_staff and not request.user.is_superuser:
            return Response({
                'error': 'Only administrators can delete consent records.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        instance = self.get_object()
        self.perform_destroy(instance)
        
        return Response({
            'message': 'Legal consent deleted successfully.'
        }, status=status.HTTP_204_NO_CONTENT)
