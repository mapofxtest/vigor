from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory, abort
from datetime import date
from werkzeug.utils import secure_filename
import random
import os
import uuid
import db
import validacion_ia

app = Flask(__name__)
app.secret_key = "vigor-demo-secret"

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


def q(conn, sql, params=()):
    return conn.execute(sql, params).fetchall()


def one(conn, sql, params=()):
    return conn.execute(sql, params).fetchone()


def _guardar_y_analizar(archivo, tipo_documento):
    """Guarda el archivo subido en disco (si hay alguno) y ejecuta el análisis de IA
    (hoy simulado, ver validacion_ia.py). Devuelve (nombre_original, ruta_relativa,
    estado_ia, comentario_ia, confianza). Este resultado es solo la PRE-VALIDACIÓN de
    la IA: el estado final que ve el acudiente lo decide el administrador."""
    if not archivo or not archivo.filename:
        estado_ia, comentario, confianza = validacion_ia.analizar_documento(None, tipo_documento)
        return None, None, estado_ia, comentario, confianza

    nombre_original = secure_filename(archivo.filename) or "documento"
    extension = os.path.splitext(nombre_original)[1]
    nombre_disco = f"{uuid.uuid4().hex}{extension}"
    ruta_absoluta = os.path.join(UPLOAD_DIR, nombre_disco)
    archivo.save(ruta_absoluta)

    estado_ia, comentario, confianza = validacion_ia.analizar_documento(ruta_absoluta, tipo_documento)
    return nombre_original, nombre_disco, estado_ia, comentario, confianza


def _borrar_archivo_si_existe(ruta_archivo):
    if not ruta_archivo:
        return
    ruta_absoluta = os.path.join(UPLOAD_DIR, ruta_archivo)
    try:
        if os.path.isfile(ruta_absoluta):
            os.remove(ruta_absoluta)
    except OSError:
        pass


# ---------------------------------------------------------------- landing --

@app.route("/")
def landing():
    conn = db.get_connection()
    torneo = one(conn, "SELECT * FROM torneos LIMIT 1")
    n_clubes = one(conn, "SELECT COUNT(*) c FROM clubes")["c"]
    n_jugadores = one(conn, "SELECT COUNT(*) c FROM jugadores")["c"]
    n_ciudades = one(conn, "SELECT COUNT(*) c FROM ciudades")["c"]
    conn.close()
    return render_template("landing.html", torneo=torneo, n_clubes=n_clubes,
                            n_jugadores=n_jugadores, n_ciudades=n_ciudades)


# --------------------------------------------------------------- admin ----

@app.route("/admin/reiniciar-demo", methods=["POST"])
def reiniciar_demo():
    db.build_database()
    flash("Datos demo reiniciados: todo vuelve al estado inicial, listo para presentar.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin")
def admin_dashboard():
    conn = db.get_connection()
    torneo = one(conn, "SELECT * FROM torneos LIMIT 1")
    stats = {
        "torneos": one(conn, "SELECT COUNT(*) c FROM torneos")["c"],
        "clubes": one(conn, "SELECT COUNT(*) c FROM clubes")["c"],
        "jugadores": one(conn, "SELECT COUNT(*) c FROM jugadores")["c"],
        "partidos_jugados": one(conn, "SELECT COUNT(*) c FROM partidos WHERE estado='Finalizado'")["c"],
    }
    ciudades = q(conn, """SELECT c.nombre, COUNT(cl.id) n_clubes
                           FROM ciudades c LEFT JOIN clubes cl ON cl.ciudad_id = c.id
                           GROUP BY c.id ORDER BY c.nombre""")

    tabla = q(conn, "SELECT id, nombre, codigo FROM clubes")
    posiciones = []
    for club in tabla:
        cid = club["id"]
        pj = one(conn, """SELECT COUNT(*) c FROM partidos
                           WHERE estado='Finalizado' AND (club_local_id=? OR club_visitante_id=?)""",
                 (cid, cid))["c"]
        gf = one(conn, """SELECT COALESCE(SUM(CASE WHEN club_local_id=? THEN goles_local ELSE goles_visitante END),0) g
                           FROM partidos WHERE estado='Finalizado' AND (club_local_id=? OR club_visitante_id=?)""",
                 (cid, cid, cid))["g"]
        gc = one(conn, """SELECT COALESCE(SUM(CASE WHEN club_local_id=? THEN goles_visitante ELSE goles_local END),0) g
                           FROM partidos WHERE estado='Finalizado' AND (club_local_id=? OR club_visitante_id=?)""",
                 (cid, cid, cid))["g"]
        ganados = one(conn, """SELECT COUNT(*) c FROM partidos WHERE estado='Finalizado' AND
                              ((club_local_id=? AND goles_local>goles_visitante) OR
                               (club_visitante_id=? AND goles_visitante>goles_local))""", (cid, cid))["c"]
        empatados = one(conn, """SELECT COUNT(*) c FROM partidos WHERE estado='Finalizado' AND
                              (club_local_id=? OR club_visitante_id=?) AND goles_local=goles_visitante""",
                        (cid, cid))["c"]
        perdidos = pj - ganados - empatados
        pts = ganados * 3 + empatados
        posiciones.append({"club": club, "pj": pj, "g": ganados, "e": empatados, "p": perdidos,
                            "gf": gf, "gc": gc, "pts": pts})
    posiciones.sort(key=lambda x: (-x["pts"], -(x["gf"] - x["gc"])))

    proximos = q(conn, """SELECT p.*, cl.nombre local_nombre, cv.nombre visitante_nombre, e.nombre estadio_nombre
                           FROM partidos p
                           JOIN clubes cl ON cl.id = p.club_local_id
                           JOIN clubes cv ON cv.id = p.club_visitante_id
                           JOIN estadios e ON e.id = p.estadio_id
                           WHERE p.estado='Programado'
                           ORDER BY p.fecha, p.hora LIMIT 6""")

    docs_pendientes = one(conn, "SELECT COUNT(*) c FROM documentos WHERE estado='Pendiente'")["c"]
    docs_rechazados = one(conn, "SELECT COUNT(*) c FROM documentos WHERE estado='Rechazado'")["c"]

    conn.close()
    return render_template("admin_dashboard.html", torneo=torneo, stats=stats, ciudades=ciudades,
                            posiciones=posiciones[:12], proximos=proximos,
                            docs_pendientes=docs_pendientes, docs_rechazados=docs_rechazados)


@app.route("/admin/torneos", methods=["GET", "POST"])
def admin_torneos():
    conn = db.get_connection()
    if request.method == "POST":
        conn.execute("""INSERT INTO torneos (nombre, categoria, temporada, fecha_inicio, fecha_fin, estado)
                         VALUES (?,?,?,?,?,?)""",
                     (request.form["nombre"], request.form["categoria"], request.form["temporada"],
                      request.form["fecha_inicio"], request.form["fecha_fin"], "En curso"))
        conn.commit()
        flash(f"Torneo \"{request.form['nombre']}\" creado.", "success")
        conn.close()
        return redirect(url_for("admin_torneos"))
    torneos = q(conn, "SELECT * FROM torneos ORDER BY id DESC")
    conn.close()
    return render_template("torneos.html", torneos=torneos)


@app.route("/admin/clubes", methods=["GET", "POST"])
def admin_clubes():
    conn = db.get_connection()
    if request.method == "POST":
        ciudad_id = request.form["ciudad_id"]
        ciudad_nombre = one(conn, "SELECT nombre FROM ciudades WHERE id=?", (ciudad_id,))["nombre"]
        codigo = f"{ciudad_nombre[:3].upper()}-{random.randint(200,999)}"
        torneo_id = one(conn, "SELECT id FROM torneos ORDER BY id DESC LIMIT 1")["id"]
        conn.execute("INSERT INTO clubes (nombre, ciudad_id, codigo, color, torneo_id) VALUES (?,?,?,?,?)",
                     (request.form["nombre"], ciudad_id, codigo, "#2E7D46", torneo_id))
        conn.commit()
        flash(f"Club \"{request.form['nombre']}\" creado con código {codigo}.", "success")
        conn.close()
        return redirect(url_for("admin_clubes"))

    clubes = q(conn, """SELECT cl.*, c.nombre ciudad_nombre,
                        (SELECT COUNT(*) FROM jugadores j WHERE j.club_id=cl.id) n_jugadores,
                        (SELECT COUNT(*) FROM staff s WHERE s.club_id=cl.id) n_staff
                        FROM clubes cl JOIN ciudades c ON c.id = cl.ciudad_id
                        ORDER BY c.nombre, cl.nombre""")
    ciudades = q(conn, "SELECT * FROM ciudades ORDER BY nombre")
    conn.close()
    return render_template("clubes.html", clubes=clubes, ciudades=ciudades)


@app.route("/admin/clubes/<int:club_id>", methods=["GET", "POST"])
def admin_club_detail(club_id):
    conn = db.get_connection()
    if request.method == "POST":
        conn.execute("INSERT INTO staff (club_id, nombre, rol, telefono, email) VALUES (?,?,?,?,?)",
                     (club_id, request.form["nombre"], request.form["rol"],
                      request.form["telefono"], request.form["email"]))
        conn.commit()
        flash(f"{request.form['nombre']} inscrito como {request.form['rol']}.", "success")
        conn.close()
        return redirect(url_for("admin_club_detail", club_id=club_id))

    club = one(conn, """SELECT cl.*, c.nombre ciudad_nombre FROM clubes cl
                         JOIN ciudades c ON c.id = cl.ciudad_id WHERE cl.id=?""", (club_id,))
    staff = q(conn, "SELECT * FROM staff WHERE club_id=? ORDER BY rol", (club_id,))
    jugadores = q(conn, """SELECT j.*, p.nombre padre_nombre FROM jugadores j
                            LEFT JOIN padres p ON p.id = j.padre_id
                            WHERE j.club_id=? ORDER BY j.nombre""", (club_id,))
    conn.close()
    return render_template("club_detail.html", club=club, staff=staff, jugadores=jugadores)


@app.route("/admin/documentos")
def admin_documentos():
    conn = db.get_connection()
    clubes = q(conn, "SELECT id, nombre FROM clubes ORDER BY nombre")
    club_id = request.args.get("club_id", type=int)
    mostrar = request.args.get("mostrar", "pendientes")  # "pendientes" o "todos"
    busqueda = request.args.get("q", "").strip()

    filtros, params = [], []
    if club_id:
        filtros.append("j.club_id = ?")
        params.append(club_id)
    if busqueda:
        filtros.append("j.nombre LIKE ?")
        params.append(f"%{busqueda}%")
    where = ("WHERE " + " AND ".join(filtros)) if filtros else ""

    filas_jugadores = q(conn, f"""SELECT j.*, cl.nombre club_nombre, p.nombre padre_nombre
                                   FROM jugadores j
                                   JOIN clubes cl ON cl.id = j.club_id
                                   LEFT JOIN padres p ON p.id = j.padre_id
                                   {where}
                                   ORDER BY j.nombre""", params)

    jugadores = []
    for j in filas_jugadores:
        docs = q(conn, "SELECT * FROM documentos WHERE jugador_id=? ORDER BY id", (j["id"],))
        no_aprobados = [d for d in docs if d["estado"] != "Aprobado"]
        if mostrar == "pendientes" and not no_aprobados:
            continue
        jugadores.append({"jugador": j, "documentos": docs, "no_aprobados": no_aprobados})

    resumen = q(conn, "SELECT estado, COUNT(*) c FROM documentos GROUP BY estado")
    conn.close()
    return render_template("documentos.html", clubes=clubes, club_id=club_id, mostrar=mostrar,
                            jugadores=jugadores, resumen=resumen, busqueda=busqueda)


@app.route("/admin/documentos/<int:doc_id>/revisar", methods=["POST"])
def revisar_documento(doc_id):
    nuevo_estado = request.form["estado"]
    conn = db.get_connection()
    comentario_admin = {
        "Aprobado": "Revisado manualmente por el administrador: documento válido.",
        "Rechazado": "Revisado manualmente por el administrador: documento no válido.",
    }.get(nuevo_estado, None)
    conn.execute("UPDATE documentos SET estado=?, comentario_admin=? WHERE id=?",
                 (nuevo_estado, comentario_admin, doc_id))
    conn.commit()
    conn.close()
    flash("Documento actualizado.", "success")
    return redirect(request.referrer or url_for("admin_documentos"))


@app.route("/admin/documentos/<int:doc_id>/eliminar", methods=["POST"])
def eliminar_documento(doc_id):
    conn = db.get_connection()
    doc = one(conn, "SELECT * FROM documentos WHERE id=?", (doc_id,))
    if doc:
        _borrar_archivo_si_existe(doc["ruta_archivo"])
        conn.execute("""UPDATE documentos SET nombre_archivo=NULL, ruta_archivo=NULL,
                         estado='Pendiente', estado_ia='Pendiente',
                         comentario_ia='Aún no se ha cargado este documento.',
                         confianza_ia=NULL, comentario_admin=NULL, fecha_carga=NULL
                         WHERE id=?""", (doc_id,))
        conn.commit()
        flash("Documento eliminado. El acudiente deberá volver a cargarlo.", "success")
    conn.close()
    return redirect(request.referrer or url_for("admin_documentos"))


@app.route("/uploads/<path:filename>")
def ver_documento_archivo(filename):
    if not os.path.isfile(os.path.join(UPLOAD_DIR, filename)):
        abort(404)
    return send_from_directory(UPLOAD_DIR, filename)


@app.route("/admin/partidos/<int:partido_id>")
def partido_detail(partido_id):
    conn = db.get_connection()
    partido = one(conn, """SELECT p.*, cl.nombre local_nombre, cl.color local_color,
                                   cv.nombre visitante_nombre, cv.color visitante_color,
                                   e.nombre estadio_nombre, ci.nombre ciudad_nombre
                            FROM partidos p
                            JOIN clubes cl ON cl.id = p.club_local_id
                            JOIN clubes cv ON cv.id = p.club_visitante_id
                            JOIN estadios e ON e.id = p.estadio_id
                            JOIN ciudades ci ON ci.id = e.ciudad_id
                            WHERE p.id=?""", (partido_id,))
    eventos = q(conn, """SELECT ev.*, j.nombre jugador_nombre FROM eventos ev
                          LEFT JOIN jugadores j ON j.id = ev.jugador_id
                          WHERE ev.partido_id=? ORDER BY ev.minuto""", (partido_id,))
    conn.close()
    return render_template("partido_detail.html", partido=partido, eventos=eventos)


@app.route("/admin/seguimiento")
def seguimiento():
    conn = db.get_connection()
    partidos = q(conn, """SELECT p.*, cl.nombre local_nombre, cv.nombre visitante_nombre,
                                  e.nombre estadio_nombre, ci.nombre ciudad_nombre
                           FROM partidos p
                           JOIN clubes cl ON cl.id = p.club_local_id
                           JOIN clubes cv ON cv.id = p.club_visitante_id
                           JOIN estadios e ON e.id = p.estadio_id
                           JOIN ciudades ci ON ci.id = e.ciudad_id
                           ORDER BY p.jornada, p.fecha""")
    jornadas = {}
    for p in partidos:
        jornadas.setdefault(p["jornada"], []).append(p)
    conn.close()
    return render_template("seguimiento.html", jornadas=jornadas)


# ------------------------------------------------------------ inscripcion --

COMENTARIOS_IA = validacion_ia.COMENTARIOS_SIMULADOS


@app.route("/inscripcion", methods=["GET", "POST"])
def inscripcion():
    conn = db.get_connection()
    club = None
    error = None
    if request.method == "POST":
        codigo = request.form.get("codigo", "").strip().upper()
        club = one(conn, "SELECT * FROM clubes WHERE codigo=?", (codigo,))
        if not club:
            error = "No encontramos ningún club con ese código. Verifícalo con el director técnico."
    conn.close()
    return render_template("inscripcion.html", club=club, error=error,
                            documentos_requeridos=db.DOCUMENTOS_REQUERIDOS)


@app.route("/inscripcion/consultar", methods=["GET", "POST"])
def inscripcion_consultar():
    conn = db.get_connection()
    error = None
    resultados = []
    buscado = False
    codigo = request.form.get("codigo", "").strip().upper()
    nombre = request.form.get("nombre", "").strip()

    if request.method == "POST":
        buscado = True
        club = one(conn, "SELECT * FROM clubes WHERE codigo=?", (codigo,))
        if not club:
            error = "No encontramos ningún club con ese código. Verifícalo con el director técnico."
        elif not nombre:
            error = "Escribe el nombre del jugador para buscarlo."
        else:
            resultados = q(conn, """SELECT j.*, cl.nombre club_nombre FROM jugadores j
                                     JOIN clubes cl ON cl.id = j.club_id
                                     WHERE j.club_id = ? AND j.nombre LIKE ?
                                     ORDER BY j.nombre""", (club["id"], f"%{nombre}%"))
            if not resultados:
                error = "No encontramos ningún jugador con ese nombre inscrito en este club."

    conn.close()
    return render_template("inscripcion_consultar.html", error=error, resultados=resultados,
                            codigo=codigo, nombre=nombre, buscado=buscado)


@app.route("/inscripcion/requisitos-documentos")
def requisitos_documentos():
    return render_template("requisitos_documentos.html", documentos=db.DOCUMENTOS_REQUERIDOS)


@app.route("/inscripcion/<codigo>/formulario", methods=["GET", "POST"])
def inscripcion_formulario(codigo):
    conn = db.get_connection()
    club = one(conn, "SELECT * FROM clubes WHERE codigo=?", (codigo.upper(),))
    if not club:
        conn.close()
        return redirect(url_for("inscripcion"))

    if request.method == "POST":
        conn.execute("INSERT INTO padres (nombre, telefono, email, parentesco) VALUES (?,?,?,?)",
                     (request.form["padre_nombre"], request.form["padre_telefono"],
                      request.form["padre_email"], request.form["parentesco"]))
        padre_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        conn.execute("""INSERT INTO jugadores
            (club_id, padre_id, nombre, fecha_nacimiento, categoria, posicion, numero_camiseta,
             talla_uniforme, eps, tipo_sangre, alergias, contacto_emergencia, telefono_emergencia,
             observaciones_medicas)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (club["id"], padre_id, request.form["jugador_nombre"], request.form["fecha_nacimiento"],
             request.form["categoria"], request.form["posicion"], request.form.get("numero_camiseta") or None,
             request.form["talla_uniforme"], request.form["eps"], request.form["tipo_sangre"],
             request.form.get("alergias") or "Ninguna", request.form["padre_nombre"],
             request.form["padre_telefono"], request.form.get("observaciones_medicas") or "Ninguna"))
        jugador_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        faltantes = []
        for d in db.DOCUMENTOS_REQUERIDOS:
            archivo = request.files.get(f"archivo_{d['campo']}")
            nombre_original, ruta_archivo, estado_ia, comentario_ia, confianza = _guardar_y_analizar(archivo, d["tipo"])
            if nombre_original is None:
                faltantes.append(d["tipo"])
            conn.execute("""INSERT INTO documentos
                (jugador_id, tipo, nombre_archivo, ruta_archivo, estado, estado_ia, comentario_ia, confianza_ia, fecha_carga)
                VALUES (?,?,?,?,?,?,?,?,?)""",
                (jugador_id, d["tipo"], nombre_original, ruta_archivo, "Pendiente", estado_ia, comentario_ia,
                 confianza, date.today().isoformat() if nombre_original else None))
        conn.commit()
        conn.close()

        if faltantes:
            flash(f"Inscripción guardada, pero falta cargar {len(faltantes)} de 3 documentos: "
                  f"{', '.join(faltantes)}. Puedes subirlos apenas los tengas a la mano.", "warning")
        else:
            flash("Inscripción y documentos guardados con éxito. La IA ya hizo su pre-validación; "
                  "el administrador confirmará el resultado final.", "success")
        return redirect(url_for("inscripcion_confirmacion", jugador_id=jugador_id))

    conn.close()
    return render_template("inscripcion_formulario.html", club=club, categorias=db.CATEGORIAS,
                            posiciones=db.POSICIONES, eps_list=db.EPS_LIST,
                            documentos_requeridos=db.DOCUMENTOS_REQUERIDOS)


@app.route("/inscripcion/confirmacion/<int:jugador_id>")
def inscripcion_confirmacion(jugador_id):
    conn = db.get_connection()
    jugador = one(conn, """SELECT j.*, cl.nombre club_nombre FROM jugadores j
                            JOIN clubes cl ON cl.id = j.club_id WHERE j.id=?""", (jugador_id,))
    documentos = q(conn, "SELECT * FROM documentos WHERE jugador_id=?", (jugador_id,))
    conn.close()
    documentos_info = {d["tipo"]: db.get_doc_info(d["tipo"]) for d in documentos}
    return render_template("inscripcion_confirmacion.html", jugador=jugador, documentos=documentos,
                            documentos_info=documentos_info)


@app.route("/inscripcion/documentos/<int:doc_id>/subir", methods=["POST"])
def subir_documento(doc_id):
    """Guarda el archivo cargado, borra el archivo anterior si estaba incorrecto, y
    ejecuta la pre-validación por IA (hoy simulada). El estado final vuelve a quedar
    en Pendiente hasta que el administrador lo confirme."""
    conn = db.get_connection()
    doc = one(conn, "SELECT * FROM documentos WHERE id=?", (doc_id,))
    archivo = request.files.get("archivo")
    nombre_original, ruta_archivo, estado_ia, comentario_ia, confianza = _guardar_y_analizar(archivo, doc["tipo"])

    if nombre_original is None:
        # No se seleccionó ningún archivo nuevo: no tocar el archivo existente.
        conn.close()
        flash("No seleccionaste ningún archivo. Elige un archivo antes de subir.", "warning")
        return redirect(url_for("inscripcion_confirmacion", jugador_id=doc["jugador_id"]))

    # Se cargó un archivo nuevo: borrar el anterior (si estaba incorrecto) y reemplazar.
    _borrar_archivo_si_existe(doc["ruta_archivo"])
    conn.execute("""UPDATE documentos SET nombre_archivo=?, ruta_archivo=?, estado='Pendiente',
                     estado_ia=?, comentario_ia=?, confianza_ia=?, comentario_admin=NULL, fecha_carga=?
                     WHERE id=?""",
                 (nombre_original, ruta_archivo, estado_ia, comentario_ia, confianza,
                  date.today().isoformat(), doc_id))
    conn.commit()
    jugador_id = doc["jugador_id"]
    conn.close()
    flash(f'"{doc["tipo"]}" se guardó con éxito. La IA ya hizo su pre-validación; '
          f"queda a la espera de confirmación del administrador.", "success")
    return redirect(url_for("inscripcion_confirmacion", jugador_id=jugador_id))


if __name__ == "__main__":
    app.run(debug=True, port=5050)
