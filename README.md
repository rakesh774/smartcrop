# Agri-Direct: Farmer-Buyer Portal

A high-contrast, ultra-accessible web application designed for farmers and buyers in rural farming communities. Features big-button UI, clean interface, and marketplace functionality.

## 🌟 Key Features

### 🔐 Passwordless Authentication
- **Facial Login Integration**: Secure, webcam-based biometric capture during registration and login.
- No need to remember complex passwords—just scan your face.

### 🎙️ Voice-Enabled Portal
- **Voice Assistant**: Integrated voice commands for navigating the marketplace, parsing crop info, and checking stats.
- Perfect for low-literacy users and hands-free interaction.

### 👤 User Profiles
- **Profile Dashboard**: Manage account details, update facial credentials, and view personal information.

### ♿ Ultra-Accessible UI
- **High-contrast colors**: Green (Accept/Add), Red (Reject/Cancel), Yellow (Info), Blue (Navigation)
- **Large buttons** (80px minimum) with clear icons (🌾, 💰, 👨‍🌾, 🛒)
- **20px minimum font size** for all text
- **Color-coded cards** for easy recognition

### 👥 User Roles
- **Farmers**: Add products, manage inventory, view orders
- **Buyers**: Browse marketplace, place orders, track purchases

## 🚀 Getting Started

### Prerequisites
- Python 3.7+
- Flask
- Modern web browser

### Installation
1. Clone the repository
2. Install dependencies: `pip install flask numpy`
3. Run the server: `python main.py`
4. Open http://127.0.0.1:5000 in your browser

### Sample Users for Testing
**Farmers:**
- Ahmed Khan: farmer1@gmail.com / farmer1
- Ravi Pillai: farmer2@gmail.com / farmer2

**Buyers:**
- buyer1@gmail.com / buyer1
- buyer2@gmail.com / buyer2

## 🛠️ Technical Implementation

### Frontend Technologies
- **HTML5/CSS3**: High-contrast styling
- **JavaScript**: Dynamic marketplace and order management
- **Tailwind CSS**: Modern responsive design
- **Responsive Design**: Works on mobile and desktop

### Backend Technologies
- **Flask**: Python web framework
- **JSON Storage**: Simple file-based data persistence
- **RESTful APIs**: Clean separation of concerns

## 📱 Accessibility Features

### Visual Accessibility
- High contrast ratios (minimum 4.5:1)
- Large touch targets (44px minimum)
- Clear iconography with text labels
- Consistent color coding throughout

### Cognitive Accessibility
- Simple, linear workflows
- Progressive disclosure of information
- Consistent interaction patterns

## 🔧 API Endpoints

### Authentication
- `POST /api/login` - User authentication
- `POST /api/logout` - User logout

### Marketplace
- `GET /api/marketplace-crops` - Get all available crops
- `GET /api/crops` - Get crop data
- `POST /api/order` - Place new order

### Farmer Management
- `GET /api/farmer/products/:farmer_id` - Get farmer's products
- `POST /api/farmer/products/:farmer_id` - Add new product
- `PUT /api/farmer/products/:farmer_id/:product_id` - Update product
- `DELETE /api/farmer/products/:farmer_id/:product_id` - Delete product

### Orders
- `GET /api/orders` - Get all orders
- `GET /api/orders/farmer/:farmer_id` - Get farmer's orders
- `GET /api/orders/buyer/:buyer_id` - Get buyer's orders
- `PUT /api/orders/:order_id/status` - Update order status

## 📊 Data Structure

### Users
```json
{
  "farmers": [
    {
      "user_id": "farmer_001",
      "name": "Ahmed Khan",
      "email": "farmer1@gmail.com",
      "password": "farmer1"
    }
  ],
  "buyers": [...]
}
```

### Crops
```json
{
  "rice": {
    "info": {"price": 120, "location": "Tamil Nadu", "trend": "Up"},
    "history": [90, 95, 100, 105, 110, 115, 118, 120, 122, 120],
    "farmer_name": "Manoj Kumar",
    "description": "Premium basmati rice"
  }
}
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add voice commands or accessibility improvements
4. Test with screen readers and voice input
5. Submit a pull request

## 📄 License

This project is open source and available under the MIT License.

## 🙏 Acknowledgments

- Designed for low-literacy users in farming communities
- Inspired by successful voice-powered applications
- Built with accessibility best practices in mind#
