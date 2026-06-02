from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from mobile.serializers import StudentPerSubjectSerializer
from accounts.models import CustomUser

class StudentsPerSubjectView(ListAPIView):
    serializer_class = StudentPerSubjectSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        subject_id = self.kwargs["subject_id"]

        qs = CustomUser.objects.filter(
            subjectenrollment__subject_id=subject_id
        ).order_by('-last_name')

        # Optional filters
        status = self.request.GET.get("status", "enrolled")
        if status:
            qs = qs.filter(subjectenrollment__status=status)

        sem_id = self.request.GET.get("semester_id")
        if sem_id:
            qs = qs.filter(subjectenrollment__semester_id=sem_id)

        cvg = self.request.GET.get("can_view_grade")
        if cvg is not None:
            # accept "1/0/true/false/True/False"
            truthy = {"1","true","yes","on","True","TRUE"}
            qs = qs.filter(subjectenrollment__can_view_grade=(cvg in truthy))

        # Order and dedupe
        qs = qs.order_by("last_name", "first_name").distinct()
        return qs