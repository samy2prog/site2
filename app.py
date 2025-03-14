import os
import psycopg2
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

# Connexion à la base de données PostgreSQL
DATABASE_URL = os.getenv("DATABASE_URL")

def get_db():
    try:
        conn = psycopg2.connect(DATABASE_URL, sslmode="require")
        return conn
    except Exception as e:
        print(f"❌ Impossible de se connecter à PostgreSQL : {e}")
        return None

# 📌 Route pour afficher les commandes
@app.route("/")
def index():
    return render_template("index.html")

# 📌 Route pour afficher les commandes
@app.route("/orders")
def orders():
    conn = get_db()
    if conn is None:
        return jsonify({"error": "Connexion à la base de données impossible"}), 500

    cur = conn.cursor()
    cur.execute("SELECT * FROM orders ORDER BY created_at DESC")
    orders = cur.fetchall()
    cur.close()
    conn.close()

    return render_template("orders.html", orders=orders)

# 📌 Route pour effectuer un achat
@app.route("/buy", methods=["POST"])
def buy():
    if request.content_type != "application/json":
        return jsonify({"error": "Le Content-Type doit être 'application/json'"}), 415

    data = request.get_json()
    product_name = data.get("product_name")
    payment_method = data.get("payment_method")

    if not product_name or not payment_method:
        return jsonify({"error": "Données invalides"}), 400

    conn = get_db()
    if conn is None:
        return jsonify({"error": "Impossible de se connecter à la base de données"}), 500

    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO orders (product_name, payment_method) VALUES (%s, %s) RETURNING id",
            (product_name, payment_method),
        )
        order_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"message": "Commande enregistrée", "order_id": order_id}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 📌 Route pour demander un remboursement
@app.route("/refund", methods=["POST"])
def request_refund():
    if request.content_type != "application/json":
        return jsonify({"error": "Le Content-Type doit être 'application/json'"}), 415

    data = request.get_json()
    order_id = data.get("order_id")

    if not order_id:
        return jsonify({"error": "Données invalides"}), 400

    conn = get_db()
    if conn is None:
        return jsonify({"error": "Impossible de se connecter à la base de données"}), 500

    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO refunds (order_id, status) VALUES (%s, 'En attente') RETURNING id",
            (order_id,),
        )
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"message": "Remboursement demandé avec succès"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
