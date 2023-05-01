function toggleDarkMode() {
    var background_elements = document.getElementsByClassName("bg-color");
    [].forEach.call(background_elements, function(element) {
        element.classList.toggle("dark-mode-bg");
    });

    var moonlight_elements = document.getElementsByClassName("moonlight");
    [].forEach.call(moonlight_elements, function(element) {
        element.classList.toggle("dark-mode-moonlight");
    });

    var toggle_button_elements = document.getElementsByClassName("css-toggle-button");
    [].forEach.call(toggle_button_elements, function(element) {
        element.classList.toggle("dark-mode-toggle-button");
    });
}