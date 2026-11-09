// Encabezado de las páginas de gestión (Empresa y Administrador):
// muestra los enlaces exclusivos del administrador y maneja el cierre de sesión.
// Ocultar enlaces es solo comodidad: el servidor bloquea igualmente esas
// páginas y APIs a quien no tenga el rol.
document.addEventListener('DOMContentLoaded', async () => {
  try {
    const response = await fetch('/usuario-actual', { credentials: 'same-origin' });
    if (response.status === 401) { window.location.href = '/login'; return; }
    if (!response.ok) return;
    const perfil = await response.json();
    if (perfil.rol === 'Administrador') {
      document.querySelectorAll('[data-solo-admin]').forEach(enlace => { enlace.hidden = false; });
    }
  } catch {
    // Sin perfil los enlaces de administrador quedan ocultos
  }
});

document.getElementById('cerrarSesion')?.addEventListener('click', async () => {
  try {
    const response = await fetch('/logout', { method: 'POST', credentials: 'same-origin' });
    // 401 = la sesión ya no existía: se trata como cierre exitoso
    if (!response.ok && response.status !== 401) {
      alert('No fue posible cerrar la sesión. Intenta nuevamente.');
      return;
    }
    window.location.href = '/login';
  } catch {
    alert('Error de conexión con el servidor. Tu sesión sigue abierta.');
  }
});
