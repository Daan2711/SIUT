// Panel de administración: muestra los totales de vacantes, postulaciones y
// sugerencias pendientes.
document.addEventListener('DOMContentLoaded', async () => {
  const aviso = document.getElementById('avisoPanel');

  const leer = async url => {
    const response = await fetch(url, { credentials: 'same-origin' });
    if (response.status === 401) { window.location.href = '/login'; throw new Error('sin sesión'); }
    const datos = await response.json();
    if (!response.ok || !datos.ok) throw new Error(datos.mensaje || 'Error');
    return datos;
  };
  const mostrar = (id, valor) => { document.getElementById(id).textContent = String(valor); };

  const resultados = await Promise.allSettled([
    leer('/api/vacantes'),
    leer('/api/postulaciones'),
    leer('/api/sugerencias'),
  ]);
  const [vacantes, postulaciones, sugerencias] = resultados;

  if (vacantes.status === 'fulfilled') mostrar('totalVacantes', vacantes.value.vacantes.length);
  if (postulaciones.status === 'fulfilled') mostrar('totalPostulaciones', postulaciones.value.postulaciones.length);
  if (sugerencias.status === 'fulfilled') {
    const conteo = sugerencias.value.conteo || {};
    mostrar('totalPendientes', (conteo['Recibida'] || 0) + (conteo['En revisión'] || 0));
  }

  if (resultados.some(r => r.status === 'rejected')) {
    aviso.textContent = 'No se pudieron cargar algunos datos. Recarga la página para intentarlo de nuevo.';
    aviso.hidden = false;
  }
});
