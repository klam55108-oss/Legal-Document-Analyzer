// Main JavaScript for the Legal Document Analyzer application

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // File upload handler
    const fileInput = document.getElementById('file');
    if (fileInput) {
        fileInput.addEventListener('change', function() {
            const fileNameField = document.querySelector('.custom-file-label');
            if (fileNameField) {
                fileNameField.textContent = this.files[0] ? this.files[0].name : 'Choose file';
            }
        });
    }
    
    // API Key copy button
    const apiKeyCopyBtn = document.getElementById('apiKeyCopy');
    if (apiKeyCopyBtn) {
        apiKeyCopyBtn.addEventListener('click', function() {
            const apiKeyInput = document.getElementById('apiKey');
            apiKeyInput.select();
            document.execCommand('copy');
            
            // Show copied message
            this.textContent = 'Copied!';
            setTimeout(() => {
                this.textContent = 'Copy';
            }, 2000);
        });
    }
    
    // Document search functionality
    const docSearchInput = document.getElementById('documentSearch');
    if (docSearchInput) {
        docSearchInput.addEventListener('keyup', function() {
            const searchTerm = this.value.toLowerCase();
            const documentRows = document.querySelectorAll('.document-row');
            
            documentRows.forEach(row => {
                const fileName = row.querySelector('.document-name').textContent.toLowerCase();
                if (fileName.includes(searchTerm)) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            });
        });
    }
    
    // Brief search functionality
    const briefSearchInput = document.getElementById('briefSearch');
    if (briefSearchInput) {
        briefSearchInput.addEventListener('keyup', function() {
            const searchTerm = this.value.toLowerCase();
            const briefRows = document.querySelectorAll('.brief-row');
            
            briefRows.forEach(row => {
                const briefTitle = row.querySelector('.brief-title').textContent.toLowerCase();
                if (briefTitle.includes(searchTerm)) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            });
        });
    }
    
    // Generate brief form validation
    const generateBriefForm = document.getElementById('generateBriefForm');
    if (generateBriefForm) {
        generateBriefForm.addEventListener('submit', function(event) {
            const focusAreas = document.getElementById('focusAreas').value;
            if (!focusAreas.trim()) {
                // It's optional, so we don't prevent submission
                console.log('No focus areas specified');
            }
            
            // Find and disable the submit button to prevent multiple submissions
            const submitButton = this.querySelector('button[type="submit"]');
            if (submitButton) {
                submitButton.disabled = true;
                submitButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Generating...';
            }
            
            // Close the modal after submission
            const modal = bootstrap.Modal.getInstance(document.getElementById('generateBriefModal'));
            if (modal) {
                modal.hide();
            }
            
            // Show a processing message
            const alertDiv = document.createElement('div');
            alertDiv.classList.add('alert', 'alert-info', 'alert-dismissible', 'fade', 'show', 'mt-3');
            alertDiv.innerHTML = `
                <strong>Generating brief...</strong> This may take a few moments.
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            `;
            document.querySelector('.tab-content').prepend(alertDiv);
        });
    }
    
    // Handle statute verification
    const verifyStatuteButtons = document.querySelectorAll('.verify-statute');
    if (verifyStatuteButtons.length > 0) {
        verifyStatuteButtons.forEach(button => {
            button.addEventListener('click', async function() {
                const statuteId = this.getAttribute('data-statute-id');
                const statusBadge = document.querySelector(`.statute-status-${statuteId}`);
                const spinner = this.querySelector('.spinner-border');
                
                // Show spinner
                spinner.classList.remove('d-none');
                this.disabled = true;
                
                try {
                    const response = await fetch(`/api/statutes/${statuteId}`, {
                        method: 'PUT',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': 'Bearer ' + document.querySelector('meta[name="api-token"]').getAttribute('content')
                        }
                    });
                    
                    const data = await response.json();
                    
                    // Update status badge
                    if (statusBadge) {
                        statusBadge.textContent = data.is_current ? 'Current' : 'Outdated';
                        statusBadge.classList.remove('bg-success', 'bg-danger');
                        statusBadge.classList.add(data.is_current ? 'bg-success' : 'bg-danger');
                    }
                    
                    // Show alert
                    const alertDiv = document.createElement('div');
                    alertDiv.classList.add('alert', data.is_current ? 'alert-success' : 'alert-warning', 'alert-dismissible', 'fade', 'show', 'mt-3');
                    alertDiv.innerHTML = `
                        Statute verification complete: ${data.reference} is ${data.is_current ? 'current' : 'outdated'}.
                        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                    `;
                    document.querySelector('.statute-alerts').appendChild(alertDiv);
                    
                } catch (error) {
                    console.error('Error verifying statute:', error);
                    // Show error alert
                    const alertDiv = document.createElement('div');
                    alertDiv.classList.add('alert', 'alert-danger', 'alert-dismissible', 'fade', 'show', 'mt-3');
                    alertDiv.innerHTML = `
                        Error verifying statute: ${error.message}
                        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                    `;
                    document.querySelector('.statute-alerts').appendChild(alertDiv);
                } finally {
                    // Hide spinner
                    spinner.classList.add('d-none');
                    this.disabled = false;
                }
            });
        });
    }
    
    // Markdown rendering (if needed)
    const markdownContainers = document.querySelectorAll('.markdown-content');
    if (markdownContainers.length > 0 && typeof marked !== 'undefined') {
        markdownContainers.forEach(container => {
            const markdown = container.getAttribute('data-markdown');
            if (markdown) {
                container.innerHTML = marked(markdown);
            }
        });
    }
});

// API Request Helper
async function apiRequest(endpoint, method = 'GET', data = null) {
    const headers = {
        'Content-Type': 'application/json'
    };
    
    // Add API token if available
    const apiTokenMeta = document.querySelector('meta[name="api-token"]');
    if (apiTokenMeta) {
        headers['Authorization'] = 'Bearer ' + apiTokenMeta.getAttribute('content');
    }
    
    const options = {
        method: method,
        headers: headers
    };
    
    if (data && (method === 'POST' || method === 'PUT')) {
        options.body = JSON.stringify(data);
    }
    
    try {
        const response = await fetch(endpoint, options);
        return await response.json();
    } catch (error) {
        console.error('API Request Error:', error);
        throw error;
    }
}
