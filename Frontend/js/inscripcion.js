// Inscripción a eventos: guarda nombre y correo del alumno en SIUT.
// El evento llega en la URL (inscripcion.html?evento=UT%20Canta%202026).
document.addEventListener('DOMContentLoaded', async () => {
  const form = document.getElementById('formInscripcion');
  const select = document.getElementById('inscripcionEvento');
  const nombre = document.getElementById('inscripcionNombre');
  const correo = document.getElementById('inscripcionCorreo');
  const mensaje = document.getElementById('mensajeInscripcion');
  const boton = document.getElementById('enviarInscripcion');
  let eventos = [];

  const leerJson = async response => {
    try { return await response.json(); } catch { return {}; }
  };
  const mostrar = texto => { mensaje.textContent = texto; mensaje.hidden = !texto; };
  const normalizar = valor => (valor || '').normalize('NFD').replace(/[̀-ͯ]/g, '').trim().toLowerCase();

  // Avisa si ya está inscrito en el evento elegido
  function revisarSeleccion() {
    const evento = eventos.find(e => String(e.id) === select.value);
    const inscrito = Boolean(evento && evento.inscrito);
    boton.disabled = !evento || inscrito;
    mostrar(inscrito ? 'Ya estás inscrito en este evento.' : '');
  }
  select.addEventListener('change', revisarSeleccion);

  async function cargarEventos() {
    const response = await fetch('/api/eventos', { credentials: 'same-origin' });
    if (response.status === 401) { window.location.href = '/login'; return; }
    const datos = await leerJson(response);
    if (!response.ok || !datos.ok) throw new Error(datos.mensaje || 'Error');
    eventos = datos.eventos;

    const opciones = [new Option('Selecciona un evento', '')];
    eventos.forEach(e => opciones.push(new Option(e.titulo, String(e.id))));
    select.replaceChildren(...opciones);

    const pedido = normalizar(new URLSearchParams(window.location.search).get('evento'));
    const elegido = eventos.find(e => normalizar(e.titulo) === pedido);
    if (elegido) select.value = String(elegido.id);
    if (!eventos.length) mostrar('Por ahora no hay eventos con inscripciones abiertas.');
    revisarSeleccion();
  }

  async function precargarDatos() {
    try {
      const response = await fetch('/usuario-actual', { credentials: 'same-origin' });
      if (!response.ok) return;
      const perfil = await leerJson(response);
      if (!nombre.value) nombre.value = `${perfil.nombre || ''} ${perfil.apellido || ''}`.trim();
      if (!correo.value) correo.value = perfil.email || '';
    } catch {
      // El alumno puede escribir sus datos a mano
    }
  }

  form.addEventListener('submit', async evento => {
    evento.preventDefault();
    if (boton.disabled) return;
    if (!form.reportValidity()) return;

    boton.disabled = true;
    boton.textContent = 'Enviando…';
    mostrar('');
    let enviado = false;
    try {
      const response = await fetch(`/api/eventos/${encodeURIComponent(select.value)}/inscripcion`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'same-origin',
        body: JSON.stringify({ nombre: nombre.value.trim(), correo: correo.value.trim() })
      });
      if (response.status === 401) { window.location.href = '/login'; return; }
      const datos = await leerJson(response);
      if (!response.ok || !datos.ok) {
        if (response.status === 409) {
          const elegido = eventos.find(e => String(e.id) === select.value);
          if (elegido) elegido.inscrito = true;
        }
        mostrar(datos.mensaje || 'No fue posible guardar tu inscripción.');
        return;
      }
      enviado = true;
      window.location.href = 'confirmacion.html';
    } catch {
      mostrar('No se pudo conectar con SIUT. Verifica tu conexión e intenta nuevamente.');
    } finally {
      if (!enviado) {
        // Se reactiva sin borrar el mensaje de error
        const elegido = eventos.find(e => String(e.id) === select.value);
        boton.textContent = 'Enviar';
        boton.disabled = !elegido || elegido.inscrito;
      }
    }
  });

  precargarDatos();
  try {
    await cargarEventos();
  } catch {
    select.replaceChildren(new Option('No se pudieron cargar los eventos', ''));
    boton.disabled = true;
    mostrar('No se pudieron cargar los eventos. Intenta nuevamente más tarde.');
  }
});
