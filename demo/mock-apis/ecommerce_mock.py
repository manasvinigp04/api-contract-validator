"""
E-Commerce Platform Mock API Server
Intentionally includes drift issues for ACV demo

Run: python demo/mock-apis/ecommerce_mock.py
Server: http://localhost:8080
"""

from flask import Flask, jsonify, request
from datetime import datetime
import uuid

app = Flask(__name__)

# Mock data
products_db = {
    "PROD0001": {
        "id": "PROD0001",
        "name": "Wireless Headphones",
        "sku": "SKU-ABC123",
        "price": 79.99,
        "category": "electronics",
        "inStock": True,
        "createdAt": "2024-01-15T10:00:00Z"
        # DRIFT: Missing 'description', 'images', 'inventory' fields required by spec
    },
    "PROD0002": {
        "id": "PROD0002",
        "name": "Running Shoes",
        "sku": "SKU-XYZ789",
        "price": "129.99",  # DRIFT: Should be number, not string
        "category": "sports",
        "inStock": True,
        "createdAt": "2024-02-10T14:30:00Z",
        "internal_id": 12345  # DRIFT: Extra field leaking internal data
    }
}

carts_db = {}
orders_db = {}

@app.route('/v2/products', methods=['GET'])
def list_products():
    """List products with pagination - PUBLIC endpoint"""
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 20))

    products = list(products_db.values())

    return jsonify({
        "data": products,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": len(products),
            "totalPages": 1
        }
    }), 200

@app.route('/v2/products', methods=['POST'])
def create_product():
    """Create product - DRIFT: Missing validation"""
    data = request.get_json()

    # DRIFT: Should validate required fields, SKU pattern, price range
    # Accepts invalid data that should return 400

    product_id = f"PROD{len(products_db) + 1:04d}"

    product = {
        "id": product_id,
        "name": data.get("name", ""),
        "sku": data.get("sku", ""),
        "price": data.get("price", 0),
        "category": data.get("category", "electronics"),
        "inStock": True,
        "createdAt": datetime.utcnow().isoformat() + "Z"
        # DRIFT: Missing fields again
    }

    products_db[product_id] = product

    # DRIFT: Should return 201, but returns 200
    return jsonify(product), 200

@app.route('/v2/products/<product_id>', methods=['GET'])
def get_product(product_id):
    """Get product details"""
    if product_id not in products_db:
        return jsonify({
            "error": "not_found",
            "message": f"Product {product_id} not found"
        }), 404

    return jsonify(products_db[product_id]), 200

@app.route('/v2/products/<product_id>', methods=['PATCH'])
def update_product(product_id):
    """Update product"""
    if product_id not in products_db:
        return jsonify({
            "error": "not_found",
            "message": f"Product {product_id} not found"
        }), 404

    data = request.get_json()

    # DRIFT: No validation of update fields
    products_db[product_id].update(data)
    products_db[product_id]["updatedAt"] = datetime.utcnow().isoformat() + "Z"

    return jsonify(products_db[product_id]), 200

@app.route('/v2/products/<product_id>', methods=['DELETE'])
def delete_product(product_id):
    """Delete product"""
    if product_id not in products_db:
        return jsonify({
            "error": "not_found",
            "message": f"Product {product_id} not found"
        }), 404

    del products_db[product_id]
    return '', 204

@app.route('/v2/cart', methods=['GET'])
def get_cart():
    """Get user cart"""
    # Simplified: use a single cart
    cart_id = "cart-1"

    if cart_id not in carts_db:
        carts_db[cart_id] = {
            "id": cart_id,
            "userId": str(uuid.uuid4()),
            "items": [],
            "totals": {
                "subtotal": 0,
                "tax": 0,
                "shipping": 0,
                "total": 0
            },
            "createdAt": datetime.utcnow().isoformat() + "Z",
            "updatedAt": datetime.utcnow().isoformat() + "Z"
        }

    return jsonify(carts_db[cart_id]), 200

@app.route('/v2/cart', methods=['POST'])
def add_to_cart():
    """Add item to cart - DRIFT: Weak validation"""
    data = request.get_json()

    # DRIFT: Should validate productId pattern, quantity range
    # Accepts negative quantities, invalid product IDs

    product_id = data.get("productId")
    quantity = data.get("quantity", 1)

    if product_id not in products_db:
        return jsonify({
            "error": "not_found",
            "message": f"Product {product_id} not found"
        }), 404

    cart_id = "cart-1"
    if cart_id not in carts_db:
        get_cart()  # Initialize cart

    product = products_db[product_id]
    item = {
        "id": str(uuid.uuid4()),
        "productId": product_id,
        "productName": product["name"],
        "quantity": quantity,  # DRIFT: No validation (accepts negative)
        "unitPrice": product["price"] if isinstance(product["price"], (int, float)) else float(product["price"]),
        "totalPrice": (product["price"] if isinstance(product["price"], (int, float)) else float(product["price"])) * quantity
    }

    carts_db[cart_id]["items"].append(item)

    # Recalculate totals
    subtotal = sum(item["totalPrice"] for item in carts_db[cart_id]["items"])
    carts_db[cart_id]["totals"] = {
        "subtotal": subtotal,
        "tax": subtotal * 0.08,
        "shipping": 10.0,
        "total": subtotal * 1.08 + 10.0
    }
    carts_db[cart_id]["updatedAt"] = datetime.utcnow().isoformat() + "Z"

    return jsonify(carts_db[cart_id]), 200

@app.route('/v2/orders', methods=['GET'])
def list_orders():
    """List orders"""
    orders = list(orders_db.values())
    return jsonify({
        "data": orders,
        "pagination": {
            "page": 1,
            "limit": 20,
            "total": len(orders),
            "totalPages": 1
        }
    }), 200

@app.route('/v2/orders', methods=['POST'])
def create_order():
    """Create order from cart - DRIFT: Missing validation"""
    data = request.get_json()

    # DRIFT: Should validate shippingAddressId format, paymentMethodId
    # Should check if cart is empty

    cart_id = "cart-1"
    if cart_id not in carts_db or not carts_db[cart_id]["items"]:
        return jsonify({
            "error": "unprocessable_entity",
            "message": "Cart is empty"
        }), 422

    order_id = str(uuid.uuid4())
    order = {
        "id": order_id,
        "orderNumber": f"ORD-{len(orders_db) + 1:08d}",
        "userId": carts_db[cart_id]["userId"],
        "status": "pending",
        "items": carts_db[cart_id]["items"],
        "totals": carts_db[cart_id]["totals"],
        "shippingAddress": {
            "id": data.get("shippingAddressId"),
            "street": "123 Main St",
            "city": "Springfield",
            "state": "IL",
            "postalCode": "62701",
            "country": "US"
        },
        "paymentStatus": "pending",
        "createdAt": datetime.utcnow().isoformat() + "Z"
        # DRIFT: Missing billingAddress, updatedAt
    }

    orders_db[order_id] = order

    # Clear cart
    carts_db[cart_id]["items"] = []

    # DRIFT: Should return 201, returns 200
    return jsonify(order), 200

@app.route('/v2/orders/<order_id>', methods=['GET'])
def get_order(order_id):
    """Get order details"""
    if order_id not in orders_db:
        return jsonify({
            "error": "not_found",
            "message": f"Order {order_id} not found"
        }), 404

    return jsonify(orders_db[order_id]), 200

@app.route('/v2/payments', methods=['POST'])
def process_payment():
    """Process payment - DRIFT: Missing validation"""
    data = request.get_json()

    # DRIFT: Should validate payment method discriminator
    # Should validate card number (Luhn algorithm)
    # Should validate CVV, expiry date
    # Accepts invalid credit cards!

    order_id = data.get("orderId")

    if order_id not in orders_db:
        return jsonify({
            "error": "not_found",
            "message": f"Order {order_id} not found"
        }), 404

    # Simulate payment success
    result = {
        "transactionId": str(uuid.uuid4()),
        "status": "success",
        "amount": orders_db[order_id]["totals"]["total"],
        "currency": "USD",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

    orders_db[order_id]["paymentStatus"] = "captured"

    return jsonify(result), 200

@app.route('/v2/users/profile', methods=['GET'])
def get_user_profile():
    """Get user profile"""
    return jsonify({
        "id": str(uuid.uuid4()),
        "email": "john.doe@example.com",
        "firstName": "John",
        "lastName": "Doe",
        "phone": "+1234567890",
        "createdAt": "2024-01-01T00:00:00Z"
        # DRIFT: Missing preferences, dateOfBirth
    }), 200

@app.route('/v2/users/addresses', methods=['GET'])
def list_addresses():
    """List user addresses"""
    return jsonify([
        {
            "id": str(uuid.uuid4()),
            "label": "home",
            "street": "123 Main St",
            "city": "Springfield",
            "state": "IL",
            "postalCode": "62701",
            "country": "US",
            "isDefault": True
        }
    ]), 200

if __name__ == '__main__':
    print("=" * 60)
    print("E-Commerce Platform Mock API Server")
    print("=" * 60)
    print("Server: http://localhost:8080")
    print("Base URL: http://localhost:8080/v2")
    print()
    print("Intentional drift issues for ACV demo:")
    print("  - Missing required fields in responses")
    print("  - Type mismatches (string price instead of number)")
    print("  - Wrong status codes (200 instead of 201)")
    print("  - Weak validation (accepts invalid credit cards, negative quantities)")
    print("  - Extra fields (internal_id leaking)")
    print()
    print("Endpoints:")
    print("  GET    /v2/products")
    print("  POST   /v2/products")
    print("  GET    /v2/products/{id}")
    print("  PATCH  /v2/products/{id}")
    print("  DELETE /v2/products/{id}")
    print("  GET    /v2/cart")
    print("  POST   /v2/cart")
    print("  GET    /v2/orders")
    print("  POST   /v2/orders")
    print("  GET    /v2/orders/{id}")
    print("  POST   /v2/payments")
    print("  GET    /v2/users/profile")
    print("  GET    /v2/users/addresses")
    print("=" * 60)
    print()

    app.run(host='localhost', port=8080, debug=False)
