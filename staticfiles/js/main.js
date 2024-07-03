$(document).ready(function() {
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
});