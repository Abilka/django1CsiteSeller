from rest_framework import status, viewsets
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.views import APIView

from blog.models import BlogPost

from .import_serializers import BlogPostImportSerializer
from .import_service import save_import_chunk
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


class BlogPostImportView(APIView):
    permission_classes = [IsStaffUser]
    parser_classes = (JSONParser, MultiPartParser, FormParser)

    def post(self, request):
        serializer = BlogPostImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = save_import_chunk(serializer.validated_data)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        if result['status'] == 'completed':
            post = BlogPost.objects.get(pk=result['id'])
            response_serializer = BlogPostSerializer(post, context={'request': request})
            return Response(
                response_serializer.data,
                status=status.HTTP_201_CREATED if result['created'] else status.HTTP_200_OK,
            )

        return Response(result, status=status.HTTP_202_ACCEPTED)
