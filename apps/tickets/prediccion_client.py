"""
Cliente HTTP para el servicio de predicción de prioridad (Fase 3).
El gestor llama a este módulo; nunca el navegador del operador directamente.
"""
import logging
import os

import requests

logger = logging.getLogger(__name__)

TIMEOUT_SEGUNDOS = 5  # El gestor no espera más de esto — nunca bloquea el flujo


def _get_url():
    # Se lee en cada llamada para garantizar que django-environ ya procesó el .env.
    # Si se leyera al importar el módulo, puede ejecutarse antes de que las variables
    # de entorno estén disponibles en os.environ.
    base = os.environ.get("PREDICCION_SERVICE_URL", "http://127.0.0.1:5000")
    return f"{base.rstrip('/')}/predict"


def obtener_sugerencia(descripcion: str, categoria: str, servicio_afectado: str) -> dict | None:
    """
    Llama al endpoint /predict del servicio Flask y devuelve el resultado.

    Retorna un dict con: prioridad_predicha, confianza, probabilidades_por_clase, version_modelo.
    Retorna None si el servicio no responde o devuelve error — el flujo del gestor
    continua sin sugerencia en ese caso.
    """
    url = _get_url()
    payload = {
        "descripcion": descripcion,
        "categoria": categoria,
        "servicio_afectado": servicio_afectado,
    }

    try:
        response = requests.post(url, json=payload, timeout=TIMEOUT_SEGUNDOS)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        logger.warning("Servicio de prediccion no disponible en %s", url)
        return None
    except requests.exceptions.Timeout:
        logger.warning("Timeout al contactar el servicio de prediccion (%ss)", TIMEOUT_SEGUNDOS)
        return None
    except requests.exceptions.HTTPError as exc:
        logger.warning(
            "Error HTTP del servicio de prediccion: %s -- %s",
            exc.response.status_code,
            exc.response.text[:200],
        )
        return None
    except Exception as exc:
        logger.error("Error inesperado al contactar el servicio de prediccion: %s", exc)
        return None
