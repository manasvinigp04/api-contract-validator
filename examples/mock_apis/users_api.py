"""
Simple Mock API Server for Testing

Run with: python examples/mock_apis/users_api.py
"""

from flask import Flask, jsonify, request

app = Flask(__name__)

# Mock data
users_db = [
    {"id": 1, "email": "john@example.com", "name": "John Doe", "age": 30, "status": "active"},
    {"id": 2, "email": "jane@example.com", "name": "Jane Smith", "age": 25, "status": "active"},
]

next_id = 3


@app.route("/users", methods=["GET"])
def list_users():
    """List all users."""
    return jsonify(users_db), 200


@app.route("/users", methods=["POST"])
def create_user():
    """Create a new user."""
    global next_id

    data = request.get_json()

    # Validation (intentionally weak for drift detection demo)
    if not data:
        return jsonify({"error": "bad_request", "message": "Request body required"}), 400

    # Note: Missing validation for email format and name length
    # This will cause validation drift to be detected

    user = {
        "id": next_id,
        "email": data.get("email", ""),
        "name": data.get("name", ""),
        "age": data.get("age"),
        "status": "active",
    }

    users_db.append(user)
    next_id += 1

    return jsonify(user), 201


@app.route("/users/<int:user_id>", methods=["GET"])
def get_user(user_id):
    """Get user by ID."""
    user = next((u for u in users_db if u["id"] == user_id), None)

    if user:
        return jsonify(user), 200
    else:
        return jsonify({"error": "not_found", "message": f"User {user_id} not found"}), 404


if __name__ == "__main__":
    print("Starting mock Users API server on http://localhost:8000")
    print("Endpoints:")
    print("  GET    /users")
    print("  POST   /users")
    print("  GET    /users/<id>")
    print()
    app.run(host="localhost", port=8000, debug=True)
