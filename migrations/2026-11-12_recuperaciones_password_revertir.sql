-- =========================================================================
-- Revierte: 2026-11-12_recuperaciones_password.sql
--
-- Borra la tabla de códigos de recuperación (y su índice). Solo contiene
-- códigos temporales: no se pierde información de los usuarios.
-- Antes de ejecutarlo, quita de la app la recuperación de contraseña
-- (Controllers/recuperacionController.py) o fallará al pedir un código.
-- =========================================================================
BEGIN;

DROP TABLE IF EXISTS recuperaciones_password;

COMMIT;
