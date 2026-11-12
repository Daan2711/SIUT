// Encabezado de SIUT (todos los roles):
// - Menú lateral en celular (botón ☰) con fondo oscurecido.
// - Submenús del administrador («Bolsa de empleo», «Comunidad»).
// - Menú de perfil con «Cerrar sesión».
// - Sombra del encabezado al hacer scroll.
// Qué opciones ve cada rol lo decide <body data-rol> (lo pone el servidor);
// ocultar opciones es solo presentación: el servidor valida cada permiso.
document.addEventListener('DOMContentLoaded', () => {
  const header = document.querySelector('header.encabezado');
  if (!header) return;
  const nav = document.getElementById('menuPrincipal');
  const toggle = document.getElementById('menuToggle');
  const perfilBoton = document.getElementById('perfilBoton');
  const perfilMenu = document.getElementById('perfilMenu');
  const grupos = [...header.querySelectorAll('.nav-grupo-boton')];
  const esCelular = () => window.matchMedia('(max-width: 900px)').matches;

  // --- Submenús y menú de perfil ---------------------------------------
  const cerrarGrupos = excepto => grupos.forEach(boton => {
    if (boton !== excepto) {
      boton.setAttribute('aria-expanded', 'false');
      boton.parentElement.classList.remove('abierto');
    }
  });
  const cambiarPerfil = abierto => {
    if (!perfilBoton || !perfilMenu) return;
    perfilMenu.hidden = !abierto;
    perfilBoton.setAttribute('aria-expanded', String(abierto));
  };

  grupos.forEach(boton => {
    boton.addEventListener('click', evento => {
      evento.stopPropagation();
      const abierto = boton.getAttribute('aria-expanded') !== 'true';
      cerrarGrupos(boton);
      cambiarPerfil(false);
      boton.setAttribute('aria-expanded', String(abierto));
      boton.parentElement.classList.toggle('abierto', abierto);
    });
  });

  perfilBoton?.addEventListener('click', evento => {
    evento.stopPropagation();
    cerrarGrupos();
    cambiarPerfil(perfilMenu.hidden);
  });

  // Clic fuera: cierra submenús y perfil
  document.addEventListener('click', evento => {
    if (!evento.target.closest('.nav-grupo')) cerrarGrupos();
    if (!evento.target.closest('.perfil')) cambiarPerfil(false);
  });

  // --- Menú lateral en celular -----------------------------------------
  const fondo = document.createElement('div');
  fondo.className = 'nav-fondo';
  fondo.hidden = true;
  document.body.appendChild(fondo);

  const cambiarMenu = abierto => {
    if (!nav || !toggle) return;
    nav.classList.toggle('abierto', abierto);
    fondo.hidden = !abierto;
    document.body.classList.toggle('menu-abierto', abierto);
    toggle.setAttribute('aria-expanded', String(abierto));
    toggle.setAttribute('aria-label', abierto ? 'Cerrar menú' : 'Abrir menú');
  };
  toggle?.addEventListener('click', evento => {
    evento.stopPropagation();
    cambiarPerfil(false);
    cambiarMenu(!nav.classList.contains('abierto'));
  });
  fondo.addEventListener('click', () => cambiarMenu(false));
  nav?.querySelectorAll('a').forEach(enlace => enlace.addEventListener('click', () => cambiarMenu(false)));
  // Al pasar a pantalla grande se cierra el menú lateral
  window.addEventListener('resize', () => { if (!esCelular()) cambiarMenu(false); });

  // --- Teclado: Escape cierra lo que esté abierto -------------------------
  document.addEventListener('keydown', evento => {
    if (evento.key !== 'Escape') return;
    const grupoAbierto = grupos.find(b => b.getAttribute('aria-expanded') === 'true');
    if (grupoAbierto) { cerrarGrupos(); grupoAbierto.focus(); return; }
    if (perfilMenu && !perfilMenu.hidden) { cambiarPerfil(false); perfilBoton.focus(); return; }
    if (nav?.classList.contains('abierto')) { cambiarMenu(false); toggle.focus(); }
  });

  // --- Sombra al hacer scroll ---------------------------------------------
  const sombra = () => header.classList.toggle('con-sombra', window.scrollY > 4);
  window.addEventListener('scroll', sombra, { passive: true });
  sombra();

  // --- Cerrar sesión --------------------------------------------------------
  document.getElementById('cerrarSesion')?.addEventListener('click', async evento => {
    const boton = evento.currentTarget;
    boton.disabled = true;
    try {
      const response = await fetch('/logout', { method: 'POST', credentials: 'same-origin' });
      // 401 = la sesión ya no existía: se trata como cierre exitoso
      if (!response.ok && response.status !== 401) {
        alert('No fue posible cerrar la sesión. Intenta nuevamente.');
        boton.disabled = false;
        return;
      }
      localStorage.removeItem('nombreUsuario');
      window.location.href = '/login';
    } catch {
      alert('Error de conexión con el servidor. Tu sesión sigue abierta.');
      boton.disabled = false;
    }
  });
});
