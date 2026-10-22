document.addEventListener('DOMContentLoaded', () => {
    const toggle = document.getElementById('menuToggle');
    const nav = document.querySelector('header nav');

    if (toggle && nav) {
        toggle.addEventListener('click', () => {
            nav.classList.toggle('abierto');
        });

        // Cierra el menú al elegir una opción (en móvil)
        nav.querySelectorAll('a').forEach(enlace => {
            enlace.addEventListener('click', () => {
                nav.classList.remove('abierto');
            });
        });
    }
});
