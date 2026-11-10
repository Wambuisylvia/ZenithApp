from flask import Flask, request, jsonify
import pymysql
from flask_cors import CORS  # 🌟 1. IMPORT THIS NEW LINE
import os
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv


load_dotenv()

app = Flask(__name__)
CORS(app)  # 🌟 2. ADD THIS NEW LINE right below app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = "static/images"

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENAI_API_KEY")
)

# ====================== DATABASE CONNECTION HELPER ======================
def get_db_connection():
    return pymysql.connect(
        user="root",
        host="localhost",
        password="",           # Put your password if any
        database="Zenith",
        cursorclass=pymysql.cursors.DictCursor
    )
from flask import Flask, jsonify, request
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

import os


OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        user_message = data.get('message', '')
        total_saved = data.get('totalSaved', 0)
        goals_count = data.get('goalsCount', 0)
        
        system_instructions = f"""
        You are Zeni, a friendly, encouraging, and sharp AI financial assistant built into PesaWise.
        Current live metrics:
        - Total Saved: KSh {total_saved}
        - Active Goals Count: {goals_count}
        
        Instructions:
        - Chat with the user about their budgeting, savings, and financial goals.
        - Reference their exact numbers to encourage them.
        - Keep answers concise, practical, and warm. Use Kenyan Shillings (KSh).
        """
        
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "google/gemini-2.5-flash",
                "messages": [
                    {"role": "system", "content": system_instructions},
                    {"role": "user", "content": user_message}
                ]
            }
        )
        
        result = response.json()
        if "choices" in result and len(result["choices"]) > 0:
            return jsonify({"reply": result["choices"][0]["message"]["content"]})
        else:
            return jsonify({"reply": "🤖 Sorry, I had trouble processing that. Try again!"})
            
    except Exception as e:
        print("Backend Error:", e)
        return jsonify({"reply": "❌ Connected to server, but couldn't reach OpenRouter."}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)

# ====================== USERS ======================
@app.route("/api/signup", methods=["POST"])
def signup():
    try:
        first_name = request.form["first_name"]
        email = request.form["email"]
        password = request.form["password"]   # In production: Hash the password!

        conn = get_db_connection()
        cursor = conn.cursor()

        sql = """INSERT INTO users (first_name, email, password_hash) 
                 VALUES (%s, %s, %s)"""
        cursor.execute(sql, (first_name, email, password))
        
        conn.commit()
        return jsonify({"message": "Account created successfully"})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    finally:
        conn.close()


@app.route("/api/signin", methods=["POST"])
def signin():
    try:
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db_connection()
        cursor = conn.cursor()

        sql = "SELECT id, first_name, email, currency FROM users WHERE email=%s AND password_hash=%s"
        cursor.execute(sql, (email, password))
        
        user = cursor.fetchone()
        
        if user:
            return jsonify({"message": "Login successful", "user": user})
        else:
            return jsonify({"message": "Invalid email or password"}), 401
    
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    finally:
        conn.close()


# ====================== ACCOUNTS ======================
@app.route("/api/accounts", methods=["POST"])
def create_account():
    try:
        user_id = request.form["user_id"]
        name = request.form["name"]
        acc_type = request.form["type"]          # checking, savings, investment, etc.
        balance = request.form.get("balance", 0.00)
        currency = request.form.get("currency", "USD")
        institution = request.form.get("institution")

        conn = get_db_connection()
        cursor = conn.cursor()

        sql = """INSERT INTO accounts (user_id, name, type, balance, currency, institution) 
                 VALUES (%s, %s, %s, %s, %s, %s)"""
        cursor.execute(sql, (user_id, name, acc_type, balance, currency, institution))
        conn.commit()
        
        return jsonify({"message": "Account created successfully"})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    finally:
        conn.close()


@app.route("/api/accounts/<int:user_id>", methods=["GET"])
def get_accounts(user_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        sql = "SELECT * FROM accounts WHERE user_id = %s AND is_active = TRUE"
        cursor.execute(sql, (user_id,))
        accounts = cursor.fetchall()
        
        return jsonify(accounts)
    finally:
        conn.close()


# ====================== TRANSACTIONS ======================
@app.route("/api/transactions", methods=["POST"])
def create_transaction():
    try:
        user_id = request.form["user_id"]
        account_id = request.form["account_id"]
        amount = request.form["amount"]
        trans_type = request.form["type"]           # income, expense, transfer
        description = request.form.get("description")
        category_id = request.form.get("category_id")
        transaction_date = request.form.get("transaction_date", datetime.now().date())

        conn = get_db_connection()
        cursor = conn.cursor()

        sql = """INSERT INTO transactions 
                 (user_id, account_id, amount, type, description, category_id, transaction_date) 
                 VALUES (%s, %s, %s, %s, %s, %s, %s)"""
        
        cursor.execute(sql, (user_id, account_id, amount, trans_type, description, category_id, transaction_date))
        conn.commit()
        
        return jsonify({"message": "Transaction added successfully"})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    finally:
        conn.close()


@app.route("/api/transactions/<int:user_id>", methods=["GET"])
def get_transactions(user_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        sql = """SELECT t.*, c.name as category_name 
                 FROM transactions t 
                 LEFT JOIN transaction_categories c ON t.category_id = c.id 
                 WHERE t.user_id = %s 
                 ORDER BY t.transaction_date DESC"""
        cursor.execute(sql, (user_id,))
        transactions = cursor.fetchall()
        
        return jsonify(transactions)
    finally:
        conn.close()


# ====================== GOALS ======================
@app.route("/api/goals", methods=["POST"])
def create_goal():
    try:
        user_id = request.form["user_id"]
        title = request.form["title"]
        target_amount = request.form["target_amount"]
        target_date = request.form.get("target_date")

        conn = get_db_connection()
        cursor = conn.cursor()

        sql = """INSERT INTO goals (user_id, title, target_amount, target_date) 
                 VALUES (%s, %s, %s, %s)"""
        cursor.execute(sql, (user_id, title, target_amount, target_date))
        conn.commit()
        
        return jsonify({"message": "Goal created successfully"})
    finally:
        conn.close()


@app.route("/api/goals/<int:user_id>", methods=["GET"])
def get_goals(user_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM goals WHERE user_id = %s", (user_id,))
        return jsonify(cursor.fetchall())
    finally:
        conn.close()


# ====================== REMINDERS ======================
@app.route("/api/reminders", methods=["POST"])
def create_reminder():
    try:
        user_id = request.form["user_id"]
        text = request.form["text"]
        due_date = request.form.get("due_date")

        conn = get_db_connection()
        cursor = conn.cursor()

        sql = "INSERT INTO reminders (user_id, text, due_date) VALUES (%s, %s, %s)"
        cursor.execute(sql, (user_id, text, due_date))
        conn.commit()
        
        return jsonify({"message": "Reminder created"})
    finally:
        conn.close()


@app.route("/api/reminders/<int:user_id>", methods=["GET"])
def get_reminders(user_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM reminders WHERE user_id = %s ORDER BY due_date", (user_id,))
        return jsonify(cursor.fetchall())
    finally:
        conn.close()


# ====================== RUN APP ======================
if __name__ == "__main__":
    app.run(debug=True)
