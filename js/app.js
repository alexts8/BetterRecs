const sliders = document.querySelectorAll('input[type="range"]');


sliders.forEach(slider => {
    const valueSpan = document.getElementById(`${slider.id}Value`);
    slider.addEventListener('input', () => {
        valueSpan.textContent = slider.value;
    });
});