from flask import Flask, request, jsonify
import xmlrpc.client
import requests
from flask_cors import CORS, cross_origin
from datetime import datetime
from dotenv import load_dotenv
import os

# load_dotenv()

app = Flask(__name__)
CORS(app,support_credentials=True)
# Odoo connection details
url = "https://mnbvc.odoo.com/"
db = "mnbvc"
username = "sikander@simplability.com"
api_key = "f150c5c6575f058e8e57d115da4506bc5c213b25"



def get_odoo_connection():
    common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
    print(common.version())
    uid = common.authenticate(db, username, api_key, {})
    print("uid: ",uid)
    models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))
    return uid, models

@app.route('/')
def hello_world():
    return 'Hello, World!'
            


@app.route('/products/fields', methods=['GET'])
def get_product_fields():
    uid, models = get_odoo_connection()
    if uid:
        try:
            fields = models.execute_kw(db, uid, api_key, 'product.product', 'fields_get', [], {'attributes': ['string', 'type', 'required']})
            return jsonify(fields)
        except Exception as e:
            return jsonify({"message": "Error retrieving fields", "error": str(e)}), 500
    else:
        return jsonify({"message": "Failed to authenticate"}), 401

@app.route('/partners', methods=['GET'])
def get_partners():
    uid, models = get_odoo_connection()
    if uid:
        try:
            partner_ids = models.execute_kw(db, uid, api_key, 'res.partner', 'search', [[]])
            if partner_ids:
                partners = models.execute_kw(db, uid, api_key, 'res.partner', 'read', [partner_ids], {'fields': ['id', 'name']})
                return jsonify(partners)
            else:
                return jsonify({"message": "No partners found"}), 404
        except Exception as e:
            return jsonify({"message": "Error retrieving partners", "error": str(e)}), 500
    else:
        return jsonify({"message": "Failed to authenticate"}), 401


@app.route('/rfq/fields', methods=['GET'])
def get_rfq_fields(rfq_id=183):
    uid, models = get_odoo_connection()
    if uid:
        try:
            # Read the RFQ record
            rfq = models.execute_kw(db, uid, api_key, 'purchase.order', 'read', [[rfq_id]])
            
            # Get fields definition for purchase.order model
            fields = models.execute_kw(db, uid, api_key, 'account.analytic.plan', 'fields_get', [])
            
            return jsonify({"rfq": rfq, "fields": list(fields.keys())})
        except Exception as e:
            return jsonify({"message": "Error retrieving RFQ fields", "error": str(e)}), 500
    else:
        return jsonify({"message": "Failed to authenticate"}), 401


@app.route('/farms', methods=['GET'])
def get_farms():
    uid, models = get_odoo_connection()
    if uid:
        try:
            fields = models.execute_kw(db, uid, api_key, 'account.analytic.account', 'search_read', [])
            
            # Extract unique display names and their corresponding IDs
            unique_display_names = {}
            for item in fields:
                display_name = item["display_name"]
                id_ = item["id"]
                if "/" in display_name:  # Check if "/" is present in the display name
                    unique_display_names[display_name] = id_
            
            # Construct response JSON
            response_data = [{"display_name": display_name, "id": id_} for display_name, id_ in unique_display_names.items()]
            
            return jsonify(response_data)
        except Exception as e:
            return jsonify({"message": "Error retrieving fields", "error": str(e)}), 500
    else:
        return jsonify({"message": "Failed to authenticate"}), 401


@app.route('/farms_list', methods=['GET'])
def get_farms_list():
    uid, models = get_odoo_connection()
    if uid:
        try:
            fields = models.execute_kw(db, uid, api_key, 'account.analytic.account', 'search_read', [])
            
            # Extract unique display names and their corresponding IDs
            unique_display_names = {}
            for item in fields:
                display_name = item["display_name"]
                id_ = item["id"]
                if "/" in display_name:  # Check if "/" is present in the display name
                    unique_display_names[id_] = display_name
            
            return jsonify(unique_display_names)
        except Exception as e:
            return jsonify({"message": "Error retrieving fields", "error": str(e)}), 500
    else:
        return jsonify({"message": "Failed to authenticate"}), 401


products_list = {}
filtered_products = {}

@app.route('/products', methods=['GET'])
def get_products():
    global filtered_products
    global products_list
    start_time = datetime.now()
    print(f"API call started at: {start_time}")
    uid, models = get_odoo_connection()
    if uid:
        product_ids = models.execute_kw(db, uid, api_key, 'product.product', 'search', [[]])
        print("1")
        if product_ids:
            products = models.execute_kw(db, uid, api_key, 'product.product', 'read', [product_ids], {'fields': ['id', 'name']})
            print("2")
            for product in products:
                product_id = product['id']
                product_name = product['name']
                products_list[product_id] = product_name

                if '/' in product_name:
                    trimmed_name = product_name.split('/')[-1].strip()
                    filtered_products[product_id] = trimmed_name
            print("3")
            end_time = datetime.now()
            print(f"API call ended at: {end_time}")
            print(f"API call duration: {end_time - start_time}")
            return jsonify(products_list)
            # return jsonify({"filtered_products": filtered_products, "products_list": products_list})
        else:
            return jsonify({"message": "No products found"}), 404
    else:
        return jsonify({"message": "Failed to authenticate"}), 401



@app.route('/products_create', methods=['POST'])
def create_products_and_rfq():
    global products_list  
    uid, models = get_odoo_connection()
    if uid:
        try:
            data = request.json
            order_lines = []

            for session in data:
                for item in session['data']:
                    image_data_list = item.get('imageData', [])
                    source = item.get('source')

                    for image_data in image_data_list:
                        if image_data.get('deleted') == False:
                            product_id = int(image_data.get('type'))
                            qty = image_data.get('quantity')

                            if not product_id or not qty or not source:
                                continue

                            order_line_vals = {
                                'product_id': product_id,
                                'product_qty': qty,
                                # 'product_uom': 12,
                                "analytic_distribution": {
                                    "3": 100,
                                    str(source): 100.0
                                },
                            }

                            order_lines.append((0, 0, order_line_vals))

            # Construct the values for the RFQ
            rfq_vals = {
                'partner_id': 10,  
                'order_line': order_lines,
                'picking_type_id': 136,  
            }

            # Create the RFQ
            rfq_id = models.execute_kw(db, uid, api_key, 'purchase.order', 'create', [rfq_vals])

            print(f"RFQ created with ID: {rfq_id}")
            return jsonify({"message": "RFQ created", "rfq_id": rfq_id}), 201
        except Exception as e:
            print(f"Error creating products or RFQ: {str(e)}")
            return jsonify({"message": "Error creating products or RFQ", "error": str(e)}), 500
    else:
        print("Failed to authenticate")
        return jsonify({"message": "Failed to authenticate"}), 401


if __name__ == '__main__':  
     app.run('0.0.0.0',ssl_context=('192.168.0.4.pem','192.168.0.4-key.pem'))