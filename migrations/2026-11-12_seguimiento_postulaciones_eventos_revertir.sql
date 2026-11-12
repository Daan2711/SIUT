-- =========================================================================
-- Revierte 2026-11-12_seguimiento_postulaciones_eventos.sql
--
-- ATENCIÓN: borra los comentarios de las empresas, el nombre y correo de
-- las inscripciones y la marca «OK». Los eventos solo se borran si no
-- tienen inscripciones (las llaves foráneas son ON DELETE RESTRICT).
-- =========================================================================
BEGIN;

ALTER TABLE postulaciones
    DROP COLUMN IF EXISTS revisada_en,
    DROP COLUMN IF EXISTS revisada_por,
    DROP COLUMN IF EXISTS comentario_empresa,
    DROP COLUMN IF EXISTS comentario_en;

ALTER TABLE usuario_evento
    DROP COLUMN IF EXISTS nombre,
    DROP COLUMN IF EXISTS correo,
    DROP COLUMN IF EXISTS confirmada,
    DROP COLUMN IF EXISTS confirmada_por,
    DROP COLUMN IF EXISTS confirmada_en;

DELETE FROM eventos e
WHERE e.titulo IN ('Hackathon', 'UT Canta 2026', 'Club Música')
  AND NOT EXISTS (SELECT 1 FROM usuario_evento ue WHERE ue.evento_id = e.id);

COMMIT;
