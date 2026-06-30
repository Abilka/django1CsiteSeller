from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from landing.models import MigrationPath, OneCConfiguration
from landing.tools.migration_calc import estimate_migration
from landing.tools.platform_check import PlatformCheckError, check_platform_compatibility
from landing.tools.query_formatter import format_query
from landing.tools.release_feed import get_release_feed
from landing.tools.task_estimator import estimate_tasks


class PlatformCheckSerializer(serializers.Serializer):
    configuration = serializers.CharField()
    platform_version = serializers.CharField()
    target_release = serializers.CharField(required=False, allow_blank=True)
    current_release = serializers.CharField(required=False, allow_blank=True)


class TaskEstimatorSerializer(serializers.Serializer):
    typical_task_ids = serializers.ListField(child=serializers.IntegerField(), required=False, default=list)
    price_item_ids = serializers.ListField(child=serializers.IntegerField(), required=False, default=list)


class QueryFormatterSerializer(serializers.Serializer):
    query = serializers.CharField(allow_blank=True)


class MigrationCalcSerializer(serializers.Serializer):
    migration_path = serializers.CharField()


class ReleaseFeedSerializer(serializers.Serializer):
    days = serializers.IntegerField(required=False, default=90, min_value=1, max_value=365)
    configuration = serializers.CharField(required=False, allow_blank=True)


def _resolve_configuration(ref: str) -> OneCConfiguration | None:
    if ref.isdigit():
        return OneCConfiguration.objects.filter(pk=int(ref), is_published=True).first()
    return OneCConfiguration.objects.filter(slug=ref, is_published=True).first()


class PlatformCheckToolView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = PlatformCheckSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        configuration = _resolve_configuration(serializer.validated_data['configuration'])
        if configuration is None:
            return Response({'detail': 'Конфигурация не найдена.', 'code': 'not_found'}, status=status.HTTP_404_NOT_FOUND)
        try:
            result = check_platform_compatibility(
                configuration,
                serializer.validated_data['platform_version'],
                serializer.validated_data.get('target_release') or None,
                serializer.validated_data.get('current_release') or None,
            )
        except PlatformCheckError as exc:
            return Response({'detail': str(exc), 'code': exc.code}, status=status.HTTP_400_BAD_REQUEST)
        return Response(result.__dict__)


class TaskEstimatorToolView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = TaskEstimatorSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = estimate_tasks(
            serializer.validated_data.get('typical_task_ids', []),
            serializer.validated_data.get('price_item_ids', []),
        )
        return Response({
            'items': [item.__dict__ for item in result.items],
            'total_hours': result.total_hours,
            'total_price': result.total_price,
            'hourly_rate': result.hourly_rate,
        })


class QueryFormatterToolView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = QueryFormatterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = format_query(serializer.validated_data.get('query', ''))
        return Response(result.__dict__)


class MigrationCalcToolView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = MigrationCalcSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        path = MigrationPath.objects.filter(
            slug=serializer.validated_data['migration_path'],
            is_published=True,
        ).prefetch_related('steps').first()
        if path is None:
            return Response({'detail': 'Маршрут миграции не найден.', 'code': 'not_found'}, status=status.HTTP_404_NOT_FOUND)
        result = estimate_migration(path)
        return Response({
            'path_slug': result.path_slug,
            'path_name': result.path_name,
            'source_name': result.source_name,
            'target_name': result.target_name,
            'description': result.description,
            'steps': [step.__dict__ for step in result.steps],
            'total_hours': result.total_hours,
            'total_price': result.total_price,
            'hourly_rate': result.hourly_rate,
        })


class ReleaseFeedToolView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        serializer = ReleaseFeedSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        items = get_release_feed(
            days=serializer.validated_data['days'],
            configuration_slug=serializer.validated_data.get('configuration') or None,
        )
        return Response({
            'items': [item.__dict__ for item in items],
            'count': len(items),
        })
