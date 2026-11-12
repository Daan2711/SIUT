-- Revierte 2026-11-12_borrar_playing_with_neon.sql: recrea la tabla de ejemplo
-- de Neon con sus 10 filas originales (copiadas en solo lectura antes de borrarla).
-- Solo es necesario si se quiere recuperar esa tabla; SIUT no la usa.
BEGIN;

CREATE TABLE public.playing_with_neon (
    id    SERIAL PRIMARY KEY,
    name  TEXT NOT NULL,
    value REAL
);

INSERT INTO public.playing_with_neon (id, name, value) VALUES
    (1, 'c4ca4238a0', 0.67934245),
    (2, 'c81e728d9d', 0.7445786),
    (3, 'eccbc87e4b', 0.26937535),
    (4, 'a87ff679a2', 0.96532154),
    (5, 'e4da3b7fbb', 0.9240149),
    (6, '1679091c5a', 0.71384877),
    (7, '8f14e45fce', 0.023780832),
    (8, 'c9f0f895fb', 0.15303853),
    (9, '45c48cce2e', 0.056952473),
    (10, 'd3d9446802', 0.70537347);

SELECT setval('public.playing_with_neon_id_seq', 10, true);

COMMIT;
