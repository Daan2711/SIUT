-- =========================================================================
-- Revertir: 2026-11-09_corregir_validar_perfiles_usuario.sql
-- Restaura la definición original copiada de Neon el 2026-11-09.
-- ⚠️ La versión original vuelve a impedir INSERT/UPDATE en usuarios.
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
    IF TG_TABLE_NAME IN ('alumnos','profesores') AND TG_OP = 'UPDATE'
       AND OLD.usuario_id IS DISTINCT FROM NEW.usuario_id THEN
        PERFORM validar_un_usuario(OLD.usuario_id);
    END IF;
    RETURN NULL;
END;
$function$;

COMMIT;
