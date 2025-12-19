document.addEventListener("DOMContentLoaded", function () {
    // flash message fading logic
    let flashMessages = document.querySelectorAll(".flash-messages li");
    flashMessages.forEach(function (message) {
        setTimeout(function () {
            message.style.opacity = "0"; // start fade out
        }, 3000); // wait for 3 seconds before fading
        message.addEventListener("transitionend", function () {
            message.remove(); // remove after transition completes
        });
    });

    // function to fetch restaurants dynamically
    function fetchRestaurants() {
        fetch("/restaurants")
            .then(response => response.text())
            .then(html => {
                let parser = new DOMParser();
                let doc = parser.parseFromString(html, "text/html");
                let newList = doc.querySelector(".list") ? doc.querySelector(".list").innerHTML : "";

                let restaurantList = document.querySelector(".list");
                if (restaurantList) {
                    restaurantList.innerHTML = newList;
                }
            })
            .catch(error => console.error("Error fetching restaurants:", error));
    }

    // auto-refresh restaurant list every 10 seconds (only if on the restaurants page)
    if (document.getElementById("anPageName")?.value === "restaurants") {
        setInterval(fetchRestaurants, 10000);
    }

// function to fetch and display balance
function fetchBalance() {
    fetch("/balance")
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                showModal("Error: " + data.error);
            } else {
                showModal("Your balance is: " + data.balance+ " €");
            }
        })
        .catch(error => console.error("Error fetching balance:", error));
}

    // function to show the modal with custom text
    function showModal(text) {
        const modal = document.getElementById("balance-modal");
        const balanceText = document.getElementById("balance-text");
        const closeButton = document.getElementById("close-balance-modal");

        // set the modal text
        balanceText.textContent = text;

        // show the modal
        modal.classList.add("show");

        // close the modal when the close button is clicked
        closeButton.addEventListener("click", () => {
            modal.classList.remove("show");
        });

        // close the modal when clicking outside the modal content
        window.addEventListener("click", (event) => {
            if (event.target === modal) {
                modal.classList.remove("show");
            }
        });
    }

    // attach balance fetch to the button
    const balanceButton = document.getElementById("balance-btn");
    if (balanceButton) {
        balanceButton.addEventListener("click", (event) => {
            event.preventDefault(); // Prevent navigation
            fetchBalance();
        });
    }


    // cart visibility update
    function updateCartDisplay() {
        let cartItems = document.getElementById("cart-items");
        let emptyMessage = document.getElementById("cart-empty-message");

        if (cartItems && emptyMessage) {
            if (cartItems.children.length === 0) {
                emptyMessage.style.display = "block";  // show "Your cart is empty"
                cartItems.style.display = "none";      // hide cart items
            } else {
                emptyMessage.style.display = "none";   // hide "Your cart is empty"
                cartItems.style.display = "block";     // show cart items
            }
        }
    }

    // run function when the page loads
    updateCartDisplay();
});


// establish WebSocket connection
var socket = io.connect('http://localhost:5000');

// function to join a restaurant WebSocket room
function joinRestaurantRoom(restaurantId) {
    socket.emit('join_restaurant', { restaurant_id: restaurantId });
}

// function to handle new order notifications
socket.on('new_order', function(data) {
    console.log("New order received:", data);
    if (data.restaurant_id == window.RESTAURANT_ID) {
        // instead of reloading the page, appending the new order to an order list
        let orderList = document.getElementById('order-list');
        let newOrderItem = document.createElement('li');
        newOrderItem.innerText = "New Order ID: " + data.order_id;
        orderList.appendChild(newOrderItem);
        alert("New order received! Order ID: " + data.order_id);
    }
});

if (!sessionStorage.getItem('tab_session_id')) {
    sessionStorage.setItem('tab_session_id', crypto.randomUUID());
}
const tabSessionId = sessionStorage.getItem('tab_session_id');

socket.emit('join_user', {
    user_id: USER_ID,
    tab_session_id: TAB_SESSION_ID
});

const userId = 'USER_ID';
// include tab_session_id in all outgoing requests
fetch(`/some_endpoint?tab_session_id=${tabSessionId}`, {
    method: 'POST',
    body: JSON.stringify({ user_id: userId })
});

document.getElementById('login-form').addEventListener('submit', function (e) {
    const tabSessionId = sessionStorage.getItem('tab_session_id');
    const formData = new FormData(this);
    formData.append('tab_session_id', tabSessionId);

    fetch('/login', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            window.location.href = '/home';
        } else {
            alert(data.message);
        }
    })
    .catch(error => console.error('Login error:', error));

    e.preventDefault();
});


// define order statuses
let orderStatuses = {
    "processing": "Processing",
    "completed": "Completed",
    "cancelled": "Cancelled",
    "being_prepared": "Being Prepared",
};

function updateOrderStatus(orderId, status) {
    fetch(`/update-order-status/${orderId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ status: orderStatuses[status] })
    })
    .then(response => response.json())
    .then(data => {
        console.log('Order status updated:', data);
        
        // update the status on the frontend
        document.getElementById(`order-status-${orderId}`).innerText = data.orderStatus;

        // if available, update the balances as well
        if (data.customerBalance !== undefined) {
            document.getElementById(`customer-balance-${orderId}`).innerText = `Customer Balance: €${data.customerBalance}`;
        }

        if (data.restaurantBalance !== undefined) {
            document.getElementById(`restaurant-balance-${orderId}`).innerText = `Restaurant Balance: €${data.restaurantBalance}`;
        }
    })
    .catch(error => {
        console.error('Error updating status:', error);
    });
}

document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".add-to-cart").forEach(button => {
        button.addEventListener("click", function () {
            let itemId = this.getAttribute("data-item-id");

            fetch(`/cart/add/${itemId}`, { method: "GET" })
            .then(response => response.text())
            .then(() => {
                alert("Item added to cart!");
                location.reload(); // Refresh the page to update the cart
            })
            .catch(error => console.error("Error adding to cart:", error));
        });
    });
});


document.addEventListener("DOMContentLoaded", function() {
    let cartItems = JSON.parse('{{ cart_items | tojson | safe }}');
    document.getElementById("items-data").value = JSON.stringify(cartItems);
});