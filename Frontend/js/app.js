const imagenes = [

"img/2.png",

"img/3.jpeg",

"img/4.jpeg"

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