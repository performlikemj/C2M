// Collect Payment Method for Monthly Membership
if (document.getElementById('payment-form')) {
    var stripe = Stripe(stripePublicKey);
    var elements = stripe.elements();
    var cardElement = elements.create('card');

    cardElement.mount('#card-element');

    var form = document.getElementById('payment-form');
    form.addEventListener('submit', function(event) {
        event.preventDefault();
        setLoading(true);

        stripe.createPaymentMethod({
            type: 'card',
            card: cardElement,
        }).then(function(result) {
            if (result.error) {
                showError(result.error.message);
                setLoading(false);
            } else {
                // Send paymentMethod.id to your server
                fetch(addPaymentMethodUrl, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken
                    },
                    body: JSON.stringify({
                        payment_method_id: result.paymentMethod.id
                    })
                }).then(function(response) {
                    return response.json();
                }).then(function(data) {
                    if (data.status === 'success') {
                        window.location.href = data.redirect_url;
                    } else {
                        showError(data.message);
                        setLoading(false);
                    }
                });
            }
        });
    });

    function showError(message) {
        var errorElement = document.getElementById('card-errors');
        errorElement.textContent = message;
        errorElement.style.display = 'block';
    }

    function setLoading(isLoading) {
        var spinner = document.getElementById('spinner');
        var buttonText = document.getElementById('button-text');
        if (isLoading) {
            spinner.style.display = 'inline-block';
            buttonText.style.display = 'none';
        } else {
            spinner.style.display = 'none';
            buttonText.style.display = 'inline-block';
        }
    }
}

// Helper function to extract the language prefix from the URL
function getLanguagePrefix() {
    const path = window.location.pathname;
    const segments = path.split('/');
    // Assuming the language code is always the first segment after the first slash
    return segments[1]; // This will be 'en', 'jp', etc.
}

// Check In/Out functionality
if (document.getElementById('qr-video')) {
    const codeReader = new ZXing.BrowserQRCodeReader();
    let action = null;
    const videoElement = document.getElementById('qr-video');
    const sessionModal = document.getElementById('sessionModal');
    const closeModal = document.querySelector('.close');

    let currentUsername = null; // Variable to hold the username after scanning QR code

    function startScanning(actionType) {
        action = actionType;
        console.log(action + ' mode');

        codeReader.decodeFromVideoDevice(null, 'qr-video', (result, err) => {
            if (result && action) {
                console.log(result);
                fetch(`/${languagePrefix}/gym/${action}/${result.text}/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken
                    },
                }).then(response => response.json())
                .then(data => {
                    console.log(data);
                    if (data.status === 'success' && action === 'check_in') {
                        // Capture the username from the response
                        currentUsername = data.user;

                        // Update the UI with membership and session details
                        document.getElementById('remaining-regular-sessions').innerText = data.membership.remaining_sessions;
                        document.getElementById('remaining-personal-training-sessions').innerText = data.membership.remaining_personal_trainings;

                        const sessionSelect = document.getElementById('session_id');
                        sessionSelect.innerHTML = '';
                        data.sessions.forEach(session => {
                            sessionSelect.innerHTML += `<option value="${session.id}">${session.name}</option>`;
                        });

                        const trainerSelect = document.getElementById('trainer_id');
                        trainerSelect.innerHTML = '';
                        data.trainers.forEach(trainer => {
                            trainerSelect.innerHTML += `<option value="${trainer.id}">${trainer.name}</option>`;
                        });

                        // Show the modal
                        sessionModal.style.display = 'block';
                    } else {
                        window.location.href = '/gym/scan/';
                    }
                }).catch(err => console.error('Fetch error:', err));
            }
            if (err && !(err instanceof ZXing.NotFoundException)) {
                console.error(err);
            }
        });
    }

    document.getElementById('checkInButton').addEventListener('click', () => startScanning('check_in'));
    document.getElementById('checkOutButton').addEventListener('click', () => startScanning('check_out'));

    closeModal.onclick = function() {
        sessionModal.style.display = 'none';
    }

    window.onclick = function(event) {
        if (event.target == sessionModal) {
            sessionModal.style.display = 'none';
        }
    }

    document.getElementById('sessionSelectionForm').addEventListener('submit', function(e) {
        e.preventDefault();
        const formData = new FormData(this);
        const sessionType = formData.get('session_type');
        const sessionId = formData.get('session_id');
        const trainerId = formData.get('trainer_id');

        if (!currentUsername) {
            console.error('No username available for submitting session details.');
            alert('Scan a user QR code first.');
            return;
        }

        fetch(`/${languagePrefix}/gym/select_session/${currentUsername}/`, {
            method: 'POST',
            body: JSON.stringify({
                session_type: sessionType,
                session_id: sessionId,
                trainer_id: trainerId
            }),
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            }
        }).then(response => response.json())
        .then(data => {
            if(data.status === 'success') {
                window.location.href = '/gym/scan/';
            } else {
                console.error('Error:', data.message);
                alert(data.message);
            }
        }).catch(err => console.error('Fetch error:', err));
    });

    document.querySelectorAll('input[name="session_type"]').forEach(input => {
        input.addEventListener('change', function() {
            const personalFields = document.getElementById('personal_training_fields');
            if (this.value === 'personal_training') {
                personalFields.style.display = '';
            } else {
                personalFields.style.display = 'none';
            }
        });
    });
}

// Language Switcher
document.addEventListener("DOMContentLoaded", function() {
    const languageSelect = document.getElementById("language-select");
    const languageForm = document.getElementById("language-form");

    if (languageSelect && languageForm) {
        console.log("Language switcher initialized");
        languageSelect.addEventListener("change", function() {
            console.log("Language changed to: ", languageSelect.value);
            languageForm.submit();
        });
    }
});


// Collect Payment
if (document.getElementById('payment-form')) {
    var stripe = Stripe(stripePublicKey);
    var elements = stripe.elements();
    var card = elements.create('card');
    card.mount('#card-element');

    var form = document.getElementById('payment-form');
    form.addEventListener('submit', function(event) {
        event.preventDefault();

        stripe.createPaymentMethod({
            type: 'card',
            card: card,
        }).then(function(result) {
            if (result.error) {
                var errorElement = document.getElementById('card-errors');
                errorElement.textContent = result.error.message;
            } else {
                fetch(createCheckoutSessionUrl, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken
                    },
                    body: JSON.stringify({
                        payment_method_id: result.paymentMethod.id,
                        membership_type_id: membershipTypeId
                    })
                }).then(function(response) {
                    return response.json();
                }).then(function(session) {
                    return stripe.redirectToCheckout({ sessionId: session.id });
                }).catch(function(error) {
                    console.error('Error:', error);
                });
            }
        });
    });
}

// Select Membership
if (document.getElementById('show-cancel-form')) {
    document.addEventListener("DOMContentLoaded", function() {
        const showCancelFormBtn = document.getElementById("show-cancel-form");
        const cancelForm = document.getElementById("cancel-form");

        showCancelFormBtn.addEventListener("click", function() {
            if (cancelForm.style.display === "none") {
                cancelForm.style.display = "block";
            } else {
                cancelForm.style.display = "none";
            }
        });
    });
}

// Select Session Type
if (document.getElementById('sessionSelectionForm')) {
    document.getElementById("sessionSelectionForm").addEventListener("submit", async function(e) {
        e.preventDefault();
        const form = e.target;
        const formData = new FormData(form);

        const response = await fetch(form.action, {
            method: "POST",
            headers: {
                "X-CSRFToken": form.querySelector("[name=csrfmiddlewaretoken]").value
            },
            body: formData
        });

        if (response.ok) {
            const redirectUrl = document.getElementById("redirect-url").dataset.url;
            window.location.href = redirectUrl;  // Redirect to personal schedule or another page
        } else {
            alert("Failed to select session.");
        }
    });

    function togglePersonalTrainingFields() {
        const personalTrainingFields = document.getElementById("personal_training_fields");
        const sessionType = document.querySelector("input[name='session_type']:checked").value;
        personalTrainingFields.style.display = sessionType === "personal_training" ? "block" : "none";
    }

    document.querySelectorAll("input[name='session_type']").forEach(input => {
        input.addEventListener("change", togglePersonalTrainingFields);
    });
}
