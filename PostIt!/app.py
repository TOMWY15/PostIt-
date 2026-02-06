from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = "postit_secret_key" # Necessario per gestire le sessioni utenti

# Database temporaneo in memoria (in un'app reale useresti SQLite o PostgreSQL)
users = {} # {username: password}
posts = [] # [{author: str, content: str}]

@app.route('/')
def index():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('index.html', user=session['user'], posts=posts)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Logica semplice: se l'utente non esiste, lo registra
        if username not in users:
            users[username] = password
        
        if users[username] == password:
            session['user'] = username
            return redirect(url_for('index'))
            
    return render_template('index.html', auth_mode=True)

@app.route('/post', methods=['POST'])
def add_post():
    if 'user' in session:
        content = request.form.get('content')
        if content:
            posts.insert(0, {'author': session['user'], 'content': content})
    return redirect(url_for('index'))

@app.route('/delete/<int:post_id>')
def delete_post(post_id):
    if 'user' in session:
        # Rimuove il post se l'indice esiste (logica semplificata)
        if 0 <= post_id < len(posts):
            if posts[post_id]['author'] == session['user']:
                posts.pop(post_id)
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
