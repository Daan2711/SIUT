document.getElementById('btnLogout').addEventListener('click', function() {
    fetch('/logout', { method: 'POST' })
    .then(() => {
        localStorage.removeItem('nombreUsuario');
        window.location.href = '/login';
    });
});

const imagenesSlider = ["img/1.png", "img/2.png", "img/3.png", "img/4.png"];
let indiceSlider = 0;

function cambiarImagenSlider() {
    indiceSlider = (indiceSlider + 1) % imagenesSlider.length;
    document.getElementById("imagenSlider").src = imagenesSlider[indiceSlider];
}

setInterval(cambiarImagenSlider, 3000);
