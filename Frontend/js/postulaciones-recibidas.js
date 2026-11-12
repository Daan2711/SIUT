document.addEventListener('DOMContentLoaded', async () => {
  const list = document.getElementById('listaPostulaciones');
  const count = document.getElementById('contadorPostulaciones');
  const empty = document.getElementById('sinPostulaciones');
  const filtro = document.getElementById('filtroVacante');
  let postulaciones = [];

  const leerJson = async response => {
    try { return await response.json(); } catch { return {}; }
  };
  const enviarJson = async (url, cuerpo) => {
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify(cuerpo || {})
    });
    if (response.status === 401) { window.location.href = '/login'; throw new Error('Tu sesión terminó.'); }
    const datos = await leerJson(response);
    if (!response.ok || !datos.ok) throw new Error(datos.mensaje || 'No fue posible guardar.');
    return datos.postulacion;
  };
  // Copia el seguimiento devuelto por el servidor y vuelve a pintar la lista
  const actualizar = (p, seguimiento) => {
    Object.assign(p, {
      estado: seguimiento.estado, revisada_en: seguimiento.revisada_en,
      comentario: seguimiento.comentario, comentario_en: seguimiento.comentario_en,
    });
    render();
  };

  // --- Cuadro de comentario ----------------------------------------------
  const dialogo = document.getElementById('dialogoComentario');
  const formComentario = document.getElementById('formComentario');
  const texto = document.getElementById('comentarioTexto');
  const resultado = document.getElementById('comentarioResultado');
  const mensajeComentario = document.getElementById('mensajeComentario');
  const botonEnviar = document.getElementById('enviarComentario');
  let actual = null;

  function abrirComentario(p) {
    actual = p;
    document.getElementById('comentarioCandidato').textContent = `${p.alumno} · ${p.vacante_titulo}`;
    texto.value = p.comentario || '';
    resultado.value = (p.estado === 'Aceptada' || p.estado === 'Rechazada') ? p.estado : '';
    mensajeComentario.hidden = true;
    botonEnviar.disabled = false;
    dialogo.showModal();
    texto.focus();
  }
  const cerrarComentario = () => dialogo.close();
  document.getElementById('cerrarComentario').addEventListener('click', cerrarComentario);
  document.getElementById('cancelarComentario').addEventListener('click', cerrarComentario);
  dialogo.addEventListener('click', evento => { if (evento.target === dialogo) cerrarComentario(); });

  formComentario.addEventListener('submit', async evento => {
    evento.preventDefault();
    if (!actual) return;
    const comentario = texto.value.trim();
    if (!comentario) {
      mensajeComentario.textContent = 'Escribe un comentario para el alumno.';
      mensajeComentario.className = 'mensaje-postulacion error';
      mensajeComentario.hidden = false;
      return;
    }
    botonEnviar.disabled = true;
    mensajeComentario.hidden = true;
    try {
      const seguimiento = await enviarJson(
        `/api/postulaciones/${encodeURIComponent(actual.id)}/comentario`,
        { comentario, resultado: resultado.value });
      actualizar(actual, seguimiento);
      cerrarComentario();
    } catch (error) {
      mensajeComentario.textContent = error.message;
      mensajeComentario.className = 'mensaje-postulacion error';
      mensajeComentario.hidden = false;
      botonEnviar.disabled = false;
    }
  });

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

    // «Recibido»: avisa al alumno y abre el cuadro de comentario
    const acciones = el('div', 'postulacion-acciones');
    const recibido = el('button', 'btn-empleo-outline btn-recibido',
      p.revisada_en ? (p.comentario ? 'Editar comentario' : 'Comentar') : 'Recibido');
    recibido.type = 'button';
    recibido.addEventListener('click', async () => {
      if (p.revisada_en) { abrirComentario(p); return; }
      recibido.disabled = true;
      try {
        actualizar(p, await enviarJson(`/api/postulaciones/${encodeURIComponent(p.id)}/recibido`));
        abrirComentario(p);
      } catch (error) {
        alert(error.message);
        recibido.disabled = false;
      }
    });
    acciones.append(cv, recibido);
    card.appendChild(acciones);

    if (p.revisada_en) {
      card.appendChild(el('p', 'vacante-fecha', `✓ Marcada como recibida el ${formatDate(p.revisada_en)}`));
    }
    if (p.comentario) {
      const caja = el('div', 'seguimiento-comentario');
      caja.append(el('strong', '', 'Tu comentario'), el('p', '', p.comentario));
      card.appendChild(caja);
    }

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
