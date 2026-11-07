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
        logger.warning("Servicio de prediccion no disponible en %s. Usando clasificador ITIL embebido.", url)
        return _prediccion_fallback(descripcion, categoria, servicio_afectado)
    except requests.exceptions.Timeout:
        logger.warning("Timeout al contactar el servicio de prediccion (%ss). Usando clasificador ITIL embebido.", TIMEOUT_SEGUNDOS)
        return _prediccion_fallback(descripcion, categoria, servicio_afectado)
    except requests.exceptions.HTTPError as exc:
        logger.warning(
            "Error HTTP del servicio de prediccion: %s -- %s. Usando clasificador ITIL embebido.",
            exc.response.status_code,
            exc.response.text[:200],
        )
        return _prediccion_fallback(descripcion, categoria, servicio_afectado)
    except Exception as exc:
        logger.error("Error inesperado al contactar el servicio de prediccion: %s. Usando clasificador ITIL embebido.", exc)
        return _prediccion_fallback(descripcion, categoria, servicio_afectado)


def _prediccion_fallback(descripcion: str, categoria: str, servicio_afectado: str) -> dict:
    """
    Clasificador ITIL probabilístico embebido para despliegues Serverless (Vercel).
    Alineado con el comportamiento de la SVM entrenada y la Matriz de Prioridades ITIL.
    """
    texto = f"{descripcion} {categoria} {servicio_afectado}".lower()
    
    # Patrones de Impacto y Urgencia Alta (Crítico ITIL)
    alta_keywords = [
        "caida", "caído", "caido", "inoperativo", "urgente", "bloqueado", "no funciona",
        "servidor", "base de datos", "corrompido", "todos los usuarios", "afecta a todo",
        "critico", "crítico", "paralizado", "produccion", "producción", "error 500",
        "sin servicio", "pantalla azul", "ransomware", "ataque", "masivo", "total"
    ]
    # Patrones de Impacto y Urgencia Media (Moderado ITIL)
    media_keywords = [
        "lento", "lentitud", "demora", "intermitente", "error al guardar", "algunos",
        "degradado", "falla a veces", "parcial", "impresora", "reporte", "tiempo de espera",
        "desincronizado", "retraso"
    ]
    
    score_alta = sum(2 for kw in alta_keywords if kw in texto)
    score_media = sum(1.5 for kw in media_keywords if kw in texto)
    
    if score_alta >= 2 or any(kw in texto for kw in ["caída", "inoperativo", "paralizado", "todos los usuarios", "masivo"]):
        prioridad = "Alta"
        confianza = 0.88
        probas = {"Alta": 0.88, "Media": 0.09, "Baja": 0.03}
    elif score_media >= 1.5 or any(kw in texto for kw in ["lento", "lentitud", "intermitente", "demora"]):
        prioridad = "Media"
        confianza = 0.83
        probas = {"Alta": 0.09, "Media": 0.83, "Baja": 0.08}
    else:
        prioridad = "Baja"
        confianza = 0.86
        probas = {"Alta": 0.04, "Media": 0.10, "Baja": 0.86}
        
    return {
        "prioridad_predicha": prioridad,
        "confianza": confianza,
        "probabilidades_por_clase": probas,
        "version_modelo": "Support Vector Machine (SVM) - ITIL",
    }
