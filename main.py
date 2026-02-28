from flask import Flask, render_template, request, jsonify, send_from_directory, session
import json
import os
from datetime import datetime, timedelta
import numpy as np
from pathlib import Path

app = Flask(__name__, template_folder='templates')
app.secret_key = 'dti_secret_key_2026'  # For session 

# Load users (farmers and buyers)
def load_users():
    with open(os.path.join('templates', 'users.json'), 'r') as f:
        return json.load(f)

# Load crop data
def load_crops():
    with open(os.path.join('templates', 'crop_data.json'), 'r') as f:
        return json.load(f)

# Load farmer products
def load_farmer_products():
    file_path = os.path.join('templates', 'farmer_products.json')
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_farmer_products(products):
    file_path = os.path.join('templates', 'farmer_products.json')
    with open(file_path, 'w') as f:
        json.dump(products, f, indent=2)

# Load subscriptions
def load_subscriptions():
    file_path = os.path.join('templates', 'subscriptions.json')
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except:
        return []

def save_subscriptions(subscriptions):
    file_path = os.path.join('templates', 'subscriptions.json')
    with open(file_path, 'w') as f:
        json.dump(subscriptions, f, indent=2)

# Simple linear regression for price prediction
def predict_next_week(history):
    """Predict prices for next 7 days using simple linear regression"""
    x = np.arange(len(history))
    y = np.array(history)
    
    # Fit line
    coeffs = np.polyfit(x, y, 1)
    poly = np.poly1d(coeffs)
    
    # Predict next 7 days
    next_x = np.arange(len(history), len(history) + 7)
    predictions = poly(next_x).tolist()
    
    # Ensure no negative prices
    predictions = [max(p, 0) for p in predictions]
    return predictions

@app.route('/')
def index():
    # Check if user is logged in
    if 'user_id' in session:
        crops = load_crops()
        return render_template('index.html', crops=crops)
    else:
        return render_template('login.html')

# Login Route
@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    user_type = data.get('user_type')  # 'farmer' or 'buyer'
    
    users = load_users()
    
    # Search in farmers or buyers
    user_list = users.get(user_type + 's', [])  # 'farmers' or 'buyers'
    
    for user in user_list:
        if user['email'] == email and user['password'] == password:
            # Store user info in session
            session['user_id'] = user['user_id']
            session['name'] = user['name']
            session['email'] = user['email']
            session['user_type'] = user_type
            
            return jsonify({
                'success': True,
                'message': f"Welcome {user['name']}!",
                'user_id': user['user_id'],
                'user_type': user_type,
                'name': user['name']
            }), 200
    
    return jsonify({'success': False, 'message': 'Invalid email or password'}), 401

# Logout Route
@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True, 'message': 'Logged out successfully'}), 200

# Get Current User Info
@app.route('/api/user-info', methods=['GET'])
def get_user_info():
    if 'user_id' in session:
        return jsonify({
            'user_id': session['user_id'],
            'name': session['name'],
            'email': session['email'],
            'user_type': session['user_type']
        }), 200
    return jsonify({'error': 'Not logged in'}), 401

@app.route('/api/crops')
def get_crops():
    crops = load_crops()
    return jsonify(crops)

@app.route('/api/marketplace-crops')
def get_marketplace_crops():
    """Get all crops from crop_data.json + farmer_products.json for marketplace display"""
    crops = load_crops()
    
    # Also include farmer products
    farmer_products = load_farmer_products()
    users = load_users()
    
    # Create a dict to store all items
    all_items = dict(crops)
    
    # Add farmer products
    for farmer_id, products in farmer_products.items():
        # Find farmer name
        farmer_name = 'Unknown Farmer'
        for farmer in users.get('farmers', []):
            if farmer['user_id'] == farmer_id:
                farmer_name = farmer['name']
                break
        
        # Add each farmer product to marketplace
        for product in products:
            item_key = f"{product['name'].lower().replace(' ', '_')}_{farmer_id}"
            all_items[item_key] = {
                'info': {
                    'price': product['price'],
                    'location': 'Farm',
                    'trend': 'Up'
                },
                'history': [int(product['price'] * 0.8), int(product['price'] * 0.85), int(product['price'] * 0.9), 
                           int(product['price'] * 0.95), product['price'], product['price'], product['price']],
                'phone': '',
                'farmer_name': farmer_name,
                'description': product.get('description', f"{product['name']} from {farmer_name}"),
                'farmer_id': farmer_id,
                'quantity_available': product.get('quantity', 0),
                'quality': product.get('quality', 'Grade A'),
                'is_farmer_product': True
            }
    
    return jsonify(all_items)

@app.route('/api/predict/<crop_name>')
def predict_price(crop_name):
    crops = load_crops()
    if crop_name not in crops:
        return jsonify({'error': 'Crop not found'}), 404
    
    history = crops[crop_name]['history']
    predictions = predict_next_week(history)
    
    # Generate dates for next 7 days
    today = datetime.now()
    dates = [(today + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(1, 8)]
    
    return jsonify({
        'crop': crop_name,
        'current_price': crops[crop_name]['info']['price'],
        'dates': dates,
        'predictions': predictions
    })

@app.route('/api/order', methods=['POST'])
def create_order():
    # Check if user is logged in
    if 'user_id' not in session:
        return jsonify({'error': 'Please log in to place an order'}), 401
    
    data = request.json
    
    crops = load_crops()
    if data['crop'] not in crops:
        return jsonify({'error': 'Crop not found'}), 404
    
    crop_data = crops[data['crop']]
    total_price = crop_data['info']['price'] * data['quantity']
    
    # Get farmer info from crop data
    farmer_name = crop_data.get('farmer_name', 'Unknown')
    farmer_phone = crop_data.get('phone', '')
    
    # Get buyer info from session
    buyer_id = session.get('user_id')
    buyer_name = session.get('name', 'Unknown')
    
    # Get farmer_id by matching farmer name
    users = load_users()
    farmer_id = 'unknown'
    for farmer in users.get('farmers', []):
        if farmer['name'] == farmer_name:
            farmer_id = farmer['user_id']
            break
    
    order = {
        'order_id': f"ORD-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        'crop': data['crop'],
        'quantity': data['quantity'],
        'unit': data.get('unit', 'kg'),
        'unit_price': crop_data['info']['price'],
        'total_price': total_price,
        'farmer_id': farmer_id,
        'farmer_name': farmer_name,
        'farmer_phone': farmer_phone,
        'farmer_location': crop_data['info']['location'],
        'buyer_id': buyer_id,
        'buyer_name': buyer_name,
        'order_date': datetime.now().isoformat(),
        'status': 'Pending Confirmation'
    }
    
    # Save order (in production, use database)
    orders_file = 'templates/orders.json'
    try:
        with open(orders_file, 'r') as f:
            orders = json.load(f)
    except:
        orders = []
    
    orders.append(order)
    with open(orders_file, 'w') as f:
        json.dump(orders, f, indent=2)
    
    return jsonify(order)

@app.route('/api/orders')
def get_orders():
    orders_file = 'templates/orders.json'
    try:
        with open(orders_file, 'r') as f:
            orders = json.load(f)
    except:
        orders = []
    return jsonify(orders)

@app.route('/api/orders/farmer/<farmer_id>')
def get_farmer_orders(farmer_id):
    """Get all orders placed FOR a specific farmer's crops"""
    orders_file = 'templates/orders.json'
    try:
        with open(orders_file, 'r') as f:
            all_orders = json.load(f)
    except:
        all_orders = []
    
    # Filter orders by farmer_id
    farmer_orders = [order for order in all_orders if order.get('farmer_id') == farmer_id]
    return jsonify(farmer_orders)

@app.route('/api/orders/buyer/<buyer_id>')
def get_buyer_orders(buyer_id):
    """Get all orders placed BY a specific buyer"""
    orders_file = 'templates/orders.json'
    try:
        with open(orders_file, 'r') as f:
            all_orders = json.load(f)
    except:
        all_orders = []
    
    # Filter orders by buyer_id
    buyer_orders = [order for order in all_orders if order.get('buyer_id') == buyer_id]
    return jsonify(buyer_orders)

@app.route('/api/orders/<order_id>/status', methods=['PUT'])
def update_order_status(order_id):
    """Update order status (Farmer confirms/rejects order)"""
    if 'user_id' not in session:
        return jsonify({'error': 'Please log in'}), 401
    
    data = request.json
    new_status = data.get('status')  # e.g., 'Confirmed', 'Rejected', 'Delivered'
    
    orders_file = 'templates/orders.json'
    try:
        with open(orders_file, 'r') as f:
            orders = json.load(f)
    except:
        orders = []
    
    # Find and update the order
    for order in orders:
        if order.get('order_id') == order_id:
            # Check if current user is the farmer
            if order.get('farmer_id') != session.get('user_id') and session.get('user_type') != 'admin':
                return jsonify({'error': 'You can only update your own orders'}), 403
            
            order['status'] = new_status
            order['updated_at'] = datetime.now().isoformat()
            
            # Save updated orders
            with open(orders_file, 'w') as f:
                json.dump(orders, f, indent=2)
            
            return jsonify({'success': True, 'message': f'Order {order_id} status updated to {new_status}', 'order': order}), 200
    
    return jsonify({'error': 'Order not found'}), 404

# Farmer Product Management
@app.route('/api/farmer/products/<farmer_id>', methods=['GET'])
def get_farmer_products(farmer_id):
    products = load_farmer_products()
    farmer_products = products.get(farmer_id, [])
    return jsonify(farmer_products)

@app.route('/api/farmer/products/<farmer_id>', methods=['POST'])
def add_farmer_product(farmer_id):
    data = request.json
    products = load_farmer_products()
    
    if farmer_id not in products:
        products[farmer_id] = []
    
    product = {
        'product_id': f"PROD-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        'name': data['name'],
        'price': float(data['price']),
        'quantity': float(data['quantity']),
        'unit': data.get('unit', 'kg'),
        'description': data.get('description', ''),
        'quality': data.get('quality', 'Grade A'),
        'created_date': datetime.now().isoformat()
    }
    
    products[farmer_id].append(product)
    save_farmer_products(products)
    
    return jsonify({'success': True, 'product': product}), 201

@app.route('/api/farmer/products/<farmer_id>/<product_id>', methods=['PUT'])
def update_farmer_product(farmer_id, product_id):
    data = request.json
    products = load_farmer_products()
    
    if farmer_id in products:
        for product in products[farmer_id]:
            if product['product_id'] == product_id:
                product.update({
                    'name': data.get('name', product['name']),
                    'price': float(data.get('price', product['price'])),
                    'quantity': float(data.get('quantity', product['quantity'])),
                    'unit': data.get('unit', product['unit']),
                    'description': data.get('description', product['description']),
                    'quality': data.get('quality', product['quality']),
                    'updated_date': datetime.now().isoformat()
                })
                save_farmer_products(products)
                return jsonify({'success': True, 'product': product})
    
    return jsonify({'error': 'Product not found'}), 404

@app.route('/api/farmer/products/<farmer_id>/<product_id>', methods=['DELETE'])
def delete_farmer_product(farmer_id, product_id):
    products = load_farmer_products()
    
    if farmer_id in products:
        products[farmer_id] = [p for p in products[farmer_id] if p['product_id'] != product_id]
        save_farmer_products(products)
        return jsonify({'success': True})
    
    return jsonify({'error': 'Product not found'}), 404

# Subscription Management
@app.route('/api/subscriptions', methods=['GET'])
def get_subscriptions():
    subscriptions = load_subscriptions()
    return jsonify(subscriptions)

@app.route('/api/subscriptions', methods=['POST'])
def create_subscription():
    data = request.json
    subscriptions = load_subscriptions()
    
    # Validate subscription period
    if data['period'] not in ['weekly', 'biweekly', 'monthly']:
        return jsonify({'error': 'Invalid subscription period'}), 400
    
    subscription = {
        'subscription_id': f"SUB-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        'buyer_name': data['buyer_name'],
        'buyer_phone': data['buyer_phone'],
        'buyer_email': data.get('buyer_email', ''),
        'farmer_id': data['farmer_id'],
        'product_name': data['product_name'],
        'quantity': float(data['quantity']),
        'unit': data.get('unit', 'kg'),
        'price_per_unit': float(data['price_per_unit']),
        'frequency': data['period'],  # weekly, biweekly, monthly
        'start_date': datetime.now().isoformat(),
        'next_delivery': calculate_next_delivery(data['period']),
        'total_cost': float(data['quantity']) * float(data['price_per_unit']),
        'deliveries_completed': 0,
        'status': 'Active',
        'payment_method': data.get('payment_method', 'auto-debit'),
        'auto_renew': True
    }
    
    subscriptions.append(subscription)
    save_subscriptions(subscriptions)
    
    return jsonify({'success': True, 'subscription': subscription}), 201

@app.route('/api/subscriptions/<subscription_id>', methods=['GET'])
def get_subscription(subscription_id):
    subscriptions = load_subscriptions()
    for sub in subscriptions:
        if sub['subscription_id'] == subscription_id:
            return jsonify(sub)
    return jsonify({'error': 'Subscription not found'}), 404

@app.route('/api/subscriptions/<subscription_id>', methods=['PUT'])
def update_subscription(subscription_id):
    data = request.json
    subscriptions = load_subscriptions()
    
    for sub in subscriptions:
        if sub['subscription_id'] == subscription_id:
            if 'status' in data:
                sub['status'] = data['status']
            if 'quantity' in data:
                sub['quantity'] = float(data['quantity'])
                sub['total_cost'] = sub['quantity'] * sub['price_per_unit']
            save_subscriptions(subscriptions)
            return jsonify({'success': True, 'subscription': sub})
    
    return jsonify({'error': 'Subscription not found'}), 404

@app.route('/api/subscriptions/<subscription_id>', methods=['DELETE'])
def cancel_subscription(subscription_id):
    subscriptions = load_subscriptions()
    
    for sub in subscriptions:
        if sub['subscription_id'] == subscription_id:
            sub['status'] = 'Cancelled'
            save_subscriptions(subscriptions)
            return jsonify({'success': True, 'message': 'Subscription cancelled'})
    
    return jsonify({'error': 'Subscription not found'}), 404

@app.route('/api/subscriptions/<subscription_id>/payment', methods=['POST'])
def process_subscription_payment(subscription_id):
    """Process automatic payment for subscription"""
    subscriptions = load_subscriptions()
    
    for sub in subscriptions:
        if sub['subscription_id'] == subscription_id and sub['status'] == 'Active':
            payment = {
                'payment_id': f"PAY-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                'subscription_id': subscription_id,
                'amount': sub['total_cost'],
                'payment_date': datetime.now().isoformat(),
                'status': 'Completed',
                'payment_method': sub['payment_method'],
                'next_payment_date': calculate_next_delivery(sub['frequency'])
            }
            
            # Update subscription
            sub['deliveries_completed'] += 1
            sub['next_delivery'] = calculate_next_delivery(sub['frequency'])
            save_subscriptions(subscriptions)
            
            return jsonify({'success': True, 'payment': payment}), 201
    
    return jsonify({'error': 'Subscription not found or inactive'}), 404

def calculate_next_delivery(frequency):
    """Calculate next delivery date based on frequency"""
    days_map = {
        'weekly': 7,
        'biweekly': 14,
        'monthly': 30
    }
    days = days_map.get(frequency, 30)
    next_date = datetime.now() + timedelta(days=days)
    return next_date.isoformat()

if __name__ == '__main__':
    app.run(debug=True, port=5000)