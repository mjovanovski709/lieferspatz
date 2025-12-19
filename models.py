from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import enum

# Initialize database
db = SQLAlchemy()

# Enum for UserType
class UserType(enum.Enum):
    Customer = "Customer"
    Restaurant = "Restaurant"

# User model
class User(db.Model):
    __tablename__ = 'Users'
    UserID = db.Column(db.Integer, primary_key=True)
    EmailAddress = db.Column(db.String(100), nullable=False, unique=True)
    Password = db.Column(db.String(255), nullable=False)
    UserType = db.Column(db.Enum(UserType), nullable=False)
    
    # Relationships
    customer = db.relationship('Customer', backref='user', uselist=False)
    restaurant = db.relationship('Restaurant', backref='user', uselist=False)
    cart_items = db.relationship('CartItem', backref='user', lazy=True)

# Customer model
class Customer(db.Model):
    __tablename__ = 'Customers'  # Add this line to specify the table name
    UserID = db.Column(db.Integer, db.ForeignKey('Users.UserID'), primary_key=True)
    FirstName = db.Column(db.String(50), nullable=False)
    LastName = db.Column(db.String(50), nullable=False)
    Address = db.Column(db.String(255), nullable=False) 
    PostNumber = db.Column(db.String(10), nullable=False) 
    Balance = db.Column(db.Float, default=100.0)



# Restaurant model
class Restaurant(db.Model):
    __tablename__ = 'Restaurants'
    RestaurantID = db.Column(db.Integer, primary_key=True)
    UserID = db.Column(db.Integer, db.ForeignKey('Users.UserID'), nullable=False)
    Name = db.Column(db.String(100), nullable=False)
    Address = db.Column(db.String(255), nullable=False) 
    PostalCode = db.Column(db.String(10), nullable=False)
    Description = db.Column(db.Text, nullable=True)
    ImageURL = db.Column(db.String(255), nullable=True) 
    OpenTime = db.Column(db.Time, nullable=False)
    CloseTime = db.Column(db.Time, nullable=False)
    
    # Relationships
    menu_items = db.relationship('MenuItem', backref='restaurant', lazy=True)
    orders = db.relationship('Order', backref='restaurant', lazy=True)
    delivery_areas = db.relationship('DeliveryArea', backref='restaurant', lazy=True)




# Menu Item model
class MenuItem(db.Model):
    __tablename__ = 'MenuItems'
    MenuItemID = db.Column(db.Integer, primary_key=True)
    RestaurantID = db.Column(db.Integer, db.ForeignKey('Restaurants.RestaurantID'), nullable=False)
    Name = db.Column(db.String(100), nullable=False)
    Description = db.Column(db.Text, nullable=False)
    Price = db.Column(db.Numeric(10, 2), nullable=False)
    Category = db.Column(db.String, nullable=False, default="Uncategorized")  # Add default value
    ImageURL = db.Column(db.String, nullable=True)
    IsAvailable = db.Column(db.Boolean, default=True)


# Cart Item model
class CartItem(db.Model):
    __tablename__ = 'CartItems'
    CartItemID = db.Column(db.Integer, primary_key=True)
    UserID = db.Column(db.Integer, db.ForeignKey('Users.UserID'), nullable=False)
    MenuItemID = db.Column(db.Integer, db.ForeignKey('MenuItems.MenuItemID'), nullable=False)
    Quantity = db.Column(db.Integer, default=1)

# Order model
class Order(db.Model):
    __tablename__ = 'Orders'
    OrderID = db.Column(db.Integer, primary_key=True)
    CustomerID = db.Column(db.Integer, db.ForeignKey('Users.UserID'), nullable=False)  # Changed this line
    RestaurantID = db.Column(db.Integer, db.ForeignKey('Restaurants.RestaurantID'), nullable=False)
    Status = db.Column(db.String, default='Processing', nullable=False)
    TotalAmount = db.Column(db.Numeric(10, 2), nullable=False)
    PlatformFee = db.Column(db.Numeric(10, 2), nullable=False)
    RestaurantAmount = db.Column(db.Numeric(10, 2), nullable=False)
    Notes = db.Column(db.Text, nullable=True)
    CreatedAt = db.Column(db.DateTime, default=db.func.current_timestamp())
    UpdatedAt = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    order_items = db.relationship('OrderItem', backref='order', lazy=True)
    customer = db.relationship('User', backref='orders', lazy=True)



# Order Item model
class OrderItem(db.Model):
    __tablename__ = 'OrderItems'
    OrderItemID = db.Column(db.Integer, primary_key=True)
    MenuItemName = db.Column(db.String(255), nullable=False)  # Store name at order time
    MenuItemPrice = db.Column(db.Numeric(10, 2), nullable=False)  # Store price at order time
    OrderID = db.Column(db.Integer, db.ForeignKey('Orders.OrderID'), nullable=False)
    Quantity = db.Column(db.Integer, nullable=False)


# Delivery Area model
class DeliveryArea(db.Model):
    __tablename__ = 'DeliveryAreas'
    ID = db.Column(db.Integer, primary_key=True)
    RestaurantID = db.Column(db.Integer, db.ForeignKey('Restaurants.RestaurantID'), nullable=False)
    PostalCode = db.Column(db.String(10), nullable=False)

# Opening Hour model
class OpeningHour(db.Model):
    __tablename__ = 'OpeningHours'
    OpeningHourID = db.Column(db.Integer, primary_key=True)
    RestaurantID = db.Column(db.Integer, db.ForeignKey('Restaurants.RestaurantID'), nullable=False)
    DayOfWeek = db.Column(db.Integer, nullable=False)  # 0 (Monday) - 6 (Sunday)
    OpenTime = db.Column(db.String, nullable=False)
    CloseTime = db.Column(db.String, nullable=False)

# Platform model (for tracking platform balance)
class Platform(db.Model):
    __tablename__ = 'Platform'
    PlatformID = db.Column(db.Integer, primary_key=True)
    Balance = db.Column(db.Numeric(10, 2), default=0.00)