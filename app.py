from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import os

# Initialize Flask app
app = Flask(__name__, static_folder='.')
CORS(app)

# Initialize Firebase

cred = credentials.Certificate("key/flask-project-75852-firebase-adminsdk-fbsvc-079ae48544.json")
firebase_admin.initialize_app(cred)

db = firestore.client()
collection_name = 'Products'  # Firestore collection
history_collection = 'History'

@app.route('/')
def home():
    return send_from_directory('.', 'front.html')  # Serve from root directory  # Render the frontend.html file

# Create or Add product
@app.route('/api/add/items', methods=['POST'])
def add_item():
    data = request.json
    name = data.get('name')
    price = data.get('price')
    stock = data.get('stock')
    if name and price is not None and stock is not None:
        # Add product
        doc_ref = db.collection(collection_name).add({'name': name, 'price': price, 'stock': stock})
        
        # Add to history without storing the reference
        db.collection(history_collection).add({
            'action': 'Product Added',
            'details': f"Added new product: {name}",
            'productData': {'name': name, 'price': price, 'stock': stock, 'id': doc_ref[1].id},
            'timestamp': firestore.SERVER_TIMESTAMP
        })
        
        return jsonify({'message': 'Product added', 'id': doc_ref[1].id}), 201
    return jsonify({'error': 'Missing product details'}), 400

# Read all products
@app.route('/api/view/items', methods=['GET'])
def get_items():
    docs = db.collection(collection_name).stream()
    items = [{'id': doc.id, **doc.to_dict()} for doc in docs]
    return jsonify(items)

# Update product
@app.route('/api/update/items/<id>', methods=['PUT'])
def update_item(id):
    data = request.json
    name = data.get('name')
    price = data.get('price')
    stock = data.get('stock')
    if name and price is not None and stock is not None:
        # Update product
        db.collection(collection_name).document(id).update({'name': name, 'price': price, 'stock': stock})
        
        # Add to history
        db.collection(history_collection).add({
            'action': 'Product Updated',
            'details': f"Updated product: {name}",
            'productData': {'id': id, 'name': name, 'price': price, 'stock': stock},
            'timestamp': firestore.SERVER_TIMESTAMP
        })
        
        return jsonify({'message': 'Product updated'})
    return jsonify({'error': 'Missing product details'}), 400

# Delete product
@app.route('/api/delete/items/<id>', methods=['DELETE'])
def delete_item(id):
    # Get product details before deletion
    product = db.collection(collection_name).document(id).get()
    if product.exists:
        product_data = product.to_dict()
        
        # Delete product
        db.collection(collection_name).document(id).delete()
        
        # Add to history
        db.collection(history_collection).add({
            'action': 'Product Deleted',
            'details': f"Deleted product: {product_data['name']}",
            'productData': {'id': id, 'name': product_data['name']},
            'timestamp': firestore.SERVER_TIMESTAMP
        })
        
        return jsonify({'message': 'Product deleted'})
    return jsonify({'error': 'Product not found'}), 404

@app.route('/api/history', methods=['GET'])
def get_history():
    try:
        # Get history items, ordered by timestamp
        docs = db.collection(history_collection)\
            .order_by('timestamp', direction=firestore.Query.DESCENDING)\
            .limit(50)\
            .stream()
        
        history = []
        for doc in docs:
            data = doc.to_dict()
            # Convert timestamp to ISO format for JSON serialization
            if data.get('timestamp'):
                data['timestamp'] = data['timestamp'].isoformat()
            history.append({'id': doc.id, **data})
            
        return jsonify(history)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)