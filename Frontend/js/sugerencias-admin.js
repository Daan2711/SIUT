// Bandeja de sugerencias del administrador: listar, filtrar por estado,
// cambiar el estado y guardar una respuesta.
document.addEventListener('DOMContentLoaded', () => {
  const ESTADOS = ['Recibida', 'En revisión', 'Atendida', 'Rechazada'];
  const LIMITE_RESPUESTA = 2000;

  const lista = document.getElementById('listaSugerencias');
  const contador = document.getElementById('contadorSugerencias');
  const vacio = document.getElementById('sinSugerencias');
  const filtro = document.getElementById('filtroEstado');

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

  function construirTarjeta(s) {
    const tarjeta = el('article', 'vacante-card sugerencia-admin');
    tarjeta.append(
      el('span', 'vacante-area', `${s.categoria} · ${s.estado}`.toLocaleUpperCase('es')),
      el('h3', '', s.remitente),
      el('p', 'vacante-empresa', `Grupo ${s.grupo} · Recibida el ${formatearFecha(s.recibida_en)}`),
      el('p', 'sugerencia-descripcion', s.descripcion)
    );

    const form = el('form', 'sugerencia-form');
    const etiquetaEstado = el('label', '', 'Estado');
    const selectEstado = el('select');
    ESTADOS.forEach(estado => {
      const opcion = el('option', '', estado);
      opcion.value = estado;
      opcion.selected = estado === s.estado;
      selectEstado.appendChild(opcion);
    });
    etiquetaEstado.appendChild(selectEstado);

    const etiquetaRespuesta = el('label', '', 'Respuesta (opcional)');
    const respuesta = el('textarea');
    respuesta.rows = 3;
    respuesta.maxLength = LIMITE_RESPUESTA;
    respuesta.value = s.respuesta || '';
    etiquetaRespuesta.appendChild(respuesta);

    const boton = el('button', 'btn-empleo-primary', 'Guardar');
    boton.type = 'submit';
    const mensaje = el('p', 'mensaje-postulacion');
    mensaje.hidden = true;
    mensaje.setAttribute('role', 'status');

    form.append(etiquetaEstado, etiquetaRespuesta, boton, mensaje);
    if (s.atendida_por) {
      form.appendChild(el('p', 'vacante-fecha',
        `Última atención: ${s.atendida_por}, ${formatearFecha(s.atendida_en)}`));
    }

    form.addEventListener('submit', async evento => {
      evento.preventDefault();
      boton.disabled = true;
      mensaje.hidden = true;
      try {
        const response = await fetch(`/api/sugerencias/${encodeURIComponent(s.id)}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'same-origin',
          body: JSON.stringify({ estado: selectEstado.value, respuesta: respuesta.value.trim() })
        });
        if (response.status === 401) { window.location.href = '/login'; return; }
        const datos = await leerJson(response);
        if (!response.ok || !datos.ok) throw new Error(datos.mensaje || 'No fue posible guardar.');
        await cargar();   // refresca la lista (y el filtro) con el estado nuevo
      } catch (error) {
        mensaje.textContent = error.message;
        mensaje.className = 'mensaje-postulacion error';
        mensaje.hidden = false;
        boton.disabled = false;
      }
    });

    tarjeta.appendChild(form);
    return tarjeta;
  }

  async function cargar() {
    const estado = filtro.value;
    const url = estado ? `/api/sugerencias?estado=${encodeURIComponent(estado)}` : '/api/sugerencias';
    try {
      const response = await fetch(url, { credentials: 'same-origin' });
      if (response.status === 401) { window.location.href = '/login'; return; }
      if (response.status === 403) { window.location.href = '/index.html'; return; }
      const datos = await leerJson(response);
      if (!response.ok || !datos.ok) throw new Error(datos.mensaje || 'Error');
      lista.replaceChildren(...datos.sugerencias.map(construirTarjeta));
      const n = datos.sugerencias.length;
      contador.textContent = `${n} ${n === 1 ? 'sugerencia' : 'sugerencias'}`;
      vacio.hidden = n !== 0;
    } catch {
      contador.textContent = 'No se pudieron cargar las sugerencias';
      vacio.textContent = 'No se pudieron cargar las sugerencias. Intenta nuevamente.';
      vacio.hidden = false;
    }
  }

  filtro.addEventListener('change', cargar);
  cargar();
});
