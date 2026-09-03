"""
Validación de documentos — Vigor
==================================

Este módulo concentra TODA la lógica de "revisión por IA" de un documento cargado.
Hoy usa una simulación aleatoria (para el prototipo/demo). Cuando quieras conectar una
IA real, es el ÚNICO lugar que hay que tocar: implementa `_analizar_con_ia_real` y
activa `USE_REAL_AI`. El resto de la aplicación (rutas, plantillas, base de datos) no
necesita cambiar.

Cómo conectar IA real (Claude) más adelante
--------------------------------------------
1. `pip install anthropic` y agrega la librería a requirements.txt.
2. Define la variable de entorno ANTHROPIC_API_KEY en tu servidor (en Render:
   Settings → Environment → Add Environment Variable).
3. Implementa `_analizar_con_ia_real(ruta_absoluta, tipo_documento)`, por ejemplo:

    from anthropic import Anthropic
    import base64

    client = Anthropic()  # toma la key de la variable de entorno

    def _analizar_con_ia_real(ruta_absoluta, tipo_documento):
        with open(ruta_absoluta, "rb") as f:
            imagen_b64 = base64.b64encode(f.read()).decode()

        prompt = f'''
        Estás validando un documento de inscripción para un torneo de fútbol infantil.
        Tipo de documento esperado: "{tipo_documento}".
        Evalúa si la imagen corresponde a ese tipo de documento, si se ve completo y
        legible, y si hay señales de que sea una fotocopia, una captura de pantalla o
        una edición digital en vez de un documento físico original.
        Responde SOLO con JSON: {{"estado": "Aprobado|Rechazado|Pendiente",
        "comentario": "...", "confianza": 0-100}}
        '''

        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=300,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                                  "data": imagen_b64}},
                    {"type": "text", "text": prompt},
                ],
            }],
        )
        import json
        data = json.loads(resp.content[0].text)
        return data["estado"], data["comentario"], data["confianza"]

4. Cambia `USE_REAL_AI = True` al final de este archivo.

Con eso, cada documento que suba un acudiente (o que un administrador vuelva a cargar)
pasará por la IA real en vez de la simulación, sin tocar `app.py` ni las plantillas.
"""

import random

USE_REAL_AI = False  # cámbialo a True cuando implementes _analizar_con_ia_real

COMENTARIOS_SIMULADOS = {
    "Aprobado": "La IA confirma que el documento corresponde al tipo solicitado y los "
                "datos coinciden con el registro del jugador.",
    "Rechazado": "La IA no pudo verificar el documento: la imagen está borrosa, no "
                 "corresponde al tipo solicitado, o parece ser una copia/descarga "
                 "digital en vez del original físico. Vuelve a cargarlo.",
    "Pendiente": "El documento requiere revisión manual de un administrador antes de "
                 "aprobarse.",
}


def _analizar_con_ia_real(ruta_absoluta, tipo_documento):
    """Placeholder. Implementa esta función siguiendo las instrucciones del docstring
    de arriba para conectar una IA real (por ejemplo, Claude con visión)."""
    raise NotImplementedError(
        "Conecta aquí tu proveedor de IA real. Mientras tanto, deja USE_REAL_AI = False."
    )


def _simular_analisis():
    estado = random.choices(["Aprobado", "Rechazado", "Pendiente"], weights=[70, 15, 15], k=1)[0]
    confianza = random.randint(60, 99) if estado != "Pendiente" else None
    return estado, COMENTARIOS_SIMULADOS[estado], confianza


def analizar_documento(ruta_absoluta, tipo_documento):
    """Punto de entrada único usado por app.py. Devuelve (estado, comentario, confianza).

    ruta_absoluta: ruta en disco del archivo recién subido, o None si no se subió nada.
    tipo_documento: el nombre del tipo de documento (ej. "Registro Civil de Nacimiento").
    """
    if ruta_absoluta is None:
        return "Pendiente", "Aún no se ha cargado este documento.", None

    if USE_REAL_AI:
        return _analizar_con_ia_real(ruta_absoluta, tipo_documento)

    return _simular_analisis()
