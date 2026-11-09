-- =========================================================================
-- Migración: guardar el CV (PDF) de cada postulación dentro de Neon
-- Fecha: 2026-11-08
--
-- Motivo: en el plan gratis de Render no hay disco persistente; los CV
-- guardados en el disco del servidor se perderían en cada despliegue o
-- reinicio. Esta tabla guarda el PDF en la base de datos.
--
-- Es un cambio solo aditivo: crea una tabla nueva y no modifica las
-- existentes. Es idempotente (se puede ejecutar más de una vez).
-- Revertir con: 2026-11-08_postulacion_cv_revertir.sql
-- =========================================================================
BEGIN;

CREATE TABLE IF NOT EXISTS postulacion_cv (
    postulacion_id BIGINT PRIMARY KEY
        REFERENCES postulaciones(id) ON DELETE RESTRICT,
    contenido      BYTEA NOT NULL,
    creado_en      TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- Igual que chk_cv_tamano de postulaciones: de 1 byte a 5 MB
    CONSTRAINT chk_postulacion_cv_tamano
        CHECK (length(contenido) > 0 AND length(contenido) <= 5242880)
);

COMMENT ON TABLE postulacion_cv IS
    'Contenido del CV (PDF) de cada postulación. Una fila por postulación.';

COMMIT;
