// Document Processing Animations
document.addEventListener('DOMContentLoaded', function() {
    // Apply processing animations to badges
    const processingBadges = document.querySelectorAll('.badge.bg-warning');
    processingBadges.forEach(badge => {
        if (badge.textContent.trim() === 'Processing') {
            badge.classList.add('processing-badge');
        }
    });

    // Apply animation to document status indicators
    setupDocumentStatusIndicators();
    
    // Setup button animations
    setupButtonAnimations();
    
    // Setup file upload animations
    setupFileUploadAnimations();
    
    // Setup brief generation animations
    setupBriefGenerationAnimations();
});

// Add animated status indicators to document statuses
function setupDocumentStatusIndicators() {
    // Find all status badges and convert them to animated indicators
    const statusBadges = document.querySelectorAll('td .badge');
    statusBadges.forEach(badge => {
        const status = badge.textContent.trim();
        const row = badge.closest('tr');
        
        if (status === 'Processing') {
            badge.innerHTML = `<span class="loading-icon"></span> ${status}`;
            badge.classList.add('processing-badge');
            
            // Add a subtle background pulsing to the entire row
            row.classList.add('processing-row');
            row.style.animation = 'processingPulse 3s infinite ease-in-out';
            row.style.backgroundColor = 'rgba(var(--bs-warning-rgb), 0.05)';
        } 
        else if (status === 'Processed') {
            // Add a subtle animation when a document is processed
            badge.classList.add('fade-in');
        }
    });
}

// Setup button ripple and hover effects
function setupButtonAnimations() {
    // Add animation classes to action buttons
    const actionButtons = document.querySelectorAll('.btn');
    actionButtons.forEach(button => {
        if (!button.classList.contains('btn-close')) {
            button.classList.add('btn-animated');
        }
    });
    
    // Add special animations to document action buttons
    const documentActionButtons = document.querySelectorAll('.document-actions .btn, .btn-group .btn');
    documentActionButtons.forEach(button => {
        button.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-2px)';
            this.style.transition = 'transform 0.2s ease';
        });
        
        button.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
        });
    });
}

// Setup file upload animations
function setupFileUploadAnimations() {
    const fileInput = document.getElementById('file');
    const uploadArea = document.querySelector('.upload-area');
    
    if (fileInput && uploadArea) {
        // Create upload progress elements
        const progressContainer = document.createElement('div');
        progressContainer.className = 'upload-progress d-none';
        progressContainer.innerHTML = `
            <div class="upload-progress-bar" style="width: 0%"></div>
        `;
        uploadArea.appendChild(progressContainer);
        
        // Add a file icon that changes based on file type
        const fileIcon = document.querySelector('.upload-icon');
        
        fileInput.addEventListener('change', function(e) {
            if (this.files && this.files[0]) {
                // Show file name
                const fileName = this.files[0].name;
                const fileNameDisplay = uploadArea.querySelector('h5') || document.createElement('h5');
                fileNameDisplay.textContent = fileName;
                
                // Animate the upload area
                uploadArea.classList.add('active');
                
                // Change icon based on file type
                if (fileName.match(/\.(pdf)$/i)) {
                    fileIcon.className = 'fas fa-file-pdf upload-icon';
                } else if (fileName.match(/\.(docx|doc)$/i)) {
                    fileIcon.className = 'fas fa-file-word upload-icon';
                } else if (fileName.match(/\.(txt)$/i)) {
                    fileIcon.className = 'fas fa-file-alt upload-icon';
                }
                
                // Show progress bar and simulate upload progress
                simulateUploadProgress(progressContainer.querySelector('.upload-progress-bar'), progressContainer);
            }
        });
        
        // Handle drag and drop animations
        uploadArea.addEventListener('dragover', function(e) {
            e.preventDefault();
            this.classList.add('active');
        });
        
        uploadArea.addEventListener('dragleave', function(e) {
            e.preventDefault();
            this.classList.remove('active');
        });
        
        uploadArea.addEventListener('drop', function(e) {
            e.preventDefault();
            this.classList.add('active');
            
            if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                fileInput.files = e.dataTransfer.files;
                const event = new Event('change');
                fileInput.dispatchEvent(event);
            }
        });
    }
}

// Simulate upload progress for better user feedback
function simulateUploadProgress(progressBar, container) {
    if (!progressBar || !container) return;
    
    // Make the progress container visible
    container.classList.remove('d-none');
    
    let width = 0;
    const interval = setInterval(function() {
        if (width >= 90) {
            clearInterval(interval);
        } else {
            width += Math.random() * 10;
            progressBar.style.width = Math.min(width, 90) + '%';
        }
    }, 300);
    
    // Listen for form submission to complete the progress
    const form = container.closest('form');
    if (form) {
        form.addEventListener('submit', function() {
            clearInterval(interval);
            progressBar.style.width = '100%';
            
            // Add upload complete animation
            setTimeout(() => {
                const completeIcon = document.createElement('div');
                completeIcon.className = 'upload-complete text-center mt-3';
                completeIcon.innerHTML = '<i class="fas fa-check-circle text-success fa-2x"></i><p class="mt-2">Upload Complete! Processing document...</p>';
                container.parentNode.appendChild(completeIcon);
            }, 500);
        }, {once: true});
    }
}

// Setup brief generation animations
function setupBriefGenerationAnimations() {
    // Add animation to brief generation buttons and forms
    const briefForms = document.querySelectorAll('#generateBriefForm');
    
    briefForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            // Find the submit button and show generating animation
            const submitBtn = this.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.innerHTML = '<span class="loading-icon"></span> Generating...';
                submitBtn.disabled = true;
            }

            // Add processing steps visual
            const modalBody = this.querySelector('.modal-body');
            if (modalBody) {
                // Create processing steps
                const stepsContainer = document.createElement('div');
                stepsContainer.className = 'processing-steps mt-4';
                stepsContainer.innerHTML = `
                    <div class="processing-step active" id="step1">
                        <div class="processing-step-icon">1</div>
                        <div class="processing-step-label">Analyzing</div>
                    </div>
                    <div class="processing-step" id="step2">
                        <div class="processing-step-icon">2</div>
                        <div class="processing-step-label">Extracting</div>
                    </div>
                    <div class="processing-step" id="step3">
                        <div class="processing-step-icon">3</div>
                        <div class="processing-step-label">Drafting</div>
                    </div>
                    <div class="processing-step" id="step4">
                        <div class="processing-step-icon">4</div>
                        <div class="processing-step-label">Finalizing</div>
                    </div>
                `;
                
                modalBody.appendChild(stepsContainer);
                
                // Animate the steps
                animateBriefGenerationSteps();
            }
        });
    });
}

// Animate brief generation steps
function animateBriefGenerationSteps() {
    const steps = ['step1', 'step2', 'step3', 'step4'];
    let currentStep = 0;
    
    const interval = setInterval(() => {
        if (currentStep > 0) {
            // Mark previous step as completed
            const prevStep = document.getElementById(steps[currentStep - 1]);
            if (prevStep) {
                prevStep.classList.remove('active');
                prevStep.classList.add('completed');
            }
        }
        
        if (currentStep < steps.length) {
            // Activate current step
            const step = document.getElementById(steps[currentStep]);
            if (step) {
                step.classList.add('active');
            }
            currentStep++;
        } else {
            clearInterval(interval);
            // Brief generation is complete, will redirect to the brief page
        }
    }, 1500);
}

// Animate document cards on page load
function animateDocumentCards() {
    const cards = document.querySelectorAll('.card');
    cards.forEach((card, index) => {
        card.classList.add('animated');
        card.style.animationDelay = (index * 0.1) + 's';
    });
}

// Animate flash messages
function animateFlashMessages() {
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach((alert, index) => {
        alert.style.animation = 'fadeInUp 0.5s ease-out ' + (index * 0.1) + 's';
        alert.style.opacity = '0';
        alert.style.animationFillMode = 'forwards';
    });
}