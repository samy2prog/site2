import os
import psycopg2
from flask import Flask, request, jsonify, render_template, redirect, url_for
from datetime import datetime

app = Flask(__name__)

# ✅ Remplace ici par ton NOUVEAU lien PostgreSQL
DATABASE_URL = "postgresql://eshop_db_d9qc_user:6IoPk0zWxCmDL9EEQshbWrmK54bdfced@dpg-cv93lh1u0jms73eevl00-a.frankfurt-postgres.render.com/eshop_db_d9qc"

def get_db():
    """Connexion à PostgreSQL"""
    try:
        print("🔗 Connexion à PostgreSQL...")
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
        print("✅ Connexion réussie !")
        return conn
    except psycopg2.OperationalError as e:
        print("❌ ERREUR DE CONNEXION À POSTGRESQL :", e)
        return None

# ✅ Route : Page d'accueil des achats
@app.route("/")
def index():
    return render_template("index.html")

# ✅ Route : Historique des commandes
@app.route("/orders")
def orders():
    db = get_db()
    if db:
        cursor = db.cursor()
        cursor.execute("SELECT id, product_name, ip, user_agent, payment_method, created_at FROM orders ORDER BY created_at DESC")
        orders = cursor.fetchall()
        cursor.close()
        db.close()
        return render_template("orders.html", orders=orders)
    else:
        return "❌ Impossible de se connecter à la base de données.", 500

# ✅ Route : Achat d'un produit
@app.route("/buy", methods=["POST"])
def buy():
    try:
        data = request.form
        product_name = data.get("product_name")
        payment_method = data.get("payment_method")
        user_ip = request.remote_addr
        user_agent = request.headers.get("User-Agent")
        created_at = datetime.utcnow()

        db = get_db()
        if db:
            cursor = db.cursor()
            cursor.execute("""
                INSERT INTO orders (product_name, ip, user_agent, payment_method, created_at)
                VALUES (%s, %s, %s, %s, %s)
            """, (product_name, user_ip, user_agent, payment_method, created_at))

            db.commit()
            cursor.close()
            db.close()

        return redirect(url_for("orders"))

    except Exception as e:
        print("❌ Erreur API achat:", e)
        return jsonify({"error": str(e)}), 500

# ✅ Route : Demande de remboursement
@app.route("/refund", methods=["POST"])
def refund():
    try:
        order_id = request.form.get("order_id")

        db = get_db()
        if db:
            cursor = db.cursor()

            # Vérifier si la commande existe
            cursor.execute("SELECT id FROM orders WHERE id = %s", (order_id,))
            order = cursor.fetchone()

            if order:
                # Insérer la demande de remboursement
                cursor.execute("""
                    INSERT INTO refunds (order_id, status, created_at)
                    VALUES (%s, %s, %s)
                """, (order_id, "En attente", datetime.utcnow()))

                db.commit()
                cursor.close()
                db.close()
                return redirect(url_for("orders"))

            else:
                return "❌ Commande non trouvée.", 404

    except Exception as e:
        print("❌ Erreur API remboursement:", e)
        return jsonify({"error": str(e)}), 500

# ✅ Route : Vérification connexion PostgreSQL
@app.route("/test-db")
def test_db():
    try:
        db = get_db()
        if db:
            cursor = db.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            db.close()
            return "✅ Connexion à PostgreSQL réussie !"
        else:
            return "❌ Impossible de se connecter à PostgreSQL"
    except Exception as e:
        return f"❌ Erreur PostgreSQL : {e}"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10002))  # Assure-toi que Site2 utilise un port différent
    app.run(host="0.0.0.0", port=port, debug=True)
