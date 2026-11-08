document.addEventListener("DOMContentLoaded", async () => {
    try {
        const response = await fetch('/usuario-actual');
        const data = await response.json();

        if (data.nombre) {
            document.getElementById("nombreAlumno").textContent = data.nombre;
        }
    } catch (error) {
        console.error("Error al obtener usuario:", error);
    }
});

document.getElementById("cerrarSesion")?.addEventListener("click", async () => {
    try {
        const response = await fetch('/logout', { method: 'POST', credentials: 'same-origin' });
        // 401 = la sesión ya no existía: se trata como cierre exitoso
        if (!response.ok && response.status !== 401) {
            alert('No fue posible cerrar la sesión. Intenta nuevamente.');
            return;
        }
        window.location.href = "/login";
    } catch (error) {
        alert('Error de conexión con el servidor. Tu sesión sigue abierta.');
    }
});