$(document).ready(function() {
    // Load the saved mode from localStorage
    const savedMode = localStorage.getItem('mode') || 'light-mode';
    applyMode(savedMode);

    // Function to apply the light or dark mode
    function applyMode(mode) {
        $('body').removeClass('light-mode dark-mode').addClass(mode);
        $('.container, .service-card, .page-header, .card, .card-header, .card-body, .list-group-item, .btn-outline-primary, .navbar, .navbar-toggler-icon, .table, .text-muted').removeClass('light-mode dark-mode').addClass(mode);

        // Change the navbar based on the mode
        if (mode === 'light-mode') {
            $('.navbar').removeClass('bg-black').addClass('bg-light navbar-light');
            $('.navbar-toggler-icon').removeClass('dark-mode').addClass('light-mode');
        } else {
            $('.navbar').removeClass('bg-light navbar-light').addClass('bg-black navbar-dark');
            $('.navbar-toggler-icon').removeClass('light-mode').addClass('dark-mode');
        }
    }

    // Toggle Light/Dark Mode
    $('#mode-switcher').on('click', function() {
        const currentMode = $('body').hasClass('light-mode') ? 'light-mode' : 'dark-mode';
        const newMode = currentMode === 'light-mode' ? 'dark-mode' : 'light-mode';

        applyMode(newMode);
        localStorage.setItem('mode', newMode);

        // Animate the heavy bag
        const icon = $('#toggle-icon');
        icon.addClass('heavy-bag-swing');
        setTimeout(function() {
            icon.removeClass('heavy-bag-swing').addClass('heavy-bag-swing-back');
        }, 150);
        setTimeout(function() {
            icon.removeClass('heavy-bag-swing-back');
        }, 300);
    });

    // Toggle dropdowns - Example of Bootstrap 5 using jQuery
    $('.dropdown-toggle').dropdown();

    // Example AJAX setup for form submissions or API interactions
    $.ajaxSetup({
        beforeSend: function(xhr, settings) {
            function getCookie(name) {
                let cookieValue = null;
                if (document.cookie && document.cookie !== '') {
                    const cookies = document.cookie.split(';');
                    for (let i = 0; i < cookies.length; i++) {
                        const cookie = jQuery.trim(cookies[i]);
                        if (cookie.substring(0, name.length + 1) === (name + '=')) {
                            cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                            break;
                        }
                    }
                }
                return cookieValue;
            }
            if (!(/^http:.*/.test(settings.url) || /^https:.*/.test(settings.url))) {
                xhr.setRequestHeader("X-CSRFToken", getCookie('csrftoken'));
            }
        }
    });

    // Handling form submission example
    $('form#myForm').on('submit', function(e) {
        e.preventDefault();
        const formData = $(this).serialize();
        $.ajax({
            url: '/my-endpoint/',
            type: 'POST',
            data: formData,
            success: function(response) {
                console.log('Success!', response);
            },
            error: function(error) {
                console.log('Error:', error);
            }
        });
    });

    // Language Switcher
    $('#body-language-switcher').on('click', function() {
        const currentLanguage = $('#language-text').text().trim();
        const newLanguage = currentLanguage === 'English' ? 'Japanese' : 'English';
        const languageCode = currentLanguage === 'English' ? 'ja' : 'en';

        // Update the language text and icon color
        $('#language-text').text(newLanguage);
        const icon = $('#body-language-switcher .fas.fa-language');
        icon.toggleClass('japanese');

        // Redirect to the new language URL
        window.location.href = `/i18n/setlang/?language=${languageCode}`;
    });
});
