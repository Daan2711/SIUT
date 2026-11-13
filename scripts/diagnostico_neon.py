"""Diagnóstico general de la base de datos de Neon, en SOLO LECTURA.

Uso (desde la raíz del repositorio, con DATABASE_URL en el .env):

    python scripts/diagnostico_neon.py

Qué revisa: espacio usado, esquema de Neon frente a Models/models.py,
triggers, restricciones e índices, consistencia de usuarios, vacantes,
postulaciones y CV, sugerencias, eventos e inscripciones, auditoría y
secuencias de ids.

Garantías:
- La conexión se abre en modo solo lectura y se verifica antes de consultar;
  no contiene ninguna instrucción que escriba en la base de datos.
- No imprime correos, nombres, contraseñas, hashes ni contenido de CV:
  solo ids, conteos y el resultado de cada comprobación.

Código de salida: 0 sin problemas (puede haber avisos), 1 con problemas,
2 si no se pudo ejecutar (falta DATABASE_URL o la sesión no es de solo lectura).
"""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

# Días hacia atrás para buscar inicios de sesión dobles
DIAS_LOGIN_DOBLE = 7
ESTADOS_SUGERENCIA = ('Recibida', 'En revisión', 'Atendida', 'Rechazada')
ESTADOS_POSTULACION = ('Recibida', 'En revisión', 'Aceptada', 'Rechazada')
TABLAS_CONTEO = ('usuarios', 'alumnos', 'profesores', 'empresas', 'vacantes', 'postulaciones',
                 'postulacion_cv', 'sugerencias', 'categorias_sugerencia', 'eventos',
                 'usuario_evento', 'auditoria', 'recuperaciones_password')
TABLAS_SECUENCIA = ('usuarios', 'alumnos', 'profesores', 'empresas', 'vacantes', 'postulaciones',
                    'sugerencias', 'eventos', 'usuario_evento', 'auditoria',
                    'recuperaciones_password')


def detener(mensaje):
    print(f'ERROR: {mensaje} No se revisó nada.', file=sys.stderr)
    sys.exit(2)


def conectar():
    """Conexión de solo lectura; termina con código 2 si no es posible."""
    from dotenv import load_dotenv
    import psycopg2

    load_dotenv(os.path.join(REPO, '.env'))
    url = os.environ.get('DATABASE_URL')
    if not url:
        detener('falta DATABASE_URL (en el .env o en el entorno).')
    conn = psycopg2.connect(url)
    conn.set_session(readonly=True)
    cur = conn.cursor()
    cur.execute('show transaction_read_only')
    if cur.fetchone()[0] != 'on':
        conn.close()
        detener('la sesión no quedó en solo lectura.')
    return conn, cur


def main():
    conn, cur = conectar()
    problemas, avisos = [], []

    def uno(sql, *args):
        cur.execute(sql, args or None)
        return cur.fetchone()[0]

    def filas(sql, *args):
        cur.execute(sql, args or None)
        return cur.fetchall()

    def revisar(nombre, sql, nivel='problema', args=None):
        """La consulta devuelve las filas con problemas (ids); vacío = OK."""
        cur.execute(sql, args)
        r = cur.fetchall()
        estado = 'OK' if not r else ('PROBLEMA' if nivel == 'problema' else 'AVISO')
        print(f'  [{estado:8}] {nombre}' + (f' -> {r[:10]}' if r else ''))
        if r:
            (problemas if nivel == 'problema' else avisos).append(nombre)

    print('== Servidor')
    print('  ', uno('select version()').split(',')[0])
    print('   solo lectura:', uno('show transaction_read_only'), '| zona horaria:', uno('show timezone'))

    print('\n== Espacio (límite del plan gratis de Neon: 0.5 GB)')
    total = uno('select pg_database_size(current_database())')
    porcentaje = total / (512 * 1024 * 1024) * 100
    print(f'   base completa: {total / 1024 / 1024:.1f} MB ({porcentaje:.1f} % del límite)')
    if porcentaje >= 80:
        avisos.append('espacio por encima del 80 %')
    for t, tam in filas("""select relname, pg_total_relation_size(c.oid) from pg_class c
                           join pg_namespace n on n.oid=c.relnamespace
                           where n.nspname='public' and c.relkind='r' order by 2 desc limit 5"""):
        print(f'   {t:24} {tam / 1024:8.0f} KB')

    print('\n== Conteos')
    for t in TABLAS_CONTEO:
        print(f'   {t:24} {uno(f"select count(*) from {t}")}')
    print('   usuarios por rol (total, activos):',
          filas('select rol, count(*), sum(case when activo then 1 else 0 end) '
                'from usuarios group by rol order by rol'))

    print('\n== Esquema de Neon frente a los modelos (Models/models.py)')
    from Database.database import db
    import Models.models  # noqa: F401  (registra las tablas en db.metadata)
    columnas_neon = {}
    for t, c in filas("""select table_name, column_name from information_schema.columns
                         where table_schema='public'"""):
        columnas_neon.setdefault(t, set()).add(c)
    for tabla in db.metadata.sorted_tables:
        if tabla.name not in columnas_neon:
            print(f'  [PROBLEMA] tabla {tabla.name} del modelo no existe en Neon')
            problemas.append(f'tabla {tabla.name}')
            continue
        faltan = [c.name for c in tabla.columns if c.name not in columnas_neon[tabla.name]]
        if faltan:
            print(f'  [PROBLEMA] {tabla.name}: columnas del modelo que no están en Neon: {faltan}')
            problemas.append(f'columnas {tabla.name}')
    modelo = {t.name for t in db.metadata.sorted_tables}
    solo_neon = sorted(set(columnas_neon) - modelo)
    print(f'   {len(modelo)} tablas del modelo revisadas'
          + (f'; tablas solo en Neon: {solo_neon}' if solo_neon else ''))

    print('\n== Triggers, restricciones e índices')
    for t, nombre, estado in filas("""select c.relname, tg.tgname, tg.tgenabled from pg_trigger tg
                                      join pg_class c on c.oid=tg.tgrelid
                                      join pg_namespace n on n.oid=c.relnamespace
                                      where n.nspname='public' and not tg.tgisinternal order by 1, 2"""):
        print(f'   {"activo  " if estado != "D" else "DESACTIV"} {t}.{nombre}')
        if estado == 'D':
            problemas.append(f'trigger desactivado {nombre}')
    revisar('restricciones sin validar (NOT VALID)',
            "select conrelid::regclass::text, conname from pg_constraint c join pg_namespace n "
            "on n.oid=c.connamespace where n.nspname='public' and not convalidated")
    revisar('índices inválidos', 'select indexrelid::regclass::text from pg_index where not indisvalid')

    print('\n== Usuarios y perfiles')
    revisar('más de 4 administradores',
            "select count(*) from usuarios where rol='Administrador' having count(*) > 4")
    revisar('roles fuera de la lista',
            "select id, rol from usuarios where rol not in ('Administrador','Alumno','Profesor','Empresa')")
    revisar('correos repetidos (sin distinguir mayúsculas)',
            'select count(*) from usuarios group by lower(email) having count(*) > 1')
    revisar('correos con espacios o mayúsculas', 'select id from usuarios where email <> lower(trim(email))',
            'aviso')
    revisar('contraseñas que no son bcrypt',
            "select id from usuarios where password_hash !~ '^\\$2[aby]\\$[0-9]{2}\\$.{53}$'")
    revisar('Alumno sin perfil de alumno',
            "select u.id from usuarios u left join alumnos a on a.usuario_id=u.id "
            "where u.rol='Alumno' and a.id is null")
    revisar('Profesor sin perfil de profesor',
            "select u.id from usuarios u left join profesores p on p.usuario_id=u.id "
            "where u.rol='Profesor' and p.id is null")
    revisar('Empresa sin empresa asignada',
            "select u.id from usuarios u left join empresas e on e.id=u.empresa_id "
            "where u.rol='Empresa' and e.id is null")
    revisar('perfil de alumno en un usuario que no es Alumno',
            "select a.id, u.rol from alumnos a join usuarios u on u.id=a.usuario_id where u.rol<>'Alumno'")
    revisar('perfil de profesor en un usuario que no es Profesor',
            "select p.id, u.rol from profesores p join usuarios u on u.id=p.usuario_id where u.rol<>'Profesor'")
    revisar('empresa asignada a un usuario que no es Empresa',
            "select id, rol from usuarios where empresa_id is not null and rol<>'Empresa'", 'aviso')
    revisar('cuentas con cambio de contraseña pendiente',
            'select id, rol from usuarios where primer_login', 'aviso')
    revisar('cuentas desactivadas', 'select id, rol from usuarios where not activo', 'aviso')
    revisar('creado_por apunta a un usuario inexistente',
            'select u.id from usuarios u left join usuarios c on c.id=u.creado_por '
            'where u.creado_por is not null and c.id is null')
    from Controllers.postulacionesController import SEMESTRES
    revisar('alumnos con un cuatrimestre que ya no está en la lista',
            'select id, semestre from alumnos where semestre is not null and semestre <> all(%s)',
            'aviso', (list(SEMESTRES),))

    print('\n== Vacantes y postulaciones')
    revisar('vacante sin empresa existente',
            'select v.id from vacantes v left join empresas e on e.id=v.empresa_id where e.id is null')
    revisar('vacante con campos obligatorios vacíos',
            "select id from vacantes where coalesce(trim(titulo),'')='' or coalesce(trim(descripcion),'')='' "
            "or coalesce(trim(requisitos),'')=''")
    revisar('postulación sin CV guardado',
            'select p.id from postulaciones p left join postulacion_cv c on c.postulacion_id=p.id '
            'where c.postulacion_id is null')
    revisar('CV guardado sin postulación',
            'select c.postulacion_id from postulacion_cv c left join postulaciones p on p.id=c.postulacion_id '
            'where p.id is null')
    revisar('CV cuyo tamaño no coincide con el registrado',
            'select p.id from postulaciones p join postulacion_cv c on c.postulacion_id=p.id '
            'where octet_length(c.contenido) <> p.cv_tamano_bytes')
    revisar('CV que no empieza con la firma %PDF-',
            "select postulacion_id from postulacion_cv where substring(contenido from 1 for 5) <> '%PDF-'::bytea")
    revisar('CV de más de 5 MB',
            'select postulacion_id from postulacion_cv where octet_length(contenido) > 5242880')
    revisar('postulación de un usuario que no es Alumno',
            'select p.id from postulaciones p join alumnos a on a.id=p.alumno_id '
            "join usuarios u on u.id=a.usuario_id where u.rol<>'Alumno'")
    revisar('postulación repetida (mismo alumno y vacante)',
            'select alumno_id, vacante_id from postulaciones group by 1, 2 having count(*) > 1')
    revisar('estado de postulación fuera de la lista',
            'select id, estado from postulaciones where estado <> all(%s)', args=(list(ESTADOS_POSTULACION),))
    revisar('postulación revisada sin quién o sin fecha',
            'select id from postulaciones where (revisada_en is null) <> (revisada_por is null)')
    revisar('postulación revisada por alguien que no es la empresa dueña ni un Administrador',
            'select p.id from postulaciones p join vacantes v on v.id=p.vacante_id '
            'join usuarios u on u.id=p.revisada_por '
            "where not (u.rol='Administrador' or (u.rol='Empresa' and u.empresa_id=v.empresa_id))")
    revisar('comentario de la empresa sin fecha (o fecha sin comentario)',
            'select id from postulaciones where (comentario_empresa is null) <> (comentario_en is null)')
    revisar('postulación con resultado o comentario sin haberse marcado como recibida',
            "select id from postulaciones where (comentario_en is not null or estado in ('Aceptada','Rechazada')) "
            'and revisada_en is null')
    revisar('vacante dada de baja con postulaciones sin revisar',
            'select v.id, count(*) from vacantes v join postulaciones p on p.vacante_id=v.id '
            'where not v.activo and p.revisada_en is null group by v.id', 'aviso')

    print('\n== Sugerencias')
    revisar('estado fuera de la lista',
            'select id, estado from sugerencias where estado <> all(%s)', args=(list(ESTADOS_SUGERENCIA),))
    revisar('atendida sin administrador o sin fecha',
            "select id from sugerencias where estado<>'Recibida' "
            'and (atendida_por is null or fecha_atencion is null)')
    revisar('atendida por alguien que no es Administrador',
            "select s.id from sugerencias s join usuarios u on u.id=s.atendida_por where u.rol<>'Administrador'")
    revisar('sugerencia sin categoría existente',
            'select s.id from sugerencias s left join categorias_sugerencia c on c.id=s.categoria_id '
            'where s.categoria_id is not null and c.id is null')

    print('\n== Eventos e inscripciones')
    revisar('evento sin título o sin fecha de inicio',
            "select id from eventos where coalesce(trim(titulo),'')='' or fecha_inicio is null")
    revisar('evento que termina antes de empezar',
            'select id from eventos where fecha_fin is not null and fecha_fin < fecha_inicio')
    revisar('inscripción repetida (mismo usuario y evento)',
            'select usuario_id, evento_id from usuario_evento group by 1, 2 having count(*) > 1')
    revisar('inscripción a un evento inexistente',
            'select i.id from usuario_evento i left join eventos e on e.id=i.evento_id where e.id is null')
    revisar('inscripción de un usuario inexistente',
            'select i.id from usuario_evento i left join usuarios u on u.id=i.usuario_id where u.id is null')
    revisar('inscripción marcada OK sin quién o sin fecha',
            'select id from usuario_evento where confirmada and (confirmada_por is null or confirmada_en is null)')
    revisar('inscripción marcada OK por alguien que no es Administrador',
            'select i.id from usuario_evento i join usuarios u on u.id=i.confirmada_por '
            "where u.rol<>'Administrador'")
    revisar('inscripción a un evento inactivo', 'select i.id from usuario_evento i join eventos e '
            'on e.id=i.evento_id where not e.activo', 'aviso')

    print('\n== Auditoría')
    revisar('registros de un usuario inexistente',
            'select a.id from auditoria a left join usuarios u on u.id=a.usuario_id '
            'where a.usuario_id is not null and u.id is null')
    revisar('registros con fecha en el futuro',
            "select id from auditoria where creado_en > now() + interval '1 minute'")
    revisar('altas de usuario sin registro en la auditoría',
            'select u.id from usuarios u where u.creado_por is not null and not exists (select 1 from auditoria a '
            "where a.accion like 'Alta de usuario%' and a.registro_id=u.id)", 'aviso')
    revisar(f'inicios de sesión dobles (menos de 5 s) en los últimos {DIAS_LOGIN_DOBLE} días',
            'select a.id, a.usuario_id from auditoria a join auditoria b '
            'on b.usuario_id=a.usuario_id and b.accion=a.accion and b.id=a.id-1 '
            "and a.creado_en - b.creado_en < interval '5 seconds' "
            "where a.accion='Inicio de sesión' and a.creado_en > now() - make_interval(days => %s)",
            'aviso', (DIAS_LOGIN_DOBLE,))
    print('   acciones registradas:', filas('select accion, count(*) from auditoria group by 1 order by 2 desc'))

    print('\n== Secuencias (el siguiente id no debe chocar con uno existente)')
    for t in TABLAS_SECUENCIA:
        seq = uno("select pg_get_serial_sequence(%s, 'id')", t)
        if not seq:
            print(f'   {t}: sin secuencia')
            continue
        ultimo = uno(f'select last_value from {seq}')
        maximo = uno(f'select coalesce(max(id), 0) from {t}')
        ok = ultimo >= maximo
        print(f'  [{"OK" if ok else "PROBLEMA":8}] {t}: secuencia {ultimo}, id máximo {maximo}')
        if not ok:
            problemas.append(f'secuencia {t}')

    conn.close()
    print('\n== RESUMEN')
    print('   problemas:', problemas or 'ninguno')
    print('   avisos   :', avisos or 'ninguno')
    return 1 if problemas else 0


if __name__ == '__main__':
    sys.exit(main())
