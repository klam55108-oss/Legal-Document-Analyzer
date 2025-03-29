// Legal Document Analyzer - Word Add-in JavaScript

// Global variables
let apiUrl = '';
let apiKey = '';
let documentId = null;
let currentBrief = null;

// Initialize Office.js
Office.onReady(function(info) {
    // Initialize Fabric UI components
    initFabricUI();
    
    // Initialize event handlers
    initEventHandlers();
    
    // Load settings
    loadSettings();
    
    // Show appropriate status message
    updateStatusMessage('Ready to analyze your document.', 'info');
});

// Initialize Fabric UI components
function initFabricUI() {
    // Initialize Pivot (Tabs)
    var pivotElements = document.querySelectorAll(".ms-Pivot");
    for (var i = 0; i < pivotElements.length; i++) {
        new fabric['Pivot'](pivotElements[i]);
    }
    
    // Initialize Spinner
    var spinnerElements = document.querySelectorAll(".ms-Spinner");
    for (var i = 0; i < spinnerElements.length; i++) {
        new fabric['Spinner'](spinnerElements[i]);
    }
    
    // Initialize TextField
    var textFieldElements = document.querySelectorAll(".ms-TextField");
    for (var i = 0; i < textFieldElements.length; i++) {
        new fabric['TextField'](textFieldElements[i]);
    }
    
    // Initialize MessageBar
    var messageBarElements = document.querySelectorAll(".ms-MessageBar");
    for (var i = 0; i < messageBarElements.length; i++) {
        new fabric['MessageBar'](messageBarElements[i]);
    }
}

// Initialize event handlers
function initEventHandlers() {
    // Tab switching
    document.getElementById('appTabs').addEventListener('click', function(event) {
        if (event.target.classList.contains('ms-Pivot-link')) {
            showTabContent(event.target.getAttribute('data-content'));
        }
    });
    
    // Analyze button
    document.getElementById('analyzeButton').addEventListener('click', analyzeDocument);
    
    // Generate brief button
    document.getElementById('generateBriefButton').addEventListener('click', generateBrief);
    
    // Insert brief button
    document.getElementById('insertBriefButton').addEventListener('click', insertBrief);
    
    // Validate statutes button
    document.getElementById('validateStatutesButton').addEventListener('click', validateStatutes);
    
    // Save settings button
    document.getElementById('saveSettingsButton').addEventListener('click', saveSettings);
}

// Show tab content
function showTabContent(tabName) {
    // Hide all tab content
    var tabContents = document.querySelectorAll('.ms-Pivot-content');
    for (var i = 0; i < tabContents.length; i++) {
        tabContents[i].style.display = 'none';
    }
    
    // Show selected tab content
    var selectedContent = document.querySelector('.ms-Pivot-content[data-content="' + tabName + '"]');
    if (selectedContent) {
        selectedContent.style.display = 'block';
    }
}

// Update status message
function updateStatusMessage(message, type = 'info') {
    var statusMessage = document.getElementById('statusMessage');
    var messageText = statusMessage.querySelector('.ms-MessageBar-text');
    
    // Update message text
    messageText.textContent = message;
    
    // Update message type
    statusMessage.className = 'ms-MessageBar';
    
    // Add appropriate style based on type
    switch (type) {
        case 'success':
            statusMessage.classList.add('ms-MessageBar--success');
            break;
        case 'error':
            statusMessage.classList.add('ms-MessageBar--error');
            break;
        case 'warning':
            statusMessage.classList.add('ms-MessageBar--warning');
            break;
        default:
            statusMessage.classList.add('ms-MessageBar--info');
            break;
    }
}

// Show loading overlay
function showLoading(message = 'Processing...') {
    document.querySelector('.loading-text').textContent = message;
    document.getElementById('loadingOverlay').style.display = 'flex';
}

// Hide loading overlay
function hideLoading() {
    document.getElementById('loadingOverlay').style.display = 'none';
}

// Load settings from storage
function loadSettings() {
    // Try to load from localStorage
    try {
        apiUrl = localStorage.getItem('legalAnalyzer_apiUrl') || '';
        apiKey = localStorage.getItem('legalAnalyzer_apiKey') || '';
        
        // Update form fields
        document.getElementById('apiUrl').value = apiUrl;
        document.getElementById('apiKey').value = apiKey;
        
        return apiUrl && apiKey;
    } catch (error) {
        console.error('Error loading settings:', error);
        return false;
    }
}

// Save settings to storage
function saveSettings() {
    // Get values from form
    apiUrl = document.getElementById('apiUrl').value.trim();
    apiKey = document.getElementById('apiKey').value.trim();
    
    // Validate
    if (!apiUrl) {
        updateStatusMessage('Please enter a valid API URL.', 'error');
        return;
    }
    
    if (!apiKey) {
        updateStatusMessage('Please enter a valid API Key.', 'error');
        return;
    }
    
    // Save to localStorage
    try {
        localStorage.setItem('legalAnalyzer_apiUrl', apiUrl);
        localStorage.setItem('legalAnalyzer_apiKey', apiKey);
        
        updateStatusMessage('Settings saved successfully!', 'success');
        return true;
    } catch (error) {
        console.error('Error saving settings:', error);
        updateStatusMessage('Error saving settings: ' + error.message, 'error');
        return false;
    }
}

// Check if settings are configured
function checkSettings() {
    if (!apiUrl || !apiKey) {
        updateStatusMessage('Please configure your API settings first.', 'warning');
        
        // Switch to settings tab
        document.getElementById('settingsTab').click();
        return false;
    }
    
    return true;
}

// Analyze the current document
function analyzeDocument() {
    // Check settings
    if (!checkSettings()) {
        return;
    }
    
    // Show loading overlay
    showLoading('Analyzing document...');
    
    // Get the document as text
    Office.context.document.getFileAsync(Office.FileType.Text, { sliceSize: 65536 }, function(result) {
        if (result.status === Office.AsyncResultStatus.Succeeded) {
            var file = result.value;
            
            // Read slices of the file
            var documentContent = '';
            var sliceCount = file.sliceCount;
            var slicesReceived = 0;
            
            // Read each slice
            file.getSliceAsync(0, function handleSlice(result) {
                if (result.status === Office.AsyncResultStatus.Succeeded) {
                    var slice = result.value;
                    documentContent += slice.data;
                    slicesReceived++;
                    
                    // If all slices received, process the document
                    if (slicesReceived === sliceCount) {
                        // Close the file
                        file.closeAsync(function() {
                            // Create a File object from the content
                            var docBlob = new Blob([documentContent], { type: 'text/plain' });
                            var formData = new FormData();
                            formData.append('file', docBlob, 'document.txt');
                            
                            // Send to API
                            fetch(apiUrl + '/api/documents', {
                                method: 'POST',
                                headers: {
                                    'X-API-Key': apiKey
                                },
                                body: formData
                            })
                            .then(response => {
                                if (!response.ok) {
                                    throw new Error('API request failed: ' + response.status);
                                }
                                return response.json();
                            })
                            .then(data => {
                                // Hide loading overlay
                                hideLoading();
                                
                                // Store document ID
                                documentId = data.id;
                                
                                // Display analysis results
                                displayAnalysisResults(data);
                                
                                // Update status
                                updateStatusMessage('Document analyzed successfully!', 'success');
                            })
                            .catch(error => {
                                // Hide loading overlay
                                hideLoading();
                                
                                // Show error
                                console.error('Error analyzing document:', error);
                                updateStatusMessage('Error analyzing document: ' + error.message, 'error');
                            });
                        });
                    } else {
                        // Get the next slice
                        file.getSliceAsync(slicesReceived, handleSlice);
                    }
                } else {
                    // Error getting slice
                    file.closeAsync();
                    hideLoading();
                    updateStatusMessage('Error reading document: ' + result.error.message, 'error');
                }
            });
        } else {
            // Error getting file
            hideLoading();
            updateStatusMessage('Error accessing document: ' + result.error.message, 'error');
        }
    });
}

// Display analysis results
function displayAnalysisResults(data) {
    // Show results section
    document.getElementById('analysisResults').style.display = 'block';
    
    // Display document info
    var documentInfoDiv = document.getElementById('documentInfo');
    documentInfoDiv.innerHTML = `
        <div><strong>Document ID:</strong> ${data.id}</div>
        <div><strong>Original Filename:</strong> ${data.original_filename || 'Unknown'}</div>
        <div><strong>File Size:</strong> ${Math.round(data.file_size / 1024)} KB</div>
        <div><strong>Content Type:</strong> ${data.content_type}</div>
        <div><strong>Uploaded:</strong> ${new Date(data.uploaded_at).toLocaleString()}</div>
    `;
    
    // Display statutes
    var statutesListDiv = document.getElementById('statutesList');
    
    if (data.statutes && data.statutes.length > 0) {
        var statutesHtml = '';
        
        data.statutes.forEach(function(statute) {
            statutesHtml += `
                <div class="statute-item ${statute.is_current ? '' : 'outdated'}">
                    <div class="statute-reference">${statute.reference}</div>
                    <div><strong>Status:</strong> ${statute.is_current ? 'Current' : 'Outdated or Amendment Exists'}</div>
                    ${statute.content ? `<div><strong>Content:</strong> ${statute.content.substring(0, 100)}...</div>` : ''}
                </div>
            `;
        });
        
        statutesListDiv.innerHTML = statutesHtml;
    } else {
        statutesListDiv.innerHTML = '<p>No statutes identified in this document.</p>';
    }
}

// Generate a brief
function generateBrief() {
    // Check settings
    if (!checkSettings()) {
        return;
    }
    
    // Check if we have a document ID
    if (!documentId) {
        updateStatusMessage('Please analyze a document first.', 'warning');
        return;
    }
    
    // Get form values
    var title = document.getElementById('briefTitle').value.trim();
    var focusAreasText = document.getElementById('briefFocusAreas').value.trim();
    
    // Process focus areas
    var focusAreas = focusAreasText ? focusAreasText.split('\n').filter(line => line.trim().length > 0) : [];
    
    // Prepare request data
    var requestData = {
        document_id: documentId
    };
    
    if (title) {
        requestData.title = title;
    }
    
    if (focusAreas.length > 0) {
        requestData.focus_areas = focusAreas;
    }
    
    // Show loading overlay
    showLoading('Generating brief...');
    
    // Send to API
    fetch(apiUrl + '/api/briefs', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-API-Key': apiKey
        },
        body: JSON.stringify(requestData)
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('API request failed: ' + response.status);
        }
        return response.json();
    })
    .then(data => {
        // Get the full brief
        return fetch(apiUrl + '/api/briefs/' + data.id, {
            method: 'GET',
            headers: {
                'X-API-Key': apiKey
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('API request failed: ' + response.status);
            }
            return response.json();
        });
    })
    .then(brief => {
        // Hide loading overlay
        hideLoading();
        
        // Store current brief
        currentBrief = brief;
        
        // Display brief
        displayBrief(brief);
        
        // Update status
        updateStatusMessage('Brief generated successfully!', 'success');
    })
    .catch(error => {
        // Hide loading overlay
        hideLoading();
        
        // Show error
        console.error('Error generating brief:', error);
        updateStatusMessage('Error generating brief: ' + error.message, 'error');
    });
}

// Display brief
function displayBrief(brief) {
    // Show results section
    document.getElementById('briefResults').style.display = 'block';
    
    // Set title
    document.getElementById('briefResultTitle').textContent = brief.title;
    
    // Display content
    document.getElementById('briefContent').textContent = brief.content;
}

// Insert brief into document
function insertBrief() {
    // Check if we have a brief
    if (!currentBrief) {
        updateStatusMessage('Please generate a brief first.', 'warning');
        return;
    }
    
    // Show loading overlay
    showLoading('Inserting brief into document...');
    
    // Get the brief content
    var title = currentBrief.title;
    var content = currentBrief.content;
    
    // Insert into document
    Office.context.document.setSelectedDataAsync(
        title + '\n\n' + content,
        { coercionType: Office.CoercionType.Text },
        function(result) {
            // Hide loading overlay
            hideLoading();
            
            if (result.status === Office.AsyncResultStatus.Succeeded) {
                // Update status
                updateStatusMessage('Brief inserted successfully!', 'success');
            } else {
                // Show error
                updateStatusMessage('Error inserting brief: ' + result.error.message, 'error');
            }
        }
    );
}

// Validate statutes
function validateStatutes() {
    // Check settings
    if (!checkSettings()) {
        return;
    }
    
    // Check if we have a document ID
    if (!documentId) {
        updateStatusMessage('Please analyze a document first.', 'warning');
        return;
    }
    
    // Show loading overlay
    showLoading('Validating statutes...');
    
    // Send to API
    fetch(apiUrl + '/api/statutes?document_id=' + documentId, {
        method: 'GET',
        headers: {
            'X-API-Key': apiKey
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('API request failed: ' + response.status);
        }
        return response.json();
    })
    .then(data => {
        // Hide loading overlay
        hideLoading();
        
        // Display statute validation results
        displayStatuteValidation(data.items);
        
        // Update status
        updateStatusMessage('Statutes validated successfully!', 'success');
    })
    .catch(error => {
        // Hide loading overlay
        hideLoading();
        
        // Show error
        console.error('Error validating statutes:', error);
        updateStatusMessage('Error validating statutes: ' + error.message, 'error');
    });
}

// Display statute validation results
function displayStatuteValidation(statutes) {
    // Show results section
    document.getElementById('statutesResults').style.display = 'block';
    
    // Count statutes
    var totalCount = statutes.length;
    var outdatedCount = statutes.filter(statute => !statute.is_current).length;
    
    // Display summary
    var summaryDiv = document.getElementById('statutesSummary');
    
    if (outdatedCount > 0) {
        summaryDiv.innerHTML = `
            <div class="ms-MessageBar ms-MessageBar--warning">
                <div class="ms-MessageBar-content">
                    <div class="ms-MessageBar-icon">
                        <i class="ms-Icon ms-Icon--Warning"></i>
                    </div>
                    <div class="ms-MessageBar-text">
                        <strong>Warning:</strong> ${outdatedCount} out of ${totalCount} statutes may be outdated or have amendments.
                    </div>
                </div>
            </div>
        `;
    } else {
        summaryDiv.innerHTML = `
            <div class="ms-MessageBar ms-MessageBar--success">
                <div class="ms-MessageBar-content">
                    <div class="ms-MessageBar-icon">
                        <i class="ms-Icon ms-Icon--Completed"></i>
                    </div>
                    <div class="ms-MessageBar-text">
                        <strong>Good news!</strong> All ${totalCount} identified statutes appear to be current.
                    </div>
                </div>
            </div>
        `;
    }
    
    // Display statutes
    var statutesListDiv = document.getElementById('validatedStatutesList');
    
    if (statutes && statutes.length > 0) {
        var statutesHtml = '';
        
        statutes.forEach(function(statute) {
            statutesHtml += `
                <div class="statute-item ${statute.is_current ? '' : 'outdated'}">
                    <div class="statute-reference">${statute.reference}</div>
                    <div><strong>Status:</strong> ${statute.is_current ? 'Current' : 'Outdated or Amendment Exists'}</div>
                    ${statute.content ? `<div><strong>Content:</strong> ${statute.content.substring(0, 100)}...</div>` : ''}
                    <div><strong>Last Verified:</strong> ${new Date(statute.verified_at).toLocaleString()}</div>
                </div>
            `;
        });
        
        statutesListDiv.innerHTML = statutesHtml;
    } else {
        statutesListDiv.innerHTML = '<p>No statutes identified in this document.</p>';
    }
}