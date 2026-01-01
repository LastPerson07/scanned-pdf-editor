document.addEventListener('DOMContentLoaded', () => {
    // Init Materialize components
    M.AutoInit();
    
    // Animations
    gsap.from(".upload-card", { opacity: 0, y: 30, duration: 1, ease: "power3.out" });
    gsap.to("#blob1", { x: 150, y: 100, duration: 12, repeat: -1, yoyo: true, ease: "sine.inOut" });
    gsap.to("#blob2", { x: -120, y: -80, duration: 15, repeat: -1, yoyo: true, ease: "sine.inOut" });
});

// DOM Elements
const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('fileInput');
const browseBtn = document.getElementById('browseBtn');
const downloadBtn = document.getElementById('downloadBtn');
const loader = document.getElementById('loader-overlay');
const modalElement = document.getElementById('editModal');
// Inputs
const newTextInput = document.getElementById('newText');
const fontSizeSlider = document.getElementById('fontSizeSlider');
const fontSizeValue = document.getElementById('fontSizeValue');
const textColor = document.getElementById('textColor');
const saveEditBtn = document.getElementById('saveEditBtn');
const zoomInBtn = document.getElementById('zoomInBtn');
const zoomOutBtn = document.getElementById('zoomOutBtn');
const resetBtn = document.getElementById('resetBtn');

// State
let stage, layer;
let sessionId = null;
let currentWordData = null; // The original OCR data
let currentGroup = null;    // The Konva Group
let edits = [];             // Array to store changes
let scaleBy = 1.1;

// --- Event Listeners ---

// 1. File Upload Logic
browseBtn.addEventListener('click', (e) => {
    e.stopPropagation(); // Stop bubbling
    fileInput.click();
});

fileInput.addEventListener('change', (e) => {
    if (e.target.files[0]) processFile(e.target.files[0]);
});

// Drag & Drop
dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('active');
});
dropZone.addEventListener('dragleave', (e) => {
    e.preventDefault();
    dropZone.classList.remove('active');
});
dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('active');
    if (e.dataTransfer.files[0]) processFile(e.dataTransfer.files[0]);
});

async function processFile(file) {
    loader.style.display = 'flex';
    
    const formData = new FormData();
    formData.append("file", file);

    try {
        const res = await fetch('/upload', { method: 'POST', body: formData });
        const data = await res.json();

        if (data.error) throw new Error(data.error);

        sessionId = data.session_id;
        initEditor(data.image_url, data.words);

        // Switch Views
        document.getElementById('upload-view').style.display = 'none';
        document.getElementById('editor-view').style.display = 'block';
        downloadBtn.classList.remove('disabled');
        
        gsap.from("#editor-view", { opacity: 0, scale: 0.95, duration: 0.5 });

    } catch (err) {
        M.toast({html: 'Error: ' + err.message, classes: 'red rounded'});
    } finally {
        loader.style.display = 'none';
    }
}

// 2. Konva Editor Logic
function initEditor(imgUrl, words) {
    const container = document.getElementById('konva-holder');
    const width = container.clientWidth;
    const height = window.innerHeight * 0.8;

    const img = new Image();
    img.onload = () => {
        // Calculate initial fit
        const imgRatio = img.naturalWidth / img.naturalHeight;
        const initialScale = Math.min(width / img.naturalWidth, height / img.naturalHeight);

        stage = new Konva.Stage({
            container: 'konva-holder',
            width: width,
            height: height,
            draggable: true
        });

        layer = new Konva.Layer();
        stage.add(layer);

        // Background Image
        const bgImage = new Konva.Image({
            image: img,
            x: 0,
            y: 0,
        });
        layer.add(bgImage);

        // Center the image initially
        stage.scale({ x: initialScale, y: initialScale });
        
        // Render OCR Words
        words.forEach((word, index) => {
            const group = new Konva.Group({
                x: word.x,
                y: word.y,
                width: word.w,
                height: word.h,
                name: 'word-group',
                id: 'word-' + index // unique ID
            });

            // Highlight Box (Invisible normally)
            const rect = new Konva.Rect({
                width: word.w,
                height: word.h,
                fill: 'rgba(99, 102, 241, 0.1)',
                stroke: 'rgba(99, 102, 241, 0.5)',
                strokeWidth: 1,
                opacity: 0 // hidden until hover
            });

            group.add(rect);
            layer.add(group);

            // Interaction
            group.on('mouseenter', () => {
                document.body.style.cursor = 'pointer';
                rect.opacity(1);
                layer.batchDraw();
            });

            group.on('mouseleave', () => {
                document.body.style.cursor = 'default';
                rect.opacity(0);
                layer.batchDraw();
            });

            group.on('click tap', () => {
                openEditModal(word, group);
            });
        });

        layer.draw();
        setupZoom();
    };
    img.src = imgUrl;
}

// 3. Zoom Controls
function setupZoom() {
    stage.on('wheel', (e) => {
        e.evt.preventDefault();
        const oldScale = stage.scaleX();
        const pointer = stage.getPointerPosition();

        const mousePointTo = {
            x: (pointer.x - stage.x()) / oldScale,
            y: (pointer.y - stage.y()) / oldScale,
        };

        let newScale = e.evt.deltaY > 0 ? oldScale / scaleBy : oldScale * scaleBy;
        stage.scale({ x: newScale, y: newScale });

        const newPos = {
            x: pointer.x - mousePointTo.x * newScale,
            y: pointer.y - mousePointTo.y * newScale,
        };
        stage.position(newPos);
        stage.batchDraw();
    });
}

zoomInBtn.onclick = () => {
    const oldScale = stage.scaleX();
    stage.scale({ x: oldScale * 1.2, y: oldScale * 1.2 });
    stage.batchDraw();
};

zoomOutBtn.onclick = () => {
    const oldScale = stage.scaleX();
    stage.scale({ x: oldScale * 0.8, y: oldScale * 0.8 });
    stage.batchDraw();
};

resetBtn.onclick = () => {
    window.location.reload();
}

// 4. Editing Logic
function openEditModal(wordData, group) {
    currentWordData = wordData;
    currentGroup = group;
    
    // Check if we already edited this word locally
    const existingEdit = edits.find(e => e.x === wordData.x && e.y === wordData.y);
    
    if (existingEdit) {
        newTextInput.value = existingEdit.new_text;
        fontSizeSlider.value = existingEdit.font_size;
        textColor.value = existingEdit.color;
    } else {
        newTextInput.value = wordData.text;
        fontSizeSlider.value = Math.max(10, Math.round(wordData.h * 0.75));
        textColor.value = "#000000";
    }

    fontSizeValue.textContent = fontSizeSlider.value;
    M.updateTextFields();
    
    const instance = M.Modal.getInstance(modalElement);
    instance.open();
    
    // Auto-focus input
    setTimeout(() => newTextInput.focus(), 100);
}

// Slider update UI
fontSizeSlider.addEventListener('input', (e) => {
    fontSizeValue.textContent = e.target.value;
});

// Save changes locally and update Canvas
saveEditBtn.addEventListener('click', () => {
    const newText = newTextInput.value;
    const size = parseInt(fontSizeSlider.value);
    const color = textColor.value;

    // Visual Update on Canvas
    // Remove old text preview if exists
    const oldPreview = currentGroup.findOne('.preview-text');
    if (oldPreview) oldPreview.destroy();

    const textPreview = new Konva.Text({
        text: newText,
        fontSize: size,
        fill: color,
        fontFamily: 'Arial', // Will be replaced by backend font
        name: 'preview-text',
        listening: false
    });

    // Center text in the box
    const textWidth = textPreview.width();
    const textHeight = textPreview.height();
    const boxWidth = currentWordData.w;
    const boxHeight = currentWordData.h;

    textPreview.position({
        x: (boxWidth - textWidth) / 2,
        y: (boxHeight - textHeight) / 2
    });
    
    // Add a white background to hide original text on canvas (preview only)
    const bgPreview = new Konva.Rect({
        width: boxWidth,
        height: boxHeight,
        fill: 'white',
        name: 'preview-bg'
    });
    
    // If updating existing, remove old bg
    const oldBg = currentGroup.findOne('.preview-bg');
    if(oldBg) oldBg.destroy();

    currentGroup.add(bgPreview);
    currentGroup.add(textPreview);
    bgPreview.moveToBottom(); // keep rect trigger on top? No, rect is invisible
    
    // Update State
    const editObj = {
        x: currentWordData.x,
        y: currentWordData.y,
        w: currentWordData.w,
        h: currentWordData.h,
        new_text: newText,
        font_size: size,
        color: color
    };

    // Remove previous edit for this word if exists, then push new
    edits = edits.filter(e => !(e.x === editObj.x && e.y === editObj.y));
    edits.push(editObj);

    layer.batchDraw();
    M.Modal.getInstance(modalElement).close();
    M.toast({html: 'Edit Applied (Preview)', classes: 'green rounded'});
});

// 5. Download / Finalize
downloadBtn.addEventListener('click', async () => {
    if (edits.length === 0) {
        M.toast({html: 'No edits made!', classes: 'orange'});
        return;
    }

    loader.style.display = 'flex';
    const formData = new FormData();
    formData.append('session_id', sessionId);
    formData.append('edits', JSON.stringify(edits));

    try {
        const res = await fetch('/edit', { method: 'POST', body: formData });
        const data = await res.json();
        
        if (data.error) throw new Error(data.error);
        
        // Trigger Download
        const link = document.createElement('a');
        link.href = data.download_url;
        link.download = 'edited_document.pdf';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        M.toast({html: 'Download Started!', classes: 'blue rounded'});
        
    } catch (err) {
        console.error(err);
        M.toast({html: 'Error generating PDF', classes: 'red'});
    } finally {
        loader.style.display = 'none';
    }
});
