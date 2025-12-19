from flask import Flask, render_template, request, redirect, session, url_for, flash, jsonify, json
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from models import db, User, Customer, Restaurant, UserType, MenuItem, CartItem, DeliveryArea, Order, OrderItem, Platform
from flask_socketio import SocketIO, emit, join_room
from datetime import datetime
from sqlalchemy.orm import joinedload
from decimal import Decimal

app = Flask(__name__)

# database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///lieferspatz.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
migrate = Migrate(app, db)
socketio = SocketIO(app)
app.secret_key = 'your_secret_key' 


@socketio.on('join_user')
def handle_user_join(data):
    user_id = data.get('user_id')
    tab_session_id = data.get('tab_session_id')
    if user_id and tab_session_id:
        room = f"user_{user_id}_{tab_session_id}"
        join_room(room)
        print(f"User {user_id} joined room {room}")


@app.before_request
def validate_tab_session():
    tab_session_id = request.form.get('tab_session_id') or request.args.get('tab_session_id')
    if 'tab_session_id' in session and session['tab_session_id'] != tab_session_id:
        session.clear()  # clear session if tab_session_id doesn't match
        flash("Session mismatch. Please log in again.", "warning")
        return redirect(url_for('login'))
    # store current tab_session_id in session
    session['tab_session_id'] = tab_session_id

# Route for Home
@app.route('/')
def home():
    user_type = session.get('user_type', None)  # Get the user type from the session (None if not logged in)
    return render_template('landing-page.html', user_type=user_type)

@app.route('/signup')
def signup():
    return render_template('sign-up.html')

@app.route('/restaurant_orders')
def restaurant_orders():
    restaurant_id = request.args.get('restaurant_id')

    if not restaurant_id:
        flash("Restaurant ID is missing.", "danger")
        return redirect(url_for('home'))  

    # fetch restaurant from database
    restaurant = db.session.get(Restaurant, restaurant_id)
    if not restaurant:
        flash("Restaurant not found.", "danger")
        return redirect(url_for('home'))  

    # statuses for ongoing and completed orders
    ongoing_statuses = ['Processing', 'Being Prepared']
    completed_statuses = ['Completed', 'Cancelled']  

    # fetch orders with related order items using joinedload for optimization
    ongoing_orders = Order.query.filter(
        Order.RestaurantID == restaurant_id,
        Order.Status.in_(ongoing_statuses)
    ).options(joinedload(Order.order_items)).all()

    completed_orders = Order.query.filter(
        Order.RestaurantID == restaurant_id,
        Order.Status.in_(completed_statuses)
    ).options(joinedload(Order.order_items)).all()

    return render_template(
        'restaurant-orders.html',
        ongoing_orders=ongoing_orders,
        completed_orders=completed_orders,
        restaurant=restaurant
    )


@app.route('/login', methods=['GET', 'POST'])
def login():
    # redirect logged-in users based on their user type
    if 'user_id' in session:
        user = db.session.get(User, session['user_id'])
        if user is None:  # clear session if user ID is invalid
            session.clear()
            return redirect(url_for('login'))

        if user.UserType == UserType.Customer:
            return redirect(url_for('orders'))  # redirect to customer orders page
        elif user.UserType == UserType.Restaurant:
            return redirect(url_for('restaurant_dashboard'))  # redirect to restaurant dashboard

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        tab_session_id = request.form.get('tab_session_id')

        # query the database for the user
        user = User.query.filter_by(EmailAddress=email).first()

        if not user:  # no user found
            flash('No account found with this email. Please sign up.', 'warning')
            return redirect(url_for('signup'))

        if user.Password != password:  # invalid password
            flash('Invalid email or password.', 'danger')
            return render_template('log-in.html')

        # successful login
        session['user_id'] = user.UserID
        session['tab_session_id'] = tab_session_id
        session['user_type'] = user.UserType.value

        if user.UserType == UserType.Customer:
            session['user_name'] = user.customer.FirstName
            flash(f'Welcome {session["user_name"]}!', 'success')
            return redirect(url_for('home'))  # automatical redirect

        elif user.UserType == UserType.Restaurant:
            session['user_name'] = user.restaurant.Name
            flash(f'Welcome {session["user_name"]}!', 'success')
            return redirect(url_for('restaurant_dashboard'))  # automatical redirect


    return render_template('log-in.html')  # render login page


@app.route('/restaurant_dashboard')
def restaurant_dashboard():
    if 'user_id' not in session:
        flash("You need to log in first.", "warning")
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    user = db.session.get(User, user_id)
    
    if user and user.UserType == UserType.Restaurant:
        restaurant = user.restaurant
        return render_template('restaurant-dashboard.html', restaurant=restaurant)
    else:
        flash("You do not have access to this page.", "danger")
        return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.clear()  # clear session data
    flash("You have been logged out.", "success")
    return redirect(url_for('login'))  # redirect to login page

@app.route('/sign_up_customer', methods=['GET', 'POST'])
def sign_up_customer():
    if request.method == 'POST':
        try:
            # collect form data
            first_name = request.form['first_name']
            last_name = request.form['last_name']
            email = request.form['email']
            password = request.form['password']
            confirm_password = request.form['confirm_password']
            address = request.form['address']
            post_number = request.form['post_number']

            # ensure that the UserType is explicitly set to Customer
            user_type = UserType.Customer

            # check if passwords match
            if password != confirm_password:
                flash('Passwords do not match!', 'danger')
                return render_template('sign-up-customer.html', user_type=user_type)

            # check if the email already exists
            existing_user = User.query.filter_by(EmailAddress=email).first()

            if existing_user:
                flash('Email is already in use. Please choose another.', 'danger')
                return render_template('sign-up-customer.html', user_type=user_type)

            # create new user with UserType as Customer
            new_user = User(EmailAddress=email, Password=password, UserType=user_type)
            db.session.add(new_user)
            db.session.commit()

            # get the newly created user ID
            user_id = new_user.UserID

            # create the new customer
            new_customer = Customer(
                UserID=user_id,
                FirstName=first_name,
                LastName=last_name,
                Address=address,
                PostNumber=post_number
            )

            db.session.add(new_customer)
            db.session.commit()

            flash('Customer sign-up successful! Please log in.', 'success')
            return redirect(url_for('login'))  # redirect to login page

        except Exception as e:
            flash(f"An error occurred: {e}", 'danger')
            print(f"Error: {str(e)}")

    return render_template('sign-up-customer.html', user_type='Customer')


@app.route('/sign-up-restaurant', methods=['GET', 'POST'])
def sign_up_restaurant():
    if request.method == 'POST':
        try:
            # collect form data
            email = request.form.get('email')
            password = request.form.get('password')
            restaurant_name = request.form.get('restaurant_name')
            address = request.form.get('address')
            postal_code = request.form.get('postal_code')
            open_time = request.form.get('open_time')
            close_time = request.form.get('close_time')
            description = request.form.get('description')
            delivery_areas = request.form.get('delivery_areas')  # comma-separated delivery areas

            # process delivery areas into a list
            delivery_area_list = [area.strip() for area in delivery_areas.split(',')] if delivery_areas else []

            # validate input
            if not all([email, password, restaurant_name, address, postal_code, open_time, close_time, description, delivery_areas]):
                flash("Please fill out all fields.", "danger")
                return redirect(url_for('sign_up_restaurant'))

            # check if the email already exists
            existing_user = User.query.filter_by(EmailAddress=email).first()
            if existing_user:
                flash('Email already exists. Please use a different one.', 'danger')
                return render_template('sign-up-restaurant.html', user_type='Restaurant')

            # convert string time ('09:00') to Python time object
            open_time_obj = datetime.strptime(open_time, '%H:%M').time()
            close_time_obj = datetime.strptime(close_time, '%H:%M').time()

            # create new user
            new_user = User(
                EmailAddress=email,
                Password=password, 
                UserType=UserType.Restaurant
            )
            db.session.add(new_user)
            db.session.commit()  # commit so new_user.UserID is generated

            # create new restaurant linked to the user
            new_restaurant = Restaurant(
                Name=restaurant_name,
                Address=address,
                PostalCode=postal_code, 
                OpenTime=open_time_obj,  # converted to time object
                CloseTime=close_time_obj,  # converted to time object
                Description=description,
                UserID=new_user.UserID  # associate restaurant with user
            )
            db.session.add(new_restaurant)
            db.session.commit()  # commit to generate RestaurantID

            # add delivery areas
            for area in delivery_area_list:
                delivery_area = DeliveryArea(
                    RestaurantID=new_restaurant.RestaurantID,
                    PostalCode=area  # delivery area postal codes
                )
                db.session.add(delivery_area)


            db.session.commit()  # commit all delivery areas

            flash('Restaurant sign-up successful! Please log in.', 'success')
            return redirect(url_for('login'))

        except Exception as e:
            db.session.rollback()  # rollback changes if there's an error
            flash(f"An error occurred: {e}", 'danger')
            print(f"Error: {str(e)}")

    return render_template('sign-up-restaurant.html', user_type='Restaurant')


@app.route('/orders')
def orders():
    if 'user_id' not in session:
        flash("You need to log in first.", "warning")
        return redirect(url_for('login'))

    user_id = session['user_id']

    # fetch orders with order items in one query (optimized)
    orders = Order.query.filter_by(CustomerID=user_id).options(joinedload(Order.order_items)).all()

    order_data = []
    for order in orders:
        items = [
            {
                "name": item.MenuItemName,  # use MenuItemName directly from OrderItem
                "quantity": item.Quantity,
                "price": float(item.MenuItemPrice),  # use MenuItemPrice directly from OrderItem
                "total": float(item.Quantity * item.MenuItemPrice)  # calculate total for each item
            }
            for item in order.order_items
        ]
        total = sum(item["total"] for item in items)  # calculate total for this order

        order_data.append({
            'order': order,
            'items': items,
            'total': total
        })

    return render_template('customer-orders.html', orders=order_data)

@app.route('/create_order', methods=['POST'])
def create_order():
    try:
        # retrieve customer id from the session
        customer_id = session.get('user_id')
        if not customer_id:
            flash("You need to be logged in to place an order.", "error")
            return redirect(url_for('login'))

        # retrieve customer and cart items based on the session's user_id
        customer = Customer.query.filter_by(UserID=customer_id).first()
        cart_items = CartItem.query.filter_by(UserID=customer_id).all()

        if not cart_items:
            flash("Your cart is empty!", "error")
            return redirect(url_for('cart'))
        
        # retrieve the note from the form
        additional_note = request.form.get('note', '').strip()

        # check if all items belong to the same restaurant
        restaurant_id = None
        total_amount = Decimal(0)
        for item in cart_items:
            menu_item = db.session.get(MenuItem, item.MenuItemID)
            if not menu_item:
                flash("One of the items is no longer available.", "error")
                return redirect(url_for('cart'))

            if restaurant_id is None:
                restaurant_id = menu_item.RestaurantID
            elif restaurant_id != menu_item.RestaurantID:
                flash("You can only order from one restaurant at a time.", "error")
                return redirect(url_for('cart'))

            item_price = Decimal(menu_item.Price)  # ensure price is Decimal
            total_amount += item_price * item.Quantity  # multiply using Decimal

        # round the total amount to 2 decimal places
        total_amount = total_amount.quantize(Decimal('0.01'))

        # calculate fees
        platform_fee = total_amount * Decimal("0.15")  # 15% platform fee
        platform_fee = platform_fee.quantize(Decimal('0.01'))

        restaurant_amount = total_amount - platform_fee
        restaurant_amount = restaurant_amount.quantize(Decimal('0.01'))

        # check if the customer has sufficient balance
        if customer.Balance < total_amount:
            flash("Insufficient balance to place the order.", "error")
            return redirect(url_for('cart'))

        # create the Order
        new_order = Order(
            CustomerID=customer_id,
            RestaurantID=restaurant_id,
            Status="Processing",
            TotalAmount=total_amount,
            PlatformFee=platform_fee,
            RestaurantAmount=restaurant_amount,
            Notes=additional_note  # save the note
            )
        db.session.add(new_order)
        db.session.flush()  # get OrderID before commit

        # create Order Items
        for item in cart_items:
            menu_item = db.session.get(MenuItem, item.MenuItemID)
            order_item = OrderItem(
                OrderID=new_order.OrderID,
                MenuItemName=menu_item.Name,  # populate MenuItemName
                MenuItemPrice=menu_item.Price,  # populate MenuItemPrice
                Quantity=item.Quantity
            )
            db.session.add(order_item)

        # deduct from customer balance
        customer.Balance -= float(total_amount)  # convert Decimal back to float

        # update platform balance
        platform = Platform.query.first()
        if not platform:
            platform = Platform(Balance=platform_fee)
            db.session.add(platform)
        else:
            platform.Balance += platform_fee

        # remove cart items after the order is created
        CartItem.query.filter_by(UserID=customer_id).delete()

        # commit transaction
        db.session.commit()

        flash("Order placed successfully!", "success")
        return redirect(url_for('orders'))

    except Exception as e:
        db.session.rollback()
        flash(f"Error: {str(e)}", "error")
        return redirect(url_for('cart'))


@app.route('/update-order-status/<int:order_id>', methods=['POST'])
def update_order_status(order_id):
    data = request.get_json()
    status = data.get('status')

    # find the order by ID
    order = db.session.query(Order).filter_by(OrderID=order_id).first()

    if not order:
        return jsonify({"message": "Order not found!"}), 404

    # handle the status update and balances
    if status == "Being Prepared":  # if the restaurant accepts the order
        # deduct from the customer's balance
        customer = db.session.get(Customer, order.CustomerID)
        if customer.Balance < order.TotalAmount:
            return jsonify({"message": "Insufficient balance to process the order!"}), 400

        customer.Balance -= order.TotalAmount

        # add to the restaurant's balance (restaurant amount after platform fee)
        restaurant = db.session.get(Restaurant, order.RestaurantID)
        restaurant.Balance += order.RestaurantAmount  # add restaurant's share

        db.session.commit()  # commit changes to balances

    # update the order status based on whether the restaurant is marking it as "done"
    if status == "Completed":
        # update the status for the restaurant to 'Completed'
        order.Status = "Completed"
        # also mark it as "Delivered" for the customer
        order.CustomerStatus = "Delivered" # update the customer status
        db.session.commit()

    # update the order status
    order.Status = status
    db.session.commit()

    return jsonify({
        "message": "Order status updated successfully!",
        "orderStatus": order.Status,
        "customerBalance": customer.Balance if customer else None,
        "restaurantBalance": restaurant.Balance if restaurant else None
    }), 200

@app.route('/accept_or_reject_order/<int:order_id>/<string:action>', methods=['POST'])
def accept_or_reject_order(order_id, action):
    order = Order.query.get(order_id)

    if not order:
        flash("Order not found.", "danger")
        return redirect(url_for('restaurant_orders', restaurant_id=session.get('restaurant_id')))

    if action == 'accept':
        order.Status = 'Being Prepared'  # update the status to 'Being Prepared'
    elif action == 'reject':
        order.Status = 'Cancelled'
        reverse_payment(order) 

    db.session.commit()
    flash(f"Order {action}ed successfully.", "success")

    # redirect back to the restaurant orders page with restaurant_id
    return redirect(url_for('restaurant_orders', restaurant_id=order.RestaurantID))


def process_payment(order):
    # deduct balance from customer account
    if order.Status == 'Being Prepared':
        customer = order.customer 
        customer.balance -= order.TotalAmount  # deduct the order amount from customer's balance
        db.session.commit()  # commit changes to the database

def reverse_payment(order):
    # ensure the order has a valid customer
    if not order.customer or not order.customer.customer:  # access the 'Customer' model via 'User'
        raise ValueError("The order does not have an associated customer with a balance.")

    customer = order.customer.customer  # access the Customer model
    customer.Balance += float(order.TotalAmount)  # adjust the customer's balance
    db.session.commit()


@app.route('/mark_as_done/<int:order_id>', methods=['POST'])
def mark_as_done(order_id):
    order = Order.query.get(order_id)

    if not order:
        flash("Order not found.", "danger")
        return redirect(url_for('restaurant_orders'))

    if order.Status != 'Being Prepared':
        flash("Only orders that are being prepared can be marked as done.", "warning")
        return redirect(url_for('restaurant_orders'))

    # update the order status to 'Completed'
    order.Status = 'Completed'

    # access the associated customer
    customer = order.customer 

    if customer:
        pass

    db.session.commit()
    flash(f"Order #{order.OrderID} has been marked as completed.", "success")
    return redirect(url_for('restaurant_orders', restaurant_id=order.RestaurantID))


@app.route('/about')
def about():
    return render_template('about-us.html')

@app.route('/menu', methods=['GET'])
def restaurant_menu():
    # get restaurant_id from the query parameters
    restaurant_id = request.args.get('restaurant_id', type=int)
    
    if not restaurant_id:
        flash("Restaurant ID is required.", "danger")
        return redirect(url_for('show_restaurants'))  # redirects to the restaurant list

    # fetch restaurant details from the database
    restaurant = db.session.get(Restaurant, restaurant_id)

    if not restaurant:
        flash("Restaurant not found.", "danger")
        return redirect(url_for('show_restaurants'))  # redirects to the restaurant list
    
    # fetch the menu items for this restaurant
    menu_items = MenuItem.query.filter_by(RestaurantID=restaurant_id).all()

    # get the current logged-in user
    user_type = session.get('user_type') 
    # check if the current user is a restaurant
    is_restaurant = user_type == "Restaurant"

    # pass the 'is_restaurant' flag to the template
    return render_template('restaurant-menu.html', restaurant=restaurant, menu_items=menu_items, is_restaurant=is_restaurant)


@app.route('/restaurants', methods=['GET'])
def show_restaurants():
    # ensure the user is logged in
    if 'user_id' not in session:
        flash("Please log in first", "warning")
        return redirect(url_for('login'))

    user_id = session['user_id']
    user = db.session.get(User, user_id)

    if user.UserType != UserType.Customer:
        flash("Only customers can access this page.", "danger")
        return redirect(url_for('home'))

    # retrieve the customer's postal code
    customer = user.customer
    if not customer:
        flash("Customer details not found.", "danger")
        return redirect(url_for('home'))

    customer_postal_code = customer.PostNumber

    # get the current time
    current_time = datetime.now().time()

    # find restaurants delivering to the customer's postal code
    delivery_areas = DeliveryArea.query.filter_by(PostalCode=customer_postal_code).all()
    restaurant_ids = [area.RestaurantID for area in delivery_areas]
    restaurants = Restaurant.query.filter(Restaurant.RestaurantID.in_(restaurant_ids)).all()

    # prepare a list of open restaurants with delivery areas
    restaurant_data = []
    for restaurant in restaurants:
        # check if the restaurant is currently open
        if restaurant.OpenTime <= current_time <= restaurant.CloseTime:
            # fetch delivery areas for this restaurant
            delivery_areas = DeliveryArea.query.filter_by(RestaurantID=restaurant.RestaurantID).all()
            delivery_area_list = [area.PostalCode for area in delivery_areas]
            delivery_area_str = ", ".join(delivery_area_list)

            open_time_formatted = restaurant.OpenTime.strftime('%H:%M')
            close_time_formatted = restaurant.CloseTime.strftime('%H:%M')
            # add restaurant info along with delivery area string
            restaurant_data.append({
                "restaurant": restaurant,
                "delivery_area_str": delivery_area_str
            })

    if not restaurant_data:
        flash("No restaurants found that deliver to your area and are currently open.", "warning")

    # pass filtered restaurants to the template
    return render_template('restaurants.html', restaurants=restaurant_data)

 
@app.route('/restaurant/<int:restaurant_id>', methods=['GET'])
def customer_menu(restaurant_id):
    restaurant = Restaurant.query.get_or_404(restaurant_id)
    menu_items = MenuItem.query.filter_by(RestaurantID=restaurant_id).all()
    
    return render_template('customer-menu.html', restaurant=restaurant, menu_items=menu_items)

@app.route('/add_item/<int:restaurant_id>', methods=['GET', 'POST'])
def restaurant_add_item(restaurant_id):
    # fetch the restaurant using the ID
    restaurant = db.session.get(Restaurant, restaurant_id)
    
    if not restaurant:
        flash("Restaurant not found.", "danger")
        return redirect(url_for('show_restaurants'))  # or redirect to another page
    
    if request.method == 'POST':
        # handle the form submission for adding a new item
        item_name = request.form['item_name']
        item_description = request.form['item_description']
        item_price = request.form['item_price']
        
        # create the new menu item with correct attribute names
        new_item = MenuItem(
            Name=item_name, 
            Description=item_description, 
            Price=item_price, 
            RestaurantID=restaurant_id 
        )
        
        # add the item to the database
        db.session.add(new_item)
        db.session.commit()
        
        flash("Menu item added successfully!", "success")
        return redirect(url_for('restaurant_menu', restaurant_id=restaurant_id))  # redirect to the menu page

    # GET request: render the form for adding an item
    return render_template('restaurant-add-item.html', restaurant=restaurant)

@app.route('/restaurant_delete_item/<int:restaurant_id>', methods=['GET', 'POST'])
def restaurant_delete_item(restaurant_id):
    # fetch the restaurant and its menu items
    restaurant = db.session.get(Restaurant, restaurant_id)
    if not restaurant:
        flash("Restaurant not found.", "danger")
        return redirect(url_for('restaurant_dashboard'))
    
    menu_items = MenuItem.query.filter_by(RestaurantID=restaurant_id).all()
    
    if request.method == 'POST':
        # get the list of items to delete
        item_ids_to_delete = request.form.getlist('delete_items')
        if item_ids_to_delete:
            for item_id in item_ids_to_delete:
                item = MenuItem.query.get(item_id)
                if item:
                    db.session.delete(item)
            db.session.commit()
            flash("Selected items have been deleted.", "success")
        else:
            flash("No items selected for deletion.", "warning")
        return redirect(url_for('restaurant_delete_item', restaurant_id=restaurant_id))
    
    return render_template('restaurant-delete-item.html', restaurant=restaurant, menu_items=menu_items)


@app.route('/restaurant_edit_item/<int:restaurant_id>/<int:item_id>', methods=['GET', 'POST'])
def restaurant_edit_item(restaurant_id, item_id):
    # fetch the restaurant and the specific item
    restaurant = db.session.get(Restaurant, restaurant_id)
    item = MenuItem.query.get(item_id)

    if not restaurant:
        flash("Restaurant not found.", "danger")
        return redirect(url_for('restaurant_dashboard'))

    if not item:
        flash("Item not found.", "danger")
        return redirect(url_for('restaurant_menu', restaurant_id=restaurant_id))

    if request.method == 'POST':
        # update the item's attributes based on the form fields
        item.Name = request.form['item_name']
        item.Description = request.form['item_description']
        item.Price = request.form['item_price']

        # commit changes to the database
        db.session.commit()
        flash("Item updated successfully.", "success")
        return redirect(url_for('restaurant_menu', restaurant_id=restaurant_id))

    # render the edit page with the item details
    return render_template(
        'restaurant-edit-item.html',
        restaurant=restaurant,
        item=item
    )


@app.route('/delete_items/<int:restaurant_id>', methods=['POST'])
def delete_items(restaurant_id):
    # get the list of items to delete
    item_ids_to_delete = request.form.getlist('delete_items')
    if item_ids_to_delete:
        for item_id in item_ids_to_delete:
            # find and delete the menu item
            item = MenuItem.query.get(item_id)
            if item:
                db.session.delete(item)
        db.session.commit()
        flash(f"{len(item_ids_to_delete)} item(s) have been deleted.", "success")
    else:
        flash("No items selected for deletion.", "warning")
    
    # redirect to the restaurant_delete_item route with the correct restaurant_id
    return redirect(url_for('restaurant_delete_item', restaurant_id=restaurant_id))


@app.route('/update_item/<int:item_id>', methods=['POST'])
def update_item(item_id):
    item = MenuItem.query.get(item_id)
    if not item:
        flash("Item not found.", "danger")
        return redirect(url_for('restaurant_menu'))
    
    # update item attributes
    item.Name = request.form['name']
    item.Description = request.form['description']
    item.Price = request.form['price']
    
    db.session.commit()
    flash("Item has been updated successfully.", "success")
    return redirect(url_for('restaurant_menu', restaurant_id=item.RestaurantID))


@app.route('/balance')
def balance():
    if 'user_id' not in session:
        return {"error": "User not logged in"}, 401

    user = db.session.get(User, session['user_id'])

    if user.UserType == UserType.Restaurant:
        restaurant = user.restaurant
        if not restaurant:
            return {"error": "Restaurant not found"}, 404

        completed_orders = Order.query.filter_by(RestaurantID=restaurant.RestaurantID, Status='Completed').all()
        total_balance = sum(order.RestaurantAmount for order in completed_orders)

        return {"balance": round(float(total_balance), 2)}

    elif user.UserType == UserType.Customer:
        customer = user.customer
        if not customer:
                return {"error": "Customer not found"}, 404
        return {"balance": round(float(customer.Balance), 2)}

    return {"error": "Balance not found"}, 404


@app.route('/cart')
def cart():
    user_id = session.get('user_id')
    if user_id is None:
        return redirect(url_for('login'))
    
    # query cart items and join with menu items
    cart_items = db.session.query(CartItem, MenuItem).join(MenuItem).filter(CartItem.UserID == user_id).all()

    # calculate the total price
    total_price = sum(float(menu_item.Price) * cart_item.Quantity for cart_item, menu_item in cart_items)

    # convert data to serializable format
    cart_items_serializable = [
        {
            'CartItemID': cart_item.CartItemID,
            'MenuItemID': menu_item.MenuItemID,
            'Name': menu_item.Name,
            'Description': menu_item.Description,
            'Price': str(menu_item.Price),  # convert Decimal to string
            'Quantity': cart_item.Quantity
        }
        for cart_item, menu_item in cart_items
    ]

    return render_template('customer-cart.html', cart_items=cart_items_serializable, total_price=total_price)


@app.route('/add_to_cart/<int:menu_item_id>')
def add_to_cart(menu_item_id):
    if 'user_id' not in session:
        flash("Please log in first", "warning")
        return redirect(url_for('login'))

    user_id = session['user_id']
    user = db.session.get(User, user_id)

    if user.UserType == UserType.Restaurant:
        flash("Restaurants cannot add items to the cart.", "warning")
        return redirect(url_for('restaurant_dashboard'))  # or redirect to a relevant restaurant page

    cart_item = CartItem.query.filter_by(UserID=user_id, MenuItemID=menu_item_id).first()

    if cart_item:
        # increment the quantity if the cart item already exists
        cart_item.Quantity += 1
    else:
        # create a new cart item if it doesn't exist
        cart_item = CartItem(UserID=user_id, MenuItemID=menu_item_id, Quantity=1)
        db.session.add(cart_item)

    # commit the session to save changes
    db.session.commit()

    flash("Item added to cart", "success")
    return redirect(url_for('cart'))


@app.route('/remove_from_cart/<int:menu_item_id>')
def remove_from_cart(menu_item_id):
    if 'user_id' not in session:
        flash("Please log in first", "warning")
        return redirect(url_for('login'))

    user_id = session['user_id']
    cart_item = CartItem.query.filter_by(UserID=user_id, MenuItemID=menu_item_id).first()

    if cart_item:
        if cart_item.Quantity > 1:
            cart_item.Quantity -= 1
        else:
            db.session.delete(cart_item)
        db.session.commit()

    flash("Item removed from cart", "success")
    return redirect(url_for('cart'))


if __name__ == '__main__':
    app.run(debug=True)