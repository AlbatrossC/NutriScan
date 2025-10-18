const imageInput = document.getElementById('imageInput');
const preview = document.getElementById('preview');
const placeholder = document.getElementById('placeholder');
const extractBtn = document.getElementById('extractBtn');
const statusDiv = document.getElementById('status');
const dropZone = document.getElementById('dropZone');
const dropZoneContent = document.getElementById('dropZoneContent');
const dropZonePreview = document.getElementById('dropZonePreview');
const dropZoneImage = document.getElementById('dropZoneImage');
const aboutBtn = document.getElementById('aboutBtn');
const aboutModal = document.getElementById('aboutModal');

let imgDataURL = "";

// Modal functionality
aboutBtn.addEventListener('click', () => {
    aboutModal.classList.add('show');
});

document.querySelectorAll('.close').forEach(closeBtn => {
    closeBtn.addEventListener('click', (e) => {
        const modalId = e.target.getAttribute('data-modal');
        document.getElementById(modalId).classList.remove('show');
    });
});

window.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal')) {
        e.target.classList.remove('show');
    }
});

// Drop zone click
dropZone.addEventListener('click', () => {
    imageInput.click();
});

// Drag and drop functionality
dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('drag-over');
});

dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('drag-over');
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('drag-over');
    
    const files = e.dataTransfer.files;
    if (files.length > 0 && files[0].type.startsWith('image/')) {
        handleImageFile(files[0]);
    }
});

// File input change
imageInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) {
        handleImageFile(file);
    }
});

function handleImageFile(file) {
    const reader = new FileReader();
    reader.onload = (event) => {
        imgDataURL = event.target.result;
        
        // Show image in drop zone
        dropZoneImage.src = imgDataURL;
        dropZoneContent.classList.add('hidden');
        dropZonePreview.classList.add('show');
        
        // Show image in preview area
        preview.src = imgDataURL;
        preview.classList.add('show');
        placeholder.style.display = 'none';
        
        extractBtn.disabled = false;
    };
    reader.readAsDataURL(file);
}

// Extract and analyze
extractBtn.addEventListener('click', async () => {
    if (!imgDataURL) {
        alert("Please select an image first!");
        return;
    }

    try {
        // Step 1: Extract text from image
        statusDiv.textContent = "Step 1/2: Extracting text from image...";
        statusDiv.className = 'show loading';
        
        const { data: { text } } = await Tesseract.recognize(
            imgDataURL,
            'eng',
            {
                logger: m => console.log(m)
            }
        );

        console.log("Extracted text:", text);

        // Step 2: Send to server for analysis
        statusDiv.textContent = "Step 2/2: Analyzing ingredients with AI...";
        
        const response = await fetch('/analyze', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ text: text })
        });

        const result = await response.json();

        if (response.ok) {
            // Store result and redirect (or handle as needed)
            sessionStorage.setItem('analysisResult', JSON.stringify(result));
            window.location.href = '/result';
        } else {
            statusDiv.textContent = "Error: " + (result.error || "Analysis failed");
            statusDiv.className = 'show error';
        }

    } catch (error) {
        console.error("Error:", error);
        statusDiv.textContent = "Error: " + error.message;
        statusDiv.className = 'show error';
    }
});