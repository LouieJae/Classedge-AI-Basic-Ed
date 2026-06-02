from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.filters import SearchFilter
from accounts.models import DisplayImage
from accounts.serializers import DisplayImageSerializer
from accounts.utils import CustomPagination
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from accounts.views import IsSuperUser

# Login page carousel image
class DisplayImageViewSet(ModelViewSet):
    queryset = DisplayImage.objects.all()
    serializer_class = DisplayImageSerializer
    pagination_class = CustomPagination
    filter_backends = [SearchFilter]
    search_fields = ['name']
    permission_classes = [IsAuthenticated, IsSuperUser]
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()

        if 'image' not in request.data or not request.data['image']:
            mutable_data = request.data.copy() if hasattr(request.data, 'copy') else request.data
            if 'image' in mutable_data:
                mutable_data.pop('image')
            serializer = self.get_serializer(instance, data=mutable_data, partial=partial)
        else:
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def toggle_display(self, request, pk=None):
        display_image = self.get_object()
        display_image.is_displayed = not display_image.is_displayed
        display_image.save()
        return Response({'status': 'success', 'is_displayed': display_image.is_displayed})

@login_required
def display_image_list(request):
    return render(request,'display_image/display_image.html')