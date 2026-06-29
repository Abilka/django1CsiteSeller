from rest_framework import viewsets
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticatedOrReadOnly

from blog.models import BlogPost

from .permissions import IsStaffUser
from .serializers import BlogPostSerializer


class BlogPostViewSet(viewsets.ModelViewSet):
    queryset = BlogPost.objects.all()
    serializer_class = BlogPostSerializer
    lookup_field = 'slug'
    lookup_value_regex = r'[\w.-]+'
    parser_classes = (JSONParser, MultiPartParser, FormParser)

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action in {'list', 'retrieve'} and not self.request.user.is_staff:
            queryset = BlogPost.published.all()
        return queryset

    def get_permissions(self):
        if self.action in {'list', 'retrieve'}:
            return [IsAuthenticatedOrReadOnly()]
        return [IsStaffUser()]
