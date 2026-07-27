document.addEventListener("DOMContentLoaded", function () {
    const contador = document.getElementById("segundos");
    const btnInicio = document.getElementById("btnInicio");
    let tiempo = 5;

    btnInicio.addEventListener("click", function () {
        window.location.href = "index.html";
    });

    const intervalo = setInterval(function () {
        tiempo--;
        contador.textContent = tiempo;
        if (tiempo <= 0) {
            clearInterval(intervalo);
            window.location.href = "index.html";
        }
    }, 1000);
});
