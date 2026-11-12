document.addEventListener('DOMContentLoaded', () => {
  const MAX_CV_BYTES = 5 * 1024 * 1024;

  const list = document.getElementById('listaVacantes');
  const getCards = () => [...list.querySelectorAll('.vacante-card')];
  const search = document.getElementById('busquedaEmpleo');
  const filters = ['filtroArea', 'filtroModalidad', 'filtroUbicacion', 'filtroExperiencia'].map(id => document.getElementById(id));
  const count = document.getElementById('contadorVacantes');
  const empty = document.getElementById('sinResultados');
  const favoritesButton = document.getElementById('btnVerFavoritos');
  const appliedButton = document.getElementById('btnVerPostuladas');
  const favorites = new Set();
  // Postulaciones del alumno, por id de vacante (vienen de /api/mis-postulaciones)
  const applied = new Map();
  let favoritesOnly = false;
  let appliedOnly = false;
  let selectedCard = null;
  let perfil = null; // datos de /usuario-actual
  const el = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = text;
    return node;
  };
  const formatDate = iso => {
    const date = new Date(iso);
    if (!iso || isNaN(date)) return '';
    return date.toLocaleString('es-MX', {
      timeZone: 'America/Monterrey', day: '2-digit', month: 'long', year: 'numeric',
      hour: '2-digit', minute: '2-digit', hour12: true
    });
  };
  const normalize = value => (value || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();

  // ---------------------------------------------------------------------
  // Filtros y favoritos
  // ---------------------------------------------------------------------
  function filterCards() {
    const term = normalize(search.value.trim());
    let visible = 0;
    getCards().forEach(card => {
      const searchable = normalize([card.dataset.titulo, card.dataset.empresa, card.dataset.ubicacion, card.dataset.area, card.dataset.descripcion].join(' '));
      const matches = searchable.includes(term)
        && (!filters[0].value || card.dataset.area === filters[0].value)
        && (!filters[1].value || card.dataset.modalidad === filters[1].value)
        && (!filters[2].value || card.dataset.ubicacion === filters[2].value)
        && (!filters[3].value || card.dataset.experiencia === filters[3].value)
        && (!favoritesOnly || favorites.has(card.dataset.id))
        && (!appliedOnly || applied.has(card.dataset.id))
        // Las vacantes cerradas solo se ven en «Mis vacantes postuladas»
        && (!card.dataset.cerrada || appliedOnly);
      card.hidden = !matches;
      if (matches) visible++;
    });
    count.textContent = `${visible} ${visible === 1 ? 'vacante encontrada' : 'vacantes encontradas'}`;
    empty.hidden = visible !== 0;
  }

  search.addEventListener('input', filterCards);
  document.getElementById('btnBuscarEmpleo').addEventListener('click', filterCards);
  filters.forEach(filter => filter.addEventListener('change', filterCards));
  // «Mis favoritos» y «Mis vacantes postuladas» son excluyentes
  function updateListButtons() {
    favoritesButton.setAttribute('aria-pressed', String(favoritesOnly));
    favoritesButton.textContent = favoritesOnly ? 'Ver todas las vacantes' : '♡ Mis favoritos';
    appliedButton.setAttribute('aria-pressed', String(appliedOnly));
    appliedButton.textContent = appliedOnly ? 'Ver todas las vacantes' : '✓ Mis vacantes postuladas';
    filterCards();
  }
  favoritesButton.addEventListener('click', () => {
    favoritesOnly = !favoritesOnly;
    if (favoritesOnly) appliedOnly = false;
    updateListButtons();
  });
  appliedButton.addEventListener('click', () => {
    appliedOnly = !appliedOnly;
    if (appliedOnly) favoritesOnly = false;
    updateListButtons();
  });

  // Delegación de eventos: las tarjetas se crean dinámicamente
  list.addEventListener('click', event => {
    const favButton = event.target.closest('.btn-favorito');
    if (favButton) {
      const id = favButton.closest('.vacante-card').dataset.id;
      if (favorites.has(id)) favorites.delete(id); else favorites.add(id);
      const saved = favorites.has(id);
      favButton.textContent = saved ? '♥' : '♡';
      favButton.classList.toggle('favorito-activo', saved);
      favButton.setAttribute('aria-pressed', String(saved));
      filterCards();
      return;
    }
    const viewButton = event.target.closest('.btn-ver-vacante');
    if (viewButton) openDetail(viewButton.closest('.vacante-card'));
  });

  // ---------------------------------------------------------------------
  // Detalle de la vacante
  // ---------------------------------------------------------------------
  const dialog = document.getElementById('detalleVacante');
  function openDetail(card) {
    selectedCard = card;
    document.getElementById('detalleArea').textContent = card.dataset.area;
    document.getElementById('detalleTitulo').textContent = card.dataset.titulo;
    document.getElementById('detalleEmpresa').textContent = card.dataset.empresa;
    document.getElementById('detalleUbicacion').textContent = `⌖ ${card.dataset.ubicacion}`;
    const tagsBox = document.getElementById('detalleTags');
    tagsBox.innerHTML = '';
    [card.dataset.modalidad, card.dataset.experiencia, card.dataset.jornada].forEach(tag => {
      const span = document.createElement('span'); span.textContent = tag; tagsBox.appendChild(span);
    });
    document.getElementById('detalleDescripcion').textContent = card.dataset.descripcion;
    document.getElementById('detalleRequisitos').textContent = card.dataset.requisitos;
    document.getElementById('detalleJornada').textContent = card.dataset.jornada;
    showFollowUp(card);
    dialog.showModal();
  }

  // Seguimiento de la postulación dentro del detalle de la vacante
  const followUpBox = document.getElementById('detalleSeguimiento');
  const applyButton = document.getElementById('btnPostularme');
  const applyNote = document.getElementById('detalleNotaPostular');
  function showFollowUp(card) {
    const p = applied.get(card.dataset.id);
    applyButton.hidden = Boolean(p);
    applyNote.hidden = Boolean(p);
    followUpBox.hidden = !p;
    if (!p) { followUpBox.replaceChildren(); return; }

    const empresa = p.empresa || card.dataset.empresa;
    const parts = [el('p', 'seguimiento-titulo', '✓ Ya te postulaste a esta vacante')];
    if (card.dataset.cerrada) {
      parts.push(el('p', 'seguimiento-cerrada', 'Vacante cerrada: la empresa la dio de baja y ya no recibe postulaciones.'));
    }
    if (p.enviada_en) parts.push(el('p', 'seguimiento-fecha', `Enviada el ${formatDate(p.enviada_en)}`));
    if (p.revisada_en) {
      const aviso = el('p', 'seguimiento-aviso');
      aviso.append('La empresa ', el('strong', '', empresa),
        ' ha recibido tu información y la está revisando, en breve nos comunicaremos contigo.');
      parts.push(aviso);
    } else {
      parts.push(el('p', 'seguimiento-aviso', 'Tu postulación fue enviada. Te avisaremos aquí cuando la empresa la reciba.'));
    }
    if (p.estado === 'Aceptada' || p.estado === 'Rechazada') {
      parts.push(el('p', `seguimiento-resultado resultado-${p.estado.toLowerCase()}`, `Resultado: ${p.estado}`));
    }
    if (p.comentario) {
      const box = el('div', 'seguimiento-comentario');
      box.append(el('strong', '', `Comentario de ${empresa}`), el('p', '', p.comentario));
      if (p.comentario_en) box.appendChild(el('small', '', formatDate(p.comentario_en)));
      parts.push(box);
    }
    followUpBox.replaceChildren(...parts);
  }
  document.getElementById('cerrarDetalle').addEventListener('click', () => dialog.close());
  dialog.addEventListener('click', event => { if (event.target === dialog) dialog.close(); });

  // ---------------------------------------------------------------------
  // Formulario de postulación
  // ---------------------------------------------------------------------
  const formDialog = document.getElementById('formularioPostulacion');
  const form = document.getElementById('formPostulacion');
  const formMessage = document.getElementById('mensajePostulacion');
  const submitButton = document.getElementById('enviarPostulacion');
  const cvInput = document.getElementById('postCv');

  const showMessage = (message, type) => {
    formMessage.textContent = message;
    formMessage.className = `mensaje-postulacion ${type}`;
    formMessage.hidden = false;
  };
  const resetSubmit = () => {
    // Solo se bloquea si sabemos que no es alumno; si el perfil no cargó, decide el servidor
    submitButton.disabled = Boolean(perfil && !perfil.alumno);
    submitButton.textContent = 'Enviar postulación';
  };

  function fillProfile() {
    if (!perfil) return;
    document.getElementById('postNombre').value = `${perfil.nombre || ''} ${perfil.apellido || ''}`.trim();
    document.getElementById('postCorreo').value = perfil.email || '';
    const alumno = perfil.alumno;
    document.getElementById('postMatricula').value = alumno ? alumno.matricula || '' : '';
    if (alumno) {
      // Solo se precarga si el campo está vacío, para no borrar lo que ya escribió
      const telefono = document.getElementById('postTelefono');
      const carrera = document.getElementById('postCarrera');
      const semestre = document.getElementById('postSemestre');
      if (!telefono.value) telefono.value = alumno.telefono || '';
      if (!carrera.value) carrera.value = alumno.carrera || '';
      if (!semestre.value && alumno.semestre) semestre.value = alumno.semestre;
    }
  }

  document.getElementById('btnPostularme').addEventListener('click', () => {
    if (!selectedCard) return;
    document.getElementById('formVacanteTitulo').textContent = selectedCard.dataset.titulo;
    document.getElementById('formVacanteEmpresa').textContent = `${selectedCard.dataset.empresa} · ${selectedCard.dataset.ubicacion} · ${selectedCard.dataset.modalidad}`;
    formMessage.hidden = true;
    fillProfile();
    resetSubmit();
    if (perfil && !perfil.alumno) {
      showMessage('Tu cuenta no tiene registro de alumno, por lo que no puedes postularte. Contacta a Servicios Escolares.', 'error');
    }
    formDialog.showModal();
  });
  const closeForm = () => formDialog.close();
  document.getElementById('cerrarFormulario').addEventListener('click', closeForm);
  document.getElementById('cancelarPostulacion').addEventListener('click', closeForm);
  formDialog.addEventListener('click', event => { if (event.target === formDialog) closeForm(); });

  cvInput.addEventListener('change', () => {
    const file = cvInput.files[0];
    let error = '';
    if (file && !file.name.toLowerCase().endsWith('.pdf')) error = 'El CV debe ser un archivo PDF.';
    else if (file && file.size > MAX_CV_BYTES) error = 'El CV no puede pesar más de 5 MB.';
    cvInput.setCustomValidity(error);
    if (error) showMessage(error, 'error'); else formMessage.hidden = true;
  });

  // Lee la respuesta como JSON aunque el servidor devuelva otra cosa
  const readJson = async response => {
    try { return await response.json(); } catch { return {}; }
  };

  form.addEventListener('submit', async event => {
    event.preventDefault();
    if (!selectedCard) return;
    if (!form.reportValidity()) return;

    const formData = new FormData(form);
    formData.append('vacante_id', selectedCard.dataset.id);

    submitButton.disabled = true;
    submitButton.textContent = 'Enviando…';
    formMessage.hidden = true;
    let enviado = false;
    try {
      const response = await fetch('/api/postulaciones', {
        method: 'POST',
        credentials: 'same-origin',
        body: formData // el navegador pone el Content-Type multipart con su boundary
      });
      if (response.status === 401) { window.location.href = '/login'; return; }
      const result = await readJson(response);
      if (!response.ok || !result.ok) {
        showMessage(result.mensaje || 'No fue posible guardar tu postulación.', 'error');
        return;
      }
      enviado = true;
      showMessage(`¡Listo! Tu postulación quedó registrada con el folio #${result.id}.`, 'exito');
      const appliedCard = selectedCard;
      applied.set(appliedCard.dataset.id, {
        id: result.id, vacante_id: Number(appliedCard.dataset.id), empresa: appliedCard.dataset.empresa,
        estado: 'Recibida', enviada_en: new Date().toISOString(),
      });
      markApplied(appliedCard);
      showFollowUp(appliedCard);
      filterCards();
      submitButton.textContent = 'Postulación enviada ✓';
      form.reset();
      setTimeout(() => { closeForm(); dialog.close(); resetSubmit(); }, 1800);
    } catch (error) {
      showMessage('No se pudo conectar con SIUT. Verifica tu conexión e intenta nuevamente.', 'error');
    } finally {
      if (!enviado) resetSubmit();
    }
  });

  // ---------------------------------------------------------------------
  // Carga de vacantes desde la API
  // ---------------------------------------------------------------------
  const avatarClasses = ['', 'avatar-orange', 'avatar-purple', 'avatar-blue'];
  const initials = name => {
    const parts = (name || '').trim().split(/\s+/).filter(Boolean);
    if (!parts.length) return '··';
    return (parts.length === 1 ? parts[0].slice(0, 2) : parts[0][0] + parts[1][0]).toUpperCase();
  };
  // Marca «✓ Postulado» en la tarjeta de una vacante a la que ya se postuló
  function markApplied(card) {
    if (!applied.has(card.dataset.id) || card.querySelector('.badge-postulado')) return;
    card.classList.add('vacante-postulada');
    card.querySelector('.vacante-card-top').insertBefore(
      el('span', 'badge-postulado', '✓ Postulado'),
      card.querySelector('.btn-favorito'));
  }

  function buildCard(v) {
    const card = el('article', 'vacante-card');
    card.dataset.id = String(v.id);
    ['area', 'modalidad', 'ubicacion', 'experiencia', 'titulo', 'empresa', 'descripcion', 'requisitos', 'jornada']
      .forEach(key => { card.dataset[key] = v[key] || ''; });

    const top = el('div', 'vacante-card-top');
    const avatar = el('div', `empresa-avatar ${avatarClasses[v.id % avatarClasses.length]}`.trim(), initials(v.empresa));
    const fav = el('button', 'btn-favorito', '♡');
    fav.type = 'button';
    fav.setAttribute('aria-label', `Guardar ${v.titulo}`);
    fav.setAttribute('aria-pressed', 'false');
    top.append(avatar, fav);

    const place = v.ubicacion === 'Remoto' ? 'Remoto' : `${v.ubicacion}, Nuevo León`;
    const tags = el('div', 'vacante-tags');
    [v.modalidad, v.experiencia, v.jornada].forEach(tag => tags.appendChild(el('span', '', tag)));

    const more = el('button', 'btn-ver-vacante', 'Ver vacante ');
    more.type = 'button';
    more.appendChild(el('span', '', '→'));

    card.append(
      top,
      el('span', 'vacante-area', (v.area || '').toLocaleUpperCase('es')),
      el('h3', '', v.titulo),
      el('p', 'vacante-empresa', v.empresa),
      el('p', 'vacante-ubicacion', `⌖ ${place}`),
      tags,
      more
    );
    return card;
  }

  async function loadVacancies() {
    try {
      const response = await fetch('/api/vacantes', { credentials: 'same-origin' });
      if (response.status === 401) { window.location.href = '/login'; return; }
      const result = await readJson(response);
      if (!response.ok || !result.ok || !Array.isArray(result.vacantes)) throw new Error(result.mensaje || 'Error');
      result.vacantes.forEach(v => list.appendChild(buildCard(v)));
      getCards().forEach(markApplied);
      filterCards();
    } catch (error) {
      count.textContent = 'No se pudieron cargar las vacantes';
      empty.textContent = 'No se pudieron cargar las vacantes. Intenta nuevamente más tarde.';
      empty.hidden = false;
    }
  }

  async function loadProfile() {
    try {
      const response = await fetch('/usuario-actual', { credentials: 'same-origin' });
      if (response.ok) perfil = await readJson(response);
    } catch {
      perfil = null;
    }
  }

  // Postulaciones del alumno: marca las tarjetas y alimenta el seguimiento
  async function loadApplications() {
    try {
      const response = await fetch('/api/mis-postulaciones', { credentials: 'same-origin' });
      const result = await readJson(response);
      if (!response.ok || !result.ok || !Array.isArray(result.postulaciones)) return;
      result.postulaciones.forEach(p => applied.set(String(p.vacante_id), p));
      getCards().forEach(markApplied);
      filterCards();
    } catch {
      // Sin esta información el alumno puede seguir viendo vacantes
    }
  }

  // Vacantes a las que se postuló y que la empresa ya dio de baja:
  // se muestran con la leyenda «Vacante cerrada» (solo en «Mis vacantes postuladas»)
  function addClosedCards() {
    applied.forEach(p => {
      if (p.vacante_activa !== false || !p.vacante) return;
      if (list.querySelector(`.vacante-card[data-id="${CSS.escape(String(p.vacante_id))}"]`)) return;
      const card = buildCard(p.vacante);
      card.dataset.cerrada = '1';
      card.classList.add('vacante-cerrada');
      card.querySelector('.vacante-card-top').insertBefore(
        el('span', 'badge-cerrada', 'Vacante cerrada'), card.querySelector('.btn-favorito'));
      markApplied(card);
      list.appendChild(card);
    });
    filterCards();
  }

  loadProfile();
  Promise.all([loadApplications(), loadVacancies()]).then(addClosedCards);
});
