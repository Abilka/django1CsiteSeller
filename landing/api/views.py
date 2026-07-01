from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from landing.models import OneCConfiguration, OneCRelease
from landing.services.update_calculator import UpdatePathError, UpdatePathResult, calculate_update_path
from landing.services.version_utils import sort_versions_newest_first

from .serializers import (
    CalculateUpdateSerializer,
    OneCConfigurationDetailSerializer,
    OneCConfigurationSerializer,
    OneCReleaseSerializer,
    UpdatePathResultSerializer,
)


def _serialize_update_result(result: UpdatePathResult) -> dict:
    payload = result.__dict__.copy()
    payload['chain'] = [
        {'version': step.version, 'url': step.url}
        for step in result.chain
    ]
    return payload


class OneCConfigurationViewSet(viewsets.ModelViewSet):
    queryset = OneCConfiguration.objects.prefetch_related('releases').all()
    lookup_field = 'slug'
    lookup_value_regex = r'[\w.-]+'

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return OneCConfigurationDetailSerializer
        return OneCConfigurationSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action in {'list', 'retrieve'} and not self.request.user.is_staff:
            queryset = queryset.filter(is_published=True)
        return queryset

    @action(detail=True, methods=['get'])
    def versions(self, request, slug=None):
        configuration = self.get_object()
        versions = sort_versions_newest_first(
            list(
                OneCRelease.objects.filter(configuration=configuration)
                .values_list('version', flat=True)
            )
        )
        latest = configuration.latest_release
        return Response({
            'configuration': configuration.slug,
            'latest_version': latest.version if latest else None,
            'versions': versions,
        })

    @action(detail=True, methods=['post'], url_path='calculate')
    def calculate(self, request, slug=None):
        configuration = self.get_object()
        current_version = request.data.get('current_version', '')
        try:
            result = calculate_update_path(configuration, current_version)
        except UpdatePathError as exc:
            return Response({'detail': str(exc), 'code': exc.code}, status=status.HTTP_400_BAD_REQUEST)
        return Response(UpdatePathResultSerializer(_serialize_update_result(result)).data)


class OneCReleaseViewSet(viewsets.ModelViewSet):
    queryset = OneCRelease.objects.select_related('configuration').all()
    serializer_class = OneCReleaseSerializer
    filterset_fields = ['configuration']

    def get_queryset(self):
        queryset = super().get_queryset()
        configuration = self.request.query_params.get('configuration')
        configuration_slug = self.request.query_params.get('configuration_slug')
        if configuration:
            queryset = queryset.filter(configuration_id=configuration)
        if configuration_slug:
            queryset = queryset.filter(configuration__slug=configuration_slug)
        return queryset


class CalculateUpdateView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = CalculateUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        config_ref = serializer.validated_data['configuration']
        configuration = self._resolve_configuration(config_ref)
        if configuration is None:
            return Response(
                {'detail': f'Конфигурация «{config_ref}» не найдена.', 'code': 'not_found'},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            result = calculate_update_path(
                configuration,
                serializer.validated_data['current_version'],
            )
        except UpdatePathError as exc:
            return Response({'detail': str(exc), 'code': exc.code}, status=status.HTTP_400_BAD_REQUEST)

        return Response(UpdatePathResultSerializer(_serialize_update_result(result)).data)

    def _resolve_configuration(self, ref: str) -> OneCConfiguration | None:
        if ref.isdigit():
            return OneCConfiguration.objects.filter(pk=int(ref)).first()
        return OneCConfiguration.objects.filter(slug=ref).first()


class ConfigurationVersionsView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, slug):
        configuration = get_object_or_404(
            OneCConfiguration,
            slug=slug,
            is_published=True,
        )
        versions = sort_versions_newest_first(
            list(
                OneCRelease.objects.filter(configuration=configuration)
                .values_list('version', flat=True)
            )
        )
        latest = configuration.latest_release
        return Response({
            'configuration': configuration.slug,
            'name': configuration.name,
            'latest_version': latest.version if latest else None,
            'versions': versions,
        })
