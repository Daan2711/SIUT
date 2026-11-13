-- =========================================================================
-- Migración: códigos para recuperar la contraseña («¿Olvidaste tu contraseña?»)
-- Fecha: 2026-11-12
--
-- Tabla nueva recuperaciones_password: un código de 4 dígitos por solicitud,
-- guardado cifrado con bcrypt (nunca en claro). Vence a los 10 minutos y se
-- anula con 5 intentos fallidos o al pedir uno nuevo (usado_en).
-- La usa Controllers/recuperacionController.py.
--
-- Solo crea una tabla; no modifica ni borra datos existentes.
-- Es idempotente (se puede ejecutar más de una vez).
-- Revertir con: 2026-11-12_recuperaciones_password_revertir.sql
-- =========================================================================
BEGIN;

CREATE TABLE IF NOT EXISTS recuperaciones_password (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    usuario_id  BIGINT       NOT NULL REFERENCES usuarios(id) ON DELETE RESTRICT,
    codigo_hash VARCHAR(100) NOT NULL,
    vence_en    TIMESTAMPTZ  NOT NULL,
    intentos    SMALLINT     NOT NULL DEFAULT 0,
    usado_en    TIMESTAMPTZ  NULL,
    creado_en   TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT chk_recuperaciones_intentos CHECK (intentos BETWEEN 0 AND 5)
);

CREATE INDEX IF NOT EXISTS idx_recuperaciones_usuario
    ON recuperaciones_password (usuario_id, creado_en DESC);

COMMENT ON TABLE recuperaciones_password IS
    'Códigos de 4 dígitos para recuperar la contraseña por correo (cifrados con bcrypt).';
COMMENT ON COLUMN recuperaciones_password.codigo_hash IS
    'Hash bcrypt del código; el código en claro solo viaja en el correo.';
COMMENT ON COLUMN recuperaciones_password.usado_en IS
    'Cuándo se usó para restablecer la contraseña o se anuló (5 intentos fallidos o código nuevo).';

COMMIT;
