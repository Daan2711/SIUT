-- =========================================================================
-- Migración: seguimiento de postulaciones e inscripciones a eventos
-- Fecha: 2026-11-12
--
-- 1. postulaciones: la empresa marca la postulación como recibida y deja
--    un comentario para el alumno.
-- 2. usuario_evento: nombre y correo que escribe el alumno al inscribirse,
--    y la marca «OK» del administrador.
-- 3. eventos: los 3 eventos de la página de inicio (fecha provisional
--    1 de diciembre de 2026, hora de Monterrey).
--
-- Solo agrega columnas y filas; no modifica ni borra datos existentes.
-- Es idempotente (se puede ejecutar más de una vez).
-- Revertir con: 2026-11-12_seguimiento_postulaciones_eventos_revertir.sql
-- =========================================================================
BEGIN;

-- 1. Seguimiento de postulaciones ---------------------------------------
ALTER TABLE postulaciones
    ADD COLUMN IF NOT EXISTS revisada_en        TIMESTAMPTZ NULL,
    ADD COLUMN IF NOT EXISTS revisada_por       BIGINT NULL
        REFERENCES usuarios(id) ON DELETE RESTRICT,
    ADD COLUMN IF NOT EXISTS comentario_empresa VARCHAR(1500) NULL,
    ADD COLUMN IF NOT EXISTS comentario_en      TIMESTAMPTZ NULL;

COMMENT ON COLUMN postulaciones.revisada_en IS
    'Cuándo la empresa marcó la postulación como recibida (botón «Recibido»).';
COMMENT ON COLUMN postulaciones.comentario_empresa IS
    'Comentario de la empresa para el alumno.';

-- 2. Datos de la inscripción a eventos -----------------------------------
ALTER TABLE usuario_evento
    ADD COLUMN IF NOT EXISTS nombre         VARCHAR(150) NULL,
    ADD COLUMN IF NOT EXISTS correo         VARCHAR(254) NULL,
    ADD COLUMN IF NOT EXISTS confirmada     BOOLEAN NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS confirmada_por BIGINT NULL
        REFERENCES usuarios(id) ON DELETE RESTRICT,
    ADD COLUMN IF NOT EXISTS confirmada_en  TIMESTAMPTZ NULL;

COMMENT ON COLUMN usuario_evento.confirmada IS
    'El administrador marcó la inscripción como «OK».';

-- 3. Eventos de la página de inicio --------------------------------------
INSERT INTO eventos (titulo, descripcion, fecha_inicio, publicado, activo)
SELECT v.titulo, v.descripcion, TIMESTAMPTZ '2026-12-01 00:00:00 America/Monterrey', true, true
FROM (VALUES
    ('Hackathon', 'Concurso para probar tus habilidades de programación'),
    ('UT Canta 2026', '¡Demuestra tu habilidad de canto!'),
    ('Club Música', '¿Tocas algún instrumento? Únete al club de música')
) AS v(titulo, descripcion)
WHERE NOT EXISTS (SELECT 1 FROM eventos e WHERE e.titulo = v.titulo);

COMMIT;
