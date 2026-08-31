(function () {
    const STORAGE_KEY = 'counter:value';
    const countEl = document.getElementById('count');
    const incrementBtn = document.getElementById('increment');

    // BUG: value is never restored from storage and never saved.
    let count = 0;

    function render() {
        countEl.textContent = String(count);
    }

    incrementBtn.addEventListener('click', function () {
        count = count + 1;
        render();
    });

    render();
})();
