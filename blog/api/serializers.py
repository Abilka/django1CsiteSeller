from slugify import slugify as make_slug
from rest_framework import serializers

from blog.models import BlogPost


class BlogPostSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    slug = serializers.SlugField(required=False, allow_blank=True, max_length=220)

    class Meta:
        model = BlogPost
        fields = (
            'id',
            'title',
            'slug',
            'excerpt',
            'body',
            'cover_image',
            'meta_title',
            'meta_description',
            'is_published',
            'published_at',
            'created_at',
            'updated_at',
            'url',
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'url')

    def get_url(self, obj):
        request = self.context.get('request')
        path = obj.get_absolute_url()
        if request is not None:
            return request.build_absolute_uri(path)
        return path

    def validate_slug(self, value):
        slug = make_slug(value, max_length=220)
        if not slug:
            raise serializers.ValidationError('Укажите корректный slug.')
        return slug

    def validate(self, attrs):
        title = attrs.get('title', getattr(self.instance, 'title', ''))
        slug = attrs.get('slug')
        if not slug and title:
            attrs['slug'] = make_slug(title, max_length=220)
        return attrs

    def create(self, validated_data):
        slug = validated_data.get('slug') or make_slug(validated_data['title'], max_length=220)
        validated_data['slug'] = self._ensure_unique_slug(slug)
        return super().create(validated_data)

    def _ensure_unique_slug(self, slug: str, exclude_pk=None) -> str:
        base = slug
        counter = 1
        while True:
            queryset = BlogPost.objects.filter(slug=slug)
            if exclude_pk is not None:
                queryset = queryset.exclude(pk=exclude_pk)
            if not queryset.exists():
                return slug
            counter += 1
            slug = f'{base}-{counter}'
