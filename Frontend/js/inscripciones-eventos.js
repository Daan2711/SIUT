// Inscripciones a eventos (solo administrador): listar, filtrar y marcar «OK».
document.addEventListener('DOMContentLoaded', async () => {
  const lista = document.getElementById('listaInscripciones');
  const contador = document.getElementById('contadorInscripciones');
  const vacio = document.getElementById('sinInscripciones');
  const filtroEvento = document.getElementById('filtroEvento');
  const filtroConfirmada = document.getElementById('filtroConfirmada');
  let inscripciones = [];

  const el = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = text;
    return node;
  };
  const formatearFecha = iso => {
    const fecha = new Date(iso);
    if (!iso || isNaN(fecha)) return '';
    return fecha.toLocaleString('es-MX', {
      timeZone: 'America/Monterrey', day: '2-digit', month: 'long', year: 'numeric',
      hour: '2-digit', minute: '2-digit', hour12: true
    });
  };
  const leerJson = async response => {
    try { return await response.json(); } catch { return {}; }
  };

  function tarjeta(i) {
    const card = el('article', `vacante-card inscripcion-evento${i.confirmada ? ' inscripcion-ok' : ''}`);
    const datos = el('dl', 'postulacion-datos');
    datos.append(el('dt', '', 'Correo'), el('dd', '', i.correo || '—'));
    card.append(
      el('span', 'vacante-area', (i.evento || '').toLocaleUpperCase('es')),
      el('h3', '', i.nombre || 'Sin nombre'),
      datos,
      el('p', 'vacante-fecha', `Inscrito el ${formatearFecha(i.inscrito_en)}`)
    );

    const boton = el('button', i.confirmada ? 'btn-empleo-outline' : 'btn-empleo-primary',
      i.confirmada ? '✓ OK (deshacer)' : 'Marcar OK');
    boton.type = 'button';
    boton.setAttribute('aria-pressed', String(i.confirmada));
    boton.addEventListener('click', async () => {
      boton.disabled = true;
      try {
        const response = await fetch(`/api/inscripciones-eventos/${encodeURIComponent(i.id)}/ok`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'same-origin',
          body: JSON.stringify({ confirmada: !i.confirmada })
        });
        if (response.status === 401) { window.location.href = '/login'; return; }
        const respuesta = await leerJson(response);
        if (!response.ok || !respuesta.ok) throw new Error(respuesta.mensaje || 'No fue posible actualizar.');
        Object.assign(i, respuesta.inscripcion);
        pintar();
      } catch (error) {
        alert(error.message);
        boton.disabled = false;
      }
    });
    card.appendChild(boton);
    if (i.confirmada && i.confirmada_en) {
      card.appendChild(el('p', 'vacante-fecha', `Marcada OK el ${formatearFecha(i.confirmada_en)}`));
    }
    return card;
  }

  function pintar() {
    const evento = filtroEvento.value;
    const estado = filtroConfirmada.value;
    const visibles = inscripciones.filter(i =>
      (!evento || String(i.evento_id) === evento)
      && (!estado || (estado === 'ok') === i.confirmada));
    lista.replaceChildren(...visibles.map(tarjeta));
    const n = visibles.length;
    const pendientes = visibles.filter(i => !i.confirmada).length;
    contador.textContent = `${n} ${n === 1 ? 'inscripción' : 'inscripciones'} · ${pendientes} por revisar`;
    vacio.hidden = n !== 0;
  }

  filtroEvento.addEventListener('change', pintar);
  filtroConfirmada.addEventListener('change', pintar);

  try {
    const response = await fetch('/api/inscripciones-eventos', { credentials: 'same-origin' });
    if (response.status === 401) { window.location.href = '/login'; return; }
    if (response.status === 403) { window.location.href = '/index.html'; return; }
    const datos = await leerJson(response);
    if (!response.ok || !datos.ok) throw new Error(datos.mensaje || 'Error');
    inscripciones = datos.inscripciones;

    const eventos = new Map();
    inscripciones.forEach(i => eventos.set(String(i.evento_id), i.evento));
    eventos.forEach((titulo, id) => filtroEvento.appendChild(new Option(titulo, id)));
    pintar();
  } catch {
    contador.textContent = 'No se pudieron cargar las inscripciones';
    vacio.textContent = 'No se pudieron cargar las inscripciones. Intenta nuevamente.';
    vacio.hidden = false;
  }
});
