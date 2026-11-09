-- =========================================================================
-- Migración: corregir la función validar_perfiles_usuario() en Neon
-- Fecha: 2026-11-09
--
-- Problema: la función la comparten 3 triggers (en usuarios, alumnos y
-- profesores). En la condición
--     IF TG_TABLE_NAME IN ('alumnos','profesores') AND TG_OP = 'UPDATE'
--        AND OLD.usuario_id IS DISTINCT FROM NEW.usuario_id THEN
-- PL/pgSQL evalúa la expresión completa y resuelve OLD.usuario_id aunque
-- el trigger corra sobre 'usuarios', que no tiene esa columna. Resultado:
-- todo INSERT o UPDATE en usuarios fallaba al confirmar la transacción con
--     record "old" has no field "usuario_id"
-- (no se podían crear cuentas ni completar el cambio de contraseña).
--
-- Corrección: la comparación de OLD.usuario_id pasa a un IF anidado, que
-- solo se evalúa en UPDATE de alumnos/profesores. El resto de la función
-- (las reglas de perfiles por rol) no cambia.
--
-- La función se creó directamente en Neon (no estaba en el repositorio);
-- este archivo la versiona. Idempotente. Revertir con:
--     2026-11-09_corregir_validar_perfiles_usuario_revertir.sql
-- =========================================================================
BEGIN;

CREATE OR REPLACE FUNCTION public.validar_perfiles_usuario()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_usuario_id BIGINT;
    v_rol VARCHAR(20);
    v_total_alumnos INTEGER;
    v_total_profesores INTEGER;
BEGIN
    IF TG_TABLE_NAME = 'usuarios' THEN
        v_usuario_id := CASE WHEN TG_OP = 'DELETE' THEN OLD.id ELSE NEW.id END;
    ELSIF TG_TABLE_NAME = 'alumnos' THEN
        v_usuario_id := CASE WHEN TG_OP = 'DELETE' THEN OLD.usuario_id ELSE NEW.usuario_id END;
    ELSIF TG_TABLE_NAME = 'profesores' THEN
        v_usuario_id := CASE WHEN TG_OP = 'DELETE' THEN OLD.usuario_id ELSE NEW.usuario_id END;
    END IF;

    -- En cambios de usuario_id en un perfil, también revisar la asociación anterior.
    PERFORM validar_un_usuario(v_usuario_id);
    -- Corrección 2026-11-09: el IF anidado evita evaluar OLD.usuario_id cuando
    -- el trigger corre sobre 'usuarios' (esa tabla no tiene usuario_id; antes
    -- todo INSERT/UPDATE en usuarios fallaba con
    -- 'record "old" has no field "usuario_id"').
    IF TG_TABLE_NAME IN ('alumnos','profesores') AND TG_OP = 'UPDATE' THEN
        IF OLD.usuario_id IS DISTINCT FROM NEW.usuario_id THEN
            PERFORM validar_un_usuario(OLD.usuario_id);
        END IF;
    END IF;
    RETURN NULL;
END;
$function$;

COMMIT;
