document.addEventListener("DOMContentLoaded", function () {
    const formulario = document.getElementById("formularioReporte");

    formulario.addEventListener("submit", function (evento) {
        evento.preventDefault();

        Swal.fire({
            title: "¡Envío exitoso!",
            text: "Tu reporte ha sido procesado correctamente.",
            icon: "success",
            confirmButtonColor: "#ff8a00",
            confirmButtonText: "Aceptar"
        }).then(function () {
            window.location.href = "confirmacion.html";
        });
    });
});
