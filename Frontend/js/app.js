const imagenes = [
    "img/1.png", // Asegúrate de tener esta imagen
    "img/2.png",
    "img/3.jpeg",
    "img/4.jpeg" // Agrega la segunda foto
];

let indice = 0;

function mostrarImagen(){
    const img = document.getElementById("imagenSlider"); 
    if(img){
        img.src = imagenes[indice];
    }
}

function siguiente(){
    indice++;
    if(indice >= imagenes.length){
        indice = 0;
    }
    mostrarImagen();
}

function anterior(){
    indice--;
    if(indice < 0){
        indice = imagenes.length - 1;
    }
    mostrarImagen();
}

setInterval(() => {
    if(document.getElementById("imagenSlider")){
        siguiente();
    }
}, 5000);