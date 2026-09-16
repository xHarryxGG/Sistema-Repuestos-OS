function formatUSD(amount) {
    return '$' + Number(amount).toFixed(2);
}

function formatBS(amount) {
    return 'Bs. ' + Number(amount).toLocaleString('es-VE', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

async function fetchTasaBCV() {
    const btn = document.getElementById('btn-fetch-bcv');
    if (btn) {
        btn.disabled = true;
        btn.textContent = 'Consultando...';
    }
    try {
        const res = await fetch('/api/tasa-bcv');
        const data = await res.json();
        if (data.tasa) {
            const tasa = Math.round(Number(data.tasa) * 100) / 100;
            const input = document.getElementById('tasa-cambio');
            if (input) {
                input.value = tasa.toFixed(2);
                input.dispatchEvent(new Event('input'));
            }
            updateSidebarTasa(tasa);
            showToast(data.success ? `Tasa BCV actualizada: ${tasa.toFixed(2)} Bs/$` : `Usando tasa local: ${tasa.toFixed(2)} Bs/$`, data.success ? 'success' : 'warning');
        }
    } catch (e) {
        showToast('Error al consultar el BCV', 'error');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.textContent = 'Obtener del BCV';
        }
    }
}

async function updateTasaManual() {
    const input = document.getElementById('tasa-cambio');
    if (!input) return;
    const tasa = Math.round(parseFloat(input.value) * 100) / 100;
    if (isNaN(tasa) || tasa <= 0) {
        showToast('Ingrese una tasa válida', 'error');
        return;
    }
    input.value = tasa.toFixed(2);
    input.dispatchEvent(new Event('input'));
    const formData = new FormData();
    formData.append('tasa', tasa);
    await fetch('/api/tasa', { method: 'POST', body: formData });
    updateSidebarTasa(tasa);
    showToast('Tasa actualizada manualmente', 'success');
}

function updateSidebarTasa(tasa) {
    const el = document.getElementById('sidebar-tasa');
    if (el) el.textContent = Number(tasa).toFixed(2) + ' Bs/$';
}

function showToast(message, type = 'info') {
    const colors = {
        success: 'bg-green-600',
        error: 'bg-red-600',
        warning: 'bg-yellow-600',
        info: 'bg-brand-600'
    };
    const toast = document.createElement('div');
    toast.className = `fixed bottom-4 right-4 z-50 px-4 py-3 rounded-lg text-white text-sm shadow-lg animate-fade-in ${colors[type] || colors.info}`;
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}

document.addEventListener('DOMContentLoaded', () => {
    const btnBCV = document.getElementById('btn-fetch-bcv');
    if (btnBCV) btnBCV.addEventListener('click', fetchTasaBCV);

    const btnManual = document.getElementById('btn-update-tasa');
    if (btnManual) btnManual.addEventListener('click', updateTasaManual);
});
