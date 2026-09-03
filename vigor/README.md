# Vigor — Prototipo de gestión de torneos deportivos

Prototipo navegable para Vigor: creación de torneos, inscripción de clubes/staff/jugadores
con código por club, carga de documentos con revisión simulada por IA, y un panel de
seguimiento gerencial del torneo. Datos 100% ficticios (municipios de la Sabana de
Occidente de Cundinamarca: Facatativá, Madrid, Mosquera, Funza, Bojacá, Zipacón, El Rosal
y Subachoque).

## Cómo correrlo

```bash
python -m venv venv
source venv/bin/activate        # En Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Abre http://127.0.0.1:5050 en el navegador.

La primera vez que corres la app se crea automáticamente `vigor.db` (SQLite) con datos
demo: 1 torneo, 8 ciudades, 8 estadios, 12 clubes, ~34 personas de staff, ~148 jugadores
con sus acudientes, documentos en distintos estados y 36 partidos con goles y tarjetas.

Para regenerar los datos demo desde cero (borra `vigor.db` y la vuelve a crear):

```bash
python db.py
```

## Qué incluye este dummy

- **Panel gerencial** (`/admin`): marcador con cifras del torneo, ciudades participantes,
  tabla de posiciones calculada en vivo y próximos partidos.
- **Torneos** (`/admin/torneos`): listado y creación de nuevos torneos.
- **Clubes** (`/admin/clubes`): listado con código único por club, creación de clubes
  (el código se genera automáticamente), y detalle de cada club con su nómina y staff.
- **Inscripción de staff**: dentro del detalle de cada club.
- **Documentos** (`/admin/documentos`): cola de revisión con filtros por estado
  (Pendiente / Rechazado / Aprobado) y acciones para aprobar o rechazar manualmente.
- **Seguimiento** (`/admin/seguimiento`): partidos agrupados por jornada, con detalle de
  cronología (goles, faltas, tarjetas) por partido.
- **Flujo del acudiente** (`/inscripcion`): ingreso con el código del club, formulario
  extendido del jugador (datos médicos, EPS, contacto de emergencia, etc.) y carga de
  documentos con una revisión automática simulada (aprobado / pendiente / rechazado con
  un comentario, como lo haría un motor de IA real).

## Cómo montarla en un servidor gratuito (Render)

Recomiendo **Render**: no pide tarjeta de crédito, despliega directo desde GitHub y
soporta Flask sin configuración especial. El proyecto ya trae todo lo necesario
(`Procfile`, `render.yaml` y `gunicorn` en `requirements.txt`).

1. Sube esta carpeta a un repositorio de GitHub (puede ser privado).
2. Entra a [render.com](https://render.com) y crea una cuenta gratuita.
3. "New" → "Web Service" → conecta tu repositorio de GitHub.
4. Render detecta el `render.yaml` automáticamente. Si te pide los campos a mano, usa:
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `gunicorn app:app --bind 0.0.0.0:$PORT`
   - **Plan:** Free
5. Click en "Create Web Service". En 2–3 minutos te da una URL pública tipo
   `https://vigor-prototipo.onrender.com` — esa es la página de inicio (`index`) del proyecto.

**Dos límites del plan gratuito a tener en cuenta (normales para un dummy):**
- El servicio "se duerme" tras ~15 min sin tráfico; la primera visita después tarda
  cerca de un minuto en despertar.
- El disco no es permanente entre reinicios: si el servicio se reinicia, `vigor.db` se
  vuelve a generar desde cero con los datos demo (perderías inscripciones nuevas hechas
  a mano). Para un dummy está bien; si luego quieres persistencia real, Render también
  ofrece una base de datos PostgreSQL gratuita por 90 días que podemos conectar.

Alternativa igual de válida y sin tarjeta: **PythonAnywhere**, más manual (subes el
código y configuras la app Flask desde su panel web) pero muy estable para un solo
servicio pequeño.

## Próximos pasos sugeridos (fuera de este dummy)

- Autenticación real por rol (admin, staff de club, acudiente).
- Integración real de IA (visión) para leer y validar los documentos cargados.
- Notificaciones automáticas a acudientes cuando un documento es rechazado.
- Multi-torneo simultáneo con selector activo en la barra superior.
