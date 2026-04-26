// Character count for textarea
const textarea = document.getElementById('inputText');
const charCount = document.getElementById('charCount');

if (textarea) {
    textarea.addEventListener('input', function() {
        const length = this.value.length;
        charCount.textContent = length;
        
        if (length > 500) {
            this.value = this.value.substring(0, 500);
            charCount.textContent = 500;
        }
        
        // Visual feedback
        if (length > 400) {
            charCount.style.color = '#e53e3e';
        } else if (length > 300) {
            charCount.style.color = '#ed8936';
        } else {
            charCount.style.color = '#a0aec0';
        }
    });
}

// Form submission with loading state
const form = document.getElementById('predictionForm');
const loading = document.getElementById('loading');

if (form) {
    form.addEventListener('submit', function() {
        if (loading) {
            loading.classList.remove('hidden');
        }
        
        // Disable submit button
        const submitBtn = form.querySelector('button[type="submit"]');
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Analyzing...';
        }
    });
}

// Clear form function
function clearForm() {
    if (textarea) {
        textarea.value = '';
        charCount.textContent = '0';
        charCount.style.color = '#a0aec0';
        textarea.focus();
    }
    
    // Hide result section
    const resultSection = document.getElementById('resultSection');
    if (resultSection) {
        resultSection.classList.add('hidden');
    }
    
    // Re-enable submit button
    if (form) {
        const submitBtn = form.querySelector('button[type="submit"]');
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<i class="fas fa-magic"></i> Analyze Sentiment';
        }
    }
}

// Animate progress bars on page load
document.addEventListener('DOMContentLoaded', function() {
    const progressFills = document.querySelectorAll('.progress-fill');
    progressFills.forEach(fill => {
        const width = fill.style.width;
        fill.style.width = '0%';
        setTimeout(() => {
            fill.style.width = width;
        }, 100);
    });
});

// Add keyboard shortcut (Ctrl+Enter to submit)
if (textarea) {
    textarea.addEventListener('keydown', function(e) {
        if (e.ctrlKey && e.key === 'Enter') {
            form.dispatchEvent(new Event('submit'));
        }
    });
}

// YouTube form handling
const youtubeForm = document.getElementById('youtubeForm');
const youtubeLoading = document.getElementById('youtubeLoading');

if (youtubeForm) {
    youtubeForm.addEventListener('submit', function() {
        if (youtubeLoading) {
            youtubeLoading.classList.remove('hidden');
        }
        
        // Disable submit button
        const submitBtn = youtubeForm.querySelector('button[type="submit"]');
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Fetching...';
        }
    });
}

// Clear YouTube form
function clearYoutubeForm() {
    const videoUrl = document.getElementById('videoUrl');
    if (videoUrl) {
        videoUrl.value = '';
        videoUrl.focus();
    }
    
    // Hide result section
    const youtubeResultSection = document.getElementById('youtubeResultSection');
    if (youtubeResultSection) {
        youtubeResultSection.classList.add('hidden');
    }
    
    // Re-enable submit button
    if (youtubeForm) {
        const submitBtn = youtubeForm.querySelector('button[type="submit"]');
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<i class="fab fa-youtube"></i> Analyze Comments';
        }
    }
    
    // Hide loading
    if (youtubeLoading) {
        youtubeLoading.classList.add('hidden');
    }
}
