from app import db, app  # Import your Flask app and database instance
from models import User, Restaurant, MenuItem, DeliveryArea, UserType  # Import all necessary models
from decimal import Decimal
from datetime import time  # Add this import
import random

# Postal codes for delivery
postal_codes = [
    47547, 47546, 46509, 46507, 47051, 47053, 47055, 47057,
    47059, 47061, 47063, 47065, 47067, 47069, 47071, 47073, 47075
]

# Random restaurant opening hours
def random_time():
    open_hour = random.randint(6, 10)  # Open between 6 AM and 10 AM
    close_hour = random.randint(18, 23)  # Close between 6 PM and 11 PM
    return f"{open_hour:02d}:00", f"{close_hour:02d}:00"

# Restaurant data
restaurant_names = [
    "El Poncho", "El Toro", "Balkan Grill", "Mama's Pizza",
    "Schnitzel Haus", "Burger Meister", "Sushi World",
    "Taco Town", "Curry King", "Pasta Bella"
]

german_streets = [
    "Berliner Str. 23", "Hauptstr. 45", "Kaiserallee 7",
    "Mozartstr. 10", "Goethestr. 16", "Schillerstr. 50",
    "Lindenweg 12", "Marktplatz 30", "Rheinstr. 25", "Bismarckstr. 60"
]

# Sample menu item names and descriptions
menu_item_names = [
    "Mozzarella Pizza", "Balkan Burger", "Spaghetti Carbonara", "Grilled Chicken",
    "Caesar Salad", "BBQ Ribs", "Margherita Pizza", "Tuna Salad", "Chicken Alfredo",
    "Beef Lasagna"
]

menu_item_descriptions = [
    "Tasty flavoured just like in Italy",
    "Rich and juicy with Balkan spices",
    "Creamy and delightful pasta dish",
    "Perfectly grilled, tender and juicy",
    "Crisp lettuce with tangy dressing",
    "Fall-off-the-bone BBQ goodness",
    "Classic, fresh and mouth-watering",
    "Light and refreshing with greens",
    "Delicious creamy pasta perfection",
    "Layers of pasta and rich sauce"
]

def create_restaurants():
    for i, name in enumerate(restaurant_names):
        open_time, close_time = random_time()

        # Convert open_time and close_time strings to Python time objects
        open_time_obj = time(int(open_time.split(":")[0]), int(open_time.split(":")[1]))
        close_time_obj = time(int(close_time.split(":")[0]), int(close_time.split(":")[1]))

        postal_code = random.choice(postal_codes)
        delivery_areas = random.sample(postal_codes, k=5)

        # Create a User for the restaurant
        user = User(
            EmailAddress=f"{name.lower().replace(' ', '')}@web.de",
            Password="password",
            UserType=UserType.Restaurant
        )
        db.session.add(user)
        db.session.flush()

        # Create a Restaurant associated with the User
        restaurant = Restaurant(
            UserID=user.UserID,
            Name=name,
            Address=german_streets[i],
            PostalCode=postal_code,
            OpenTime=open_time_obj,  # Use the time object
            CloseTime=close_time_obj,  # Use the time object
            Description=f"Welcome to {name}, the best in town!"
        )
        db.session.add(restaurant)
        db.session.flush()

        # Add delivery areas
        for area in delivery_areas:
            delivery_area = DeliveryArea(RestaurantID=restaurant.RestaurantID, PostalCode=area)
            db.session.add(delivery_area)

        # Add menu items

# Update menu item creation logic
        for j in range(10):
            item_name = menu_item_names[j % len(menu_item_names)]  # Cycle through names
            description = menu_item_descriptions[j % len(menu_item_descriptions)]  # Cycle through descriptions
            price = Decimal(f"{random.randint(5, 20)},{random.randint(10, 99)}".replace(",", "."))  # Generate random decimal prices

            menu_item = MenuItem(
            RestaurantID=restaurant.RestaurantID,
            Name=item_name,
            Description=description,
            Price=price
            )
            db.session.add(menu_item)

    db.session.commit()
    print("Restaurants and their menu items added successfully!")


if __name__ == "__main__":
    # Ensure tables are created
    with app.app_context():
        db.create_all()
        print("Tables created successfully!")
        create_restaurants()  # Populate the database
