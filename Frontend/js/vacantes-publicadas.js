document.addEventListener('DOMContentLoaded', async () => {
  const list = document.getElementById('listaPublicadas');
  const count = document.getElementById('contadorPublicadas');
  const empty = document.getElementById('sinPublicadas');
  const avatarClasses = ['', 'avatar-orange', 'avatar-purple', 'avatar-blue'];

  const el = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  };
  const initials = name => {
    const parts = (name || '').trim().split(/\s+/).filter(Boolean);
    if (!parts.length) return '··';
    return (parts.length === 1 ? parts[0].slice(0, 2) : parts[0][0] + parts[1][0]).toUpperCase();
  };
  const formatDate = iso => {
    const date = new Date(iso);
    if (isNaN(date)) return '';
    return date.toLocaleString('es-MX', {
      timeZone: 'America/Monterrey', day: '2-digit', month: 'long', year: 'numeric',
      hour: '2-digit', minute: '2-digit', hour12: true
    });
  };

  function buildCard(v) {
    const card = el('article', 'vacante-card');
    const top = el('div', 'vacante-card-top');
    top.appendChild(el('div', `empresa-avatar ${avatarClasses[v.id % avatarClasses.length]}`.trim(), initials(v.empresa)));
    const place = v.ubicacion === 'Remoto' ? 'Remoto' : `${v.ubicacion}, Nuevo León`;
    const tags = el('div', 'vacante-tags');
    [v.modalidad, v.experiencia, v.jornada].forEach(tag => tags.appendChild(el('span', '', tag)));
    card.append(
      top,
      el('span', 'vacante-area', v.area.toLocaleUpperCase('es')),
      el('h3', '', v.titulo),
      el('p', 'vacante-empresa', v.empresa),
      el('p', 'vacante-ubicacion', `⌖ ${place}`),
      tags,
      el('p', 'vacante-fecha', `Publicada el ${formatDate(v.publicada_en)}`)
    );

    // Editar y borrar: solo en las vacantes de tu empresa (o todas, si eres administrador).
    // El servidor vuelve a validar el permiso.
    if (v.editable) {
      const acciones = el('div', 'postulacion-acciones vacante-acciones');
      const editar = el('a', 'btn-empleo-outline btn-editar-vacante', 'Editar');
      editar.href = `cargar-vacantes.html?editar=${encodeURIComponent(v.id)}`;
      const borrar = el('button', 'btn-empleo-outline btn-borrar-vacante', 'Borrar');
      borrar.type = 'button';
      borrar.addEventListener('click', () => darDeBaja(v, card, borrar));
      acciones.append(editar, borrar);
      card.appendChild(acciones);
    }
    return card;
  }

  function updateCount() {
    const n = list.querySelectorAll('.vacante-card').length;
    count.textContent = `${n} ${n === 1 ? 'vacante publicada' : 'vacantes publicadas'}`;
    empty.hidden = n !== 0;
  }

  async function darDeBaja(v, card, boton) {
    const n = v.postulaciones || 0;
    const aviso = n
      ? `

Tiene ${n} ${n === 1 ? 'postulación' : 'postulaciones'}: se conservarán y las seguirás viendo en «Postulaciones recibidas». Los alumnos que se postularon la verán como «Vacante cerrada».`
      : '';
    if (!window.confirm(`¿Borrar la vacante «${v.titulo}»? Dejará de mostrarse a los alumnos.${aviso}`)) return;

    boton.disabled = true;
    try {
      const response = await fetch(`/api/vacantes/${encodeURIComponent(v.id)}/baja`, {
        method: 'POST',
        credentials: 'same-origin'
      });
      if (response.status === 401) { window.location.href = '/login'; return; }
      let result = {};
      try { result = await response.json(); } catch { /* respuesta no JSON */ }
      if (!response.ok || !result.ok) throw new Error(result.mensaje || 'No fue posible borrar la vacante.');
      card.remove();
      updateCount();
    } catch (error) {
      alert(error.message);
      boton.disabled = false;
    }
  }

  try {
    const response = await fetch('/api/vacantes', { credentials: 'same-origin' });
    if (response.status === 401) { window.location.href = '/login'; return; }
    const result = await response.json();
    if (!response.ok || !result.ok) throw new Error(result.mensaje || 'Error');
    result.vacantes.forEach(v => list.appendChild(buildCard(v)));
    updateCount();
  } catch (error) {
    count.textContent = 'No se pudieron cargar las vacantes';
    empty.textContent = 'No se pudieron cargar las vacantes. Intenta nuevamente.';
    empty.hidden = false;
  }
});
