from flask import Flask, render_template, request, redirect, url_for, jsonify
import psycopg2
import hashlib
from datetime import datetime
import os

app = Flask(__name__)

# 🔹 Connexion à PostgreSQL (Remplace avec ton lien Render)
DATABASE_URL = "postgresql://eshop_db_d9qc_user:6IoPk0zWxCmDL9EEQshbWrmK54bdfced@dpg-cv93lh1u0jms73eevl00-a.frankfurt-postgres.render.com/eshop_db_d9qc"

def get_db():
    """Établit une connexion avec PostgreSQL."""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except Exception as e:
        print(f"❌ ERREUR DE CONNEXION À POSTGRESQL : {e}")
        return None

# 🔹 Création des tables si elles n'existent pas
def create_tables():
    conn = get_db()
    if conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                ip VARCHAR(45),
                user_agent TEXT,
                fingerprint TEXT UNIQUE,
                refund_count INT DEFAULT 0,
                risk_score INT DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS orders (
                id SERIAL PRIMARY KEY,
                product_name TEXT,
                ip VARCHAR(45),
                user_agent TEXT,
                payment_method TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS refunds (
                id SERIAL PRIMARY KEY,
                order_id INT REFERENCES orders(id) ON DELETE CASCADE,
                status VARCHAR(20) DEFAULT 'En attente',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        cursor.close()
        conn.close()
create_tables()

# 🔹 Route pour afficher les commandes
@app.route("/orders")
def orders():
    conn = get_db()
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, product_name, payment_method, created_at FROM orders ORDER BY created_at DESC")
        orders = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template("orders.html", orders=orders)
    return "Erreur de connexion à la base de données", 500

# 🔹 Route pour enregistrer un achat
@app.route("/buy", methods=["POST"])
def buy():
    try:
        product_name = request.form.get("product_name")
        payment_method = request.form.get("payment_method")
        user_agent = request.headers.get("User-Agent")
        ip = request.remote_addr  # Capture l'IP du client

        if not product_name or not payment_method:
            return jsonify({"error": "Données manquantes"}), 400

        conn = get_db()
        if conn:
            cursor = conn.cursor()

            # Vérifier si l'utilisateur existe déjà
            cursor.execute("SELECT id, refund_count FROM users WHERE ip = %s", (ip,))
            user = cursor.fetchone()

            if user:
                user_id, refund_count = user
                cursor.execute("UPDATE users SET refund_count = refund_count WHERE id = %s", (user_id,))
            else:
                cursor.execute("""
                    INSERT INTO users (ip, user_agent, fingerprint, refund_count, risk_score, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
                """, (ip, user_agent, hashlib.sha256(ip.encode()).hexdigest(), 0, 0, datetime.utcnow()))
                user_id = cursor.fetchone()[0]

            # Insérer la commande
            cursor.execute("""
                INSERT INTO orders (product_name, ip, user_agent, payment_method, created_at)
                VALUES (%s, %s, %s, %s, %s)
            """, (product_name, ip, user_agent, payment_method, datetime.utcnow()))

            conn.commit()
            cursor.close()
            conn.close()

            return redirect(url_for("orders"))

        else:
            return jsonify({"error": "Connexion à la base de données impossible"}), 500

    except Exception as e:
        print("❌ Erreur API achat:", e)
        return jsonify({"error": str(e)}), 500

# 🔹 Route pour enregistrer une demande de remboursement
@app.route("/refund", methods=["POST"])
def refund():
    try:
        # ✅ Vérification du Content-Type
        if request.content_type != "application/json":
            return jsonify({"error": "Le Content-Type doit être 'application/json'"}), 415

        data = request.get_json()
        if not data or "order_id" not in data:
            return jsonify({"error": "Données manquantes ou mal formatées"}), 400

        order_id = data.get("order_id")

        conn = get_db()
        if conn:
            cursor = conn.cursor()

            # ✅ Vérifie si la commande existe
            cursor.execute("SELECT ip FROM orders WHERE id = %s", (order_id,))
            order = cursor.fetchone()

            if not order:
                return jsonify({"error": "Commande non trouvée"}), 404

            ip = order[0]

            # ✅ Vérifie si l'utilisateur existe déjà
            cursor.execute("SELECT id, refund_count FROM users WHERE ip = %s", (ip,))
            user = cursor.fetchone()

            if user:
                user_id, refund_count = user
                cursor.execute("UPDATE users SET refund_count = refund_count + 1 WHERE id = %s", (user_id,))
            else:
                cursor.execute("""
                    INSERT INTO users (ip, user_agent, fingerprint, refund_count, risk_score, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (ip, "Inconnu", hashlib.sha256(ip.encode()).hexdigest(), 1, 0, datetime.utcnow()))

            # ✅ Insère la demande de remboursement
            cursor.execute("""
                INSERT INTO refunds (order_id, status, created_at)
                VALUES (%s, %s, %s)
            """, (order_id, "En attente", datetime.utcnow()))

            conn.commit()
            cursor.close()
            conn.close()

            return jsonify({"message": "Demande de remboursement enregistrée"}), 200
        else:
            return jsonify({"error": "Connexion à la base de données impossible"}), 500

    except Exception as e:
        print("❌ Erreur API remboursement:", e)
        return jsonify({"error": str(e)}), 500


# 🔹 Route pour afficher le dashboard avec les utilisateurs et remboursements
@app.route("/dashboard")
def dashboard():
    conn = get_db()
    if conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT u.id, u.ip, u.user_agent, u.fingerprint, u.refund_count, u.risk_score, u.created_at, 
                   COALESCE(r.status, 'Aucun remboursement') AS refund_status
            FROM users u 
            LEFT JOIN refunds r ON u.id = r.order_id
            ORDER BY u.created_at DESC
        """)
        users = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template("dashboard.html", users=users)
    return "Erreur de connexion à la base de données", 500

# 🔹 Lancer l'application
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10002, debug=True)
