from rest_framework import serializers
from activity.models import StudentActivity, Activity, RetakeRecord
from .retake_serializers import RetakeRecordSerializers

class ActivitySerializer(serializers.ModelSerializer):
    # `id` is retained for API backward-compatibility; it now mirrors local_id (cuid string).
    id = serializers.CharField(source='local_id', read_only=True)
    # local_id is the primary key (editable=False on the model, which DRF would
    # normally make read-only). We re-declare it as writable+optional so mobile
    # clients doing offline-first sync can send the cuid they generated; if the
    # field is absent or blank, Activity.save() falls back to its cuid default.
    local_id = serializers.CharField(required=False, allow_blank=True, max_length=36)
    lessons = serializers.PrimaryKeyRelatedField(source='additional_modules', many=True, read_only=True)
    activity_type_id = serializers.IntegerField(write_only=True, required=False)
    subject_id = serializers.IntegerField(write_only=True, required=False)
    term_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = Activity
        fields = [
            'id','activity_name','activity_type','activity_type_id','subject','subject_id',
            'term','term_id','lessons','start_time','end_time','show_score','max_score',
            'passing_score','passing_score_type','time_duration','max_retake','retake_method',
            'activity_instruction','classroom_mode','shuffle_questions','is_graded','local_id'
        ]
        extra_kwargs = {
            'activity_type': {'read_only': True},
            'subject': {'read_only': True},
            'term': {'read_only': True},
        }

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        if rep.get('classroom_mode'):
            rep['show_score'] = True
        return rep

    def create(self, validated_data):
        request = self.context.get('request')
        # Use request.headers for case-insensitive lookup. WSGI stores the raw
        # value at request.META['HTTP_X_PLATFORM'], but request.headers hides
        # that HTTP_ prefix convention from us.
        platform = (request.headers.get('X-Platform', '') if request else '').strip().lower()

        # Debug trace: print what mobile sent, and the gate decision. Remove
        # once PowerSync upload path is verified in production.
        raw_data = getattr(request, 'data', None) if request else None
        print('[ActivitySerializer.create] X-Platform header:', repr(platform))
        if request is not None:
            # Dump everything the client actually sent so we can see whether
            # X-Platform is arriving under a different name, being stripped
            # by a proxy, or just missing entirely.
            print('[ActivitySerializer.create] all request.headers:',
                  dict(request.headers))
            meta_http_keys = {
                k: v for k, v in request.META.items() if k.startswith('HTTP_')
            }
            print('[ActivitySerializer.create] HTTP_* in META     :', meta_http_keys)
        print('[ActivitySerializer.create] raw request.data :',
              dict(raw_data) if raw_data is not None else None)
        print('[ActivitySerializer.create] validated_data   :', dict(validated_data))

        # Extract the _id fields and map them to the actual foreign key fields
        activity_type_id = validated_data.pop('activity_type_id', None)
        subject_id = validated_data.pop('subject_id', None)
        term_id = validated_data.pop('term_id', None)

        # Only honor a client-supplied local_id when the caller identifies as
        # the mobile platform (X-Platform: mobile). Any other caller — web,
        # missing header, or a spoofed value — gets the server-generated cuid
        # default so a buggy/rogue client can't hijack the PK.
        incoming_local_id = validated_data.get('local_id')
        if platform != 'mobile' or not incoming_local_id:
            dropped = validated_data.pop('local_id', None)
            print('[ActivitySerializer.create] local_id dropped (platform='
                  f'{platform!r}, value={dropped!r}) -> server will generate cuid')
        else:
            print('[ActivitySerializer.create] local_id honored from mobile:',
                  incoming_local_id)

        if activity_type_id:
            validated_data['activity_type_id'] = activity_type_id
        if subject_id:
            validated_data['subject_id'] = subject_id
        if term_id:
            validated_data['term_id'] = term_id

        if validated_data.get('classroom_mode'):
            validated_data['show_score'] = True

        instance = super().create(validated_data)
        print('[ActivitySerializer.create] saved Activity pk:', instance.pk)
        return instance

class PendingStudentActivitySerializer(serializers.ModelSerializer):
    id = serializers.CharField(source='activity.pk', read_only=True)
    activity_name = serializers.CharField(source='activity.activity_name', read_only=True)
    activity_type = serializers.CharField(source='activity.activity_type.name', read_only=True)
    subject_name = serializers.CharField(source='activity.subject.subject_name', read_only=True)
    start_time = serializers.DateTimeField(source='activity.start_time', read_only=True)
    end_time = serializers.DateTimeField(source='activity.end_time', read_only=True)

    class Meta:
        model = StudentActivity
        fields = [
            'id',
            'activity_name',
            'activity_type',
            'subject_name',
            'start_time',
            'end_time',
            'retake_count',
        ]


class ActivityDetailsSerializer(serializers.ModelSerializer):
    # `id` is retained for API backward-compatibility; it now mirrors local_id (cuid string).
    id = serializers.CharField(source='local_id', read_only=True)
    activity_type_name = serializers.CharField(source='activity_type.name', read_only=True)
    lesson_urls = serializers.SerializerMethodField()
    student_retake_count = serializers.SerializerMethodField()
    remaining_attempts = serializers.SerializerMethodField()
    attempts = serializers.SerializerMethodField()
    ongoing_attempt = serializers.SerializerMethodField()

    class Meta:
        model = Activity
        fields = ['id', 'activity_name', 'activity_type', 'activity_type_name', 'subject_id',
                  'start_time', 'end_time',
                  'show_score', 'max_score', 'passing_score', 'passing_score_type',
                  'time_duration', 'max_retake', 'show_score',
                  'retake_method', 'activity_instruction', 'classroom_mode', 'shuffle_questions',
                  'student_retake_count', 'remaining_attempts', 'lesson_urls', 'attempts', 'ongoing_attempt',
                  ]

    def get_lesson_urls(self, obj):
        request = self.context.get('request')
        return [
            {
                "id": m.id,
                "lesson_name": m.file_name,
                "lesson_url": m.url,
                "lesson_file": request.build_absolute_uri(m.file.url) if m.file and request else None
            }
            for m in obj.additional_modules.all()
        ]

    def get_student_retake_count(self, obj):
        """Return the number of retakes/attempts the student has made."""
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated:
            return 0
        
        # Count how many attempts the student has made
        return RetakeRecord.objects.filter(
            student_activity__activity=obj,
            student_activity__student=user
        ).count()

    def get_remaining_attempts(self, obj):
        """Calculate remaining attempts for the student."""
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated:
            return obj.max_retake
        
        # Count how many attempts the student has made
        attempt_count = RetakeRecord.objects.filter(
            student_activity__activity=obj,
            student_activity__student=user
        ).count()
        
        # Calculate remaining attempts
        remaining = obj.max_retake - attempt_count
        return max(0, remaining)  # Ensure it doesn't go negative

    def get_attempts(self, obj):
        """Return this student's RetakeRecord list for this activity, using the existing serializer."""
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated:
            return []

        # Same filter as your RetakeView: only this student + this activity
        retakes = (
            RetakeRecord.objects
            .filter(student_activity__activity=obj, student_activity__student=user)
            .order_by('-retake_number')
        )

        return RetakeRecordSerializers(retakes, many=True, context=self.context).data

    def get_ongoing_attempt(self, obj):
        """Return the ongoing attempt if one exists."""
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated:
            return None
        
        # Find ongoing attempt
        try:
            ongoing_retake = RetakeRecord.objects.get(
                student_activity__activity=obj,
                student_activity__student=user,
                status='ongoing'
            )
            return RetakeRecordSerializers(ongoing_retake, context=self.context).data
        except RetakeRecord.DoesNotExist:
            return None
        except RetakeRecord.MultipleObjectsReturned:
            # If multiple ongoing attempts exist, return the latest one
            ongoing_retake = RetakeRecord.objects.filter(
                student_activity__activity=obj,
                student_activity__student=user,
                status='ongoing'
            ).order_by('-retake_number').first()
            return RetakeRecordSerializers(ongoing_retake, context=self.context).data if ongoing_retake else None