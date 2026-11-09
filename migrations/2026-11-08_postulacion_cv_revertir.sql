-- =========================================================================
-- Revertir: 2026-11-08_postulacion_cv.sql
--
-- ⚠️ ELIMINA TODOS LOS CV GUARDADOS. Las postulaciones quedan sin su PDF.
-- Solo usar si se vuelve a guardar los CV en disco o en otro almacenamiento.
-- =========================================================================
BEGIN;

DROP TABLE IF EXISTS postulacion_cv;

COMMIT;
