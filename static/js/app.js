// Inditex Stok Takip Sistemi - JavaScript Functions

// Global değişkenler
let notifications = [];
let refreshInterval;

// Sayfa yüklendiğinde çalışacak fonksiyonlar
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
    setupEventListeners();
    startAutoRefresh();
    
    // Fade-in animasyonu ekle
    document.body.classList.add('fade-in');
});

// Uygulamayı başlat
function initializeApp() {
    console.log('Inditex Stok Takip Sistemi başlatılıyor...');
    
    // Tooltip'leri başlat
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Toast bildirimlerini başlat
    const toastElList = [].slice.call(document.querySelectorAll('.toast'));
    toastElList.map(function (toastEl) {
        return new bootstrap.Toast(toastEl);
    });
    
    // Mevcut bildirim sayısını güncelle
    updateNotificationBadge();
}

// Event listener'ları kur
function setupEventListeners() {
    // Arama kutusuna focus olduğunda
    const searchInput = document.getElementById('search-input');
    if (searchInput) {
        searchInput.addEventListener('focus', function() {
            this.classList.add('border-primary');
        });
        
        searchInput.addEventListener('blur', function() {
            this.classList.remove('border-primary');
        });
    }
    
    // Klavye kısayolları
    document.addEventListener('keydown', function(e) {
        // Ctrl + K: Arama kutusuna odaklan
        if (e.ctrlKey && e.key === 'k') {
            e.preventDefault();
            const searchInput = document.getElementById('search-input');
            if (searchInput) {
                searchInput.focus();
            }
        }
        
        // Ctrl + N: Yeni ürün ekle
        if (e.ctrlKey && e.key === 'n') {
            e.preventDefault();
            window.location.href = '/add_product';
        }
        
        // Ctrl + R: Sayfayı yenile
        if (e.ctrlKey && e.key === 'r') {
            e.preventDefault();
            refreshData();
        }
    });
    
    // Escape tuşu ile modal'ları kapat
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            const openModals = document.querySelectorAll('.modal.show');
            openModals.forEach(modal => {
                const modalInstance = bootstrap.Modal.getInstance(modal);
                if (modalInstance) {
                    modalInstance.hide();
                }
            });
        }
    });
}

// Otomatik yenileme başlat
function startAutoRefresh() {
    // Her 5 dakikada bir stok verilerini kontrol et
    refreshInterval = setInterval(function() {
        checkStockLevels();
    }, 5 * 60 * 1000); // 5 dakika
}

// Otomatik yenileme durdur
function stopAutoRefresh() {
    if (refreshInterval) {
        clearInterval(refreshInterval);
    }
}

// Stok seviyelerini kontrol et
function checkStockLevels() {
    fetch('/api/check_stock')
        .then(response => response.json())
        .then(data => {
            if (data.alerts && data.alerts.length > 0) {
                data.alerts.forEach(alert => {
                    showNotification(alert.type, alert.message);
                });
            }
        })
        .catch(error => {
            console.error('Stok kontrolü hatası:', error);
        });
}

// Bildirim göster
function showNotification(type, message, duration = 5000) {
    const notification = {
        id: Date.now(),
        type: type,
        message: message,
        timestamp: new Date()
    };
    
    notifications.push(notification);
    
    // Toast bildirim oluştur
    createToast(notification);
    
    // Bildirim rozetini güncelle
    updateNotificationBadge();
    
    // Belirtilen süre sonra bildirimi kaldır
    setTimeout(() => {
        removeNotification(notification.id);
    }, duration);
}

// Toast bildirim oluştur
function createToast(notification) {
    const toastContainer = getOrCreateToastContainer();
    
    const toastEl = document.createElement('div');
    toastEl.className = `toast align-items-center text-white bg-${getBootstrapColorClass(notification.type)} border-0`;
    toastEl.setAttribute('role', 'alert');
    toastEl.setAttribute('aria-live', 'assertive');
    toastEl.setAttribute('aria-atomic', 'true');
    toastEl.setAttribute('data-notification-id', notification.id);
    
    toastEl.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                <i class="bi bi-${getIconClass(notification.type)} me-2"></i>
                ${notification.message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;
    
    toastContainer.appendChild(toastEl);
    
    const toast = new bootstrap.Toast(toastEl);
    toast.show();
    
    // Toast kapandığında bildirimi kaldır
    toastEl.addEventListener('hidden.bs.toast', function() {
        removeNotification(notification.id);
        toastEl.remove();
    });
}

// Toast container'ı al veya oluştur
function getOrCreateToastContainer() {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        container.style.zIndex = '1055';
        document.body.appendChild(container);
    }
    return container;
}

// Bootstrap renk sınıfını al
function getBootstrapColorClass(type) {
    const colorMap = {
        'success': 'success',
        'error': 'danger',
        'warning': 'warning',
        'info': 'info'
    };
    return colorMap[type] || 'info';
}

// İkon sınıfını al
function getIconClass(type) {
    const iconMap = {
        'success': 'check-circle',
        'error': 'exclamation-triangle',
        'warning': 'exclamation-triangle',
        'info': 'info-circle'
    };
    return iconMap[type] || 'info-circle';
}

// Bildirimi kaldır
function removeNotification(id) {
    notifications = notifications.filter(n => n.id !== id);
    updateNotificationBadge();
}

// Bildirim rozetini güncelle
function updateNotificationBadge() {
    const badge = document.getElementById('notification-badge');
    if (badge) {
        if (notifications.length > 0) {
            badge.textContent = notifications.length;
            badge.style.display = 'inline-block';
        } else {
            badge.style.display = 'none';
        }
    }
}

// Loading durumu göster
function showLoading(message = 'Yükleniyor...') {
    const overlay = document.createElement('div');
    overlay.className = 'loading-overlay';
    overlay.id = 'loading-overlay';
    overlay.innerHTML = `
        <div class="loading-content">
            <div class="spinner-border text-primary mb-3" role="status">
                <span class="visually-hidden">Yükleniyor...</span>
            </div>
            <p class="mb-0">${message}</p>
        </div>
    `;
    
    document.body.appendChild(overlay);
}

// Loading durumunu gizle
function hideLoading() {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        overlay.remove();
    }
}

// API çağrısı yap
async function apiCall(url, options = {}) {
    try {
        showLoading('İşlem gerçekleştiriliyor...');
        
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
            }
        };
        
        const response = await fetch(url, { ...defaultOptions, ...options });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        hideLoading();
        
        return data;
    } catch (error) {
        hideLoading();
        console.error('API çağrısı hatası:', error);
        showNotification('error', 'Bir hata oluştu. Lütfen tekrar deneyin.');
        throw error;
    }
}

// Tabloyu filtrele
function filterTable(tableId, searchTerm, columns = []) {
    const table = document.getElementById(tableId);
    if (!table) return;
    
    const rows = table.getElementsByTagName('tbody')[0].getElementsByTagName('tr');
    searchTerm = searchTerm.toLowerCase();
    
    Array.from(rows).forEach(row => {
        let found = false;
        
        if (columns.length === 0) {
            // Tüm sütunlarda ara
            const cells = row.getElementsByTagName('td');
            for (let cell of cells) {
                if (cell.textContent.toLowerCase().includes(searchTerm)) {
                    found = true;
                    break;
                }
            }
        } else {
            // Belirtilen sütunlarda ara
            columns.forEach(columnIndex => {
                const cell = row.cells[columnIndex];
                if (cell && cell.textContent.toLowerCase().includes(searchTerm)) {
                    found = true;
                }
            });
        }
        
        row.style.display = found ? '' : 'none';
    });
}

// Tabloyu sırala
function sortTable(tableId, columnIndex, direction = 'asc') {
    const table = document.getElementById(tableId);
    if (!table) return;
    
    const tbody = table.getElementsByTagName('tbody')[0];
    const rows = Array.from(tbody.getElementsByTagName('tr'));
    
    rows.sort((a, b) => {
        const aVal = a.cells[columnIndex].textContent.trim();
        const bVal = b.cells[columnIndex].textContent.trim();
        
        // Sayısal değerleri kontrol et
        const aNum = parseFloat(aVal);
        const bNum = parseFloat(bVal);
        
        if (!isNaN(aNum) && !isNaN(bNum)) {
            return direction === 'asc' ? aNum - bNum : bNum - aNum;
        } else {
            return direction === 'asc' 
                ? aVal.localeCompare(bVal, 'tr')
                : bVal.localeCompare(aVal, 'tr');
        }
    });
    
    // Sıralanmış satırları tekrar ekle
    rows.forEach(row => tbody.appendChild(row));
}

// Form validasyonu
function validateForm(formId, rules = {}) {
    const form = document.getElementById(formId);
    if (!form) return false;
    
    let isValid = true;
    
    Object.keys(rules).forEach(fieldName => {
        const field = form.querySelector(`[name="${fieldName}"]`);
        const rule = rules[fieldName];
        
        if (field) {
            // Mevcut hata mesajlarını temizle
            const existingError = field.parentNode.querySelector('.invalid-feedback');
            if (existingError) {
                existingError.remove();
            }
            field.classList.remove('is-invalid');
            
            // Validasyon kontrolü
            if (rule.required && !field.value.trim()) {
                showFieldError(field, 'Bu alan zorunludur.');
                isValid = false;
            } else if (rule.minLength && field.value.length < rule.minLength) {
                showFieldError(field, `En az ${rule.minLength} karakter olmalıdır.`);
                isValid = false;
            } else if (rule.maxLength && field.value.length > rule.maxLength) {
                showFieldError(field, `En fazla ${rule.maxLength} karakter olabilir.`);
                isValid = false;
            } else if (rule.pattern && !rule.pattern.test(field.value)) {
                showFieldError(field, rule.message || 'Geçersiz format.');
                isValid = false;
            }
        }
    });
    
    return isValid;
}

// Alan hatası göster
function showFieldError(field, message) {
    field.classList.add('is-invalid');
    
    const errorDiv = document.createElement('div');
    errorDiv.className = 'invalid-feedback';
    errorDiv.textContent = message;
    
    field.parentNode.appendChild(errorDiv);
}

// Tarih formatla
function formatDate(date, format = 'dd.mm.yyyy hh:mm') {
    const d = new Date(date);
    
    const day = String(d.getDate()).padStart(2, '0');
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const year = d.getFullYear();
    const hours = String(d.getHours()).padStart(2, '0');
    const minutes = String(d.getMinutes()).padStart(2, '0');
    
    return format
        .replace('dd', day)
        .replace('mm', month)
        .replace('yyyy', year)
        .replace('hh', hours)
        .replace('mm', minutes);
}

// Sayı formatla
function formatNumber(number, decimals = 0) {
    return new Intl.NumberFormat('tr-TR', {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals
    }).format(number);
}

// Para formatla
function formatCurrency(amount, currency = 'TRY') {
    return new Intl.NumberFormat('tr-TR', {
        style: 'currency',
        currency: currency
    }).format(amount);
}

// Clipboard'a kopyala
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(function() {
        showNotification('success', 'Panoya kopyalandı!');
    }).catch(function(err) {
        console.error('Kopyalama hatası:', err);
        showNotification('error', 'Kopyalama başarısız.');
    });
}

// Dosya indir
function downloadFile(url, filename) {
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.click();
}

// Sayfa yenilendiğinde interval'ları temizle
window.addEventListener('beforeunload', function() {
    stopAutoRefresh();
});

// Global hata yakalayıcı
window.addEventListener('error', function(e) {
    console.error('Global hata:', e.error);
    showNotification('error', 'Beklenmeyen bir hata oluştu.');
});

// Promise rejection yakalayıcı
window.addEventListener('unhandledrejection', function(e) {
    console.error('Promise rejection:', e.reason);
    showNotification('error', 'İşlem tamamlanamadı.');
});

// Debug modu için console log
if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    console.log('🚀 Inditex Stok Takip Sistemi - Debug Modu Aktif');
    console.log('📊 Mevcut bildirimler:', notifications);
}
