document.getElementById('btn-pdf').addEventListener('click', () => {
    const elemento = document.getElementById('area-pdf');
    const opciones = {
        margin:       0.5,
        filename:     'Mi_Horario_UTSC.pdf',
        image:        { type: 'jpeg', quality: 0.98 },
        html2canvas:  { scale: 2, useCORS: true },
        jsPDF:        { unit: 'in', format: 'letter', orientation: 'portrait' }
    };
    html2pdf().set(opciones).from(elemento).save()
        .catch(err => alert('Error PDF: ' + err.message));
});
