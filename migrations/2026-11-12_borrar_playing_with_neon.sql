-- Borra la tabla de ejemplo que Neon crea al abrir un proyecto. SIUT no la usa:
-- no la referencian modelos, controladores, llaves foráneas, vistas, triggers ni
-- funciones (revisado en solo lectura el 2026-11-12). Su secuencia
-- playing_with_neon_id_seq pertenece a la tabla y se borra con ella.
-- Para revertir: 2026-11-12_borrar_playing_with_neon_revertir.sql
BEGIN;

-- Sin CASCADE: si algo dependiera de la tabla, falla y no se borra nada.
DROP TABLE public.playing_with_neon;

COMMIT;
