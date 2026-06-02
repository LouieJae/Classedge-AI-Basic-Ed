from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.shortcuts import render
from django.contrib.auth.decorators import login_required, permission_required
from subject.models import SubjectGradeFinalization, Subject
from course.models import Semester, SubjectEnrollment
from django.db.models import Q
from subject.serializers.grade_finalization_serializers import (
    SubjectGradeFinalizationSerializer,
    SubjectGradeFinalizationListSerializer
)
from accounts.utils import CustomPagination


class SubjectGradeFinalizationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing grade finalization status for subjects per semester.
    
    Endpoints:
    - GET /api/grade-finalization/ - List all finalization records
    - POST /api/grade-finalization/ - Create new finalization record
    - GET /api/grade-finalization/{id}/ - Retrieve specific record
    - PUT/PATCH /api/grade-finalization/{id}/ - Update finalization status
    - DELETE /api/grade-finalization/{id}/ - Delete finalization record
    - POST /api/grade-finalization/{id}/finalize/ - Mark as finalized
    - POST /api/grade-finalization/{id}/unfinalize/ - Mark as not finalized
    - GET /api/grade-finalization/by-semester/{semester_id}/ - Get all for a semester
    """
    queryset = SubjectGradeFinalization.objects.select_related(
        'subject', 'semester', 'finalized_by'
    ).all()
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPagination
    
    def get_serializer_class(self):
        if self.action == 'list':
            return SubjectGradeFinalizationListSerializer
        return SubjectGradeFinalizationSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by semester if provided
        semester_id = self.request.query_params.get('semester')
        if semester_id:
            queryset = queryset.filter(semester_id=semester_id)
        
        # Filter by subject if provided
        subject_id = self.request.query_params.get('subject')
        if subject_id:
            queryset = queryset.filter(subject_id=subject_id)
        
        # Filter by finalization status if provided
        is_finalized = self.request.query_params.get('is_finalized')
        if is_finalized is not None:
            queryset = queryset.filter(is_finalized=is_finalized.lower() == 'true')
        
        return queryset.order_by('-semester__start_date', 'subject__subject_name')
    
    def perform_create(self, serializer):
        # Don't set finalized_by on creation, only when finalizing
        serializer.save()

    def create(self, request, *args, **kwargs):
        """Idempotent create / upsert.

        `SubjectGradeFinalization` has `unique_together = ('subject', 'semester')`,
        so a second POST for the same pair would otherwise hit the auto-attached
        UniqueTogetherValidator and surface as HTTP 409 Conflict. The grade-
        finalization page POSTs here with `is_finalized=true` to finalize a
        subject that has no tracking row yet — so if the row already exists,
        we apply the requested `is_finalized` state to it and return 200.
        """
        subject_id = request.data.get('subject') or request.data.get('subject_id')
        semester_id = request.data.get('semester') or request.data.get('semester_id')

        # Coerce to int defensively — JSON ints come through as ints, but form
        # posts come through as strings.
        try:
            subject_id = int(subject_id) if subject_id is not None else None
            semester_id = int(semester_id) if semester_id is not None else None
        except (TypeError, ValueError):
            subject_id = semester_id = None

        if subject_id and semester_id:
            existing = SubjectGradeFinalization.objects.filter(
                subject_id=subject_id, semester_id=semester_id,
            ).select_related('subject', 'semester', 'finalized_by').first()
            if existing is not None:
                requested_state = request.data.get('is_finalized')
                if requested_state is not None and bool(requested_state) != existing.is_finalized:
                    existing.is_finalized = bool(requested_state)
                    if existing.is_finalized:
                        existing.finalized_at = timezone.now()
                        existing.finalized_by = request.user
                    else:
                        existing.finalized_at = None
                        existing.finalized_by = None
                    existing.save()
                serializer = self.get_serializer(existing)
                return Response(serializer.data, status=status.HTTP_200_OK)

        return super().create(request, *args, **kwargs)
    
    @action(detail=True, methods=['post'], url_path='finalize')
    def finalize_grades(self, request, pk=None):
        """
        Mark grades as finalized for this subject-semester combination.
        Sets is_finalized=True, records timestamp and user.
        """
        finalization = self.get_object()
        
        if finalization.is_finalized:
            return Response(
                {'message': 'Grades are already finalized for this subject.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        finalization.is_finalized = True
        finalization.finalized_at = timezone.now()
        finalization.finalized_by = request.user
        finalization.save()
        
        serializer = self.get_serializer(finalization)
        return Response({
            'message': 'Grades successfully finalized.',
            'data': serializer.data
        }, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'], url_path='unfinalize')
    def unfinalize_grades(self, request, pk=None):
        """
        Mark grades as not finalized for this subject-semester combination.
        Sets is_finalized=False, clears timestamp and user.
        """
        finalization = self.get_object()
        
        if not finalization.is_finalized:
            return Response(
                {'message': 'Grades are already not finalized for this subject.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        finalization.is_finalized = False
        finalization.finalized_at = None
        finalization.finalized_by = None
        finalization.save()
        
        serializer = self.get_serializer(finalization)
        return Response({
            'message': 'Grades successfully unfinalized.',
            'data': serializer.data
        }, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'], url_path='by-semester/(?P<semester_id>[^/.]+)')
    def by_semester(self, request, semester_id=None):
        """
        Get all finalization records for a specific semester.
        """
        queryset = self.get_queryset().filter(semester_id=semester_id)
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'], url_path='bulk-finalize')
    def bulk_finalize(self, request):
        """
        Finalize multiple subjects at once.
        Expects: {"subject_ids": [1, 2, 3], "semester_id": 1}
        """
        subject_ids = request.data.get('subject_ids', [])
        semester_id = request.data.get('semester_id')
        
        if not subject_ids or not semester_id:
            return Response(
                {'error': 'subject_ids and semester_id are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            semester = Semester.objects.get(id=semester_id)
        except Semester.DoesNotExist:
            return Response(
                {'error': 'Semester not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        finalized_count = 0
        created_count = 0
        
        for subject_id in subject_ids:
            try:
                subject = Subject.objects.get(id=subject_id)
                finalization, created = SubjectGradeFinalization.objects.get_or_create(
                    subject=subject,
                    semester=semester,
                    defaults={
                        'is_finalized': True,
                        'finalized_at': timezone.now(),
                        'finalized_by': request.user
                    }
                )
                
                if created:
                    created_count += 1
                    finalized_count += 1
                elif not finalization.is_finalized:
                    finalization.is_finalized = True
                    finalization.finalized_at = timezone.now()
                    finalization.finalized_by = request.user
                    finalization.save()
                    finalized_count += 1
                    
            except Subject.DoesNotExist:
                continue
        
        return Response({
            'message': f'Successfully finalized {finalized_count} subjects ({created_count} new records created).',
            'finalized_count': finalized_count,
            'created_count': created_count
        }, status=status.HTTP_200_OK)


@login_required
@permission_required('subject.view_subjectenrollment', raise_exception=True)
def grade_finalization_page(request):
    """
    Render the grade finalization management page.
    """
    semesters = Semester.objects.all().order_by('-start_date')
    
    # Get current active semester
    today = timezone.localdate()
    current_semester = Semester.objects.filter(
        start_date__lte=today,
        end_date__gte=today
    ).first()
    
    if not current_semester and semesters.exists():
        current_semester = semesters.first()

    # Allow overriding via ?semester=<id>
    selected_id = request.GET.get('semester')
    selected_semester = current_semester
    if selected_id:
        selected_semester = Semester.objects.filter(id=selected_id).first() or current_semester

    subject_rows = []
    finalized_count = 0
    if selected_semester:
        subject_qs = (
            Subject.objects
            .filter(subjectenrollment__semester=selected_semester)
            .filter(gradebook_components__isnull=False)
            .select_related('assign_teacher', 'assign_teacher__profile')
            .distinct()
            .order_by('subject_name')
        )

        role = getattr(request.user, 'role_name', None)
        if role == 'teacher':
            subject_qs = subject_qs.filter(
                Q(assign_teacher=request.user) |
                Q(substitute_teacher=request.user, allow_substitute_teacher=True) |
                Q(collaborators=request.user)
            ).distinct()

        finalizations = SubjectGradeFinalization.objects.filter(
            semester=selected_semester,
            subject__in=subject_qs,
        ).select_related('finalized_by', 'finalized_by__profile')
        finalization_map = {f.subject_id: f for f in finalizations}

        for subj in subject_qs:
            teacher = subj.assign_teacher
            if teacher:
                profile = getattr(teacher, 'profile', None)
                first = (getattr(profile, 'first_name', '') or teacher.first_name or '').strip()
                last = (getattr(profile, 'last_name', '') or teacher.last_name or '').strip()
                teacher_name = (f"{first} {last}".strip()) or teacher.get_username()
            else:
                teacher_name = 'Unassigned'

            fin = finalization_map.get(subj.id)
            is_finalized = bool(fin and fin.is_finalized)
            if is_finalized:
                finalized_count += 1

            finalized_by_name = None
            if fin and fin.finalized_by:
                fb = fin.finalized_by
                fb_profile = getattr(fb, 'profile', None)
                fb_first = (getattr(fb_profile, 'first_name', '') or fb.first_name or '').strip()
                fb_last = (getattr(fb_profile, 'last_name', '') or fb.last_name or '').strip()
                finalized_by_name = (f"{fb_first} {fb_last}".strip()) or fb.get_username()

            subject_rows.append({
                'id': subj.id,
                'subject_name': subj.subject_name,
                'subject_code': subj.subject_code,
                'teacher_name': teacher_name,
                'is_finalized': is_finalized,
                'finalization_id': fin.id if fin else None,
                'finalized_at': fin.finalized_at if fin else None,
                'finalized_by_name': finalized_by_name,
            })

    total = len(subject_rows)
    context = {
        'semesters': semesters,
        'current_semester': current_semester,
        'selected_semester': selected_semester,
        'subject_rows': subject_rows,
        'stat_total': total,
        'stat_finalized': finalized_count,
        'stat_pending': total - finalized_count,
    }

    return render(request, 'subject/grade_finalization.html', context)
