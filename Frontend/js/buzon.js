document.addEventListener("DOMContentLoaded", function () {
    const formulario = document.getElementById("formularioReporte");
    const selectDepartamento = document.getElementById("departamento");
    const grupoOtro = document.getElementById("grupoOtroDepartamento");
    const inputOtro = document.getElementById("otroDepartamento");

    // Mostrar u ocultar el campo de texto libre según la opción elegida
    selectDepartamento.addEventListener("change", function () {
        if (selectDepartamento.value === "Otro") {
            grupoOtro.style.display = "block";
            inputOtro.setAttribute("required", "required");
        } else {
            grupoOtro.style.display = "none";
            inputOtro.removeAttribute("required");
            inputOtro.value = "";
        }
    });

    formulario.addEventListener("submit", function (evento) {
        evento.preventDefault();

        // Departamento final: si eligió "Otro", se usa lo que escribió
        const departamentoFinal =
            selectDepartamento.value === "Otro"
                ? inputOtro.value.trim()
                : selectDepartamento.value;

        if (selectDepartamento.value === "Otro" && departamentoFinal === "") {
            Swal.fire({
                title: "Falta información",
                text: "Por favor especifica el departamento o área.",
                icon: "warning",
                confirmButtonColor: "#ff8a00"
            });
            return;
        }

        const datos = {
            nombre: document.getElementById("nombre").value.trim(),
            grupo: document.getElementById("grupo").value.trim(),
            departamento: departamentoFinal,
            descripcion: document.getElementById("descripcion").value.trim()
        };

        // Deshabilitamos el botón para evitar doble envío
        const btnEnviar = formulario.querySelector(".btn-enviar");
        btnEnviar.disabled = true;

        fetch("/guardar-sugerencia", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            credentials: "same-origin", // manda la cookie de sesión
            body: JSON.stringify(datos)
        })
            .then(function (respuesta) {
                return respuesta.json().then(function (cuerpo) {
                    return { ok: respuesta.ok, cuerpo: cuerpo };
                });
            })
            .then(function (resultado) {
                btnEnviar.disabled = false;

                if (!resultado.ok) {
                    Swal.fire({
                        title: "No se pudo enviar",
                        text: resultado.cuerpo.error || "Ocurrió un error inesperado.",
                        icon: "error",
                        confirmButtonColor: "#ff8a00"
                    });
                    return;
                }

                Swal.fire({
                    title: "¡Envío exitoso!",
                    text: "Tu reporte ha sido procesado correctamente.",
                    icon: "success",
                    confirmButtonColor: "#ff8a00",
                    confirmButtonText: "Aceptar"
                }).then(function () {
                    window.location.href = "confirmacion.html";
                });
            })
            .catch(function () {
                btnEnviar.disabled = false;
                Swal.fire({
                    title: "Error de conexión",
                    text: "No se pudo contactar al servidor. Intenta de nuevo.",
                    icon: "error",
                    confirmButtonColor: "#ff8a00"
                });
            });
    });
});
