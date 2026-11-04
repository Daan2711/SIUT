document.addEventListener('DOMContentLoaded', () => {
  const list = document.getElementById('listaVacantes');
  const getCards = () => [...list.querySelectorAll('.vacante-card')];
  const search = document.getElementById('busquedaEmpleo');
  const filters = ['filtroArea', 'filtroModalidad', 'filtroUbicacion', 'filtroExperiencia'].map(id => document.getElementById(id));
  const count = document.getElementById('contadorVacantes');
  const empty = document.getElementById('sinResultados');
  const favoritesButton = document.getElementById('btnVerFavoritos');
  const favorites = new Set();
  let favoritesOnly = false;
  let selectedCard = null;
  const normalize = value => (value || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();

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
        && (!favoritesOnly || favorites.has(card.dataset.titulo));
      card.hidden = !matches;
      if (matches) visible++;
    });
    count.textContent = `${visible} ${visible === 1 ? 'vacante encontrada' : 'vacantes encontradas'}`;
    empty.hidden = visible !== 0;
  }

  search.addEventListener('input', filterCards);
  document.getElementById('btnBuscarEmpleo').addEventListener('click', filterCards);
  filters.forEach(filter => filter.addEventListener('change', filterCards));
  favoritesButton.addEventListener('click', () => {
    favoritesOnly = !favoritesOnly;
    favoritesButton.setAttribute('aria-pressed', String(favoritesOnly));
    favoritesButton.textContent = favoritesOnly ? 'Ver todas las vacantes' : '♡ Mis favoritos';
    filterCards();
  });

  list.addEventListener('click', event => {
    const button = event.target.closest('.btn-favorito');
    if (!button) return;
    const card = button.closest('.vacante-card');
    const title = card.dataset.titulo;
    if (favorites.has(title)) favorites.delete(title); else favorites.add(title);
    const saved = favorites.has(title);
    button.textContent = saved ? '♥' : '♡';
    button.classList.toggle('favorito-activo', saved);
    button.setAttribute('aria-pressed', String(saved));
    filterCards();
  });

  const dialog = document.getElementById('detalleVacante');
  list.addEventListener('click', event => {
    const button = event.target.closest('.btn-ver-vacante');
    if (!button) return;
    const card = button.closest('.vacante-card');
    selectedCard = card;
    document.getElementById('detalleArea').textContent = card.dataset.area;
    document.getElementById('detalleTitulo').textContent = card.dataset.titulo;
    document.getElementById('detalleEmpresa').textContent = card.dataset.empresa;
    document.getElementById('detalleUbicacion').textContent = `⌖ ${card.dataset.ubicacion}`;
    document.getElementById('detalleTags').innerHTML = '';
    [card.dataset.modalidad, card.dataset.experiencia, card.dataset.jornada].forEach(tag => {
      const span = document.createElement('span'); span.textContent = tag; document.getElementById('detalleTags').appendChild(span);
    });
    document.getElementById('detalleDescripcion').textContent = card.dataset.descripcion;
    document.getElementById('detalleRequisitos').textContent = card.dataset.requisitos;
    document.getElementById('detalleJornada').textContent = card.dataset.jornada;
    dialog.showModal();
  });
  document.getElementById('cerrarDetalle').addEventListener('click', () => dialog.close());
  dialog.addEventListener('click', event => { if (event.target === dialog) dialog.close(); });
  const formDialog = document.getElementById('formularioPostulacion');
  const form = document.getElementById('formPostulacion');
  const formMessage = document.getElementById('mensajePostulacion');
  const showMessage = (message, type) => {
    formMessage.textContent = message;
    formMessage.className = `mensaje-postulacion ${type}`;
    formMessage.hidden = false;
  };

  document.getElementById('btnPostularme').addEventListener('click', () => {
    if (!selectedCard) return;
    document.getElementById('formVacanteTitulo').textContent = selectedCard.dataset.titulo;
    document.getElementById('formVacanteEmpresa').textContent = `${selectedCard.dataset.empresa} · ${selectedCard.dataset.ubicacion} · ${selectedCard.dataset.modalidad}`;
    formMessage.hidden = true;
    formDialog.showModal();
  });
  const closeForm = () => formDialog.close();
  document.getElementById('cerrarFormulario').addEventListener('click', closeForm);
  document.getElementById('cancelarPostulacion').addEventListener('click', closeForm);
  formDialog.addEventListener('click', event => { if (event.target === formDialog) closeForm(); });

  form.addEventListener('submit', async event => {
    event.preventDefault();
    if (!selectedCard) return;
    if (!form.reportValidity()) return;
    const submitButton = document.getElementById('enviarPostulacion');
    const formData = Object.fromEntries(new FormData(form).entries());
    const payload = {
      ...formData,
      vacante_titulo: selectedCard.dataset.titulo,
      empresa: selectedCard.dataset.empresa,
      ubicacion: selectedCard.dataset.ubicacion,
      modalidad: selectedCard.dataset.modalidad
    };
    submitButton.disabled = true;
    submitButton.textContent = 'Guardando…';
    formMessage.hidden = true;
    try {
      const response = await fetch('/api/postulaciones', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'same-origin',
        body: JSON.stringify(payload)
      });
      const result = await response.json();
      if (!response.ok || !result.ok) {
        showMessage(result.mensaje || 'No fue posible guardar tu postulación.', 'error');
        return;
      }
      showMessage(`¡Listo! Tu postulación quedó registrada con el folio #${result.id}.`, 'exito');
      submitButton.textContent = 'Postulación guardada ✓';
      form.reset();
      setTimeout(() => { closeForm(); dialog.close(); submitButton.disabled = false; submitButton.textContent = 'Enviar postulación'; }, 1800);
    } catch (error) {
      showMessage('No se pudo conectar con SIUT. Verifica que el servidor esté iniciado e intenta nuevamente.', 'error');
    } finally {
      if (!formMessage.classList.contains('exito')) {
        submitButton.disabled = false;
        submitButton.textContent = 'Enviar postulación';
      }
    }
  });
  const avatarClasses = ['', 'avatar-orange', 'avatar-purple', 'avatar-blue'];
  const initials = name => {
    const parts = (name || '').trim().split(/\s+/).filter(Boolean);
    if (!parts.length) return '··';
    return (parts.length === 1 ? parts[0].slice(0, 2) : parts[0][0] + parts[1][0]).toUpperCase();
  };
  const el = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  };

  function buildCard(v) {
    const card = el('article', 'vacante-card');
    ['area', 'modalidad', 'ubicacion', 'experiencia', 'titulo', 'empresa', 'descripcion', 'requisitos', 'jornada']
      .forEach(key => { card.dataset[key] = v[key]; });

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
      el('span', 'vacante-area', v.area.toLocaleUpperCase('es')),
      el('h3', '', v.titulo),
      el('p', 'vacante-empresa', v.empresa),
      el('p', 'vacante-ubicacion', `⌖ ${place}`),
      tags,
      more
    );
    return card;
  }

  async function loadPublishedVacancies() {
    try {
      const response = await fetch('/api/vacantes', { credentials: 'same-origin' });
      if (!response.ok) return;
      const result = await response.json();
      if (!result.ok || !Array.isArray(result.vacantes)) return;
      result.vacantes.forEach(v => list.appendChild(buildCard(v)));
      filterCards();
    } catch (error) {
      console.error('No se pudieron cargar las vacantes publicadas:', error);
    }
  }

  filterCards();
  loadPublishedVacancies();
});
