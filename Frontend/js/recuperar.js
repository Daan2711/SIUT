// «¿Olvidaste tu contraseña?» en login.html.
// Pasos: confirmar → correo → código de 4 dígitos → nueva contraseña.
// El servidor (Controllers/recuperacionController.py) valida todo; aquí solo
// se guía al usuario. Archivo propio por la CSP (script-src 'self').
(function () {
    const ESPERA_REENVIO = 60; // segundos

    async function leerJson(response) {
        try {
            return await response.json();
        } catch {
            return {};
        }
    }

    function mensajePorEstado(status) {
        if (status === 429) return 'Demasiados intentos. Espera unos minutos e intenta de nuevo.';
        if (status >= 500) return 'El servidor no está disponible en este momento. Intenta en unos minutos.';
        return 'No fue posible completar la solicitud';
    }

    async function enviar(url, datos) {
        const response = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(datos)
        });
        const data = await leerJson(response);
        if (!response.ok && !data.error) data.error = mensajePorEstado(response.status);
        return { ok: response.ok, data: data };
    }

    document.addEventListener('DOMContentLoaded', function () {
        const enlace = document.getElementById('enlaceRecuperar');
        const dialogo = document.getElementById('dialogoRecuperar');
        if (!enlace || !dialogo || typeof dialogo.showModal !== 'function') return;

        const pasos = dialogo.querySelectorAll('[data-paso]');
        const paso = nombre => dialogo.querySelector(`[data-paso="${nombre}"]`);
        const campoEmail = document.getElementById('recuperarEmail');
        const campoCodigo = document.getElementById('recuperarCodigo');
        const campoNueva = document.getElementById('recuperarNueva');
        const campoConfirmar = document.getElementById('recuperarConfirmar');
        const botonReenviar = dialogo.querySelector('[data-accion="reenviar"]');
        const avisoLogin = document.getElementById('avisoLogin');
        let correo = '';
        let temporizador = null;

        function mostrarPaso(nombre) {
            pasos.forEach(p => { p.hidden = p.dataset.paso !== nombre; });
            const actual = paso(nombre);
            limpiarMensaje(actual);
            const primerCampo = actual.querySelector('input');
            (primerCampo || actual.querySelector('[data-accion="continuar"]'))?.focus();
        }

        function mensaje(contenedor, texto, exito) {
            const caja = contenedor.querySelector('.mensaje-recuperar');
            caja.textContent = texto;
            caja.classList.toggle('exito', Boolean(exito));
            caja.hidden = false;
        }

        function limpiarMensaje(contenedor) {
            const caja = contenedor.querySelector('.mensaje-recuperar');
            if (caja) caja.hidden = true;
        }

        function ocupado(formulario, si) {
            formulario.querySelectorAll('button').forEach(b => {
                if (b.dataset.accion === 'reenviar') return;
                b.disabled = si;
            });
        }

        function iniciarEsperaReenvio() {
            clearInterval(temporizador);
            let restantes = ESPERA_REENVIO;
            botonReenviar.disabled = true;
            botonReenviar.textContent = `Reenviar código (${restantes} s)`;
            temporizador = setInterval(function () {
                restantes -= 1;
                if (restantes <= 0) {
                    clearInterval(temporizador);
                    botonReenviar.disabled = false;
                    botonReenviar.textContent = 'Reenviar código';
                } else {
                    botonReenviar.textContent = `Reenviar código (${restantes} s)`;
                }
            }, 1000);
        }

        function cerrar() {
            clearInterval(temporizador);
            dialogo.close();
        }

        // Al cerrar (botón o Esc) todo vuelve a empezar y no quedan datos escritos
        dialogo.addEventListener('close', function () {
            clearInterval(temporizador);
            dialogo.querySelectorAll('form').forEach(f => f.reset());
            dialogo.querySelectorAll('button').forEach(b => { b.disabled = false; });
            botonReenviar.disabled = true;
            botonReenviar.textContent = 'Reenviar código';
        });

        enlace.addEventListener('click', function (event) {
            event.preventDefault();
            if (avisoLogin) avisoLogin.hidden = true;
            dialogo.showModal();
            mostrarPaso('confirmar');
        });

        dialogo.querySelectorAll('[data-accion="cancelar"]').forEach(b => b.addEventListener('click', cerrar));

        dialogo.querySelector('[data-accion="continuar"]').addEventListener('click', function () {
            // Se rellena con el correo que ya esté escrito en el login
            campoEmail.value = document.getElementById('email').value.trim();
            mostrarPaso('correo');
        });

        async function pedirCodigo(formulario) {
            const respuesta = await enviar('/recuperar-password/solicitar', { email: correo });
            if (!respuesta.ok) {
                mensaje(formulario, respuesta.data.error);
                return false;
            }
            return respuesta.data.mensaje;
        }

        // Paso 2: correo
        paso('correo').addEventListener('submit', async function (event) {
            event.preventDefault();
            const formulario = event.currentTarget;
            correo = campoEmail.value.trim().toLowerCase();
            if (!correo || !campoEmail.checkValidity()) {
                mensaje(formulario, 'Escribe un correo válido');
                return;
            }
            ocupado(formulario, true);
            try {
                const texto = await pedirCodigo(formulario);
                if (texto) {
                    mostrarPaso('codigo');
                    paso('codigo').querySelector('[data-texto="enviado"]').textContent = texto;
                    iniciarEsperaReenvio();
                }
            } catch (error) {
                console.error('Error:', error);
                mensaje(formulario, 'Error de conexión con el servidor');
            } finally {
                ocupado(formulario, false);
            }
        });

        // Solo dígitos en el código
        campoCodigo.addEventListener('input', function () {
            campoCodigo.value = campoCodigo.value.replace(/\D/g, '').slice(0, 4);
        });

        botonReenviar.addEventListener('click', async function () {
            const formulario = paso('codigo');
            botonReenviar.disabled = true;
            try {
                const texto = await pedirCodigo(formulario);
                if (texto) {
                    campoCodigo.value = '';
                    mensaje(formulario, 'Te enviamos un código nuevo. El anterior ya no sirve.', true);
                    iniciarEsperaReenvio();
                } else {
                    botonReenviar.disabled = false;
                }
            } catch (error) {
                console.error('Error:', error);
                mensaje(formulario, 'Error de conexión con el servidor');
                botonReenviar.disabled = false;
            }
        });

        // Paso 3: código
        paso('codigo').addEventListener('submit', async function (event) {
            event.preventDefault();
            const formulario = event.currentTarget;
            const codigo = campoCodigo.value.trim();
            if (!/^\d{4}$/.test(codigo)) {
                mensaje(formulario, 'El código tiene 4 dígitos');
                return;
            }
            ocupado(formulario, true);
            try {
                const respuesta = await enviar('/recuperar-password/verificar', { email: correo, codigo: codigo });
                if (respuesta.ok) {
                    mostrarPaso('nueva');
                } else {
                    mensaje(formulario, respuesta.data.error);
                    campoCodigo.select();
                    if (respuesta.data.agotado) {
                        clearInterval(temporizador);
                        botonReenviar.disabled = false;
                        botonReenviar.textContent = 'Reenviar código';
                    }
                }
            } catch (error) {
                console.error('Error:', error);
                mensaje(formulario, 'Error de conexión con el servidor');
            } finally {
                ocupado(formulario, false);
            }
        });

        // Paso 4: nueva contraseña
        paso('nueva').addEventListener('submit', async function (event) {
            event.preventDefault();
            const formulario = event.currentTarget;
            const nueva = campoNueva.value;
            const confirmar = campoConfirmar.value;
            if (!nueva || !confirmar) {
                mensaje(formulario, 'Debes completar ambos campos');
                return;
            }
            if (nueva !== confirmar) {
                mensaje(formulario, 'Las contraseñas no coinciden');
                return;
            }
            if (nueva.length < 8) {
                mensaje(formulario, 'La contraseña debe tener al menos 8 caracteres');
                return;
            }
            ocupado(formulario, true);
            try {
                const respuesta = await enviar('/recuperar-password/restablecer', {
                    nueva_password: nueva,
                    confirmar_password: confirmar
                });
                if (!respuesta.ok) {
                    mensaje(formulario, respuesta.data.error);
                    return;
                }
                cerrar();
                document.getElementById('email').value = correo;
                const campoPassword = document.getElementById('password');
                campoPassword.value = '';
                if (avisoLogin) {
                    avisoLogin.textContent = respuesta.data.mensaje || 'Contraseña actualizada. Ya puedes iniciar sesión.';
                    avisoLogin.hidden = false;
                }
                campoPassword.focus();
            } catch (error) {
                console.error('Error:', error);
                mensaje(formulario, 'Error de conexión con el servidor');
            } finally {
                ocupado(formulario, false);
            }
        });
    });
})();
