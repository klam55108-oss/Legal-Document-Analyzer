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
    
    // Setup cloud integrations animations
    setupIntegrationsAnimations();
    
    // Animate document cards on page load
    animateDocumentCards();
    
    // Animate flash messages
    animateFlashMessages();
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

// Setup cloud integrations animations
function setupIntegrationsAnimations() {
    // Add animations to integration cards
    const integrationCards = document.querySelectorAll('.card');
    integrationCards.forEach((card, index) => {
        card.classList.add('animated');
        card.style.animationDelay = (index * 0.1) + 's';
    });
    
    // Add connection animation for integration buttons
    const connectButtons = document.querySelectorAll('[id^="connect"]');
    connectButtons.forEach(button => {
        button.addEventListener('click', function() {
            // Show connecting animation
            const originalText = this.textContent;
            this.innerHTML = '<span class="loading-icon"></span> Connecting...';
            this.disabled = true;
            
            // Get the closest form
            const form = this.closest('form');
            if (form) {
                // Create a connection visual in the modal
                const modalContent = this.closest('.modal-content');
                if (modalContent) {
                    const connectionStatus = document.createElement('div');
                    connectionStatus.className = 'connection-status mt-3';
                    connectionStatus.innerHTML = `
                        <div class="connection-visual">
                            <div class="connection-source">
                                <i class="fas fa-laptop fa-2x"></i>
                                <span>LegalDataInsights</span>
                            </div>
                            <div class="connection-line">
                                <div class="connection-dot"></div>
                            </div>
                            <div class="connection-target">
                                <i class="fas ${getServiceIcon(this.id)} fa-2x"></i>
                                <span>${getServiceName(this.id)}</span>
                            </div>
                        </div>
                    `;
                    
                    // Add to modal
                    const modalBody = modalContent.querySelector('.modal-body');
                    if (modalBody) {
                        modalBody.appendChild(connectionStatus);
                        // Animate the connection dot
                        animateConnectionDot(connectionStatus.querySelector('.connection-dot'));
                    }
                }
            }
            
            // Simulate connection process (in a real app, this would be an actual API call)
            setTimeout(() => {
                // Reset button
                this.innerHTML = originalText;
                this.disabled = false;
                
                // Show success message
                const successMessage = document.createElement('div');
                successMessage.className = 'alert alert-success mt-3 upload-complete';
                successMessage.innerHTML = '<i class="fas fa-check-circle me-2"></i> Successfully connected! Redirecting...';
                
                // Add to modal
                const modalContent = this.closest('.modal-content');
                if (modalContent) {
                    const modalBody = modalContent.querySelector('.modal-body');
                    if (modalBody) {
                        modalBody.appendChild(successMessage);
                    }
                }
                
                // In a real app, redirect to the next page or close modal
                // For the demo, we'll just close the modal after a delay
                setTimeout(() => {
                    const modal = bootstrap.Modal.getInstance(this.closest('.modal'));
                    if (modal) {
                        modal.hide();
                    }
                }, 1500);
            }, 2500);
        });
    });
}

// Helper function to get the service icon based on button ID
function getServiceIcon(buttonId) {
    if (buttonId.includes('GoogleDrive')) return 'fa-google-drive';
    if (buttonId.includes('Dropbox')) return 'fa-dropbox';
    if (buttonId.includes('Box')) return 'fa-box';
    if (buttonId.includes('MSGraph')) return 'fa-microsoft';
    if (buttonId.includes('Airtable')) return 'fa-table';
    return 'fa-cloud';
}

// Helper function to get the service name based on button ID
function getServiceName(buttonId) {
    if (buttonId.includes('GoogleDrive')) return 'Google Drive';
    if (buttonId.includes('Dropbox')) return 'Dropbox';
    if (buttonId.includes('Box')) return 'Box';
    if (buttonId.includes('MSGraph')) return 'Microsoft 365';
    if (buttonId.includes('Airtable')) return 'Airtable';
    return 'Cloud Service';
}

// Animate the connection dot traveling from source to target
function animateConnectionDot(dot) {
    if (!dot) return;
    
    // Reset the animation
    dot.style.animation = 'none';
    dot.offsetHeight; // Trigger reflow
    
    // Start the animation
    dot.style.animation = 'moveRightWithPulse 2.5s ease-in-out infinite';
}