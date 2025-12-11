document.addEventListener('DOMContentLoaded', function () {
    const filterItems = document.querySelectorAll('.filter-item');
    const filteredDataContainer = document.getElementById('filtered-data');
    const slPorRevisar = document.getElementById('sl-por-revisar');
    const proveedorField = document.getElementById('proveedor-field');
    const slField = document.getElementById('sl-field');
    const ordenCompraField = document.getElementById('orden-compra-field');
    const expandedItemsContainer = document.getElementById('expanded-items');
    const selectedBox = document.getElementById('selected-box');
    const qrReader = document.getElementById('qr-reader');
    const qrReaderContainer = document.getElementById('qr-reader-container');
    const closeQrReader = document.getElementById('close-qr-reader');
    const itemsTable = document.querySelector('.scan-table');

    // Filtrar datos al hacer clic en las cajas
    filterItems.forEach(item => {
        item.addEventListener('click', function () {
            const caja = this.getAttribute('data-caja');

            filterItems.forEach(i => i.classList.remove('selected-item'));
            this.classList.add('selected-item');

            selectedBox.textContent = `Misceláneos de la caja: ${caja}`;
            itemsTable.style.backgroundColor = '';

            fetch(`/filter_data?caja=${caja}`)
                .then(response => response.json())
                .then(data => {
                    filteredDataContainer.innerHTML = '';

                    data.forEach(row => {
                        const tr = document.createElement('tr');
                        tr.classList.add('selectable-row');
                        tr.innerHTML = `
                            <td>${row.Trailer_List}</td>
                            <td>${row.Factura_List}</td>
                            <td>${row.Orden_Compra_List}</td>
                            <td>${row.Proveedor_List}</td>
                            <td>${row.Ref_SL_List}</td>
                            <td>${row.Qty_List}</td>
                            <td>${row.Estatus_List}</td>
                        `;

                        if (row.Estatus_List === 'Completado') {
                            tr.style.backgroundColor = 'green';
                        } else if (row.Estatus_List === 'En Proceso') {
                            tr.style.backgroundColor = 'yellow';
                        } else if (row.Estatus_List === 'Por_Validar') {
                            tr.style.backgroundColor = '';
                        }

                        filteredDataContainer.appendChild(tr);
                    });

                    slPorRevisar.textContent = `SLs Por Revisar: ${data.length}`;

                    const rows = document.querySelectorAll('.selectable-row');
                    rows.forEach(row => {
                        row.addEventListener('click', function () {
                            rows.forEach(r => r.classList.remove('selected-row'));
                            this.classList.add('selected-row');

                            itemsTable.style.backgroundColor = '';

                            const proveedor = this.children[3].textContent;
                            const sl = this.children[4].textContent;
                            const ordenCompra = this.children[2].textContent;
                            const qty = parseInt(this.children[5].textContent);

                            proveedorField.textContent = proveedor;
                            slField.textContent = sl;
                            ordenCompraField.textContent = ordenCompra;

                            expandedItemsContainer.innerHTML = '';
                            fetch(`/expand_data?sl=${sl}&orden_compra=${ordenCompra}`)
                                .then(response => response.json())
                                .then(data => {
                                    data.forEach(item => {
                                        const tr = document.createElement('tr');
                                        tr.setAttribute('data-sl', item.SL);
                                        tr.setAttribute('data-qty', item.Sequence);
                                        tr.setAttribute('data-orden-compra', item.OrdenCompra);
                                        
                                        tr.innerHTML = `
                                            <td>${item.SL}</td>
                                            <td>${item.Sequence}</td>
                                            <td>${item.OrdenCompra}</td>
                                            <td>
                                                <img src="/static/images/barcode.png" alt="QR" class="qr-image">
                                            </td>
                                        `;

                                        if (item.QR_Val) {
                                            tr.style.backgroundColor = 'green';
                                            // ✅ Agregar botón de evidencia si ya fue escaneado
                                            const evidenceTd = document.createElement('td');
                                            if (item.Foto && item.Foto !== '') {
                                                // ✅ CORREGIDO: Usar la ruta correcta con fotos_evidencia
                                                evidenceTd.innerHTML = `
                                                    <button class="btn-ver-foto" data-foto="/static/uploads/fotos_evidencia/${item.Foto}">Ver Foto</button>
                                                `;
                                            } else {
                                                evidenceTd.innerHTML = `
                                                    <input type="file" class="foto-evidencia" accept="image/*" style="display:none;">
                                                    <button class="btn-subir-foto">Subir Evidencia</button>
                                                `;
                                            }
                                            tr.appendChild(evidenceTd);
                                        } else if (item.Pending) {
                                            tr.style.backgroundColor = 'rgba(255, 0, 0, 0.2)';
                                        } else {
                                            tr.style.backgroundColor = '';
                                        }

                                        expandedItemsContainer.appendChild(tr);
                                    });
                                })
                                .catch(error => console.error('Error al cargar los datos de los QR:', error));
                        });
                    });
                })
                .catch(error => console.error('Error al obtener los datos filtrados:', error));
        });
    });

    // ✅ Inicializar ZXing con Hints para soportar códigos de barras y QR
    const hints = new Map();
    hints.set(ZXing.DecodeHintType.POSSIBLE_FORMATS, [
        ZXing.BarcodeFormat.CODE_128,
        ZXing.BarcodeFormat.CODE_39,
        ZXing.BarcodeFormat.EAN_13,
        ZXing.BarcodeFormat.EAN_8,
        ZXing.BarcodeFormat.UPC_A,
        ZXing.BarcodeFormat.UPC_E,
        ZXing.BarcodeFormat.QR_CODE
    ]);

    const codeReader = new ZXing.BrowserMultiFormatReader(hints);

    // Evento para cerrar el escáner
    closeQrReader.addEventListener('click', () => {
        qrReader.style.display = 'none';
        codeReader.reset();
    });

    // Función para verificar si todos los códigos han sido escaneados correctamente
    function checkIfAllScanned() {
        const totalQRCodes = document.querySelectorAll('#expanded-items .qr-image').length;
        const scannedQRCodes = document.querySelectorAll('#expanded-items .qr-image.scanned').length;

        if (totalQRCodes === scannedQRCodes) {
            const selectedRow = document.querySelector('.selectable-row.selected-row');
            if (selectedRow) {
                selectedRow.style.backgroundColor = 'green';
            }
        }
    }

    // ✅ Evento delegado para manejar clicks en botones de subir foto
    expandedItemsContainer.addEventListener('click', function(event) {
        if (event.target.classList.contains('btn-subir-foto')) {
            const row = event.target.closest('tr');
            const fileInput = row.querySelector('.foto-evidencia');
            fileInput.click();
        }

        if (event.target.classList.contains('btn-ver-foto')) {
            const fotoUrl = event.target.getAttribute('data-foto');
            // Abrir la imagen en una nueva ventana
            window.open(fotoUrl, '_blank');
        }
    });

    // ✅ Evento delegado para manejar la selección de archivos
    expandedItemsContainer.addEventListener('change', function(event) {
        if (event.target.classList.contains('foto-evidencia')) {
            const fileInput = event.target;
            const file = fileInput.files[0];
            
            if (file) {
                const row = fileInput.closest('tr');
                const sl = row.getAttribute('data-sl');
                const qty = parseInt(row.getAttribute('data-qty'));
                const ordenCompra = row.getAttribute('data-orden-compra');

                // Leer el archivo como base64
                const reader = new FileReader();
                reader.onload = function(e) {
                    const fotoBase64 = e.target.result;

                    // Enviar al servidor
                    fetch('/guardar_foto_evidencia', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            sl: sl,
                            qty: qty,
                            orden_compra: ordenCompra,
                            foto: fotoBase64
                        })
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            alert('Foto de evidencia guardada correctamente');
                            // ✅ CORREGIDO: Actualizar el botón con la ruta correcta
                            const evidenceTd = row.querySelector('td:last-child');
                            evidenceTd.innerHTML = `
                                <button class="btn-ver-foto" data-foto="/static/uploads/fotos_evidencia/${data.foto_filename}">Ver Foto</button>
                            `;
                        } else {
                            alert(`Error: ${data.message}`);
                        }
                    })
                    .catch(error => console.error('Error al guardar la foto:', error));
                };
                reader.readAsDataURL(file);
            }
        }
    });

    // Evento para las imágenes de QR
    expandedItemsContainer.addEventListener('click', function (event) {
        if (event.target.tagName === 'IMG' && event.target.classList.contains('qr-image')) {
            qrReader.style.display = 'block';

            codeReader.decodeFromVideoDevice(
                null,
                'qr-reader-container',
                (result, err) => {
                    if (result) {
                        const scannedCode = result.text.trim();
                        const currentSL = document.getElementById('sl-field').textContent.trim();
                        const currentOrdenCompra = document.getElementById('orden-compra-field').textContent.trim();

                        const scannedSL = scannedCode.startsWith('SL') ? scannedCode.slice(2, 8) : null;
                        const scannedQty = parseInt(scannedCode.slice(-1));

                        const row = event.target.closest('tr');
                        const rowSL = row.children[0].textContent.trim();
                        const rowQty = parseInt(row.children[1].textContent.trim());
                        const rowOrdenCompra = row.children[2].textContent.trim();

                        let slValid = false;
                        let qtyValid = false;
                        let ordenCompraValid = false;

                        if (scannedQty === rowQty) {
                            qtyValid = true;
                        }

                        if (rowOrdenCompra === currentOrdenCompra) {
                            ordenCompraValid = true;
                        }

                        if (scannedSL === rowSL) {
                            slValid = true;
                        }

                        if (slValid && qtyValid && ordenCompraValid) {
                            alert('Código correcto: El SL, el Qty y la Orden de Compra son correctos.');
                            event.target.classList.add('scanned');
                            row.style.backgroundColor = 'green';

                            const fecha_hora_escaneo = new Date().toLocaleString('en-GB', {
                                year: 'numeric',
                                month: '2-digit',
                                day: '2-digit',
                                hour: '2-digit',
                                minute: '2-digit',
                                second: '2-digit'
                            }).replace(',', '');

                            fetch('/guardar_escaneo', {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/json'
                                },
                                body: JSON.stringify({
                                    sl: rowSL,
                                    qty: rowQty,
                                    orden_compra: rowOrdenCompra,
                                    estatus: 'Completado',
                                    foto_entregado: '',
                                    fecha_hora_escaneo: fecha_hora_escaneo
                                })
                            })
                            .then(response => response.json())
                            .then(data => {
                                console.log('Respuesta del servidor:', data);
                                if (!data.success) {
                                    alert(`Error: ${data.message}`);
                                    row.style.backgroundColor = 'rgba(255, 0, 0, 0.2)';
                                } else {
                                    row.style.backgroundColor = 'green';
                                    // ✅ Agregar la columna de evidencia después de escanear
                                    const evidenceTd = document.createElement('td');
                                    evidenceTd.innerHTML = `
                                        <input type="file" class="foto-evidencia" accept="image/*" style="display:none;">
                                        <button class="btn-subir-foto">Subir Evidencia</button>
                                    `;
                                    row.appendChild(evidenceTd);
                                }
                            })
                            .catch(error => console.error('Error en la solicitud:', error));
                        } else {
                            let errorMessage = 'Código incorrecto: ';
                            if (!slValid) errorMessage += 'El SL no coincide. ';
                            if (!qtyValid) errorMessage += 'El Qty no coincide. ';
                            if (!ordenCompraValid) errorMessage += 'La Orden de Compra no coincide.';

                            alert(errorMessage);
                            row.style.backgroundColor = 'rgba(255, 0, 0, 0.2)';
                        }

                        checkIfAllScanned();

                        qrReader.style.display = 'none';
                        codeReader.reset();
                    }

                    if (err && !(err instanceof ZXing.NotFoundException)) {
                        console.error(err);
                    }
                }
            );
        }
    });

    // Función para restablecer el estado de una fila
    function resetEstatus(sl, ordenCompra, row) {
        fetch('/reset_estatus', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                sl: sl,
                orden_compra: ordenCompra
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('El estado se ha restablecido correctamente.');
                row.style.backgroundColor = '';
            } else {
                console.error('Error al restablecer el estado:', data.message);
            }
        })
        .catch(error => console.error('Error en la solicitud:', error));
    }
});