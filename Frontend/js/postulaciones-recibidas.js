document.addEventListener('DOMContentLoaded', async () => {
  const list = document.getElementById('listaPostulaciones');
  const count = document.getElementById('contadorPostulaciones');
  const empty = document.getElementById('sinPostulaciones');
  const filtro = document.getElementById('filtroVacante');
  let postulaciones = [];

  const el = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = text;
    return node;
  };
  const formatDate = iso => {
    const date = new Date(iso);
    if (isNaN(date)) return '';
    return date.toLocaleString('es-MX', {
      timeZone: 'America/Monterrey', day: '2-digit', month: 'long', year: 'numeric',
      hour: '2-digit', minute: '2-digit', hour12: true
    });
  };
  const formatSize = bytes => (bytes >= 1024 * 1024)
    ? `${(bytes / (1024 * 1024)).toFixed(1)} MB`
    : `${Math.max(1, Math.round(bytes / 1024))} KB`;

  // Par etiqueta / valor; se omite si no hay valor
  const dato = (dl, etiqueta, valor) => {
    if (!valor) return;
    dl.append(el('dt', '', etiqueta), el('dd', '', valor));
  };

  function buildCard(p) {
    const card = el('article', 'vacante-card postulacion-recibida');
    card.append(
      el('span', 'vacante-area', p.vacante_titulo.toLocaleUpperCase('es')),
      el('h3', '', p.alumno),
      el('p', 'vacante-empresa', `${p.matricula || 'Sin matrícula'} · ${p.carrera || 'Carrera no indicada'}`)
    );

    const dl = el('dl', 'postulacion-datos');
    dato(dl, 'Correo', p.correo);
    dato(dl, 'Teléfono', p.telefono);
    dato(dl, 'Cuatrimestre', p.semestre);
    dato(dl, 'Habilidades', p.habilidades);
    dato(dl, 'Experiencia', p.experiencia);
    dato(dl, 'Mensaje', p.mensaje);
    dato(dl, 'Estado', p.estado);
    card.appendChild(dl);

    const cv = el('a', 'btn-empleo-primary btn-descargar-cv', `Descargar CV (${formatSize(p.cv_tamano_bytes)})`);
    cv.href = `/api/postulaciones/${encodeURIComponent(p.id)}/cv`;
    cv.setAttribute('download', '');
    card.appendChild(cv);

    card.appendChild(el('p', 'vacante-fecha', `Recibida el ${formatDate(p.recibida_en)} · Folio #${p.id}`));
    return card;
  }

  function render() {
    const seleccion = filtro.value;
    const visibles = postulaciones.filter(p => !seleccion || String(p.vacante_id) === seleccion);
    list.replaceChildren(...visibles.map(buildCard));
    const n = visibles.length;
    count.textContent = `${n} ${n === 1 ? 'postulación' : 'postulaciones'}`;
    empty.hidden = n !== 0;
  }

  filtro.addEventListener('change', render);

  try {
    const response = await fetch('/api/postulaciones', { credentials: 'same-origin' });
    if (response.status === 401) { window.location.href = '/login'; return; }
    if (response.status === 403) { window.location.href = '/index.html'; return; }
    const result = await response.json();
    if (!response.ok || !result.ok) throw new Error(result.mensaje || 'Error');
    postulaciones = result.postulaciones;

    // Opciones del filtro: una por vacante con postulaciones
    const vacantes = new Map();
    postulaciones.forEach(p => vacantes.set(String(p.vacante_id), p.vacante_titulo));
    vacantes.forEach((titulo, id) => {
      const option = el('option', '', titulo);
      option.value = id;
      filtro.appendChild(option);
    });
    render();
  } catch (error) {
    count.textContent = 'No se pudieron cargar las postulaciones';
    empty.textContent = 'No se pudieron cargar las postulaciones. Intenta nuevamente.';
    empty.hidden = false;
  }
});
