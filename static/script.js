document.addEventListener('DOMContentLoaded', () => {
    M.AutoInit();
    
    // Animations
    gsap.from(".upload-card", {y: 30, opacity: 0, duration: 1, ease: "power3.out"});
    gsap.to(".blob-1", {x: 50, y: 50, duration: 8, repeat: -1, yoyo: true, ease: "sine.inOut"});
    gsap.to(".blob-2", {x: -50, y: -50, duration: 10, repeat: -1, yoyo: true, ease: "sine.inOut"});
});

// State
let stage, layer;
let sessionId;
let edits = [];
let currentWord = null;
let currentGroup = null;

// Elements
const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('fileInput');
const browseBtn = document.getElementById('browseBtn');
const loader = document.getElementById('loader');

// --- Upload Handling ---

// Fix: Browse button click
browseBtn.addEventListener('click', (e) => {
    e.stopPropagation(); // Prevent dropzone click
    fileInput.click();
});

fileInput.addEventListener('change', (e) => {
    if(e.target.files[0]) handleUpload(e.target.files[0]);
});

// Drag & Drop
dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('hover');
});
dropZone.addEventListener('dragleave', (e) => {
    e.preventDefault();
    dropZone.classList.remove('hover');
});
dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('hover');
    if(e.dataTransfer.files[0]) handleUpload(e.dataTransfer.files[0]);
});

async function handleUpload(file) {
    loader.style.display = 'flex';
    const form = new FormData();
    form.append('file', file);

    try {
        const res = await fetch('/upload', { method: 'POST', body: form });
        const data = await res.json();
        
        if(data.error) throw new Error(data.error);

        sessionId = data.session_id;
        initEditor(data.image_url, data.words);

        document.getElementById('upload-view').classList.remove('active');
        document.getElementById('editor-view').classList.add('active');
        document.getElementById('downloadBtn').classList.remove('disabled');

    } catch (e) {
        M.toast({html: 'Error: ' + e.message, classes: 'red rounded'});
    } finally {
        loader.style.display = 'none';
    }
}

// --- Editor Logic ---

function initEditor(url, words) {
    const container = document.getElementById('konva-holder');
    const width = container.clientWidth;
    const height = container.clientHeight;

    stage = new Konva.Stage({
        container: 'konva-holder',
        width: width,
        height: height,
        draggable: true
    });

    layer = new Konva.Layer();
    stage.add(layer);

    const imgObj = new Image();
    imgObj.onload = () => {
        // Fit image logic
        const scale = Math.min(width / imgObj.naturalWidth, height / imgObj.naturalHeight) * 0.9;
        
        // Center image
        stage.scale({x: scale, y: scale});
        stage.x((width - imgObj.naturalWidth * scale) / 2);
        stage.y((height - imgObj.naturalHeight * scale) / 2);

        const kImg = new Konva.Image({ image: imgObj });
        layer.add(kImg);

        // Draw words
        words.forEach((w, i) => {
            const group = new Konva.Group({
                x: w.x, y: w.y, width: w.w, height: w.h
            });

            // Hitbox (invisible unless hovered)
            const rect = new Konva.Rect({
                width: w.w, height: w.h,
                fill: 'rgba(99, 102, 241, 0.2)',
                stroke: '#6366f1',
                strokeWidth: 2,
                opacity: 0
            });

            group.add(rect);
            layer.add(group);

            group.on('mouseenter', () => {
                document.body.style.cursor = 'pointer';
                rect.opacity(1);
            });
            group.on('mouseleave', () => {
                document.body.style.cursor = 'default';
                rect.opacity(0);
            });
            group.on('click tap', () => openModal(w, group));
        });
        
        layer.draw();
    };
    imgObj.src = url;

    // Zoom Handlers
    const scaleBy = 1.1;
    stage.on('wheel', (e) => {
        e.evt.preventDefault();
        const oldScale = stage.scaleX();
        const pointer = stage.getPointerPosition();
        const mousePointTo = {
            x: (pointer.x - stage.x()) / oldScale,
            y: (pointer.y - stage.y()) / oldScale,
        };
        const newScale = e.evt.deltaY > 0 ? oldScale / scaleBy : oldScale * scaleBy;
        stage.scale({ x: newScale, y: newScale });
        const newPos = {
            x: pointer.x - mousePointTo.x * newScale,
            y: pointer.y - mousePointTo.y * newScale,
        };
        stage.position(newPos);
    });
}

// --- Modal & Saving ---

const modalEl = document.getElementById('editModal');
const modalInst = M.Modal.init(modalEl);
const newTextIn = document.getElementById('newText');
const sizeIn = document.getElementById('fontSizeSlider');
const colorIn = document.getElementById('textColor');

function openModal(word, group) {
    currentWord = word;
    currentGroup = group;
    
    // Check existing edits
    const existing = edits.find(e => e.x === word.x && e.y === word.y);
    
    newTextIn.value = existing ? existing.new_text : word.text;
    sizeIn.value = existing ? existing.font_size : Math.round(word.h * 0.8);
    colorIn.value = existing ? existing.color : "#000000";
    
    document.getElementById('fontSizeValue').innerText = sizeIn.value + 'px';
    M.updateTextFields();
    modalInst.open();
    newTextIn.focus();
}

sizeIn.addEventListener('input', e => {
    document.getElementById('fontSizeValue').innerText = e.target.value + 'px';
});

document.getElementById('saveEditBtn').addEventListener('click', () => {
    const val = newTextIn.value;
    const size = parseInt(sizeIn.value);
    const color = colorIn.value;

    // Update Visuals
    // Remove old preview if exists
    const oldP = currentGroup.findOne('.preview');
    if(oldP) oldP.destroy();

    const previewText = new Konva.Text({
        text: val,
        fontSize: size,
        fill: color,
        fontFamily: 'Arial',
        name: 'preview',
        width: currentWord.w,
        align: 'center',
        listening: false // Click through to group
    });
    
    // Center vertically approx
    previewText.y((currentWord.h - previewText.height()) / 2);
    
    // White background for preview
    const bg = new Konva.Rect({
        width: currentWord.w, height: currentWord.h,
        fill: 'white', name: 'preview'
    });

    currentGroup.add(bg);
    currentGroup.add(previewText);
    layer.draw();

    // Save Data
    const editObj = {
        x: currentWord.x, y: currentWord.y, w: currentWord.w, h: currentWord.h,
        new_text: val, font_size: size, color: color
    };
    
    edits = edits.filter(e => !(e.x === editObj.x && e.y === editObj.y)); // Remove old
    edits.push(editObj);
    
    modalInst.close();
});

document.getElementById('downloadBtn').addEventListener('click', async () => {
    loader.style.display = 'flex';
    const form = new FormData();
    form.append('session_id', sessionId);
    form.append('edits', JSON.stringify(edits));

    const res = await fetch('/edit', { method: 'POST', body: form });
    const data = await res.json();
    loader.style.display = 'none';
    
    if(data.download_url) {
        window.location.href = data.download_url;
    }
});
