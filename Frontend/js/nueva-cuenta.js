// Formulario «Nueva cuenta» (solo administradores).
// Muestra los campos del rol elegido; los de los otros roles quedan ocultos y
// deshabilitados, así que no se validan ni se envían. El servidor repite
// todas las validaciones y rechaza cualquier rol distinto de Alumno,
// Profesor o Empresa.
document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('formCuenta');
  const message = document.getElementById('mensajeCuenta');
  const submitButton = document.getElementById('crearCuenta');
  const clearButton = document.getElementById('limpiarCuenta');
  const grupos = form.querySelectorAll('[data-rol]');
  let csrfToken = null;

  const showMessage = (text, type) => {
    message.textContent = text;
    message.className = `mensaje-postulacion ${type}`;
    message.hidden = false;
  };

  const limpiarErrores = () => {
    form.querySelectorAll('[aria-invalid="true"]').forEach(campo => campo.removeAttribute('aria-invalid'));
  };

  const marcarCampo = nombre => {
    const campo = nombre && form.elements[nombre];
    if (campo && !campo.disabled) {
      campo.setAttribute('aria-invalid', 'true');
      campo.focus();
    }
  };

  const leerJson = async response => {
    try { return await response.json(); } catch { return {}; }
  };

  function mostrarCamposDelRol() {
    const rol = form.elements.rol.value;
    grupos.forEach(grupo => {
      const activo = grupo.dataset.rol === rol;
      grupo.hidden = !activo;
      grupo.querySelectorAll('input, select').forEach(campo => { campo.disabled = !activo; });
    });
  }

  form.elements.rol.addEventListener('change', mostrarCamposDelRol);
  form.addEventListener('input', event => event.target.removeAttribute('aria-invalid'));

  clearButton.addEventListener('click', () => {
    form.reset();
    limpiarErrores();
    message.hidden = true;
    mostrarCamposDelRol();
  });

  // Token CSRF y cuatrimestres válidos (campo interno: semestre)
  (async () => {
    try {
      const response = await fetch('/api/admin/cuentas/formulario', { credentials: 'same-origin' });
      if (response.status === 401) { window.location.href = '/login'; return; }
      const data = await leerJson(response);
      if (!response.ok || !data.csrf_token) {
        showMessage(data.mensaje || 'No fue posible preparar el formulario.', 'error');
        return;
      }
      csrfToken = data.csrf_token;
      const semestre = document.getElementById('semestre');
      (data.semestres || []).forEach(valor => {
        const opcion = document.createElement('option');
        opcion.textContent = valor;
        semestre.appendChild(opcion);
      });
      submitButton.disabled = false;
    } catch {
      showMessage('No se pudo conectar con SIUT. Recarga la página.', 'error');
    }
  })();

  form.addEventListener('submit', async event => {
    event.preventDefault();
    limpiarErrores();
    message.hidden = true;
    if (!form.reportValidity()) return;
    if (form.elements.password.value !== form.elements.password_confirmacion.value) {
      showMessage('Las contraseñas no coinciden.', 'error');
      marcarCampo('password_confirmacion');
      return;
    }

    const payload = Object.fromEntries(new FormData(form).entries());
    submitButton.disabled = true;
    submitButton.textContent = 'Creando…';

    try {
      const response = await fetch('/api/admin/cuentas', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken || '' },
        credentials: 'same-origin',
        body: JSON.stringify(payload)
      });
      if (response.status === 401) { window.location.href = '/login'; return; }
      const result = await leerJson(response);
      if (!response.ok || !result.ok) {
        const mensaje = response.status === 429
          ? 'Demasiados intentos. Espera un minuto e intenta de nuevo.'
          : (result.mensaje || 'No fue posible crear la cuenta.');
        showMessage(mensaje, 'error');
        marcarCampo(result.campo);
        return;
      }
      form.reset();
      mostrarCamposDelRol();
      showMessage(result.mensaje, 'exito');
    } catch {
      showMessage('No se pudo conectar con SIUT. Verifica que el servidor esté iniciado e intenta nuevamente.', 'error');
    } finally {
      submitButton.disabled = !csrfToken;
      submitButton.textContent = 'Crear cuenta';
    }
  });

  mostrarCamposDelRol();
});
