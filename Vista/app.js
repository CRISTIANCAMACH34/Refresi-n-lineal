// URL base de la API
const API_URL = 'http://localhost:5000/api';

// Función para formatear números con separadores de miles
function formatNumber(num) {
    return new Intl.NumberFormat('es-CO').format(num);
}

// Función para mostrar mensaje de error
function mostrarError(mensaje) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'mt-4 p-4 rounded-md bg-red-50 border border-red-200';
    errorDiv.innerHTML = `<p class="text-sm text-red-700">${mensaje}</p>`;
    const form = document.getElementById('viviendaForm');
    form.insertBefore(errorDiv, form.firstChild);
    setTimeout(() => errorDiv.remove(), 5000);
}

// Función para mostrar mensaje de éxito
function mostrarExito(mensaje) {
    const successDiv = document.createElement('div');
    successDiv.className = 'mt-4 p-4 rounded-md bg-green-50 border border-green-200';
    successDiv.innerHTML = `<p class="text-sm text-green-700">${mensaje}</p>`;
    const form = document.getElementById('viviendaForm');
    form.insertBefore(successDiv, form.firstChild);
    setTimeout(() => successDiv.remove(), 5000);
}

// Función para cargar la lista de viviendas
async function cargarViviendas() {
    const loadingElement = document.getElementById('loadingViviendas');
    const listaViviendas = document.getElementById('listaViviendas');
    
    try {
        // Mostrar indicador de carga
        loadingElement.classList.remove('hidden');
        listaViviendas.innerHTML = '';
        
        const response = await fetch(`${API_URL}/viviendas`, {
            method: 'GET',
            headers: {
                'Accept': 'application/json'
            },
            credentials: 'include'
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Error al cargar las viviendas');
        }
        
        const viviendas = await response.json();
        
        if (viviendas.length === 0) {
            listaViviendas.innerHTML = `
                <li class="px-6 py-4">
                    <p class="text-gray-500 text-center">No hay viviendas registradas</p>
                </li>`;
            return;
        }

        listaViviendas.innerHTML = viviendas.map(vivienda => `
            <li class="px-6 py-4 hover:bg-gray-50">
                <div class="flex items-center justify-between">
                    <div class="flex-1 min-w-0">
                        <p class="text-sm font-medium text-blue-600 truncate">
                            ${vivienda.categoria}: ${vivienda.tipo_hogar}
                        </p>
                        <p class="text-sm text-gray-500 truncate">
                            ${vivienda.descripcion?.substring(0, 100) || 'Sin descripción'}${vivienda.descripcion?.length > 100 ? '...' : ''}
                        </p>
                        <div class="mt-2 flex flex-wrap gap-4">
                            <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                                Área: ${vivienda.area} m²
                            </span>
                            <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                                ${vivienda.habitaciones} hab.
                            </span>
                            <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                                ${vivienda.antiguedad} años
                            </span>
                        </div>
                    </div>
                    <div class="ml-4 flex-shrink-0">
                        <p class="text-lg font-semibold text-gray-900">
                            $${formatNumber(Math.round(vivienda.precio))}
                        </p>
                        <p class="text-xs text-gray-500">
                            ${new Date(vivienda.fecha_publicacion).toLocaleDateString()}
                        </p>
                    </div>
                </div>
            </li>`).join('');
    } catch (error) {
        console.error('Error al cargar viviendas:', error);
        mostrarError('Error al cargar la lista de viviendas');
    } finally {
        loadingElement.classList.add('hidden');
    }
}

// Función para actualizar estadísticas
async function actualizarEstadisticas() {
    const loadingStats = document.getElementById('loadingStats');
    
    try {
        loadingStats.classList.remove('hidden');
        
        const response = await fetch(`${API_URL}/estadisticas`, {
            method: 'GET',
            headers: {
                'Accept': 'application/json'
            },
            credentials: 'include'
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Error al cargar las estadísticas');
        }
        
        const estadisticas = await response.json();
        
        document.getElementById('promedioPrecio').textContent = `$${estadisticas.promedioPrecio?.toFixed(2) || '0.00'}`;
        document.getElementById('promedioMetro').textContent = `$${estadisticas.promedioMetro?.toFixed(2) || '0.00'}/m²`;
        document.getElementById('totalViviendas').textContent = estadisticas.totalViviendas || '0';
        
    } catch (error) {
        console.error('Error al actualizar estadísticas:', error);
        mostrarError('Error al cargar las estadísticas');
    } finally {
        loadingStats.classList.add('hidden');
    }
}

// Función para manejar el envío del formulario de predicción
async function manejarPrediccion(e) {
    e.preventDefault();
    
    try {
        const area = parseFloat(document.getElementById('area').value);
        const habitaciones = parseInt(document.getElementById('habitaciones').value);
        const antiguedad = parseInt(document.getElementById('antiguedad').value);
        const tipo_hogar = document.getElementById('tipo_hogar').value;
        const categoria = document.getElementById('categoria').value;

        // Validar campos requeridos
        if (isNaN(area) || isNaN(habitaciones) || isNaN(antiguedad)) {
            throw new Error('Por favor complete todos los campos requeridos');
        }

        const response = await fetch(`${API_URL}/prediccion`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify({
                area,
                habitaciones,
                antiguedad,
                tipo_hogar,
                categoria
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Error al realizar la predicción');
        }

        const data = await response.json();
        
        // Mostrar resultado
        const resultadoDiv = document.getElementById('resultado');
        resultadoDiv.classList.remove('hidden');
        document.getElementById('precioResultado').textContent = 
            `El precio aproximado de la vivienda es: $${formatNumber(Math.round(data.precio))}`;
        
        // Desplazarse al resultado
        resultadoDiv.scrollIntoView({ behavior: 'smooth' });
        
        // Mostrar mensaje de éxito
        mostrarExito('¡Predicción realizada con éxito!');
        
    } catch (error) {
        console.error('Error al predecir precio:', error);
        mostrarError(error.message || 'Ocurrió un error al realizar la predicción');
    }
}

// Función para obtener datos para las gráficas
async function obtenerDatosGraficas() {
    const loadingGraph = document.getElementById('loadingGraph');
    const graficoContainer = document.getElementById('graficoDispersion');
    
    try {
        loadingGraph.classList.remove('hidden');
        graficoContainer.innerHTML = '';
        
        const response = await fetch(`${API_URL}/graficos/dispersion-precio-area`, {
            method: 'GET',
            headers: {
                'Accept': 'application/json'
            },
            credentials: 'include'
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Error al cargar los datos de las gráficas');
        }
        
        const datosGraficas = await response.json();
        
        // Crear gráfica de dispersión
        const canvas = document.createElement('canvas');
        canvas.id = 'dispersionChart';
        graficoContainer.appendChild(canvas);
        
        const ctxDispersion = canvas.getContext('2d');
        new Chart(ctxDispersion, {
            type: 'scatter',
            data: {
                datasets: [{
                    label: 'Precio vs Área',
                    data: datosGraficas.map(dato => ({
                        x: dato.area,
                        y: dato.precio,
                        label: dato.tipo_hogar
                    })),
                    backgroundColor: '#36A2EB',
                    borderColor: '#1C8CFF',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    title: {
                        display: true,
                        text: 'Dispersión de Precio vs Área'
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return `Área: ${context.parsed.x}m², Precio: $${formatNumber(context.parsed.y)}`;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Precio (COP)'
                        },
                        ticks: {
                            callback: function(value) {
                                return `$${formatNumber(value)}`;
                            }
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Área (m²)'
                        }
                    }
                }
            }
        });
        
    } catch (error) {
        console.error('Error al obtener datos para gráficas:', error);
        graficoContainer.innerHTML = `
            <div class="p-4 bg-red-50 text-red-700 rounded-md">
                <p>Error al cargar el gráfico: ${error.message}</p>
            </div>`;
    } finally {
        loadingGraph.classList.add('hidden');
    }
}

// Función para inicializar la aplicación
async function inicializarAplicacion() {
    try {
        await Promise.all([
            cargarViviendas(),
            actualizarEstadisticas(),
            obtenerDatosGraficas()
        ]);
    } catch (error) {
        console.error('Error al inicializar la aplicación:', error);
        mostrarError('Error al cargar los datos iniciales');
    }
}

// Configurar event listeners
document.addEventListener('DOMContentLoaded', () => {
    // Configurar el formulario
    const form = document.getElementById('viviendaForm');
    if (form) {
        form.addEventListener('submit', manejarPrediccion);
    }
    
    // Configurar botón de actualización
    const actualizarBtn = document.getElementById('actualizarLista');
    if (actualizarBtn) {
        actualizarBtn.addEventListener('click', (e) => {
            e.preventDefault();
            cargarViviendas();
            actualizarEstadisticas();
            mostrarExito('Datos actualizados');
        });
    }
    
    // Inicializar la aplicación
    inicializarAplicacion();
});
