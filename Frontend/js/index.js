document.getElementById('btnLogout').addEventListener('click', function() {
    fetch('/logout', { method: 'POST' })
    .then(() => {
        localStorage.removeItem('nombreUsuario');
        window.location.href = '/login';
    });
});