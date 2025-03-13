from flask import Flask, request, jsonify, render_template, redirect
import psycopg2
import hashlib
from datetime import datetime
import os

app = Flask(__name__)

# 📌 Récupérer l'URL de la base de données
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://eshop_db_d9qc_user:6IoPk0zWxCmDL9EEQshbWrmK54bdfced@dpg-cv93lh1u0jms73eevl00-a.frankfurt-postgres.render.com/eshop_db_d9qc")

# 📌 Fonction pour se connecter à PostgreSQL
def get_db():
    try:
        conn = psycopg2.connect(DATABASE_URL, sslmode="require")
        return conn
    except Exception as e:
        print(f"❌ ERREUR DE CONNEXION À POSTGRESQL : {e}")
        return None

# 📌 Page d'accueil (évite les erreurs 404)
@app.route("/")
def home():
    return "✅ API en ligne - Accédez à /orders ou /refund"

# 📌 Page affichant les commandes
@app.route("/orders")
def orders():
    conn = get_db()
    if not conn:
        return "Erreur : Connexion à la base de données impossible.", 500

    cur = conn.cursor()
    cur.execute("SELECT id, product_name, payment_method, created_at FROM orders ORDER BY created_at DESC")
    orders_list = cur.fetchall()
    cur.close()
    conn.close()

    return render_template("orders.html", orders=orders_list)

# 📌 Route pour acheter un produit
@app.route("/buy", methods=["POST"])
def buy():
    try:
        data = request.get_json()
        if not data or "product_name" not in data or "payment_method" not in data:
            return jsonify({"error": "Données invalides"}), 400

        product_name = data["product_name"]
        payment_method = data["payment_method"]

        conn = get_db()
        if conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO orders (product_name, payment_method, created_at)
                VALUES (%s, %s, %s)
                RETURNING id
            """, (product_name, payment_method, datetime.utcnow()))
            
            order_id = cursor.fetchone()[0]
            conn.commit()
            cursor.close()
            conn.close()

            return jsonify({"message": "Achat effectué avec succès", "order_id": order_id}), 201
        else:
            return jsonify({"error": "Impossible de se connecter à la base de données"}), 500

    except Exception as e:
        print("❌ ERREUR API Achat :", e)
        return jsonify({"error": str(e)}), 500

# 📌 Route pour demander un remboursement
@app.route("/refund", methods=["POST"])
def refund():
    try:
        if not request.is_json:
            return jsonify({"error": "Le Content-Type doit être 'application/json'"}), 415

        data = request.get_json()
        if not data or "order_id" not in data:
            return jsonify({"error": "Données invalides"}), 400

        order_id = data["order_id"]

        conn = get_db()
        if not conn:
            return jsonify({"error": "Connexion à la base de données impossible"}), 500

        cursor = conn.cursor()

        # 📌 Vérifie si la commande existe
        cursor.execute("SELECT id FROM orders WHERE id = %s", (order_id,))
        order = cursor.fetchone()
        if not order:
            return jsonify({"error": "Commande non trouvée"}), 404

        # 📌 Insère la demande de remboursement
        cursor.execute("""
            INSERT INTO refunds (order_id, status, created_at)
            VALUES (%s, %s, %s)
        """, (order_id, "En attente", datetime.utcnow()))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"message": "Remboursement demandé avec succès"}), 200

    except Exception as e:
        print("❌ ERREUR API remboursement:", e)
        return jsonify({"error": str(e)}), 500

# 📌 Lance l'application Flask
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10002, debug=True)
