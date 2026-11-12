// «Mis notificaciones» del buzón: estado de cada sugerencia enviada por el
// usuario y la respuesta del administrador.
document.addEventListener('DOMContentLoaded', async () => {
  const lista = document.getElementById('listaNotificaciones');
  const contador = document.getElementById('contadorNotificaciones');
  if (!lista) return;

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
  const resumen = texto => (texto.length > 160 ? `${texto.slice(0, 157)}…` : texto);
  const claseEstado = estado => ({
    'Recibida': 'estado-recibida', 'En revisión': 'estado-revision',
    'Atendida': 'estado-atendida', 'Rechazada': 'estado-rechazada'
  }[estado] || '');

  function tarjeta(s) {
    const item = el('article', 'notificacion-item');
    const encabezado = el('div', 'notificacion-encabezado');
    encabezado.append(
      el('strong', '', s.categoria),
      el('span', `notificacion-estado ${claseEstado(s.estado)}`, s.estado)
    );
    item.append(
      encabezado,
      el('p', 'notificacion-descripcion', resumen(s.descripcion || '')),
      el('small', '', `Enviada el ${formatearFecha(s.enviada_en)}`)
    );
    if (s.respuesta) {
      const respuesta = el('div', 'notificacion-respuesta');
      respuesta.append(el('strong', '', 'Respuesta del administrador'), el('p', '', s.respuesta));
      if (s.atendida_en) respuesta.appendChild(el('small', '', formatearFecha(s.atendida_en)));
      item.appendChild(respuesta);
    }
    return item;
  }

  try {
    const response = await fetch('/api/mis-sugerencias', { credentials: 'same-origin' });
    if (response.status === 401) { window.location.href = '/login'; return; }
    const datos = await response.json();
    if (!response.ok || !datos.ok) throw new Error(datos.mensaje || 'Error');
    lista.replaceChildren(...datos.sugerencias.map(tarjeta));
    const n = datos.sugerencias.length;
    contador.textContent = n
      ? `${n} ${n === 1 ? 'sugerencia enviada' : 'sugerencias enviadas'}`
      : 'Aún no has enviado sugerencias.';
  } catch {
    contador.textContent = 'No se pudieron cargar tus notificaciones. Intenta nuevamente más tarde.';
  }
});
