// Protección CSRF: agrega la cabecera X-CSRF-Token a toda petición que cambia
// datos (POST, PUT, PATCH, DELETE) hacia el propio sitio. El servidor rechaza
// con 403 las que no la traen (ver app.py, «PROTECCIÓN CSRF»).
// Debe cargarse antes que los demás scripts de la página.
(function () {
  const fetchOriginal = window.fetch.bind(window);
  const METODOS = ['POST', 'PUT', 'PATCH', 'DELETE'];
  let tokenPendiente = null;

  // El token se pide una sola vez, la primera vez que hace falta
  function obtenerToken() {
    if (!tokenPendiente) {
      tokenPendiente = fetchOriginal('/api/csrf-token', { credentials: 'same-origin' })
        .then(r => (r.ok ? r.json() : {}))
        .then(datos => datos.csrf_token || '')
        .catch(() => '')
        .then(token => {
          if (!token) tokenPendiente = null;   // se reintenta en la siguiente petición
          return token;
        });
    }
    return tokenPendiente;
  }

  function esMismoSitio(url) {
    try {
      return new URL(url, window.location.href).origin === window.location.origin;
    } catch {
      return false;
    }
  }

  window.fetch = async function (recurso, opciones) {
    const peticion = recurso instanceof Request ? recurso : null;
    const metodo = ((opciones && opciones.method) || (peticion && peticion.method) || 'GET').toUpperCase();
    const url = peticion ? peticion.url : String(recurso);
    if (!METODOS.includes(metodo) || !esMismoSitio(url)) {
      return fetchOriginal(recurso, opciones);
    }
    const cabeceras = new Headers((opciones && opciones.headers) || (peticion && peticion.headers) || {});
    if (!cabeceras.has('X-CSRF-Token')) {
      cabeceras.set('X-CSRF-Token', await obtenerToken());
    }
    return fetchOriginal(recurso, Object.assign({}, opciones, { headers: cabeceras }));
  };
})();
