// Botón «ojito» para mostrar u ocultar cada campo de contraseña de la página.
// Archivo propio (sin JavaScript dentro del HTML) para cumplir la CSP: script-src 'self'.
(function () {
  const SVG = 'http://www.w3.org/2000/svg';
  const OJO = 'M1 12s4-7 11-7 11 7 11 7-4 7-11 7S1 12 1 12z M12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6z';
  const OJO_TACHADO = 'M1 12s4-7 11-7 11 7 11 7-4 7-11 7S1 12 1 12z M12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6z M3 3l18 18';

  function icono(trazo) {
    const svg = document.createElementNS(SVG, 'svg');
    svg.setAttribute('viewBox', '0 0 24 24');
    svg.setAttribute('aria-hidden', 'true');
    svg.setAttribute('focusable', 'false');
    const path = document.createElementNS(SVG, 'path');
    path.setAttribute('d', trazo);
    svg.appendChild(path);
    return svg;
  }

  function preparar(input, indice) {
    if (input.dataset.conOjito) return;
    input.dataset.conOjito = '1';
    if (!input.id) input.id = `password-${indice + 1}`;

    const envoltura = document.createElement('span');
    envoltura.className = 'campo-password';
    input.parentNode.insertBefore(envoltura, input);
    envoltura.appendChild(input);

    const boton = document.createElement('button');
    boton.type = 'button';
    boton.className = 'ver-password';
    boton.setAttribute('aria-controls', input.id);
    envoltura.appendChild(boton);

    function mostrar(visible) {
      input.type = visible ? 'text' : 'password';
      boton.setAttribute('aria-pressed', String(visible));
      boton.setAttribute('aria-label', visible ? 'Ocultar contraseña' : 'Mostrar contraseña');
      boton.title = visible ? 'Ocultar contraseña' : 'Mostrar contraseña';
      boton.replaceChildren(icono(visible ? OJO_TACHADO : OJO));
    }
    mostrar(false);

    boton.addEventListener('click', function () {
      mostrar(input.type === 'password');
      input.focus();
    });

    // Al enviar o limpiar el formulario la contraseña vuelve a ocultarse
    // (evita que quede a la vista o que el navegador la guarde como texto).
    if (input.form) {
      input.form.addEventListener('submit', () => mostrar(false), true);
      input.form.addEventListener('reset', () => mostrar(false));
    }
  }

  function iniciar() {
    document.querySelectorAll('input[type="password"]').forEach(preparar);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', iniciar);
  } else {
    iniciar();
  }
})();
