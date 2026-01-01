gsap.from(".glass-container", { opacity: 0, y: 40, duration: 1.2, ease: "power4.out" });
gsap.to("#blob1", { x: 150, y: 100, duration: 12, repeat: -1, yoyo: true, ease: "sine.inOut" });
gsap.to("#blob2", { x: -120, y: -80, duration: 15, repeat: -1, yoyo: true, ease: "sine.inOut" });

document.addEventListener('DOMContentLoaded', () => M.AutoInit());

// Prevent default drag behaviors globally
document.addEventListener('dragover', e => e.preventDefault());
document.addEventListener('drop', e => e.preventDefault());

const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('fileInput');
const browseBtn = document.getElementById('browseBtn');
const downloadBtn = document.getElementById('downloadBtn');
const modal = document.getElementById('editModal');
const newTextInput = document.getElementById('newText');
const fontSizeSlider = document.getElementById('fontSizeSlider');
const fontSizeValue = document.getElementById('fontSizeValue');
const textColor = document.getElementById('textColor');
const saveEditBtn = document.getElementById('saveEditBtn');

let stage, layer, sessionId, edits = [];
let currentWord = null;
let currentGroup = null;
let scale = 1;  // For zoom

// Avoid double triggers by using once: false and stopPropagation
dropZone.addEventListener('dragenter', (e) => {
    e.stopPropagation();
    dropZone.classList.add('dragover');
}, false);
dropZone.addEventListener('dragover', (e) => {
    e.stopPropagation();
    dropZone.classList.add('dragover');
}, false);
dropZone.addEventListener('dragleave', (e) => {
    e.stopPropagation();
    dropZone.classList.remove('dragover');
}, false);
dropZone.addEventListener('drop', (e) => {
    e.stopPropagation();
    dropZone.classList.remove('dragover');
    if (e.dataTransfer.files[0]) handleFile(e.dataTransfer.files[0]);
}, false);

dropZone.addEventListener('click', () => fileInput.click(), false);
browseBtn.addEventListener('click', () => fileInput.click(), false);
fileInput.addEventListener('change', (e) => {
    if (e.target.files[0]) handleFile(e.target.files[0]);
}, false);

async function handleFile(file) {
    // Show processing only once
    if (dropZone.innerHTML.includes("Processing")) return;  // Prevent double call
    
    dropZone.innerHTML = "<h5>Processing document...</h5><p>Please wait</p>";
    const form = new FormData();
    form.append("file", file);

    const res = await fetch('/upload', { method: 'POST', body: form });
    const data = await res.json();
    
    if (data.error) {
        dropZone.innerHTML = "<h5>Error: " + data.error + "</h5>";
        return;
    }

    sessionId = data.session_id;
    initEditor(data.image_url, data.words);

    gsap.to("#upload-view", { opacity: 0, duration: 0.5, onComplete: () => {
        document.getElementById('upload-view').style.display = 'none';
        document.getElementById('editor-view').style.display = 'block';
        gsap.from("#editor-view", { opacity: 0, y: 30, duration: 0.7 });
    }});
}

function initEditor(imageUrl, words) {
    const container = document.getElementById('konva-holder');
    const img = new Image();
    img.onload = () => {
        // Fit to viewport: calculate scale to fit 80% of height/width
        const maxWidth = window.innerWidth * 0.8;
        const maxHeight = window.innerHeight * 0.8;
        const ratio = Math.min(maxWidth / img.naturalWidth, maxHeight / img.naturalHeight);
        scale = ratio;  // Initial scale
        
        stage = new Konva.Stage({
            container: 'konva-holder',
            width: img.naturalWidth * ratio,
            height: img.naturalHeight * ratio,
            draggable: true  // Allow panning
        });
        layer = new Konva.Layer();
        stage.add(layer);

        const bg = new Konva.Image({ image: img });
        layer.add(bg);
        layer.scale({ x: ratio, y: ratio });

        words.forEach(word => {
            const group = new Konva.Group({ x: word.x, y: word.y });
            const rect = new Konva.Rect({
                width: word.w,
                height: word.h,
                fill: 'rgba(99,102,241,0.08)'
            });
            group.add(rect);
            layer.add(group);

            group.on('mouseenter', () => {
                rect.fill('rgba(99,102,241,0.25)');
                layer.draw();
                document.body.style.cursor = 'pointer';
            });
            group.on('mouseleave', () => {
                rect.fill('rgba(99,102,241,0.08)');
                layer.draw();
                document.body.style.cursor = 'default';
            });

            group.on('click', () => {
                currentGroup = group;
                currentWord = word;
                newTextInput.value = word.text || '';
                fontSizeSlider.value = Math.round(word.h * 0.8);
                fontSizeValue.textContent = fontSizeSlider.value;
                textColor.value = '#000000';
                M.updateTextFields();
                M.Modal.getInstance(modal).open();
            });
        });

        layer.draw();
        
        // Add zoom controls
        addZoomControls();
    };
    img.src = imageUrl;
}

function addZoomControls() {
    // Add buttons to sidebar or main
    const sidebar = document.querySelector('.sidebar');
    const zoomIn = document.createElement('button');
    zoomIn.textContent = '+';
    zoomIn.classList.add('btn', 'waves-effect', 'waves-light');
    zoomIn.style.marginTop = '20px';
    zoomIn.onclick = () => zoom(1.2);

    const zoomOut = document.createElement('button');
    zoomOut.textContent = '-';
    zoomOut.classList.add('btn', 'waves-effect', 'waves-light');
    zoomOut.style.marginTop = '10px';
    zoomOut.onclick = () => zoom(0.8);

    sidebar.appendChild(zoomIn);
    sidebar.appendChild(zoomOut);
    
    // Mouse wheel zoom
    stage.on('wheel', (e) => {
        e.evt.preventDefault();
        const oldScale = stage.scaleX();
        const pointer = stage.getPointerPosition();
        const mousePointTo = {
            x: (pointer.x / oldScale) - stage.x() / oldScale,
            y: (pointer.y / oldScale) - stage.y() / oldScale
