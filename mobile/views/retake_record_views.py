from rest_framework import status
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication

from activity.models import RetakeRecord, RetakeRecordDetail
from activity.services.auto_grader import (
    grade_detail,
    recompute_retake_record_score,
    recompute_student_activity_total,
)
from mobile.serializers import (
    RetakeRecordSerializer,
    RetakeRecordDetailSerializer,
)


class RetakeRecordViewSet(ModelViewSet):
    """CRUD operations for RetakeRecord objects scoped to the authenticated student."""

    serializer_class = RetakeRecordSerializer
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors, status=status.HTTP_400_BAD_REQUEST
            )

        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return RetakeRecord.objects.none()
        return (
            RetakeRecord.objects.select_related("student_activity", "student")
            .prefetch_related("retake_record_details")
            .filter(student=user)
            .order_by("-retake_time")
        )

    def perform_create(self, serializer):
        serializer.save(student=self.request.user)


class RetakeRecordDetailViewSet(ModelViewSet):
    """CRUD operations for RetakeRecordDetail objects scoped to the authenticated student."""

    serializer_class = RetakeRecordDetailSerializer
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        self.perform_update(serializer)
        return Response(serializer.data)

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return RetakeRecordDetail.objects.none()
        return (
            RetakeRecordDetail.objects.select_related(
                "retake_record",
                "student",
                "activity_question",
            )
            .filter(student=user)
            .order_by("-submission_time")
        )

    def perform_create(self, serializer):
        detail = serializer.save(student=self.request.user)
        self._regrade_chain(detail)

    def perform_update(self, serializer):
        detail = serializer.save()
        self._regrade_chain(detail)

    def _regrade_chain(self, detail):
        """Auto-grade the answer, then propagate the new score up to the
        parent RetakeRecord and StudentActivity.
        """
        grade_detail(detail)
        if detail.retake_record_id:
            recompute_retake_record_score(detail.retake_record)
            sa = detail.retake_record.student_activity
            if sa is not None:
                recompute_student_activity_total(sa)
