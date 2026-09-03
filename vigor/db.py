import sqlite3
import os
import random
from datetime import date, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "vigor.db")

SCHEMA = """
CREATE TABLE ciudades (
    id INTEGER PRIMARY KEY,
    nombre TEXT NOT NULL
);

CREATE TABLE estadios (
    id INTEGER PRIMARY KEY,
    nombre TEXT NOT NULL,
    ciudad_id INTEGER NOT NULL,
    direccion TEXT,
    capacidad INTEGER,
    FOREIGN KEY (ciudad_id) REFERENCES ciudades(id)
);

CREATE TABLE torneos (
    id INTEGER PRIMARY KEY,
    nombre TEXT NOT NULL,
    categoria TEXT NOT NULL,
    temporada TEXT,
    fecha_inicio TEXT,
    fecha_fin TEXT,
    estado TEXT DEFAULT 'En curso'
);

CREATE TABLE clubes (
    id INTEGER PRIMARY KEY,
    nombre TEXT NOT NULL,
    ciudad_id INTEGER NOT NULL,
    codigo TEXT UNIQUE NOT NULL,
    color TEXT,
    torneo_id INTEGER,
    FOREIGN KEY (ciudad_id) REFERENCES ciudades(id),
    FOREIGN KEY (torneo_id) REFERENCES torneos(id)
);

CREATE TABLE staff (
    id INTEGER PRIMARY KEY,
    club_id INTEGER NOT NULL,
    nombre TEXT NOT NULL,
    rol TEXT NOT NULL,
    telefono TEXT,
    email TEXT,
    licencia TEXT,
    FOREIGN KEY (club_id) REFERENCES clubes(id)
);

CREATE TABLE padres (
    id INTEGER PRIMARY KEY,
    nombre TEXT NOT NULL,
    telefono TEXT,
    email TEXT,
    parentesco TEXT DEFAULT 'Padre/Madre'
);

CREATE TABLE jugadores (
    id INTEGER PRIMARY KEY,
    club_id INTEGER NOT NULL,
    padre_id INTEGER,
    nombre TEXT NOT NULL,
    fecha_nacimiento TEXT,
    categoria TEXT,
    posicion TEXT,
    numero_camiseta INTEGER,
    talla_uniforme TEXT,
    eps TEXT,
    tipo_sangre TEXT,
    alergias TEXT,
    contacto_emergencia TEXT,
    telefono_emergencia TEXT,
    observaciones_medicas TEXT,
    FOREIGN KEY (club_id) REFERENCES clubes(id),
    FOREIGN KEY (padre_id) REFERENCES padres(id)
);

CREATE TABLE documentos (
    id INTEGER PRIMARY KEY,
    jugador_id INTEGER NOT NULL,
    tipo TEXT NOT NULL,
    nombre_archivo TEXT,
    estado TEXT DEFAULT 'Pendiente',
    comentario_ia TEXT,
    confianza_ia INTEGER,
    fecha_carga TEXT,
    FOREIGN KEY (jugador_id) REFERENCES jugadores(id)
);

CREATE TABLE partidos (
    id INTEGER PRIMARY KEY,
    torneo_id INTEGER NOT NULL,
    estadio_id INTEGER NOT NULL,
    club_local_id INTEGER NOT NULL,
    club_visitante_id INTEGER NOT NULL,
    fecha TEXT,
    hora TEXT,
    estado TEXT DEFAULT 'Programado',
    goles_local INTEGER DEFAULT 0,
    goles_visitante INTEGER DEFAULT 0,
    jornada INTEGER,
    FOREIGN KEY (torneo_id) REFERENCES torneos(id),
    FOREIGN KEY (estadio_id) REFERENCES estadios(id),
    FOREIGN KEY (club_local_id) REFERENCES clubes(id),
    FOREIGN KEY (club_visitante_id) REFERENCES clubes(id)
);

CREATE TABLE eventos (
    id INTEGER PRIMARY KEY,
    partido_id INTEGER NOT NULL,
    jugador_id INTEGER,
    club_id INTEGER NOT NULL,
    tipo TEXT NOT NULL,
    minuto INTEGER,
    FOREIGN KEY (partido_id) REFERENCES partidos(id),
    FOREIGN KEY (jugador_id) REFERENCES jugadores(id),
    FOREIGN KEY (club_id) REFERENCES clubes(id)
);
"""

CIUDADES = ["Facatativá", "Madrid", "Mosquera", "Funza", "Bojacá", "Zipacón", "El Rosal", "Subachoque"]

ESTADIOS = [
    ("Estadio La Manga", "Facatativá", 2500),
    ("Complejo Deportivo San Rafael", "Madrid", 1800),
    ("Unidad Deportiva Mosquera", "Mosquera", 3000),
    ("Estadio Municipal de Funza", "Funza", 2200),
    ("Polideportivo Bojacá", "Bojacá", 900),
    ("Cancha Zipacón Centro", "Zipacón", 700),
    ("Estadio El Rosal", "El Rosal", 1100),
    ("Polideportivo Subachoque", "Subachoque", 950),
]

CLUB_NOMBRES = [
    "Halcones de La Sabana", "Águilas de Facatativá", "Real Madrid Cundinamarca",
    "Deportivo Mosquera FC", "Cóndores de Funza", "Bojacá United",
    "Zipacón FC", "Estrellas del Rosal", "Sabana FC Subachoque",
    "Leones de Occidente", "Junior Sabanero", "Nueva Generación FC",
]

NOMBRES_M = ["Santiago", "Mateo", "Samuel", "Juan José", "Emmanuel", "Nicolás", "Simón",
             "Andrés", "David", "Tomás", "Sebastián", "Julián", "Martín", "Gabriel", "Esteban"]
NOMBRES_F = ["Salomé", "Mariana", "Isabella", "Valentina", "Sofía", "Luciana", "Emma",
             "Antonella", "Gabriela", "Renata", "Paula", "Camila", "Daniela"]
APELLIDOS = ["García", "Rodríguez", "Martínez", "López", "Gómez", "Díaz", "Hernández",
             "Pérez", "Sánchez", "Ramírez", "Torres", "Vargas", "Castro", "Rojas",
             "Moreno", "Suárez", "Cárdenas", "Bernal", "Pinzón", "Quintero"]

ROLES_STAFF = ["Director Técnico", "Preparador Físico", "Asistente Técnico", "Delegado", "Fisioterapeuta"]
CATEGORIAS = ["Sub-9", "Sub-11", "Sub-13", "Sub-15"]
POSICIONES = ["Portero", "Defensa Central", "Lateral", "Volante", "Delantero", "Extremo"]
EPS_LIST = ["Sura", "Sanitas", "Compensar", "Nueva EPS", "Famisanar", "Salud Total"]
TIPOS_DOC = ["Registro civil / Tarjeta de identidad", "Autorización de padres", "Carné EPS o afiliación en salud", "Certificado médico deportivo"]

random.seed(42)


def _fecha_nacimiento(categoria):
    edades = {"Sub-9": (7, 9), "Sub-11": (9, 11), "Sub-13": (11, 13), "Sub-15": (13, 15)}
    lo, hi = edades[categoria]
    edad = random.randint(lo, hi)
    hoy = date.today()
    return (hoy - timedelta(days=edad * 365 + random.randint(0, 300))).isoformat()


def build_database():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)

    cur = conn.cursor()

    # Ciudades
    ciudad_ids = {}
    for nombre in CIUDADES:
        cur.execute("INSERT INTO ciudades (nombre) VALUES (?)", (nombre,))
        ciudad_ids[nombre] = cur.lastrowid

    # Estadios
    for nombre, ciudad, cap in ESTADIOS:
        cur.execute(
            "INSERT INTO estadios (nombre, ciudad_id, direccion, capacidad) VALUES (?,?,?,?)",
            (nombre, ciudad_ids[ciudad], f"Vía principal, {ciudad}", cap),
        )

    # Torneo
    cur.execute(
        "INSERT INTO torneos (nombre, categoria, temporada, fecha_inicio, fecha_fin, estado) VALUES (?,?,?,?,?,?)",
        ("Copa Sabana de Occidente 2026", "Sub-9 a Sub-15", "2026-II",
         "2026-09-06", "2026-11-22", "En curso"),
    )
    torneo_id = cur.lastrowid

    # Clubes (uno por ciudad + algunos extra)
    club_ids = []
    colores = ["#2E7D46", "#B23A2E", "#1F4E8C", "#D6A93B", "#4A3F73", "#2E7D46",
               "#B23A2E", "#1F4E8C", "#D6A93B", "#4A3F73", "#2E7D46", "#B23A2E"]
    ciudades_ciclo = list(CIUDADES) + random.sample(CIUDADES, len(CLUB_NOMBRES) - len(CIUDADES))
    for i, nombre in enumerate(CLUB_NOMBRES):
        ciudad = ciudades_ciclo[i]
        codigo = f"{ciudad[:3].upper()}-{100 + i}"
        cur.execute(
            "INSERT INTO clubes (nombre, ciudad_id, codigo, color, torneo_id) VALUES (?,?,?,?,?)",
            (nombre, ciudad_ids[ciudad], codigo, colores[i % len(colores)], torneo_id),
        )
        club_ids.append(cur.lastrowid)

    # Staff por club
    for club_id in club_ids:
        n_staff = random.randint(2, 4)
        roles_asignados = random.sample(ROLES_STAFF, n_staff)
        for rol in roles_asignados:
            genero = random.choice([NOMBRES_M, NOMBRES_F])
            nombre = f"{random.choice(genero)} {random.choice(APELLIDOS)} {random.choice(APELLIDOS)}"
            cur.execute(
                "INSERT INTO staff (club_id, nombre, rol, telefono, email, licencia) VALUES (?,?,?,?,?,?)",
                (club_id, nombre, rol, f"3{random.randint(10,29)}{random.randint(1000000,9999999)}",
                 nombre.lower().replace(' ', '.') + "@vigor-demo.co",
                 f"LIC-{random.randint(1000,9999)}" if rol == "Director Técnico" else None),
            )

    # Padres + jugadores + documentos
    doc_estados = ["Aprobado", "Aprobado", "Aprobado", "Pendiente", "Rechazado"]
    for club_id in club_ids:
        categoria_club = random.choice(CATEGORIAS)
        n_jugadores = random.randint(10, 14)
        for _ in range(n_jugadores):
            genero = random.choice([NOMBRES_M, NOMBRES_F])
            nombre_padre = f"{random.choice(APELLIDOS)} {random.choice(NOMBRES_M + NOMBRES_F)}"
            padre_nombre = f"{random.choice(NOMBRES_M + NOMBRES_F)} {random.choice(APELLIDOS)}"
            cur.execute(
                "INSERT INTO padres (nombre, telefono, email, parentesco) VALUES (?,?,?,?)",
                (padre_nombre, f"3{random.randint(10,29)}{random.randint(1000000,9999999)}",
                 padre_nombre.lower().replace(' ', '.') + "@gmail.com",
                 random.choice(["Madre", "Padre", "Acudiente"])),
            )
            padre_id = cur.lastrowid

            nombre_jugador = f"{random.choice(genero)} {random.choice(APELLIDOS)} {random.choice(APELLIDOS)}"
            cur.execute("""INSERT INTO jugadores
                (club_id, padre_id, nombre, fecha_nacimiento, categoria, posicion, numero_camiseta,
                 talla_uniforme, eps, tipo_sangre, alergias, contacto_emergencia, telefono_emergencia,
                 observaciones_medicas)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (club_id, padre_id, nombre_jugador, _fecha_nacimiento(categoria_club), categoria_club,
                 random.choice(POSICIONES), random.randint(1, 30),
                 random.choice(["6", "8", "10", "12", "14"]), random.choice(EPS_LIST),
                 random.choice(["O+", "O-", "A+", "A-", "B+", "AB+"]),
                 random.choice(["Ninguna", "Ninguna", "Ninguna", "Alergia al polen", "Alergia a la penicilina"]),
                 padre_nombre, f"3{random.randint(10,29)}{random.randint(1000000,9999999)}",
                 random.choice(["Ninguna", "Ninguna", "Usa inhalador para el asma", "Ninguna"])))
            jugador_id = cur.lastrowid

            for tipo in TIPOS_DOC:
                estado = random.choice(doc_estados)
                comentario = {
                    "Aprobado": "Documento legible y coincide con los datos registrados del jugador.",
                    "Pendiente": "En cola de revisión automática.",
                    "Rechazado": "La imagen no coincide con el tipo de documento o está incompleta.",
                }[estado]
                cur.execute("""INSERT INTO documentos
                    (jugador_id, tipo, nombre_archivo, estado, comentario_ia, confianza_ia, fecha_carga)
                    VALUES (?,?,?,?,?,?,?)""",
                    (jugador_id, tipo, f"{tipo.split(' ')[0].lower()}_{jugador_id}.pdf", estado, comentario,
                     random.randint(70, 99) if estado != "Pendiente" else None,
                     (date.today() - timedelta(days=random.randint(0, 20))).isoformat()))

    # Partidos (round-robin simplificado por jornadas)
    estadio_ids = [row[0] for row in cur.execute("SELECT id FROM estadios").fetchall()]
    fecha_base = date(2026, 9, 6)
    jornada = 1
    clubes_shuffle = club_ids[:]
    random.shuffle(clubes_shuffle)
    for j in range(6):
        fecha_jornada = fecha_base + timedelta(days=7 * j)
        pares = list(zip(clubes_shuffle[::2], clubes_shuffle[1::2]))
        for idx, (local, visitante) in enumerate(pares):
            estadio = random.choice(estadio_ids)
            jugado = fecha_jornada < date(2026, 9, 3) + timedelta(days=7)  # solo la primera jornada ya jugada en el demo
            estado = "Finalizado" if j == 0 else ("Programado" if fecha_jornada > date.today() else "Finalizado")
            gl = random.randint(0, 5) if estado == "Finalizado" else 0
            gv = random.randint(0, 5) if estado == "Finalizado" else 0
            cur.execute("""INSERT INTO partidos
                (torneo_id, estadio_id, club_local_id, club_visitante_id, fecha, hora, estado,
                 goles_local, goles_visitante, jornada)
                VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (torneo_id, estadio, local, visitante, fecha_jornada.isoformat(),
                 f"{random.choice([8,9,10,14,15,16])}:00", estado, gl, gv, j + 1))
            partido_id = cur.lastrowid

            if estado == "Finalizado":
                for club_id, goles in ((local, gl), (visitante, gv)):
                    jugadores_club = [r[0] for r in cur.execute(
                        "SELECT id FROM jugadores WHERE club_id=?", (club_id,)).fetchall()]
                    for _ in range(goles):
                        cur.execute(
                            "INSERT INTO eventos (partido_id, jugador_id, club_id, tipo, minuto) VALUES (?,?,?,?,?)",
                            (partido_id, random.choice(jugadores_club), club_id, "Gol", random.randint(1, 90)))
                    for _ in range(random.randint(0, 3)):
                        tipo_falta = random.choice(["Falta", "Tarjeta amarilla", "Tarjeta amarilla", "Tarjeta roja"])
                        cur.execute(
                            "INSERT INTO eventos (partido_id, jugador_id, club_id, tipo, minuto) VALUES (?,?,?,?,?)",
                            (partido_id, random.choice(jugadores_club), club_id, tipo_falta, random.randint(1, 90)))

    conn.commit()
    conn.close()


def get_connection():
    if not os.path.exists(DB_PATH):
        build_database()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


if __name__ == "__main__":
    build_database()
    print(f"Base de datos demo creada en {DB_PATH}")
