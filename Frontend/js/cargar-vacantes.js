document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('formVacante');
  const message = document.getElementById('mensajeVacante');
  const submitButton = document.getElementById('publicarVacante');
  const clearButton = document.getElementById('limpiarVacante');
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

  clearButton.addEventListener('click', () => {
    form.reset();
    message.hidden = true;
    updatePreview();
  });

  form.addEventListener('submit', async event => {
    event.preventDefault();
    if (!form.reportValidity()) return;

    const payload = Object.fromEntries(new FormData(form).entries());
    if (payload.ubicacion === 'Remoto' && payload.modalidad !== 'Remoto') {
      showMessage('Si la ubicación es "Remoto", la modalidad también debe ser "Remoto".', 'error');
      return;
    }

    submitButton.disabled = true;
    submitButton.textContent = 'Publicando…';
    message.hidden = true;

    try {
      const response = await fetch('/api/vacantes', {
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
      submitButton.textContent = 'Publicar vacante';
    }
  });

  updatePreview();
});
