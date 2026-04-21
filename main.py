from flask import Flask, render_template, request, jsonify, send_from_directory, session
import json
import os
from datetime import datetime, timedelta
import numpy as np
from pathlib import Path
import re

app = Flask(__name__, template_folder='templates')
app.secret_key = 'dti_secret_key_2026'  # For session 

# Load users (farmers and buyers)
def load_users():
    with open(os.path.join('templates', 'users.json'), 'r') as f:
        return json.load(f)

# Save users data
def save_users(users):
    with open(os.path.join('templates', 'users.json'), 'w') as f:
        json.dump(users, f, indent=2)

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

def predict_next_5_months(history):
    """Predict prices for the next 5 months using a combination of linear trend, seasonality, and noise based on 10 years (10 data points)"""
    import math
    import random
    
    # We have 10 data points (representing 10 years). Let's extrapolate a monthly trend.
    # To get a 5-month prediction, we need to interpolate the yearly data into monthly,
    # or just treat the 'history' as the broad trend and predict the next 5 steps.
    
    # We'll calculate the overall yearly slope first
    x_yearly = np.arange(len(history))
    y_yearly = np.array(history)
    
    # Fit line to get long-term trend
    coeffs = np.polyfit(x_yearly, y_yearly, 1)
    slope_yearly = coeffs[0]
    intercept = coeffs[1]
    
    # Calculate average monthly slope
    slope_monthly = slope_yearly / 12
    
    # Start our prediction from the last known price to ensure continuity
    current_price = history[-1]
    
    predictions = []
    
    # Predict next 5 months
    for month in range(1, 6):
        # Base trend price for this upcoming month
        trend_price = current_price + (slope_monthly * month)
        
        # Add some seasonality (sine wave based on the month of the year to simulate harvest seasons)
        # Let's assume current month is April (month 4), so future months are 5, 6, 7, 8, 9
        future_month_idx = datetime.now().month + month
        seasonality = math.sin((future_month_idx / 12.0) * 2 * math.pi) * (current_price * 0.05) # +/- 5% fluctuation
        
        # Add noise (random fluctuation between -2% and +2%)
        noise = current_price * random.uniform(-0.02, 0.02)
        
        predicted_val = trend_price + seasonality + noise
        
        # Ensure no negative prices
        predictions.append(max(int(predicted_val), 0))
        
    return predictions

def get_all_marketplace_items():
    crops = load_crops()
    farmer_products = load_farmer_products()
    users = load_users()
    
    all_items = {}
    for k, v in crops.items():
        all_items[k] = dict(v)
        all_items[k]['display_name'] = k.replace('_', ' ').capitalize()
        
    for farmer_id, products in farmer_products.items():
        farmer_name = 'Unknown Farmer'
        for farmer in users.get('farmers', []):
            if farmer['user_id'] == farmer_id:
                farmer_name = farmer['name']
                break
                
        for product in products:
            item_key = f"{product['name'].lower().replace(' ', '_')}_{farmer_id}"
            all_items[item_key] = {
                'display_name': product['name'],
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
            
    return all_items

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

# Register Route
@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')
    phone = data.get('phone')
    location = data.get('location')
    user_type = data.get('user_type')  # 'farmer' or 'buyer'
    facial_data = data.get('facial_data', '')
    
    # Validate input
    if not all([name, email, password, phone, location, user_type]):
        return jsonify({'success': False, 'message': 'All fields are required'}), 400
    
    if user_type not in ['farmer', 'buyer']:
        return jsonify({'success': False, 'message': 'Invalid user type'}), 400
    
    users = load_users()
    user_list = users.get(user_type + 's', [])  # 'farmers' or 'buyers'
    
    # Check if email already exists
    for user in user_list:
        if user['email'] == email:
            return jsonify({'success': False, 'message': 'Email already registered'}), 409
    
    # Generate new user ID
    existing_ids = [int(user['user_id'].split('_')[1]) for user in user_list if '_' in user['user_id']]
    new_id_num = max(existing_ids) + 1 if existing_ids else 1
    new_user_id = f"{user_type}_{new_id_num:03d}"
    
    # Create new user
    new_user = {
        'user_id': new_user_id,
        'name': name,
        'email': email,
        'password': password,
        'phone': phone,
        'location': location,
        'facial_data': facial_data
    }
    
    # Add crops_grown for farmers
    if user_type == 'farmer':
        new_user['crops_grown'] = []
    
    # Add to user list and save
    user_list.append(new_user)
    users[user_type + 's'] = user_list
    save_users(users)
    
    return jsonify({
        'success': True,
        'message': f'Account created successfully! You can now login.',
        'user_id': new_user_id
    }), 201

# Face Login Route
@app.route('/api/face-login', methods=['POST'])
def face_login():
    data = request.json
    email = data.get('email')
    user_type = data.get('user_type')
    face_image = data.get('face_image')

    if not email or not user_type or not face_image:
        return jsonify({'success': False, 'message': 'Missing email, user type, or face image.'}), 400

    users = load_users()
    user_list = users.get(user_type + 's', [])
    
    for user in user_list:
        if user['email'] == email:
            if not user.get('facial_data'):
                return jsonify({'success': False, 'message': 'No facial data registered for this account. Please login with password.'}), 401
            
            # Here we "simulate" the ML comparison. In a real app we'd compare `user['facial_data']` with `face_image`.
            # Since both are set and we are simulating:
            session['user_id'] = user['user_id']
            session['name'] = user['name']
            session['email'] = user['email']
            session['user_type'] = user_type
            
            return jsonify({
                'success': True,
                'message': f"Face verified successfully. Welcome back {user['name']}!",
                'user_id': user['user_id'],
                'user_type': user_type,
                'name': user['name']
            }), 200
            
    return jsonify({'success': False, 'message': 'Email not found.'}), 404

# Update Face Profile Route
@app.route('/api/update-face', methods=['POST'])
def update_face():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
        
    data = request.json
    face_image = data.get('facial_data')
    if not face_image:
        return jsonify({'error': 'No image provided'}), 400
        
    user_type = session['user_type']
    user_id = session['user_id']
    
    users = load_users()
    user_list = users.get(user_type + 's', [])
    
    updated = False
    for user in user_list:
        if user['user_id'] == user_id:
            user['facial_data'] = face_image
            updated = True
            break
            
    if updated:
        save_users(users)
        return jsonify({'success': True, 'message': 'Facial ID updated securely.'}), 200
    
    return jsonify({'error': 'User not found'}), 404

# Logout Route
@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True, 'message': 'Logged out successfully'}), 200

# Get Current User Info
@app.route('/api/user-info', methods=['GET'])
def get_user_info():
    if 'user_id' in session:
        # Check if they have facial data
        users = load_users()
        user_list = users.get(session['user_type'] + 's', [])
        has_face = False
        location = ""
        phone = ""
        for u in user_list:
            if u['user_id'] == session['user_id']:
                has_face = bool(u.get('facial_data'))
                location = u.get('location', '')
                phone = u.get('phone', '')
                break
                
        return jsonify({
            'user_id': session['user_id'],
            'name': session['name'],
            'email': session['email'],
            'user_type': session['user_type'],
            'has_face': has_face,
            'location': location,
            'phone': phone
        }), 200
    return jsonify({'error': 'Not logged in'}), 401

@app.route('/api/crops')
def get_crops():
    crops = load_crops()
    return jsonify(crops)

@app.route('/api/marketplace-crops')
def get_marketplace_crops():
    """Get all crops from crop_data.json + farmer_products.json for marketplace display"""
    all_items = get_all_marketplace_items()
    return jsonify(all_items)

@app.route('/api/analytics')
def get_analytics():
    """Returns analytics data for the dashboard"""
    crops = load_crops()
    
    # 1. Price Trends (Average of all crops over 10 years)
    trend_data = [0] * 10
    crop_count = len(crops)
    if crop_count > 0:
        for crop_data in crops.values():
            for i, price in enumerate(crop_data['history']):
                if i < 10:
                    trend_data[i] += price
        trend_data = [round(total / crop_count) for total in trend_data]
        
    labels = [f"Year {i+1}" for i in range(10)]

    # 2. Crop Market Share (count of listings per crop)
    farmer_products = load_farmer_products()
    distribution = {}
    
    # Add base crops
    for crop_name in crops.keys():
        name = crop_name.lower().replace(' ', '_')
        distribution[name] = 1 # base listing
        
    # Add farmer crops
    for products in farmer_products.values():
        for product in products:
            name = product['name'].lower().replace(' ', '_')
            distribution[name] = distribution.get(name, 0) + 1
            
    # Top 5 for better chart visibility
    dist_labels = list(distribution.keys())
    dist_data = list(distribution.values())
    if len(dist_labels) > 5:
        sorted_dist = sorted(distribution.items(), key=lambda x: x[1], reverse=True)
        dist_labels = [k.capitalize().replace('_', ' ') for k, v in sorted_dist[:5]]
        dist_data = [v for k, v in sorted_dist[:5]]
    else:
        dist_labels = [k.capitalize().replace('_', ' ') for k in dist_labels]
        
    avg_price = round(sum([c['info']['price'] for c in crops.values()]) / max(1, len(crops)))
    
    return jsonify({
        'trend': {
            'labels': labels,
            'data': trend_data
        },
        'distribution': {
            'labels': dist_labels,
            'data': dist_data
        },
        'stats': {
            'avg_price': avg_price,
            'total_crops': len(crops)
        }
    })

@app.route('/api/predict/<crop_name>')
def predict_price(crop_name):
    all_items = get_all_marketplace_items()
    if crop_name not in all_items:
        return jsonify({'error': 'Crop not found'}), 404
    
    history = all_items[crop_name]['history']
    predictions = predict_next_5_months(history)
    
    # Generate dates for next 5 months
    import calendar
    today = datetime.now()
    dates = []
    for i in range(1, 6):
        # Calculate future month and year
        future_month = today.month + i
        future_year = today.year
        if future_month > 12:
            future_month -= 12
            future_year += 1
            
        month_name = calendar.month_abbr[future_month]
        dates.append(f"{month_name} {future_year}")
    
    return jsonify({
        'crop': crop_name,
        'current_price': all_items[crop_name]['info']['price'],
        'dates': dates,
        'predictions': predictions
    })

@app.route('/api/order', methods=['POST'])
def create_order():
    # Check if user is logged in
    if 'user_id' not in session:
        return jsonify({'error': 'Please log in to place an order'}), 401
    
    data = request.json
    
    all_items = get_all_marketplace_items()
    if data['crop'] not in all_items:
        return jsonify({'error': 'Crop not found'}), 404
    
    crop_data = all_items[data['crop']]
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
        'delivery_method': data.get('delivery_method', 'seller_delivers'),
        'payment_method': data.get('payment_method', 'cash'),
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
    if 'user_id' not in session:
        return jsonify({'error': 'Please log in'}), 401
    
    user_id = session.get('user_id')
    user_type = session.get('user_type')

    orders_file = 'templates/orders.json'
    try:
        with open(orders_file, 'r') as f:
            orders = json.load(f)
    except:
        orders = []
        
    filtered_orders = []
    for order in orders:
        if user_type == 'farmer' and order.get('farmer_id') == user_id:
            filtered_orders.append(order)
        elif user_type == 'buyer' and order.get('buyer_id') == user_id:
            filtered_orders.append(order)
        elif user_type == 'admin':
            filtered_orders.append(order)
            
    return jsonify(filtered_orders)

@app.route('/api/orders/farmer/<farmer_id>')
def get_farmer_orders(farmer_id):
    """Get all orders placed FOR a specific farmer's crops"""
    if 'user_id' not in session or (session.get('user_id') != farmer_id and session.get('user_type') != 'admin'):
        return jsonify({'error': 'Unauthorized'}), 403
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
    if 'user_id' not in session or (session.get('user_id') != buyer_id and session.get('user_type') != 'admin'):
        return jsonify({'error': 'Unauthorized'}), 403
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
    if 'user_id' not in session or (session.get('user_id') != farmer_id and session.get('user_type') != 'admin'):
        return jsonify({'error': 'Unauthorized'}), 403
    products = load_farmer_products()
    farmer_products = products.get(farmer_id, [])
    return jsonify(farmer_products)

@app.route('/api/farmer/products/<farmer_id>', methods=['POST'])
def add_farmer_product(farmer_id):
    if 'user_id' not in session or (session.get('user_id') != farmer_id and session.get('user_type') != 'admin'):
        return jsonify({'error': 'Unauthorized'}), 403
        
    data = request.json
    
    users = load_users()
    authorized = False
    for farmer in users.get('farmers', []):
        if farmer['user_id'] == farmer_id:
            crops_grown = [c.lower() for c in farmer.get('crops_grown', [])]
            product_name = data.get('name', '').lower()
            if any(crop in product_name for crop in crops_grown) or session.get('user_type') == 'admin':
                authorized = True
            break
            
    if not authorized:
        return jsonify({'error': 'You are not authorized to add products for crops you do not grow.'}), 403
        
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
        'delivery_option': data.get('delivery_option', 'seller_delivers'),
        'payment_preference': data.get('payment_preference', 'cash'),
        'created_date': datetime.now().isoformat()
    }
    
    products[farmer_id].append(product)
    save_farmer_products(products)
    
    return jsonify({'success': True, 'product': product}), 201

@app.route('/api/farmer/products/<farmer_id>/<product_id>', methods=['PUT'])
def update_farmer_product(farmer_id, product_id):
    if 'user_id' not in session or (session.get('user_id') != farmer_id and session.get('user_type') != 'admin'):
        return jsonify({'error': 'Unauthorized'}), 403
        
    data = request.json
    
    if 'name' in data:
        users = load_users()
        authorized = False
        for farmer in users.get('farmers', []):
            if farmer['user_id'] == farmer_id:
                crops_grown = [c.lower() for c in farmer.get('crops_grown', [])]
                product_name = data.get('name', '').lower()
                if any(crop in product_name for crop in crops_grown) or session.get('user_type') == 'admin':
                    authorized = True
                break
                
        if not authorized:
            return jsonify({'error': 'You are not authorized to update to a crop you do not grow.'}), 403
            
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
                    'delivery_option': data.get('delivery_option', product.get('delivery_option', 'seller_delivers')),
                    'payment_preference': data.get('payment_preference', product.get('payment_preference', 'cash')),
                    'updated_date': datetime.now().isoformat()
                })
                save_farmer_products(products)
                return jsonify({'success': True, 'product': product})
    
    return jsonify({'error': 'Product not found'}), 404

@app.route('/api/farmer/products/<farmer_id>/<product_id>', methods=['DELETE'])
def delete_farmer_product(farmer_id, product_id):
    if 'user_id' not in session or (session.get('user_id') != farmer_id and session.get('user_type') != 'admin'):
        return jsonify({'error': 'Unauthorized'}), 403
        
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

@app.route('/api/voice-command', methods=['POST'])
def process_voice_command():
    data = request.json
    command = data.get('command', '').lower()
    
    if not command:
        return jsonify({'reply': 'I did not catch that.'}), 400
        
    # Check for Price query
    # e.g., "what is the price of tomato"
    price_match = re.search(r'price of (\w+)', command)
    if price_match and 'update' not in command and 'change' not in command:
        crop_name = price_match.group(1).lower()
        crops = load_crops()
        # look for crop
        found_crop = None
        for key in crops.keys():
            if crop_name in key.lower():
                found_crop = key
                break
        if found_crop:
            price = crops[found_crop]['info']['price']
            return jsonify({'reply': f'The current market price of {crop_name} is {price} rupees per kilogram.'})
        else:
            return jsonify({'reply': f'Sorry, I could not find information for {crop_name}.'})
            
    # Check for Price Update
    # e.g., "update the price of tomato to 40 rupees" or "update tomato price to 40"
    update_match = re.search(r'update.*?(\w+).*?price.*?to\s+(\d+)', command)
    if update_match:
        crop_name = update_match.group(1).lower()
        new_price = int(update_match.group(2))
        
        if 'user_id' not in session or session.get('user_type') != 'farmer':
            return jsonify({'reply': 'You must be logged in as a farmer to update prices.'})
            
        farmer_id = session.get('user_id')
        products = load_farmer_products()
        if farmer_id in products:
            updated = False
            for p in products[farmer_id]:
                if crop_name in p['name'].lower():
                    p['price'] = new_price
                    updated = True
                    break
            if updated:
                save_farmer_products(products)
                return jsonify({'reply': f'Updated {crop_name} price to {new_price} rupees.'})
            else:
                return jsonify({'reply': f'You do not have {crop_name} in your products.'})
        else:
            return jsonify({'reply': 'You have no products to update.'})
            
    # Check for Order Status
    if 'orders' in command:
        if 'user_id' not in session:
            return jsonify({'reply': 'Please log in to check your orders.'})
            
        user_id = session.get('user_id')
        user_type = session.get('user_type')
        
        orders_file = 'templates/orders.json'
        try:
            with open(orders_file, 'r') as f:
                all_orders = json.load(f)
        except:
            all_orders = []
            
        if user_type == 'farmer':
            my_orders = [o for o in all_orders if o.get('farmer_id') == user_id]
        else:
            my_orders = [o for o in all_orders if o.get('buyer_id') == user_id]
            
        pending = len([o for o in my_orders if o.get('status') == 'Pending Confirmation'])
        if pending > 0:
            return jsonify({'reply': f'You have {pending} pending orders waiting for attention.'})
        elif len(my_orders) > 0:
            return jsonify({'reply': f'You have {len(my_orders)} total orders, but none are pending.'})
        else:
            return jsonify({'reply': 'You have no orders at the moment.'})
            
    return jsonify({'reply': 'I am not sure how to help with that. Try asking about crop prices or your orders.'})

if __name__ == '__main__':
    app.run(debug=True, port=5000)