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

        // Aquí queda disponible el valor final por si luego se envía al backend
        // const datos = {
        //     nombre: document.getElementById("nombre").value,
        //     grupo: document.getElementById("grupo").value,
        //     departamento: departamentoFinal,
        //     descripcion: document.getElementById("descripcion").value
        // };

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
