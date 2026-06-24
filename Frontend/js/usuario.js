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

    await fetch('/logout', {
        method: 'POST'
    });

    window.location.href = "/login";
});