document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('formVacante');
  const message = document.getElementById('mensajeVacante');
  const submitButton = document.getElementById('publicarVacante');
  const clearButton = document.getElementById('limpiarVacante');
  // Modo edición: cargar-vacantes.html?editar=<id>
  const editarId = new URLSearchParams(window.location.search).get('editar');
  const editando = /^\d+$/.test(editarId || '');
  const submitLabel = editando ? 'Guardar cambios' : 'Publicar vacante';
  const preview = {
    avatar: document.getElementById('prevAvatar'),
    area: document.getElementById('prevArea'),
    titulo: document.getElementById('prevTitulo'),
    empresa: document.getElementById('prevEmpresa'),
    ubicacion: document.getElementById('prevUbicacion'),
    tags: document.getElementById('prevTags')
  };

  const showMessage = (text, type) => {
    message.textContent = text;
    message.className = `mensaje-postulacion ${type}`;
    message.hidden = false;
  };

  const initials = name => {
    const parts = (name || '').trim().split(/\s+/).filter(Boolean);
    if (!parts.length) return '··';
    return (parts.length === 1 ? parts[0].slice(0, 2) : parts[0][0] + parts[1][0]).toUpperCase();
  };

  const locationLabel = ubicacion => {
    if (!ubicacion) return 'Ubicación';
    return ubicacion === 'Remoto' ? 'Remoto' : `${ubicacion}, Nuevo León`;
  };

  function updatePreview() {
    const data = Object.fromEntries(new FormData(form).entries());
    preview.avatar.textContent = initials(data.empresa);
    preview.area.textContent = (data.area || 'Área').toLocaleUpperCase('es');
    preview.titulo.textContent = data.titulo || 'Título del puesto';
    preview.empresa.textContent = data.empresa || 'Empresa';
    preview.ubicacion.textContent = `⌖ ${locationLabel(data.ubicacion)}`;
    preview.tags.innerHTML = '';
    [data.modalidad, data.experiencia, data.jornada].filter(Boolean).forEach(tag => {
      const span = document.createElement('span');
      span.textContent = tag;
      preview.tags.appendChild(span);
    });
  }

  form.addEventListener('input', updatePreview);
  form.addEventListener('change', updatePreview);

  // Un usuario con rol Empresa publica siempre a nombre de su empresa:
  // el campo se llena con ella y no se puede editar (el servidor lo ignora).
  const empresaInput = form.elements.empresa;
  let empresaPropia = null;
  const aplicarEmpresaPropia = () => {
    if (!empresaPropia) return;
    empresaInput.value = empresaPropia;
    empresaInput.readOnly = true;
    empresaInput.title = 'Las vacantes se publican a nombre de tu empresa';
  };

  clearButton.addEventListener('click', () => {
    if (editando) { window.location.href = '/vacantes-publicadas.html'; return; }
    form.reset();
    aplicarEmpresaPropia();
    message.hidden = true;
    updatePreview();
  });

  (async () => {
    try {
      const response = await fetch('/usuario-actual', { credentials: 'same-origin' });
      if (!response.ok) return;
      const perfil = await response.json();
      if (perfil.rol === 'Empresa' && perfil.empresa) {
        empresaPropia = perfil.empresa.nombre;
        aplicarEmpresaPropia();
        updatePreview();
      }
    } catch {
      // Sin perfil el formulario sigue funcionando; el servidor aplica la regla
    }
  })();

  if (editando) {
    document.title = 'Editar vacante | SIUT';
    document.getElementById('tituloCarga').textContent = 'Editar vacante';
    document.getElementById('textoCarga').textContent =
      'Corrige la información del puesto. Las postulaciones que ya recibió se conservan.';
    document.getElementById('avisoCarga').textContent =
      '🔒 Los cambios se verán de inmediato en la sección Buscar empleos y quedarán registrados en SIUT.';
    submitButton.textContent = submitLabel;
    clearButton.textContent = 'Cancelar';
    submitButton.disabled = true;   // hasta que carguen los datos

    (async () => {
      try {
        const response = await fetch(`/api/vacantes/${encodeURIComponent(editarId)}`, { credentials: 'same-origin' });
        if (response.status === 401) { window.location.href = '/login'; return; }
        let result = {};
        try { result = await response.json(); } catch { /* respuesta no JSON */ }
        if (!response.ok || !result.ok) throw new Error(result.mensaje || 'No se pudo cargar la vacante.');
        const v = result.vacante;
        ['titulo', 'empresa', 'area', 'experiencia', 'modalidad', 'ubicacion', 'jornada', 'descripcion', 'requisitos']
          .forEach(campo => { if (form.elements[campo]) form.elements[campo].value = v[campo] || ''; });
        aplicarEmpresaPropia();
        updatePreview();
        submitButton.disabled = false;
      } catch (error) {
        showMessage(`${error.message} Regresa a «Vacantes publicadas» e intenta de nuevo.`, 'error');
      }
    })();
  }

  form.addEventListener('submit', async event => {
    event.preventDefault();
    if (!form.reportValidity()) return;

    const payload = Object.fromEntries(new FormData(form).entries());
    if (payload.ubicacion === 'Remoto' && payload.modalidad !== 'Remoto') {
      showMessage('Si la ubicación es "Remoto", la modalidad también debe ser "Remoto".', 'error');
      return;
    }

    submitButton.disabled = true;
    submitButton.textContent = editando ? 'Guardando…' : 'Publicando…';
    message.hidden = true;

    try {
      const response = await fetch(editando ? `/api/vacantes/${encodeURIComponent(editarId)}` : '/api/vacantes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'same-origin',
        body: JSON.stringify(payload)
      });
      if (response.status === 401) { window.location.href = '/login'; return; }
      const result = await response.json();
      if (!response.ok || !result.ok) {
        showMessage(result.mensaje || 'No fue posible guardar la vacante.', 'error');
        return;
      }
      window.location.href = '/vacantes-publicadas.html';
      return;
    } catch (error) {
      showMessage('No se pudo conectar con SIUT. Verifica que el servidor esté iniciado e intenta nuevamente.', 'error');
    } finally {
      submitButton.disabled = false;
      submitButton.textContent = submitLabel;
    }
  });

  updatePreview();
});
