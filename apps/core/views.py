"""
Core views for health checks and system status.
"""
from django.db import connection
from django.core.cache import cache
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthCheckView(APIView):
    """Health check endpoint for the system."""

    def get(self, request):
        """Check system health including database and cache connections."""
        health_status = {
            'status': 'healthy',
            'components': {}
        }

        # Check database
        try:
            with connection.cursor() as cursor:
                cursor.execute('SELECT 1')
            health_status['components']['database'] = 'healthy'
        except Exception as e:
            health_status['components']['database'] = f'unhealthy: {str(e)}'
            health_status['status'] = 'unhealthy'

        # Check cache (Redis)
        try:
            cache.set('health_check', 'ok', timeout=10)
            if cache.get('health_check') == 'ok':
                health_status['components']['cache'] = 'healthy'
            else:
                health_status['components']['cache'] = 'unhealthy: cache read failed'
                health_status['status'] = 'unhealthy'
        except Exception as e:
            health_status['components']['cache'] = f'unhealthy: {str(e)}'
            health_status['status'] = 'unhealthy'

        status_code = status.HTTP_200_OK if health_status['status'] == 'healthy' else status.HTTP_503_SERVICE_UNAVAILABLE
        return Response(health_status, status=status_code)

