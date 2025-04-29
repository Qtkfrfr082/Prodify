from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import os

# Initialize Flask app
app = Flask(__name__, static_folder='static')
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
    brand = data.get('brand')
    processor = data.get('processor')
    ram = data.get('ram')
    storage = data.get('storage')
    gpu = data.get('gpu')
    os = data.get('os')
    condition = data.get('condition')
    warranty = data.get('warranty')

    # Validate required fields
    if name and price and stock and brand and processor and ram and storage and gpu and os and condition and warranty:
        # Add product to Firestore
        doc_ref = db.collection(collection_name).add({
            'name': name,
            'price': price,
            'stock': stock,
            'brand': brand,
            'processor': processor,
            'ram': ram,
            'storage': storage,
            'gpu': gpu,
            'os': os,
            'condition': condition,
            'warranty': warranty
        })

        # Add to history
        db.collection(history_collection).add({
            'action': 'Product Added',
            'details': f"Added new product: {brand}",
            'productData': {
                'id': doc_ref[1].id,
                'name': name,
                'price': price,
                'stock': stock,
                'brand': brand,
                'processor': processor,
                'ram': ram,
                'storage': storage,
                'gpu': gpu,
                'os': os,
                'condition': condition,
                'warranty': warranty
            },
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
    product = db.collection(collection_name).document(id).get()
    if not product.exists:
        return jsonify({'error': 'Product not found'}), 404

    # Get the existing product data
    product_data = product.to_dict()
    data = request.json

    # Store the existing data for history purposes
    existing_data = product_data.copy()

    # Extract updated fields by comparing incoming data with existing data
    updated_fields = {}
    for key in ['name', 'price', 'stock']:
        if key in data and data[key] != product_data.get(key):
            updated_fields[key] = data[key]

    if updated_fields:
        # Update product with only the changed fields
        db.collection(collection_name).document(id).update(updated_fields)

        # Add to history with both the existing and updated fields
        db.collection(history_collection).add({
            'action': 'Product Updated',
            'details': f"Updated product: {existing_data['name']}",
            'productData': {
                'id': id,
                'name': existing_data['name'],
                'existingFields': existing_data,  # Store the original data
                'updatedFields': updated_fields  # Log only the updated fields
            },
            'timestamp': firestore.SERVER_TIMESTAMP
        })

        return jsonify({'message': 'Product updated', 'updatedFields': updated_fields})
    
    # If no changes detected, return the existing product data
    return jsonify({'message': 'No changes detected', 'product': product_data}), 200

@app.route('/api/update/info/items/<id>', methods=['PUT'])
def update_item_details(id):
    product = db.collection(collection_name).document(id).get()
    if not product.exists:
        return jsonify({'error': 'Product not found'}), 404

    product_data = product.to_dict()
    data = request.json

    # Extract updated fields
    updated_fields = {}
    for key in ['brand', 'processor', 'ram', 'storage', 'gpu', 'os', 'condition', 'warranty']:
        if key in data and data[key] != product_data.get(key):
            updated_fields[key] = data[key]

    if updated_fields:
        # Update product with only the changed fields
        db.collection(collection_name).document(id).update(updated_fields)

        # Add to history
        db.collection(history_collection).add({
            'action': 'Product info Updated',
            'details': f"Updated product info: {product_data['name']}",
            'productData': {'id': id, 'name': product_data['name'], 'updatedFields': updated_fields},
            'timestamp': firestore.SERVER_TIMESTAMP
        })

        return jsonify({'message': 'Product updated', 'updatedFields': updated_fields})
    
    # If no changes detected, return the existing product data
    return jsonify({'message': 'No changes detected', 'product': product_data}), 200


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
            
            # Include updatedFields if they exist
            history_item = {
                'id': doc.id,
                'action': data.get('action'),
                'details': data.get('details'),
                'timestamp': data.get('timestamp'),
                'updatedFields': data.get('productData', {}).get('updatedFields', {})  # Extract updatedFields
            }
            history.append(history_item)
            
        return jsonify(history)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)