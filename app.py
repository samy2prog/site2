from flask import Flask, render_template, request, jsonify, g
import psycopg2
import os
import requests

app = Flask(__name__)

# 🔹 Configuration PostgreSQL sur Render
DATABASE_URL = "postgresql://eshop_user:Idx7b2u8UfXodOCQn3oGHwrzwtyP3CbI@dpg-cv908nin91rc73d5bes0-a.internal/render.com/eshop_db_c764"

def get_db():
    """Connexion à la base PostgreSQL"""
    conn = psycopg2.connect(DATABASE_URL)
    return conn

# 🔹 Création des tables dans PostgreSQL
def create_tables():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id SERIAL PRIMARY KEY,
            product_name TEXT,
            user_ip TEXT,
            user_agent TEXT,
            payment_method TEXT,
            refund_count INTEGER DEFAULT 0
        )
    """)
    db.commit()
    cursor.close()
    db.close()

create_tables()

products = [
    {"id": 1, "name": "Sneakers Nike", "price": 120},
    {"id": 2, "name": "Sac Louis Vuitton", "price": 2200},
    {"id": 3, "name": "Montre Rolex", "price": 15000}
]

@app.route("/")
def home():
    """Affichage des produits et des commandes"""
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM orders")
    orders = cursor.fetchall()
    db.close()
    
    return render_template("index.html", products=products, orders=orders)

@app.route("/checkout", methods=["POST"])
def checkout():
    """Ajout d'une commande et vérification de la fraude"""
    data = request.json

    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        INSERT INTO orders (product_name, user_ip, user_agent, payment_method, refund_count)
        VALUES (%s, %s, %s, %s, %s)
    """, (data["product_name"], data["ip"], data["user_agent"], data["payment_method"], 0))
    db.commit()

    # 🔹 Vérification de la fraude via l'API
    API_URL = "http://127.0.0.1:5000/detect"
    response = requests.post(API_URL, json=data)
    fraud_result = response.json()

    db.close()
    return jsonify({"message": "Commande enregistrée", "risk_score": fraud_result.get("risk_score", "Erreur API")})

@app.route("/refund", methods=["POST"])
def refund():
    """Gestion des remboursements"""
    data = request.json
    order_id = data["order_id"]

    db = get_db()
    cursor = db.cursor()
    
    cursor.execute("SELECT * FROM orders WHERE id = %s", (order_id,))
    order = cursor.fetchone()

    if not order:
        db.close()
        return jsonify({"error": "Commande non trouvée"}), 404

    refund_count = order[5] + 1  # Incrémente le nombre de remboursements
    cursor.execute("UPDATE orders SET refund_count = %s WHERE id = %s", (refund_count, order_id))
    db.commit()

    # 🔹 Vérification du risque après remboursement
    fraud_data = {
        "ip": order[2],
        "user_agent": order[3],
        "payment_method": order[4],
        "refund_count": refund_count
    }
    API_URL = "http://127.0.0.1:5000/detect"
    response = requests.post(API_URL, json=fraud_data)
    fraud_result = response.json()

    db.close()
    return jsonify({"message": "Remboursement effectué", "risk_score": fraud_result.get("risk_score", "Erreur API")})

if __name__ == "__main__":
    app.run(port=5002, debug=True)
