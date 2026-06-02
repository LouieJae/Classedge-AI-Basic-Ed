from django.shortcuts import render, get_object_or_404
from .serialzers import *
from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import action
from django.db.models import Q
from rest_framework.pagination import PageNumberPagination
from django.core.cache import cache
from rest_framework.decorators import api_view
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from rest_framework.permissions import IsAuthenticated
# Create your views here.

class Post_ViewSet(ModelViewSet):
    serializer_class = Post_Serializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.serializer_class.Meta.model.objects.all()
    

class Share_ViewSet(ModelViewSet):
    serializer_class = Share_Serializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.serializer_class.Meta.model.objects.all()
    

class Like_ViewSet(ModelViewSet):
    serializer_class = Like_Serializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.serializer_class.Meta.model.objects.all()
    
class Comment_ViewSet(ModelViewSet):
    serializer_class = Comment_Serializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.serializer_class.Meta.model.objects.all()
    
class Friend_ViewSet(ModelViewSet):
    serializer_class = Friend_Serializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Friend.objects.filter(to_user=self.request.user)
    
    def create(self, request, *args, **kwargs):
        from_user = request.user
        to_user_id = request.data.get('to_user')

        try:
            to_user = CustomUser.objects.get(id=int(to_user_id))
        except (CustomUser.DoesNotExist, ValueError, TypeError):
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        if from_user == to_user:
            return Response({"error": "You cannot send a friend request to yourself."}, status=status.HTTP_400_BAD_REQUEST)

        # ✅ Check if a request already exists in either direction
        if Friend.objects.filter(
            Q(from_user=from_user, to_user=to_user) | 
            Q(from_user=to_user, to_user=from_user)
        ).exists():
            return Response({"error": "Friend request already exists."}, status=status.HTTP_400_BAD_REQUEST)

        # ✅ All clear – create the friend request
        friend_request = Friend.objects.create(from_user=from_user, to_user=to_user)
        return Response(Friend_Serializer(friend_request).data, status=status.HTTP_201_CREATED)
        

    @action(detail=False, methods=['GET'], url_path='friends')
    def friends(self, request):
        """
        Get the list of friends for the logged-in user.
        """
        user = request.user
        friends = Friend.objects.filter(
            (Q(from_user=user) | Q(to_user=user)) & Q(status='accepted')
        )

        data = []
        for friend in friends:
            friend_user = friend.to_user if friend.from_user == user else friend.from_user
            profile = getattr(friend_user, 'profile', None)

            full_name = f"{friend_user.first_name or ''} {friend_user.last_name or ''}".strip().title() or friend_user.username

            photo = getattr(profile, 'student_photo', None) if profile else None
            photo_url = photo.url if photo else None

            data.append({
                "id": friend_user.id,
                "name": full_name,
                "photo": photo_url,
            })

        return Response(data, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['GET'], url_path='sent-requests')
    def sent_friend_requests(self, request):
        """
        Returns a list of user IDs to whom the logged-in user has sent friend requests.
        """
        user = request.user
        sent_requests = Friend.objects.filter(from_user=user).values_list('to_user_id', flat=True)
        return Response(list(sent_requests), status=status.HTTP_200_OK)


    @action(detail=False, methods=['GET'], url_path='pending-requests')
    def pending_requests(self, request):
        """
        Returns a list of users who have sent friend requests to the logged-in user.
        """
        friend_requests = Friend.objects.filter(to_user=request.user, status='pending').select_related('from_user')
        data = []
        for fr in friend_requests:
            u = fr.from_user
            full_name = f"{u.first_name or ''} {u.last_name or ''}".strip().title() or u.username
            print(full_name)
            profile = getattr(u, 'profile', None)
            photo = getattr(profile, 'photo', None) if profile else None
            photo_url = photo.url if photo else None
            data.append({
                "id": fr.id,
                "from_user_id": u.id,
                "from_user_name": full_name,
                "from_user_photo": photo_url,
            })
        return Response(data, status=status.HTTP_200_OK)
    

    @action(detail=False, methods=['GET'], url_path='suggestions')
    def suggestions(self, request):
        user = request.user
        
        # Get pagination parameters
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))  # Default 20 users per page

        # Exclude users who are already friends (accepted) OR who have a pending
        # request in either direction (so people you've already requested, and
        # people who've requested you, don't show up in "People you may know").
        related = Friend.objects.filter(
            Q(from_user=user) | Q(to_user=user),
            status__in=['accepted', 'pending'],
        ).values_list('from_user_id', 'to_user_id')

        exclude_ids = {user.id}
        for from_id, to_id in related:
            exclude_ids.update([from_id, to_id])

        # Suggest all users except accepted friends and self
        # Use consistent ordering instead of random for pagination
        suggestions_query = CustomUser.objects.exclude(id__in=exclude_ids).order_by('-date_joined', 'id')
        
        # Get total count
        total_count = suggestions_query.count()
        
        # Apply pagination
        start = (page - 1) * page_size
        end = start + page_size
        suggestions = suggestions_query[start:end]

        data = []
        for suggestion in suggestions:
            profile = getattr(suggestion, 'profile', None)
            full_name = f"{suggestion.first_name or ''} {suggestion.last_name or ''}".strip().title() or suggestion.username
            photo = getattr(profile, 'student_photo', None) if profile else None
            photo_url = photo.url if photo else None

            data.append({
                "id": suggestion.id,
                "name": full_name,
                "username": suggestion.username,
                "photo": photo_url,
            })

        return Response({
            "results": data,
            "page": page,
            "page_size": page_size,
            "total_count": total_count,
            "has_next": end < total_count,
            "has_previous": page > 1
        }, status=status.HTTP_200_OK)
    

    @action(detail=False, methods=['GET'], url_path='search')
    def search_users(self, request):
        """
        Search for users by first name, last name, or username
        excluding the current user and already connected users.
        """
        query = request.query_params.get('q', '').strip()
        user = request.user

        if not query:
            return Response([], status=status.HTTP_200_OK)

        # Get friends and request-related IDs to exclude
        connected = Friend.objects.filter(Q(from_user=user) | Q(to_user=user))
        exclude_ids = {user.id}
        for f in connected:
            exclude_ids.add(f.from_user.id)
            exclude_ids.add(f.to_user.id)

        # Search by username or profile name
        users = CustomUser.objects.filter(
            Q(username__icontains=query) |
            Q(profile__first_name__icontains=query) |
            Q(profile__last_name__icontains=query)
        ).exclude(id__in=exclude_ids)

        results = []
        for u in users:
            profile = getattr(u, 'profile', None)
            results.append({
                "id": u.id,
                "first_name": profile.first_name if profile else '',
                "last_name": profile.last_name if profile else '',
                "username": u.username,
                "photo": profile.student_photo.url if profile and profile.student_photo else None,
            })

        return Response(results, status=status.HTTP_200_OK)

        
    
    @action(detail=True, methods=['POST'])
    def accept(self, request, pk=None):
        """
        Accept a friend request.
        """
        try:
            friend_request = self.get_queryset().get(id=pk, to_user=request.user, status='pending')
        except Friend.DoesNotExist:
            return Response({"error": "Friend request not found or already handled."}, status=status.HTTP_404_NOT_FOUND)

        friend_request.status = 'accepted'
        friend_request.save()
        return Response({"message": "Friend request accepted."}, status=status.HTTP_200_OK)


    @action(detail=True, methods=['POST'])
    def reject(self, request, pk=None):
        """
        Reject a friend request.
        """
        try:
            friend_request = self.get_queryset().get(id=pk, to_user=request.user, status='pending')
        except Friend.DoesNotExist:
            return Response({"error": "Friend request not found or already handled."}, status=status.HTTP_404_NOT_FOUND)

        friend_request.delete() 
        return Response({"message": "Friend request rejected."}, status=status.HTTP_200_OK)
    

    @action(detail=False, methods=['POST'], url_path='cancel-request')
    def cancel_request(self, request):
        """
        Cancels a friend request that was previously sent by the user.
        """
        user = request.user
        to_user_id = request.data.get('to_user')

        try:
            to_user = CustomUser.objects.get(id=to_user_id)
            friend_request = Friend.objects.get(from_user=user, to_user=to_user, status='pending')
            friend_request.delete()
            return Response({'message': 'Friend request cancelled.'}, status=status.HTTP_200_OK)
        except (CustomUser.DoesNotExist, Friend.DoesNotExist):
            return Response({'error': 'Friend request not found.'}, status=status.HTTP_404_NOT_FOUND)

    

class Block_ViewSet(ModelViewSet):
    serializer_class = Block_Serializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.serializer_class.Meta.model.objects.all()

class ChatPagination(PageNumberPagination):
    page_size = 10  # Load 5 messages at a time
    page_size_query_param = "page_size"
    max_page_size = 50  # Prevent excessive fetching


class Chat_ViewSet(ModelViewSet):
    serializer_class = Chat_Serializer
    pagination_class = ChatPagination
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        sender_id = self.request.user.id
        receiver_id = self.request.query_params.get('receiver')

        if not receiver_id:
            return Chat.objects.none()

        # Get conversation deletion record for current user
        deleted_at = None
        try:
            deleted_convo = DeletedConversation.objects.get(user_id=sender_id, other_user_id=receiver_id)
            deleted_at = deleted_convo.deleted_at
        except DeletedConversation.DoesNotExist:
            pass

        # Get all messages between sender and receiver
        queryset = Chat.objects.filter(
            Q(sender_id=sender_id, receiver_id=receiver_id) |
            Q(sender_id=receiver_id, receiver_id=sender_id)
        )

        # Exclude per-message soft deletes for current user
        queryset = queryset.exclude(
            Q(sender_id=sender_id, deleted_by_sender=True) |
            Q(receiver_id=sender_id, deleted_by_receiver=True)
        )

        # Exclude all messages before user deleted the conversation
        if deleted_at:
            queryset = queryset.filter(created_at__gt=deleted_at)

        return queryset.order_by('-created_at')



    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True, context={"request": request})
            return self.get_paginated_response(serializer.data)  # ✅ return paginated result

        serializer = self.get_serializer(queryset, many=True, context={"request": request})
        return Response(serializer.data)


    def create(self, request, *args, **kwargs):
        sender = request.user
        receiver_id = request.data.get('receiver')
        message_text = request.data.get('message')
        file = request.FILES.get('file') 

        # Ensure receiver is valid
        receiver = CustomUser.objects.get(id=receiver_id)

        # Create the chat message
        chat_message = Chat.objects.create(
            sender=sender,
            receiver=receiver,
            message=message_text,
            file=file
        )

        return Response(Chat_Serializer(chat_message).data, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['GET'])
    def last_message(self, request):
        user = request.user
        receiver_id = request.query_params.get('receiver')

        if not receiver_id:
            return Response({"message": "Receiver ID is required"}, status=400)

        # Get all messages between both users
        messages = Chat.objects.filter(
            Q(sender_id=user.id, receiver_id=receiver_id) |
            Q(sender_id=receiver_id, receiver_id=user.id)
        ).order_by('-created_at')

        for message in messages:
            # Skip if the message was deleted for this user
            if message.sender_id == user.id and message.deleted_by_sender:
                continue
            if message.receiver_id == user.id and message.deleted_by_receiver:
                continue

            # Serialize and return the first valid message
            serialized_message = Chat_Serializer(message, context={"request": request}).data

            if message.is_deleted:
                unsent_label = "You unsent a message" if message.sender == user else "This message was unsent"
                serialized_message["display_message"] = unsent_label
            elif message.sender == user:
                serialized_message["display_message"] = f"You: {message.message}"
            else:
                serialized_message["display_message"] = f"{message.sender.profile.first_name}: {message.message}"

            return Response(serialized_message)

        return Response({"message": "No messages yet"}, status=200)
    

    @action(detail=False, methods=['POST'])
    def mark_read(self, request):
        receiver_id = int(request.query_params.get('receiver'))
        
        if not receiver_id:
            return Response({"message": "Receiver ID required"}, status=400)

        Chat.objects.filter(
            sender_id=receiver_id,
            receiver_id=request.user.id,
            is_read=False
        ).update(is_read=True)
        
        return Response({"message": "Messages marked as read"})
    

    @action(detail=False, methods=["POST"])
    def delete_conversation(self, request):
        user = request.user
        other_user_id = request.data.get("receiver")

        if not other_user_id:
            return Response({"error": "Receiver ID is required."}, status=400)

        # Mark the conversation as deleted for the current user by creating an entry in DeletedConversation
        DeletedConversation.objects.update_or_create(
            user=user,
            other_user_id=other_user_id,
            defaults={"deleted_at": timezone.now()}
        )

        # Mark the individual messages as deleted for the current user (soft delete)
        Chat.objects.filter(sender=user.id, receiver=other_user_id).update(deleted_by_sender=True)
        Chat.objects.filter(sender=other_user_id, receiver=user.id).update(deleted_by_receiver=True)

        return Response({"message": "Conversation deleted successfully."})

    
    @action(detail=False, methods=["GET"])
    def unread_counts(self, request):
        """
        Get unread message count per contact (grouped by sender)
        """
        user = request.user
        unread_messages = (
            Chat.objects
            .filter(receiver=user, is_read=False)
            .values('sender')
            .annotate(unread_count=Count('id'))
        )

        result = [
            {
                "contact_id": item["sender"],
                "unread_count": item["unread_count"]
            }
            for item in unread_messages
        ]

        return Response(result)


@api_view(["GET"])
@login_required
def check_presence(request):
    """
    Check if a user is online and return their last seen time if offline.
    """
    user_id = request.GET.get("user_id")
    if not user_id:
        return Response({"error": "user_id is required"}, status=400)

    is_online = cache.get(f"user_online_{user_id}", False)
    last_seen = cache.get(f"user_last_seen_{user_id}")

    return Response({
        "user_id": int(user_id),
        "is_online": is_online,
        "last_seen": last_seen
    })


@api_view(['GET'])
@login_required
def get_single_message(request):
    message_id = request.GET.get('message_id')
    try:
        message = Chat.objects.get(id=message_id)
        serializer = Chat_Serializer(message, context={"request": request})
        return Response(serializer.data)
    except Chat.DoesNotExist:
        return Response({"error": "Message not found"}, status=status.HTTP_404_NOT_FOUND)


class Report_ViewSet(ModelViewSet):
    serializer_class = Report_Serializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.serializer_class.Meta.model.objects.all()

class User_ViewSet(ModelViewSet):
    serializer_class = CustomUser_Serializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        friend_ids = Friend.objects.filter(
            Q(from_user=user, status="accepted") | Q(to_user=user, status="accepted")
        ).values_list('from_user_id', 'to_user_id')
        flat_friend_ids = {id for ids in friend_ids for id in ids}
        sent_request_ids = set(Friend.objects.filter(from_user=user).values_list('to_user_id', flat=True))
        excluded_ids = flat_friend_ids.union(sent_request_ids)
        excluded_ids.add(user.id)

        return CustomUser.objects.exclude(id__in=excluded_ids).exclude(is_staff=True)

@login_required
def social_media_inbox(request):
    # NOTE: We intentionally do NOT put a `messages` key in this context.
    # Django's contrib.messages framework already injects a `messages` variable
    # via the context processor, and the global _toast.html partial iterates
    # `{% for m in messages %}` to render flash notifications. Shadowing it
    # with a Chat queryset here caused every chat row to be rendered as a
    # "Notice" toast on page load (each Chat.__str__ returns
    # "sender -> receiver (Read|Unread)"). The inbox loads its actual chat
    # history client-side via the messages API, so no queryset is needed
    # in the initial template context.
    return render(request, 'social_media/social_media_inbox.html', {
        'chat_with': request.GET.get('chat_with'),
        'chat_name': request.GET.get('chat_name'),
        'chat_photo': request.GET.get('chat_photo'),
    })


class GroupChat_ViewSet(ModelViewSet):
    serializer_class = GroupChat_Serializer
    pagination_class = ChatPagination
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # ✅ Only return group chats where the current user is a member
        user = self.request.user
        return GroupChat.objects.filter(members=user)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=["get"], url_path="messages")
    def get_group_messages(self, request):
        from .models import DeletedGroupConversation

        group_id = request.GET.get("group_id")
        if not group_id:
            return Response({"error": "Missing group_id"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            group = GroupChat.objects.get(pk=group_id)
        except GroupChat.DoesNotExist:
            return Response({"error": "Group not found"}, status=status.HTTP_404_NOT_FOUND)

        if request.user not in group.members.all():
            return Response({"error": "You are not a member of this group."}, status=status.HTTP_403_FORBIDDEN)

        # Exclude messages before the user deleted the group conversation
        deleted_at = DeletedGroupConversation.objects.filter(
            user=request.user, group=group
        ).values_list('deleted_at', flat=True).first()

        messages = GroupMessage.objects.filter(group=group)

        if deleted_at:
            messages = messages.filter(created_at__gt=deleted_at)

        messages = messages.order_by('-created_at')

        page = self.paginate_queryset(messages)
        if page is not None:
            serializer = GroupMessageSerializer(page, many=True, context={"request": request})
            return self.get_paginated_response(serializer.data)

        serializer = GroupMessageSerializer(messages, many=True, context={"request": request})
        return Response({"results": serializer.data})


    @action(detail=False, methods=["post"], url_path="delete_conversation", permission_classes=[IsAuthenticated])
    def delete_conversation(self, request):
        from .models import DeletedGroupConversation

        group_id = request.data.get("id")
        user = request.user

        if not group_id:
            return Response({"error": "Missing group_id"}, status=400)

        try:
            group = GroupChat.objects.get(id=group_id)
        except GroupChat.DoesNotExist:
            return Response({"error": "Group not found."}, status=404)

        if not GroupAdmin.objects.filter(group=group, user=user).exists():
            return Response({"error": "Only group admins can do this."}, status=403)

        # Create or update deletion timestamp
        DeletedGroupConversation.objects.update_or_create(
            user=user,
            group=group,
            defaults={'deleted_at': timezone.now()}
        )

        return Response({"message": "Conversation deleted successfully for this user."})
    
    @action(detail=True, methods=["get"], url_path="members", permission_classes=[IsAuthenticated])
    def get_group_members(self, request, pk=None):
        try:
            group = GroupChat.objects.get(pk=pk)
        except GroupChat.DoesNotExist:
            return Response({"error": "Group not found."}, status=status.HTTP_404_NOT_FOUND)

        if request.user not in group.members.all():
            return Response({"error": "You are not a member of this group."}, status=status.HTTP_403_FORBIDDEN)

        admin_ids = set(GroupAdmin.objects.filter(group=group).values_list("user_id", flat=True))
        creator_id = group.created_by_id

        members = group.members.all()
        member_data = []
        for member in members:
            profile = getattr(member, 'profile', None)
            full_name = f"{member.first_name or ''} {member.last_name or ''}".strip().title() or member.username
            if profile and getattr(profile, 'student_photo', None):
                try:
                    photo = request.build_absolute_uri(profile.student_photo.url)
                except Exception:
                    photo = "/static/assets/img/def_user.jpg"
            else:
                photo = "/static/assets/img/def_user.jpg"

            member_data.append({
                "id": member.id,
                "name": full_name,
                "photo": photo,
                "role": "admin" if (member.id in admin_ids or member.id == creator_id) else "member",
                "is_creator": member.id == creator_id,
            })

        return Response({
            "members": member_data,
            "creator_id": creator_id,
            "current_user_is_creator": request.user.id == creator_id,
        }, status=status.HTTP_200_OK)
    

    @action(detail=True, methods=["post"], url_path="remove_member", permission_classes=[IsAuthenticated])
    def remove_member(self, request, pk=None):
        group = get_object_or_404(GroupChat, pk=pk)
        user_to_remove_id = request.data.get("user_id")

        if not user_to_remove_id:
            return Response({"error": "Missing user_id"}, status=400)

        if request.user != group.created_by:
            return Response({"error": "Only the group creator can remove members."}, status=403)

        try:
            user_to_remove = User.objects.get(id=user_to_remove_id)
        except User.DoesNotExist:
            return Response({"error": "User not found."}, status=404)

        if user_to_remove == request.user:
            return Response({"error": "The creator cannot remove themselves. Delete the group instead."}, status=400)

        group.members.remove(user_to_remove)
        GroupAdmin.objects.filter(group=group, user=user_to_remove).delete()

        return Response({"message": f"{user_to_remove.get_full_name()} has been removed from the group."})
    

    @action(detail=True, methods=["post"], url_path="leave", permission_classes=[IsAuthenticated])
    def leave_group(self, request, pk=None):
        group = get_object_or_404(GroupChat, pk=pk)
        user = request.user

        if not group.members.filter(id=user.id).exists():
            return Response({"error": "You are not a member of this group."}, status=403)

        if GroupAdmin.objects.filter(group=group, user=user).exists():
            return Response({"error": "Admins cannot leave the group. Ask another admin to remove you or delete the group."}, status=400)

        group.members.remove(user)

        return Response({"message": "You have left the group."})

    @action(detail=True, methods=["post"], url_path="add_members", permission_classes=[IsAuthenticated])
    def add_members(self, request, pk=None):
        group = get_object_or_404(GroupChat, pk=pk)
        if request.user != group.created_by:
            return Response({"error": "Only the group creator can add members."}, status=403)

        ids = request.data.get("user_ids") or request.data.get("userIds") or []
        if not isinstance(ids, list) or not ids:
            return Response({"error": "user_ids must be a non-empty list."}, status=400)

        added = []
        existing_ids = set(group.members.values_list('id', flat=True))
        for uid in ids:
            try:
                u = CustomUser.objects.get(id=int(uid))
            except (CustomUser.DoesNotExist, ValueError, TypeError):
                continue
            if u.id in existing_ids:
                continue
            group.members.add(u)
            added.append({"id": u.id, "name": u.get_full_name() or u.username})
        return Response({"added": added}, status=200)

    @action(detail=True, methods=["get"], url_path="eligible_users", permission_classes=[IsAuthenticated])
    def eligible_users(self, request, pk=None):
        group = get_object_or_404(GroupChat, pk=pk)
        if request.user != group.created_by:
            return Response({"error": "Only the group creator can view eligible users."}, status=403)

        accepted = Friend.objects.filter(
            Q(from_user=request.user) | Q(to_user=request.user),
            status='accepted'
        )
        friend_ids = set()
        for f in accepted:
            friend_ids.add(f.from_user_id)
            friend_ids.add(f.to_user_id)
        friend_ids.discard(request.user.id)
        friend_ids -= set(group.members.values_list('id', flat=True))

        users = CustomUser.objects.filter(id__in=friend_ids).order_by('first_name', 'last_name', 'username')
        q = (request.query_params.get('q') or '').strip()
        if q:
            users = users.filter(
                Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(username__icontains=q)
            )

        data = []
        for u in users[:50]:
            profile = getattr(u, 'profile', None)
            photo = getattr(profile, 'student_photo', None) if profile else None
            try:
                photo_url = request.build_absolute_uri(photo.url) if photo else None
            except Exception:
                photo_url = None
            full_name = f"{u.first_name or ''} {u.last_name or ''}".strip().title() or u.username
            data.append({"id": u.id, "name": full_name, "photo": photo_url})
        return Response(data, status=200)

    @action(detail=False, methods=["get"], url_path="teacher_subjects", permission_classes=[IsAuthenticated])
    def teacher_subjects(self, request):
        """Subjects the current user teaches in the active semester.

        Used by the inbox 'Create group' modal to offer a one-click
        'message my class' option. Includes student count so the UI can
        show '(24 students)' next to each subject.
        """
        from subject.models.subject_model import Subject
        from course.models.semester_model import Semester
        from course.models.subject_enrollment_model import SubjectEnrollment

        current_sem = Semester.objects.filter(end_semester=False).order_by('-start_date').first()
        if not current_sem:
            return Response([], status=200)

        user = request.user
        subjects = Subject.objects.filter(
            Q(assign_teacher=user) | Q(substitute_teacher=user) | Q(collaborators=user)
        ).distinct()

        data = []
        for s in subjects:
            count = SubjectEnrollment.objects.filter(
                subject=s, semester=current_sem, is_active_semester=True, status='enrolled'
            ).exclude(student__isnull=True).count()
            if count <= 0:
                continue
            data.append({
                'id': s.id,
                'name': getattr(s, 'subject_name', None) or str(s),
                'student_count': count,
                'semester': current_sem.semester_name,
            })
        return Response(data, status=200)

    @action(detail=False, methods=["post"], url_path="create_from_subject", permission_classes=[IsAuthenticated])
    def create_from_subject(self, request):
        """Create a group chat from a subject's current-semester roster.

        Body: { subject_id, name (optional) }. The teacher (current user)
        is added as a member and as the creator. Students with `enrolled`
        status in the current active semester become the rest of the
        membership.
        """
        from subject.models.subject_model import Subject
        from course.models.semester_model import Semester
        from course.models.subject_enrollment_model import SubjectEnrollment

        subject_id = request.data.get('subject_id') or request.data.get('subjectId')
        if not subject_id:
            return Response({"error": "subject_id is required."}, status=400)

        try:
            subject = Subject.objects.get(id=int(subject_id))
        except (Subject.DoesNotExist, ValueError, TypeError):
            return Response({"error": "Subject not found."}, status=404)

        user = request.user
        is_teacher_of_subject = (
            subject.assign_teacher_id == user.id
            or subject.substitute_teacher_id == user.id
            or subject.collaborators.filter(id=user.id).exists()
        )
        if not is_teacher_of_subject:
            return Response({"error": "You do not teach this subject."}, status=403)

        current_sem = Semester.objects.filter(end_semester=False).order_by('-start_date').first()
        if not current_sem:
            return Response({"error": "No active semester."}, status=400)

        student_ids = SubjectEnrollment.objects.filter(
            subject=subject, semester=current_sem, is_active_semester=True, status='enrolled'
        ).exclude(student__isnull=True).values_list('student_id', flat=True)

        student_ids = [sid for sid in student_ids if sid and sid != user.id]
        if not student_ids:
            return Response({"error": "No enrolled students for this subject this semester."}, status=400)

        default_name = f"{getattr(subject, 'subject_name', None) or 'Class'} — {current_sem.semester_name}"
        name = (request.data.get('name') or '').strip() or default_name

        group = GroupChat.objects.create(name=name, created_by=user)
        group.members.add(user, *student_ids)
        if request.FILES.get('photo'):
            group.photo = request.FILES['photo']
            group.save()

        return Response({
            "id": group.id,
            "name": group.name,
            "member_count": group.members.count(),
        }, status=201)

    @action(detail=True, methods=["post"], url_path="mark_read", permission_classes=[IsAuthenticated])
    def mark_read(self, request, pk=None):
        group = get_object_or_404(GroupChat, pk=pk)
        if request.user not in group.members.all():
            return Response({"error": "Not a member."}, status=403)

        ids = request.data.get("message_ids") or request.data.get("messageIds") or []
        if not isinstance(ids, list):
            return Response({"error": "message_ids must be a list."}, status=400)

        # Only mark messages that belong to this group and weren't sent by the user.
        msg_qs = GroupMessage.objects.filter(group=group, id__in=ids).exclude(sender=request.user)
        existing = set(
            GroupMessageRead.objects.filter(user=request.user, message_id__in=ids)
            .values_list('message_id', flat=True)
        )
        to_create = [
            GroupMessageRead(message=m, user=request.user)
            for m in msg_qs if m.id not in existing
        ]
        if to_create:
            GroupMessageRead.objects.bulk_create(to_create, ignore_conflicts=True)
        return Response({"marked": len(to_create)}, status=200)


@login_required
def social_media_friends(request):
    return render(request, 'social_media/social_media_friends.html')
