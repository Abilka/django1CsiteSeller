from django.urls import reverse
from rest_framework.response import Response
from rest_framework.views import APIView

from blog.api.permissions import IsStaffUser

from ..models import LeadRequest


class LeadPollView(APIView):
    """Poll for new lead requests (staff admin notifications)."""

    permission_classes = [IsStaffUser]

    def get(self, request):
        qs = LeadRequest.objects.filter(is_honeypot=False).order_by('id')
        latest_id = qs.order_by('-id').values_list('id', flat=True).first() or 0

        after_id_raw = request.query_params.get('after_id')
        if after_id_raw is None:
            return Response({'latest_id': latest_id, 'leads': []})

        try:
            after_id = int(after_id_raw)
        except (TypeError, ValueError):
            return Response(
                {'detail': 'Параметр after_id должен быть целым числом.'},
                status=400,
            )

        leads = []
        for lead in qs.filter(id__gt=after_id)[:20]:
            leads.append({
                'id': lead.pk,
                'name': lead.name,
                'phone': lead.phone,
                'service': lead.get_service_display(),
                'message': lead.message[:200] if lead.message else '',
                'created_at': lead.created_at.isoformat(),
                'admin_url': reverse('admin:landing_leadrequest_change', args=[lead.pk]),
            })

        return Response({'latest_id': latest_id, 'leads': leads})
