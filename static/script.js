group.on('click', () => {
    const updatedText = prompt("New Text:", word.text);
    if (updatedText !== null) {
        // Instead of a white box, we show a 'loading' or visual change hint
        // The real 'healing' happens on the backend export
        rect.fill('rgba(255,255,255,0.8)'); // Semi-transparent glass look for preview
        
        const label = new Konva.Text({
            text: updatedText,
            fontSize: word.h * 0.8,
            fill: '#000',
            fontStyle: 'bold',
            y: 2
        });
        group.add(label);
        State.layer.draw();

        State.edits.push({ x: word.x, y: word.y, w: word.w, h: word.h, new_text: updatedText });
        UI.downloadBtn.disabled = false;
    }
});
