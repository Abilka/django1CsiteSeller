from rest_framework import serializers


class BlogPostImportSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200)
    slug = serializers.SlugField(required=False, allow_blank=True, max_length=220)
    excerpt = serializers.CharField(required=False, allow_blank=True)
    meta_title = serializers.CharField(required=False, allow_blank=True, max_length=70)
    meta_description = serializers.CharField(required=False, allow_blank=True, max_length=160)
    is_published = serializers.BooleanField(required=False, default=False)
    published_at = serializers.DateTimeField(required=False, allow_null=True)
    chunk_index = serializers.IntegerField(min_value=0)
    chunk_total = serializers.IntegerField(min_value=1)
    body_chunk = serializers.CharField(allow_blank=True, trim_whitespace=False)

    def validate(self, attrs):
        if attrs['chunk_index'] >= attrs['chunk_total']:
            raise serializers.ValidationError('chunk_index должен быть меньше chunk_total.')
        return attrs
