from rest_framework import serializers
from .models import *
from accounts.models import CustomUser
from django.utils.timezone import localtime, now
from django.utils import timezone

User = CustomUser

class Post_Serializer(serializers.ModelSerializer):
    class Meta:
        model = Post
        fields = '__all__'

class Share_Serializer(serializers.ModelSerializer):
    class Meta:
        model = Share
        fields = '__all__'

class Like_Serializer(serializers.ModelSerializer):
    class Meta:
        model = Like
        fields = '__all__'

class Comment_Serializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = '__all__'

class Friend_Serializer(serializers.ModelSerializer):
    class Meta:
        model = Friend
        fields = '__all__'

class Block_Serializer(serializers.ModelSerializer):
    class Meta:
        model = Block
        fields = '__all__'

class Report_Serializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = '__all__'

class Chat_Serializer(serializers.ModelSerializer):
    sender_name = serializers.SerializerMethodField()
    sender_photo = serializers.SerializerMethodField()
    sender_id = serializers.IntegerField(source='sender.id', read_only=True)
    receiver_name = serializers.SerializerMethodField()
    receiver_photo = serializers.SerializerMethodField()
    is_sent = serializers.SerializerMethodField()
    formatted_time = serializers.SerializerMethodField()
    is_read = serializers.BooleanField(read_only=True)
    is_deleted = serializers.BooleanField(read_only=True)
    file = serializers.FileField(read_only=True)
    is_edited = serializers.BooleanField(read_only=True)
    reply_to = serializers.SerializerMethodField()
    reactions = serializers.SerializerMethodField()

    class Meta:
        model = Chat
        fields = ['id', 'sender', 'sender_id', 'receiver', 'message', 'created_at', 'formatted_time', 'sender_name',
                'sender_photo','receiver_name', 'receiver_photo', 'is_sent', 'is_read', 'is_deleted',
                'file','is_edited', 'reply_to' , 'reactions'
                ]

    def get_sender_name(self, obj):
        """Return sender's full name or username"""
        if hasattr(obj.sender, 'profile') and obj.sender.profile.first_name:
            return f"{obj.sender.profile.first_name} {obj.sender.profile.last_name}".strip()
        return obj.sender.username

    def get_sender_photo(self, obj):
        """Return the sender's profile image full URL"""
        request = self.context.get('request')
        if hasattr(obj.sender, 'profile') and obj.sender.profile.student_photo:
            photo_url = obj.sender.profile.student_photo.url
            return request.build_absolute_uri(photo_url) if request else photo_url
        return None
    
    def get_receiver_name(self, obj):
        """Return receiver's full name or username"""
        if hasattr(obj.receiver, 'profile') and obj.receiver.profile.first_name:
            return f"{obj.receiver.profile.first_name} {obj.receiver.profile.last_name}".strip()
        return obj.receiver.username

    def get_receiver_photo(self, obj):
        """Return the receiver's profile image full URL"""
        request = self.context.get('request')
        if hasattr(obj.receiver, 'profile') and obj.receiver.profile.student_photo:
            photo_url = obj.receiver.profile.student_photo.url
            return request.build_absolute_uri(photo_url) if request else photo_url
        return "/static/assets/dist/images/def_user.jpg"
    
    def get_is_sent(self, obj):
        """Check if the logged-in user is the sender. Compare by PK to
        avoid model-instance equality edge cases."""
        request = self.context.get("request")
        if request and getattr(request, "user", None) and getattr(request.user, "is_authenticated", False):
            return obj.sender_id == request.user.id
        return False

    def get_formatted_time(self, obj):
        local_created_at = localtime(obj.created_at)
        today = localtime(now()).date()

        if local_created_at.date() == today:
            return local_created_at.strftime("%I:%M %p") 
        return local_created_at.strftime("%b %d, %Y")
    
    def to_representation(self, instance):
        """Customize representation to replace deleted message text"""
        rep = super().to_representation(instance)

        if instance.is_deleted:
            rep["message"] = "This message was unsent"
            rep["is_deleted"] = True
            rep["file"] = None
        else:
            rep["is_deleted"] = False

        return rep
    
    def get_reply_to(self, obj):
        if obj.reply_to:
            if obj.reply_to.is_deleted:
                return {
                    "id": obj.reply_to.id,
                    "message": "This message was unsent",
                    "sender_name": self.get_sender_name(obj.reply_to),
                    "file": None
                }
            file_url = None
            if obj.reply_to.file:
                request = self.context.get('request')
                file_url = request.build_absolute_uri(obj.reply_to.file.url) if request else obj.reply_to.file.url
            return {
                "id": obj.reply_to.id,
                "message": obj.reply_to.message,
                "sender_name": self.get_sender_name(obj.reply_to),
                "file": file_url
            }
        return None
    
    def get_reactions(self, obj):
        return [
            {
                "emoji": reaction.emoji,
                "user_id": reaction.user.id
            }
            for reaction in obj.reactions.all()
        ]
    

class CustomUser_Serializer(serializers.ModelSerializer):
    student_photo = serializers.SerializerMethodField()
    class Meta:
        model = CustomUser
        fields = ['id', 'first_name', 'last_name', 'username', 'email','student_photo'] 

    def get_student_photo(self, obj):
        if hasattr(obj, 'profile') and obj.profile.student_photo:
            return obj.profile.student_photo.url
        return None
    

class GroupChat_Serializer(serializers.ModelSerializer):
    members = serializers.PrimaryKeyRelatedField( many=True, queryset=User.objects.all())
    photo = serializers.ImageField(required=False, allow_null=True)
    last_message = serializers.SerializerMethodField()
    


    class Meta:
        model = GroupChat
        fields = '__all__'
        read_only_fields = ['created_by']

    def validate_members(self, members):
        request = self.context.get('request')
        if not request:
            return members

        user_id = request.user.id
        friend_ids = set()

        accepted_friends = Friend.objects.filter(
            models.Q(from_user=user_id) | models.Q(to_user=user_id),
            status='accepted'
        )

        for friend in accepted_friends:
            # Add the friend’s user ID (not the current user) to the set
            friend_ids.add(friend.to_user.id if friend.from_user.id == user_id else friend.from_user.id)

        for member in members:
            if member.id != user_id and member.id not in friend_ids:
                raise serializers.ValidationError(f"{member.username} is not your friend.")

        return members

    def create(self, validated_data):
        request = self.context.get('request')
        creator = request.user
        validated_data['created_by'] = creator

        # Extract members from validated_data before creating the group
        members = validated_data.pop('members', [])

        # ✅ Create the group without members yet
        group = GroupChat.objects.create(**validated_data)

        # ✅ Set members and include the creator (avoid duplicates using set)
        group.members.set(set(members + [creator]))

        GroupAdmin.objects.create(group=group, user=creator)

        return group

    
    def get_last_message(self, obj):
        latest = obj.messages.order_by('-created_at').first()
        if latest:
            return GroupMessageSerializer(latest, context=self.context).data
        return None
    
    

class GroupMessageReactionSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source='user.id')

    class Meta:
        model = GroupMessageReaction
        fields = ['user_id', 'emoji']

class GroupMessageSerializer(serializers.ModelSerializer):
    sender_id = serializers.IntegerField(source='sender.id', read_only=True)
    sender_name = serializers.CharField(source='sender.get_full_name', read_only=True)
    sender_photo = serializers.SerializerMethodField()
    is_image = serializers.SerializerMethodField()
    formatted_time = serializers.SerializerMethodField()
    is_sent = serializers.SerializerMethodField()
    is_deleted = serializers.BooleanField()
    deleted_by_name = serializers.SerializerMethodField()
    reply_to = serializers.SerializerMethodField()
    reactions = GroupMessageReactionSerializer(many=True, read_only=True)
    read_by = serializers.SerializerMethodField()

    class Meta:
        model = GroupMessage
        fields = ['id', 'group', 'sender', 'sender_id', 'sender_name', 'sender_photo', 'message', 'file',
                    'is_image', 'created_at','formatted_time','is_sent', 'is_deleted','deleted_by_name','reply_to',
                    'reactions', 'read_by']

    def get_read_by(self, obj):
        request = self.context.get('request')
        reads = obj.reads.select_related('user', 'user__profile').exclude(user_id=obj.sender_id)
        out = []
        for r in reads:
            u = r.user
            full_name = f"{u.first_name or ''} {u.last_name or ''}".strip().title() or u.username
            profile = getattr(u, 'profile', None)
            photo = getattr(profile, 'student_photo', None) if profile else None
            photo_url = None
            if photo:
                try:
                    photo_url = request.build_absolute_uri(photo.url) if request else photo.url
                except Exception:
                    photo_url = None
            out.append({
                'id': u.id,
                'name': full_name,
                'photo': photo_url,
                'read_at': r.read_at.isoformat(),
            })
        return out

    def get_sender_photo(self, obj):
        try:
            return obj.sender.profile.student_photo.url if obj.sender.profile.student_photo else None
        except AttributeError:
            return None
    
    def get_is_image(self, obj):
        if obj.file:
            return obj.file.name.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp'))
        return False
    
    def get_formatted_time(self, obj):
        if obj.created_at:
            # Convert to local time if needed, then format
            local_time = timezone.localtime(obj.created_at)
            return local_time.strftime('%I:%M %p').lstrip('0')  # e.g., 10:27 AM
        return None
    
    def get_is_sent(self, obj):
        request = self.context.get('request', None)
        if request:
            return obj.sender_id == request.user.id
        return False
    
    def get_deleted_by_name(self, obj):
        return obj.deleted_by.get_full_name() if obj.deleted_by else None
    
    def get_reply_to(self, obj):
        if obj.reply_to:
            file_url = None
            if obj.reply_to.file:
                file_url = obj.reply_to.file.url
            return {
                'id': obj.reply_to.id,
                'sender_name': obj.reply_to.sender.get_full_name(),
                'message': obj.reply_to.message,
                'file': file_url
            }
        return None
    
