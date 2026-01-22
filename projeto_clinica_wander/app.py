from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
from functools import wraps

# ---------- BD ----------
def ligar_bd():
    return mysql.connector.connect(
        host="62.28.39.135",
        user="efa0125",
        password="123.Abc",
        database="efa0125_15_vet_clinic"
    )

# ---------- APP ----------
app = Flask(__name__)
app.secret_key = "chave-simples-para-formacao"

# ---------- DECORATORS DE SEGURANÇA ----------
def login_obrigatorio(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Faça login para continuar.")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def exige_roles(*roles):
    def wrapper(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if session.get("role") not in roles:
                flash("Sem permissões para esta ação.")
                return redirect(url_for("dashboard"))
            return f(*args, **kwargs)
        return decorated
    return wrapper

# ---------- LOGIN ----------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"].strip()

        cnx = ligar_bd()
        cursor = cnx.cursor(dictionary=True)

        cursor.execute(
            "SELECT id, username, password, role, cliente_id "
            "FROM users WHERE username=%s",
            (username,)
        )
        user = cursor.fetchone()

        cursor.close()
        cnx.close()

        if not user or user["password"] != password:
            flash("Username ou password inválidos.")
            return redirect(url_for("login"))

        session.clear()
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        session["role"] = user["role"]
        session["cliente_id"] = user["cliente_id"]

        flash(f"Bem-vindo, {user['username']}!")
        return redirect(url_for("dashboard"))

    return render_template("index_login.html")

# ---------- LOGOUT ----------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ---------- DASHBOARD ----------
@app.route("/dashboard")
@login_obrigatorio
def dashboard():
    return render_template("dashboard.html")

# ---------- CLIENTE ----------
@app.route("/clientes")
@login_obrigatorio
@exige_roles("cliente")
def cliente():
    cliente_id = session["cliente_id"]

    cnx = ligar_bd()
    cursor = cnx.cursor(dictionary=True)

    cursor.execute(
        "SELECT nome, telefone, email, morada, criado_at "
        "FROM clientes WHERE id=%s",
        (cliente_id,)
    )
    cliente = cursor.fetchone()

    cursor.close()
    cnx.close()

    return render_template("clientes.html", cliente=cliente)

# ---------- ANIMAIS ----------
@app.route("/animais")
@login_obrigatorio
@exige_roles("cliente")
def animais():
    cliente_id = session["cliente_id"]

    cnx = ligar_bd()
    cursor = cnx.cursor(dictionary=True)

    cursor.execute(
        "SELECT nome, especie, raca, data_nascimento "
        "FROM animais WHERE cliente_id=%s",
        (cliente_id,)
    )
    animais = cursor.fetchall()

    cursor.close()
    cnx.close()

    return render_template("animais.html", animais=animais)

# ---------- USERS (ADMIN / STAFF) ----------
@app.route("/users")
@login_obrigatorio
@exige_roles("admin", "staff")
def listar_users():
    cnx = ligar_bd()
    cursor = cnx.cursor(dictionary=True)

    cursor.execute("SELECT id, username, role FROM users")
    users = cursor.fetchall()

    cursor.close()
    cnx.close()

    return render_template("users.html", users=users)

# ---------- EDITAR USER ----------
@app.route("/users/editar/<int:id>", methods=["POST"])
@login_obrigatorio
@exige_roles("admin", "staff")
def editar_user(id):
    if session["user_id"] == id:
        flash("Não pode editar o seu próprio utilizador.")
        return redirect(url_for("listar_users"))

    username = request.form["username"].strip()
    password = request.form["password"].strip()
    role = request.form["role"].strip()

    cnx = ligar_bd()
    cursor = cnx.cursor()

    cursor.execute(
        "UPDATE users SET username=%s, password=%s, role=%s WHERE id=%s",
        (username, password, role, id)
    )
    cnx.commit()

    cursor.close()
    cnx.close()

    flash("Utilizador atualizado com sucesso.")
    return redirect(url_for("listar_users"))

# ---------- APAGAR USER ----------
@app.route("/users/apagar/<int:id>")
@login_obrigatorio
@exige_roles("admin")
def apagar_user(id):
    if session["user_id"] == id:
        flash("Não pode apagar o seu próprio utilizador.")
        return redirect(url_for("listar_users"))

    cnx = ligar_bd()
    cursor = cnx.cursor()

    cursor.execute("DELETE FROM users WHERE id=%s", (id,))
    cnx.commit()

    cursor.close()
    cnx.close()

    flash("Utilizador apagado com sucesso.")
    return redirect(url_for("listar_users"))

# ---------- CONSULTAS ----------
@app.route("/consultas/<int:animal_id>")
@login_obrigatorio
def consultas(animal_id):
    cnx = ligar_bd()
    cursor = cnx.cursor(dictionary=True)

    cursor.execute(
        "SELECT data_hora, motivo, notas "
        "FROM consultas WHERE animal_id=%s",
        (animal_id,)
    )
    consultas = cursor.fetchall()

    cursor.close()
    cnx.close()

    return render_template("consultas.html", consultas=consultas)

# ---------- RUN ----------
if __name__ == "__main__":
    app.run(debug=True)
