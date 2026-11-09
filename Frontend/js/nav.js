// Menú desplegable en pantallas pequeñas (botón ☰ del encabezado).
document.addEventListener('DOMContentLoaded', () => {
    const toggle = document.getElementById('menuToggle');
    const nav = document.querySelector('header nav');
    if (!toggle || !nav) return;

    const cambiar = abierto => {
        nav.classList.toggle('abierto', abierto);
        toggle.setAttribute('aria-expanded', String(abierto));
        toggle.setAttribute('aria-label', abierto ? 'Cerrar menú' : 'Abrir menú');
    };

    toggle.addEventListener('click', () => cambiar(!nav.classList.contains('abierto')));

    // Cierra el menú al elegir una opción o con la tecla Escape
    nav.querySelectorAll('a').forEach(enlace => enlace.addEventListener('click', () => cambiar(false)));
    document.addEventListener('keydown', evento => {
        if (evento.key === 'Escape' && nav.classList.contains('abierto')) {
            cambiar(false);
            toggle.focus();
        }
    });
});
