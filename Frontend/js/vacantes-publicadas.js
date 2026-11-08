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
    return card;
  }

  try {
    const response = await fetch('/api/vacantes', { credentials: 'same-origin' });
    if (response.status === 401) { window.location.href = '/login'; return; }
    const result = await response.json();
    if (!response.ok || !result.ok) throw new Error(result.mensaje || 'Error');
    result.vacantes.forEach(v => list.appendChild(buildCard(v)));
    const n = result.vacantes.length;
    count.textContent = `${n} ${n === 1 ? 'vacante publicada' : 'vacantes publicadas'}`;
    empty.hidden = n !== 0;
  } catch (error) {
    count.textContent = 'No se pudieron cargar las vacantes';
    empty.textContent = 'No se pudieron cargar las vacantes. Intenta nuevamente.';
    empty.hidden = false;
  }
});
