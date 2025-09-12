# tracker/services.py
import requests
from django.conf import settings
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)

class RiskTaxonomyService:
    def __init__(self):
        self.api_url = getattr(settings, 'RISK_TAXONOMY_API_URL', '')
        self.api_token = getattr(settings, 'RISK_TAXONOMY_API_TOKEN', '')
        self.timeout = getattr(settings, 'RISK_TAXONOMY_API_TIMEOUT', 30)
        self.cache_timeout = getattr(settings, 'RISK_TAXONOMY_CACHE_TIMEOUT', 3600)  # 1 hora

    def get_taxonomy_data(self):
        """Obtiene datos de taxonomía desde la API o caché"""
        cached_data = cache.get('risk_taxonomy_data')
        if cached_data:
            return cached_data

        try:
            headers = {
                'Authorization': f'Bearer {self.api_token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(
                self.api_url,
                headers=headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            taxonomy_data = response.json()
            
            # Cachear los datos
            cache.set('risk_taxonomy_data', taxonomy_data, self.cache_timeout)
            
            return taxonomy_data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching taxonomy data: {e}")
            # Podrías retornar datos de respaldo o lanzar una excepción
            return None

    def get_structured_taxonomy(self):
        """Convierte los datos de la API al formato estructurado que necesita tu aplicación"""
        raw_data = self.get_taxonomy_data()
        if not raw_data:
            return None

        # Estructurar los datos en el formato que espera tu aplicación
        taxonomy = {
            'lv1': [],
            'lv2': {},
            'lv3': {}
        }

        # Procesar los datos de la API
        for item in raw_data:
            lv1 = item.get('TAXONOMY_LEVEL1')
            lv2 = item.get('TAXONOMY_LEVEL2')
            lv3 = item.get('TAXONOMY_LEVEL3')
            tax_id = item.get('TAXONOMY_ID')

            if lv1 and lv1 not in [x[0] for x in taxonomy['lv1']]:
                taxonomy['lv1'].append((lv1, lv1))

            if lv1 and lv2:
                if lv1 not in taxonomy['lv2']:
                    taxonomy['lv2'][lv1] = []
                
                if (lv2, lv2) not in taxonomy['lv2'][lv1]:
                    taxonomy['lv2'][lv1].append((lv2, lv2))

            if lv2 and lv3:
                if lv2 not in taxonomy['lv3']:
                    taxonomy['lv3'][lv2] = []
                
                if (lv3, lv3) not in taxonomy['lv3'][lv2]:
                    taxonomy['lv3'][lv2].append((lv3, lv3))

        return taxonomy

# Singleton instance
taxonomy_service = RiskTaxonomyService()