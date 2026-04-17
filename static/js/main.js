/**
 * YouTube to MP3 Converter - Main JavaScript File
 * Handles all frontend functionality including URL validation, 
 * conversion process, and user interactions
 */

// Global variables
let currentConversionId = null;
let statusCheckInterval = null;

// DOM Elements
const elements = {
    converterForm: document.getElementById('converterForm'),
    youtubeUrl: document.getElementById('youtubeUrl'),
    validateBtn: document.getElementById('validateBtn'),
    videoInfo: document.getElementById('videoInfo'),
    videoThumbnail: document.getElementById('videoThumbnail'),
    videoTitle: document.getElementById('videoTitle'),
    videoUploader: document.getElementById('videoUploader'),
    videoDuration: document.getElementById('videoDuration'),
    estimatedSize: document.getElementById('estimatedSize'),
    downloadFormat: document.getElementById('downloadFormat'),
    qualityLabel: document.getElementById('qualityLabel'),
    audioQuality: document.getElementById('audioQuality'),
    cropSection: document.getElementById('cropSection'),
    cropStart: document.getElementById('cropStart'),
    cropEnd: document.getElementById('cropEnd'),
    convertBtn: document.getElementById('convertBtn'),
    loadingSection: document.getElementById('loadingSection'),
    loadingMessage: document.getElementById('loadingMessage'),
    progressBar: document.getElementById('progressBar'),
    downloadSection: document.getElementById('downloadSection'),
    downloadBtn: document.getElementById('downloadBtn'),
    errorSection: document.getElementById('errorSection'),
    errorMessage: document.getElementById('errorMessage'),
    themeToggle: document.getElementById('themeToggle'),
    themeIcon: document.getElementById('themeIcon')
};

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
    setupEventListeners();
    loadThemePreference();
});

/**
 * Initialize the application
 */
function initializeApp() {
    console.log('YouTube to MP3 Converter initialized');
    
    // Set initial theme
    const isDark = localStorage.getItem('theme') !== 'light';
    if (isDark) {
        document.body.classList.add('dark-mode');
        elements.themeIcon.className = 'fas fa-sun';
    } else {
        document.body.classList.add('light-mode');
        elements.themeIcon.className = 'fas fa-moon';
    }
    
    // Focus on URL input
    elements.youtubeUrl.focus();
}

/**
 * Setup all event listeners
 */
function setupEventListeners() {
    // Form submission
    elements.converterForm.addEventListener('submit', handleFormSubmit);
    
    // URL input changes
    elements.youtubeUrl.addEventListener('input', handleUrlInput);
    
    // Convert button
    elements.convertBtn.addEventListener('click', startConversion);
    
    // Download button
    elements.downloadBtn.addEventListener('click', downloadFile);
    
    // Theme toggle
    elements.themeToggle.addEventListener('click', toggleTheme);
    
    // Quality selection
    elements.audioQuality.addEventListener('change', updateEstimatedSize);
    
    // Format selection
    if(elements.downloadFormat) {
        elements.downloadFormat.addEventListener('change', handleFormatChange);
    }
    
    // Paste event for URL input
    elements.youtubeUrl.addEventListener('paste', function(e) {
        setTimeout(() => {
            handleUrlInput();
        }, 100);
    });
}

/**
 * Handle form submission
 */
function handleFormSubmit(e) {
    e.preventDefault();
    
    const url = elements.youtubeUrl.value.trim();
    
    if (!url) {
        showError('Please enter a YouTube URL');
        return;
    }
    
    // Reset previous states
    hideAllSections();
    showLoading('Validating URL...');
    
    // Reset crop inputs
    if(elements.cropStart) elements.cropStart.value = '';
    if(elements.cropEnd) elements.cropEnd.value = '';
    if(elements.downloadFormat) {
        elements.downloadFormat.value = 'mp3';
        handleFormatChange();
    }

    // Validate URL
    validateUrl(url);
}

/**
 * Handle URL input changes
 */
function handleUrlInput() {
    const url = elements.youtubeUrl.value.trim();
    
    // Clear previous error
    hideError();
    
    // Clear video info if URL is empty
    if (!url) {
        elements.videoInfo.classList.add('d-none');
    }
}

/**
 * Handle Format change
 */
function handleFormatChange() {
    const format = elements.downloadFormat.value;
    
    if (format === 'mp4') {
        elements.cropSection.classList.add('d-none');
        elements.qualityLabel.textContent = 'Video Quality';
        elements.audioQuality.innerHTML = `
            <option value="360p">360p (Data Saver)</option>
            <option value="720p" selected>720p (High Quality)</option>
            <option value="1080p">1080p (Premium Quality)</option>
        `;
        elements.convertBtn.innerHTML = '<i class="fas fa-download me-2"></i>Download MP4';
    } else {
        elements.cropSection.classList.remove('d-none');
        elements.qualityLabel.textContent = 'Audio Quality';
        elements.audioQuality.innerHTML = `
            <option value="128k">128 kbps (Good Quality)</option>
            <option value="192k" selected>192 kbps (High Quality)</option>
            <option value="320k">320 kbps (Premium Quality)</option>
        `;
        elements.convertBtn.innerHTML = '<i class="fas fa-download me-2"></i>Convert to MP3';
    }
    updateEstimatedSize();
}

/**
 * Validate YouTube URL
 */
function validateUrl(url) {
    fetch('/validate_url', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url: url })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            displayVideoInfo(data);
        } else {
            showError(data.error || 'Invalid YouTube URL');
            hideAllSections();
        }
    })
    .catch(error => {
        console.error('Validation error:', error);
        showError('Failed to validate URL. Please try again.');
        hideAllSections();
    });
}

/**
 * Display video information
 */
function displayVideoInfo(data) {
    elements.videoThumbnail.src = data.thumbnail || 'https://via.placeholder.com/320x180?text=No+Thumbnail';
    elements.videoTitle.textContent = data.title || 'Unknown Title';
    elements.videoUploader.textContent = data.uploader || 'Unknown Uploader';
    elements.videoDuration.textContent = formatDuration(data.duration);
    
    // Update estimated size
    updateEstimatedSize();
    
    // Show video info section
    elements.videoInfo.classList.remove('d-none');
    elements.loadingSection.classList.add('d-none');
    
    // Scroll to video info
    setTimeout(() => {
        elements.videoInfo.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }, 100);
}

/**
 * Update estimated file size
 */
function updateEstimatedSize() {
    const quality = elements.audioQuality.value;
    const duration = elements.videoDuration.textContent;
    
    // Simple size estimation (this would be more accurate with actual data)
    const sizeEstimates = {
        '128k': '~3 MB',
        '192k': '~5 MB', 
        '320k': '~8 MB'
    };
    
    elements.estimatedSize.textContent = sizeEstimates[quality] || 'Unknown';
}

/**
 * Parses time string (MM:SS) into seconds. Return null if invalid.
 */
function parseTimeToSeconds(timeStr) {
    if (!timeStr) return null;
    const parts = timeStr.split(':');
    if (parts.length === 1) {
        // assume seconds
        if (!isNaN(parts[0]) && parts[0].trim() !== '') return parseInt(parts[0], 10);
    } else if (parts.length === 2) {
        // MM:SS
        const m = parseInt(parts[0], 10);
        const s = parseInt(parts[1], 10);
        if (!isNaN(m) && !isNaN(s)) return m * 60 + s;
    } else if (parts.length === 3) {
        // HH:MM:SS
        const h = parseInt(parts[0], 10);
        const m = parseInt(parts[1], 10);
        const s = parseInt(parts[2], 10);
        if (!isNaN(h) && !isNaN(m) && !isNaN(s)) return h * 3600 + m * 60 + s;
    }
    return null;
}

/**
 * Start conversion process
 */
function startConversion() {
    const url = elements.youtubeUrl.value.trim();
    const quality = elements.audioQuality.value;
    const format = elements.downloadFormat ? elements.downloadFormat.value : 'mp3';
    
    let startTime = null;
    let endTime = null;

    if (format === 'mp3' && elements.cropStart && elements.cropEnd) {
        const startStr = elements.cropStart.value.trim();
        const endStr = elements.cropEnd.value.trim();
        
        if (startStr) {
            startTime = parseTimeToSeconds(startStr);
            if (startTime === null) {
                showError('Invalid Start Time. Please use MM:SS or seconds.');
                return;
            }
        }
        
        if (endStr) {
            endTime = parseTimeToSeconds(endStr);
            if (endTime === null) {
                showError('Invalid End Time. Please use MM:SS or seconds.');
                return;
            }
        }
        
        if (startTime !== null && endTime !== null && startTime >= endTime) {
            showError('Start time must be before end time.');
            return;
        }
    }

    if (!url) {
        showError('Please enter a YouTube URL');
        return;
    }
    
    // Show loading section
    elements.videoInfo.classList.add('d-none');
    elements.downloadSection.classList.add('d-none');
    showLoading(format === 'mp4' ? 'Starting video download...' : 'Starting conversion...');
    
    // Start conversion
    fetch('/convert', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
            url: url, 
            quality: quality,
            format: format,
            start_time: startTime,
            end_time: endTime
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            currentConversionId = data.conversion_id;
            startStatusChecking();
        } else {
            showError(data.error || 'Conversion failed');
            hideAllSections();
        }
    })
    .catch(error => {
        console.error('Conversion error:', error);
        showError('Failed to start conversion. Please try again.');
        hideAllSections();
    });
}

/**
 * Start checking conversion status
 */
function startStatusChecking() {
    if (!currentConversionId) return;
    
    statusCheckInterval = setInterval(() => {
        checkConversionStatus();
    }, 2000); // Check every 2 seconds
}

/**
 * Check conversion status
 */
function checkConversionStatus() {
    if (!currentConversionId) return;
    
    fetch(`/status/${currentConversionId}`)
    .then(response => response.json())
    .then(data => {
        updateProgress(data);
        
        if (data.status === 'completed') {
            clearInterval(statusCheckInterval);
            showDownload();
        } else if (data.status === 'error') {
            clearInterval(statusCheckInterval);
            showError(data.message || 'Conversion failed');
            hideAllSections();
        }
    })
    .catch(error => {
        console.error('Status check error:', error);
        // Continue checking on error
    });
}

/**
 * Update progress display
 */
function updateProgress(data) {
    if (data.progress !== undefined) {
        elements.progressBar.style.width = data.progress + '%';
    }
    
    if (data.message) {
        elements.loadingMessage.textContent = data.message;
    }
}

/**
 * Show download section
 */
function showDownload() {
    elements.loadingSection.classList.add('d-none');
    elements.downloadSection.classList.remove('d-none');
    
    const format = elements.downloadFormat ? elements.downloadFormat.value : 'mp3';
    const dlBtnText = elements.downloadSection.querySelector('h5');
    const dlBtnSub = elements.downloadSection.querySelector('p');
    if (dlBtnText) dlBtnText.textContent = format === 'mp4' ? 'Download Complete!' : 'Conversion Complete!';
    if (dlBtnSub) dlBtnSub.textContent = format === 'mp4' ? 'Your MP4 file is ready for download' : 'Your MP3 file is ready for download';
    
    elements.downloadBtn.innerHTML = `<i class="fas fa-download me-2"></i>Download ${format.toUpperCase()}`;

    // Scroll to download section
    setTimeout(() => {
        elements.downloadSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }, 100);
}

/**
 * Download the converted file
 */
function downloadFile() {
    if (!currentConversionId) {
        showError('No file to download');
        return;
    }
    
    // Create download link
    const downloadUrl = `/download/${currentConversionId}`;
    
    // Trigger download
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = '';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    // Show success message
    showSuccess('Download started! Check your downloads folder.');
}

/**
 * Show loading section
 */
function showLoading(message) {
    elements.loadingMessage.textContent = message || 'Loading...';
    elements.loadingSection.classList.remove('d-none');
    elements.errorSection.classList.add('d-none');
    elements.videoInfo.classList.add('d-none');
    elements.downloadSection.classList.add('d-none');
}

/**
 * Hide all sections except the main form
 */
function hideAllSections() {
    elements.videoInfo.classList.add('d-none');
    elements.loadingSection.classList.add('d-none');
    elements.downloadSection.classList.add('d-none');
    elements.errorSection.classList.add('d-none');
}

/**
 * Show error message
 */
function showError(message) {
    elements.errorMessage.textContent = message;
    elements.errorSection.classList.remove('d-none');
    elements.loadingSection.classList.add('d-none');
    
    // Auto-hide after 5 seconds
    setTimeout(() => {
        hideError();
    }, 5000);
}

/**
 * Hide error message
 */
function hideError() {
    elements.errorSection.classList.add('d-none');
}

/**
 * Show success message
 */
function showSuccess(message) {
    // Create temporary success alert
    const alert = document.createElement('div');
    alert.className = 'alert alert-success position-fixed';
    alert.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    alert.innerHTML = `<i class="fas fa-check-circle me-2"></i>${message}`;
    
    document.body.appendChild(alert);
    
    // Remove after 3 seconds
    setTimeout(() => {
        document.body.removeChild(alert);
    }, 3000);
}

/**
 * Toggle theme
 */
function toggleTheme() {
    const isDark = document.body.classList.contains('dark-mode');
    
    if (isDark) {
        document.body.classList.remove('dark-mode');
        document.body.classList.add('light-mode');
        elements.themeIcon.className = 'fas fa-moon';
        localStorage.setItem('theme', 'light');
    } else {
        document.body.classList.remove('light-mode');
        document.body.classList.add('dark-mode');
        elements.themeIcon.className = 'fas fa-sun';
        localStorage.setItem('theme', 'dark');
    }
}

/**
 * Load theme preference
 */
function loadThemePreference() {
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'light') {
        document.body.classList.remove('dark-mode');
        document.body.classList.add('light-mode');
        elements.themeIcon.className = 'fas fa-moon';
    }
}

/**
 * Format duration in seconds to MM:SS or HH:MM:SS
 */
function formatDuration(seconds) {
    if (!seconds || seconds <= 0) return '0:00';
    
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    
    if (hours > 0) {
        return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    } else {
        return `${minutes}:${secs.toString().padStart(2, '0')}`;
    }
}

/**
 * Debounce function for input validation
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Handle keyboard shortcuts
 */
document.addEventListener('keydown', function(e) {
    // Ctrl/Cmd + Enter to validate URL
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        if (elements.youtubeUrl.value.trim()) {
            handleFormSubmit(e);
        }
    }
    
    // Escape to clear form
    if (e.key === 'Escape') {
        if (elements.youtubeUrl.value) {
            elements.youtubeUrl.value = '';
            hideAllSections();
            elements.youtubeUrl.focus();
        }
    }
});

/**
 * Handle online/offline status
 */
window.addEventListener('online', function() {
    showSuccess('Connection restored!');
});

window.addEventListener('offline', function() {
    showError('No internet connection. Please check your network.');
});

/**
 * Prevent common form spam
 */
elements.youtubeUrl.addEventListener('paste', function(e) {
    // Strip any HTML tags from pasted content
    const text = e.clipboardData.getData('text/plain');
    e.preventDefault();
    document.execCommand('insertText', false, text);
});

/**
 * Utility function to validate YouTube URL format
 */
function isValidYouTubeUrl(url) {
    const patterns = [
        /^https?:\/\/(www\.)?youtube\.com\/watch\?v=[\w-]+/,
        /^https?:\/\/(www\.)?youtu\.be\/[\w-]+/,
        /^https?:\/\/(www\.)?youtube\.com\/embed\/[\w-]+/,
        /^https?:\/\/(www\.)?youtube\.com\/shorts\/[\w-]+/
    ];
    
    return patterns.some(pattern => pattern.test(url));
}

/**
 * Auto-clear conversion status
 */
setInterval(() => {
    // Clean up old status intervals if needed
    if (statusCheckInterval && currentConversionId) {
        // Could implement cleanup logic here
    }
}, 60000); // Every minute

// Add some console art for developers
console.log(`
╔══════════════════════════════════════╗
║       YouTube to MP3 Converter       ║
║           Version 1.0.0              ║
║                                      ║
║  Built with ❤️ using Flask & JS      ║
╚══════════════════════════════════════╝
`);