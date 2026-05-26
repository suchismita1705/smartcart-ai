from flask import Flask, render_template, request, redirect, session, url_for
from flask_sqlalchemy import SQLAlchemy
import requests
import random
import smtplib
from email.mime.text import MIMEText

app = Flask(__name__)

# ====================================
# SECRET KEY & DB CONFIG
# ====================================
app.secret_key = "smartcart_secret_key"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///smartcart.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# ====================================
# EMAIL CONFIG
# ====================================
EMAIL_ADDRESS = "smartcartai2026@gmail.com"
EMAIL_PASSWORD = "ttrs llvr jxtz ljwv"

# ====================================
# DATABASE TABLES
# ====================================
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100))
    product_name = db.Column(db.String(200))
    product_price = db.Column(db.Integer)
    product_image = db.Column(db.String(500))
    order_id = db.Column(db.String(100))
    status = db.Column(db.String(100))
    payment = db.Column(db.String(100))

class Wishlist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100))
    product_id = db.Column(db.Integer)
    product_name = db.Column(db.String(200))
    product_price = db.Column(db.Integer)
    product_image = db.Column(db.String(500))
    rating = db.Column(db.Float)
    discount = db.Column(db.Float)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200))
    price = db.Column(db.Integer)
    image = db.Column(db.String(500))
    category = db.Column(db.String(100))
    rating = db.Column(db.Float)
    discount = db.Column(db.Float)
    description = db.Column(db.Text)

# ====================================
# CREATE DATABASE
# ====================================
with app.app_context():
    db.create_all()

# ====================================
# TEMP CART & FETCH PRODUCTS
# ====================================
cart = []
API_URL = "https://dummyjson.com/products?limit=100"
products = []

try:
    response = requests.get(API_URL, timeout=20)
    response.raise_for_status()
    data = response.json()
    for item in data.get("products", []):
        products.append({
            "id": item["id"],
            "name": item["title"],
            "price": int(item["price"] * 85),
            "description": item["description"],
            "image": item["thumbnail"],
            "rating": round(item["rating"], 1),
            "discount": round(item["discountPercentage"], 1),
            "category": item["category"]
        })
except Exception as e:
    print("API Error:", e)

# ====================================
# EMAIL HELPER
# ====================================
def send_order_email(customer_email, product_name, order_id):
    try:
        subject = "SmartCart AI - Order Confirmed"
        body = f"Hello,\n\nYour order has been placed successfully 🎉\n\nOrder ID:\n{order_id}\n\nProduct:\n{product_name}\n\nThank you for shopping with SmartCart AI 🚀"
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = customer_email
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
    except Exception as e:
        print("Email Error:", e)

# ====================================
# ROUTES
# ====================================
@app.route("/")
def home():
    search = request.args.get("search", "").lower()
    category = request.args.get("category", "")

    # Start with all products fetched from the API
    filtered_products = products

    # Apply search filter
    if search:
        filtered_products = [
            p for p in filtered_products 
            if search in p["name"].lower() or search in p["description"].lower()
        ]
        
    # Apply category filter
    if category:
        filtered_products = [
            p for p in filtered_products 
            if p["category"] == category
        ]

    # Get unique categories directly from the API products
    categories = sorted(list(set(p["category"] for p in products)))

    wishlist_count = 0
    if session.get("user"):
        wishlist_count = Wishlist.query.filter_by(username=session["user"]).count()

    return render_template(
        "index.html",
        products=filtered_products,
        categories=categories,
        cart_count=len(cart),
        wishlist_count=wishlist_count
    )

@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user"): return redirect(url_for("home"))
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        if User.query.filter_by(email=email).first():
            return render_template("register.html", error="Account already exists. Please Log In.")
        new_user = User(name=name, email=email, password=password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user"): return redirect(url_for("home"))
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        user = User.query.filter_by(email=email, password=password).first()
        if user:
            session["user"] = user.name
            return redirect(url_for("home"))
        return render_template("login.html", error="Invalid Email Or Password")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect("/")

@app.route("/product/<int:id>")
def product_page(id):
    selected_product = next((p for p in products if p["id"] == id), None)
    related = [p for p in products if selected_product and p["category"] == selected_product["category"] and p["id"] != id][:4]
    w_count = Wishlist.query.filter_by(username=session.get("user", "")).count() if session.get("user") else 0
    return render_template("product.html", product=selected_product, related_products=related, cart_count=len(cart), wishlist_count=w_count)

@app.route("/add_to_cart/<int:id>")
def add_to_cart(id):
    for p in products:
        if p["id"] == id:
            for item in cart:
                if item["id"] == id:
                    item["quantity"] += 1
                    return redirect("/cart")
            p["quantity"] = 1
            cart.append(p)
            break
    return redirect("/cart")

@app.route("/cart")
def cart_page():
    total = sum(item["price"] * item["quantity"] for item in cart)
    return render_template("cart.html", cart=cart, total=total)

@app.route("/increase_quantity/<int:id>")
def increase_quantity(id):
    for item in cart:
        if item["id"] == id: item["quantity"] += 1
    return redirect("/cart")

@app.route("/decrease_quantity/<int:id>")
def decrease_quantity(id):
    for item in cart:
        if item["id"] == id and item["quantity"] > 1: item["quantity"] -= 1
    return redirect("/cart")

@app.route("/remove_from_cart/<int:id>")
def remove_from_cart(id):
    for item in cart:
        if item["id"] == id:
            cart.remove(item)
            break
    return redirect("/cart")

@app.route("/wishlist")
def wishlist_page():
    if not session.get("user"): return redirect("/login")
    items = Wishlist.query.filter_by(username=session["user"]).all()
    return render_template("wishlist.html", wishlist=items)

@app.route("/add_to_wishlist/<int:id>")
def add_to_wishlist(id):
    if not session.get("user"): return redirect("/login")
    for p in products:
        if p["id"] == id:
            if not Wishlist.query.filter_by(username=session["user"], product_id=id).first():
                db.session.add(Wishlist(username=session["user"], product_id=id, product_name=p["name"], product_price=p["price"], product_image=p["image"], rating=p["rating"], discount=p["discount"]))
                db.session.commit()
            break
    return redirect("/wishlist")

@app.route("/remove_from_wishlist/<int:id>")
def remove_from_wishlist(id):
    if not session.get("user"): return redirect("/login")
    item = Wishlist.query.filter_by(username=session["user"], product_id=id).first()
    if item:
        db.session.delete(item)
        db.session.commit()
    return redirect("/wishlist")

@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    if request.method == "POST":
        email = request.form.get("email")
        payment = request.form.get("payment")
        order_ids_created = []
        
        for item in cart:
            order_id = "SCART" + str(random.randint(10000, 99999))
            db.session.add(Order(
                username=session.get("user", "Guest"), 
                product_name=item["name"], 
                product_price=item["price"], 
                product_image=item["image"], 
                order_id=order_id, 
                status="Ordered", 
                payment=payment
            ))
            db.session.commit()
            send_order_email(email, item["name"], order_id)
            order_ids_created.append(order_id)
            
        cart.clear()
        
        display_order_id = order_ids_created[0] if order_ids_created else ""
        return render_template("order_success.html", order_id=display_order_id)
        
    return render_template("checkout.html")

@app.route("/orders")
def order_page():
    if not session.get("user"): return redirect("/login")
    orders = Order.query.filter_by(username=session["user"]).all()
    return render_template("orders.html", orders=orders)

@app.route("/update_status/<int:id>/<string:new_status>")
def update_status(id, new_status):
    if not session.get("user"): return redirect("/login")
    order = Order.query.get(id)
    if order:
        order.status = new_status
        db.session.commit()
    return redirect("/orders")

# ====================================
# BUILT-IN PRODUCT MATCHING CHATBOT
# ====================================
@app.route("/chatbot", methods=["GET", "POST"])
def chatbot_page():
    if not session.get("user"): 
        return redirect("/login")
        
    bot_reply = None
    
    if request.method == "POST":
        # 1. Get what the user typed and make it lowercase
        user_message = request.form.get("message", "").lower()
        
        # 2. Words to ignore so the search is more accurate
        stop_words = ["i", "need", "want", "a", "good", "cheap", "best", "some", "the", "for", "looking", "can", "you", "show", "me"]
        
        # 3. Clean the user's message to find the actual "keywords"
        search_words = [word for word in user_message.split() if word not in stop_words and len(word) > 2]
        
        matched_products = []
        
        # 4. If we found keywords, search our product list!
        if search_words:
            for product in products:
                # Check if any of the keywords match the product name, description, or category
                product_text = (product["name"] + " " + product["description"] + " " + product["category"]).lower()
                
                # If a match is found, add it to our list
                if any(word in product_text for word in search_words):
                    matched_products.append(product)
            
            # 5. Format the reply based on what we found
            if matched_products:
                # Take the top 3 matches to keep the reply short
                top_matches = matched_products[:3]
                
                reply_text = "I found some great options for you! 🛍️<br><br>"
                for p in top_matches:
                    # Create a clickable link to the product page
                    reply_text += f"• <a href='/product/{p['id']}' style='color:#38bdf8; text-decoration:none; font-weight:bold;'>{p['name']}</a> - ₹{p['price']}<br>"
                
                bot_reply = reply_text
            else:
                bot_reply = "I couldn't find any exact matches for that right now. Could you try asking about a different category, like 'smartphones' or 'groceries'?"
                
        else:
            bot_reply = "Hmm, I didn't quite catch that. Try asking for specific things like 'laptops', 'fragrance', or 'beauty products'!"

    return render_template("chatbot.html", bot_reply=bot_reply)

if __name__ == "__main__":
    app.run(debug=True)