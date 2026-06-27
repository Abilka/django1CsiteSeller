from rest_framework import serializers

from landing.models import OneCConfiguration, OneCRelease
from landing.services.update_calculator import normalize_version, parse_from_versions


class OneCReleaseSerializer(serializers.ModelSerializer):
    configuration_slug = serializers.CharField(source='configuration.slug', read_only=True)

    class Meta:
        model = OneCRelease
        fields = (
            'id',
            'configuration',
            'configuration_slug',
            'version',
            'release_date',
            'from_versions',
            'min_platform',
            'sort_order',
        )
        read_only_fields = ('id',)

    def validate_version(self, value):
        version = normalize_version(value)
        if not version:
            raise serializers.ValidationError('Укажите номер релиза.')
        return version

    def validate_from_versions(self, value):
        if isinstance(value, str):
            parsed = parse_from_versions(value)
        elif isinstance(value, list):
            parsed = parse_from_versions(value)
        else:
            raise serializers.ValidationError('Ожидается список версий или строка через запятую.')
        return parsed

    def validate_min_platform(self, value):
        return value.strip().strip(';').strip()


class OneCConfigurationSerializer(serializers.ModelSerializer):
    latest_version = serializers.SerializerMethodField()
    releases_count = serializers.SerializerMethodField()

    class Meta:
        model = OneCConfiguration
        fields = (
            'id',
            'slug',
            'name',
            'is_published',
            'sort_order',
            'latest_version',
            'releases_count',
        )
        read_only_fields = ('id',)

    def get_latest_version(self, obj):
        latest = obj.latest_release
        return latest.version if latest else None

    def get_releases_count(self, obj):
        return obj.releases.count()


class OneCConfigurationDetailSerializer(OneCConfigurationSerializer):
    releases = OneCReleaseSerializer(many=True, read_only=True)

    class Meta(OneCConfigurationSerializer.Meta):
        fields = OneCConfigurationSerializer.Meta.fields + ('releases',)


class CalculateUpdateSerializer(serializers.Serializer):
    configuration = serializers.CharField(
        help_text='slug или id конфигурации',
    )
    current_version = serializers.CharField()

    def validate_current_version(self, value):
        version = normalize_version(value)
        if not version:
            raise serializers.ValidationError('Укажите номер текущего релиза.')
        return version


class UpdatePathResultSerializer(serializers.Serializer):
    configuration_slug = serializers.CharField()
    configuration_name = serializers.CharField()
    current_version = serializers.CharField()
    latest_version = serializers.CharField()
    chain = serializers.ListField(child=serializers.CharField())
    min_platform = serializers.CharField()
    is_up_to_date = serializers.BooleanField()
    steps_count = serializers.IntegerField()
    hourly_rate = serializers.IntegerField()
    hours_per_release = serializers.DecimalField(max_digits=4, decimal_places=2)
    estimated_hours = serializers.DecimalField(max_digits=8, decimal_places=2)
    estimated_price = serializers.IntegerField()
