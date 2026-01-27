from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
from functools import wraps


# ---------- BD ----------
def ligar_bd():
    return mysql.connector.connect(
        host="62.28.39.135",
        user="efa0125",
        password="123.Abc",
        database="efa0125_15_vet_clinic",
    )


# ---------- APP ----------
app = Flask(__name__)
app.secret_key = "chave-simples-para-formacao"


# ---------- FUNÇÕES SIMPLES DE PERMISSÕES ----------
def esta_logado():
    return "user_id" in session


def e_admin():
    return session.get("role") == "admin"

def e_staff():
    return session.get("role") == "staff"


def exigir_login():
    if not esta_logado():
        return redirect(url_for("login"))
    return None


def exigir_admin():
    if not esta_logado():
        return redirect(url_for("login"))
    if not e_admin():
        flash("Não tem permissões para executar essa ação.")
        return redirect(url_for("users"))
    return None


# ---------- LOGIN ----------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]

        cnx = ligar_bd()
        cur = cnx.cursor(dictionary=True)

        # Agora vai buscar também o role
        cur.execute(
            "SELECT id, username, password, role FROM users WHERE username = %s",
            (username,),
        )
        user = cur.fetchone()

        cur.close()
        cnx.close()

        # Validar password (texto simples)
        if user and user["password"] == password:
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]  # <-- MUITO IMPORTANTE
            return redirect(url_for("users"))
        else:
            flash("Username ou password incorretos.")
            return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))  # volta à página inicial


# ---------- HOME (opcional) ----------
@app.route("/")
def index():
    # Página pública (sem login)
    return render_template("index.html")


# ---------- DASHBOARD ----------
@app.route("/dashboard")
def dashboard():
    redir = exigir_login()
    if redir:
        return redir

    return render_template("dashboard.html")


# ---------- CLIENTES (LISTAR) ----------
@app.route("/clientes")
def clientes():
    redir = exigir_login()
    if redir:
        return redir

    cnx = ligar_bd()
    cur = cnx.cursor(dictionary=True)

    cur.execute(
        "SELECT id, nome, telefone, email, morada, created_at FROM clientes ORDER BY id DESC"
    )
    lista_clientes = cur.fetchall()

    cur.close()
    cnx.close()

    return render_template("clientes.html", clientes=lista_clientes)


# ---------- USERS (LISTAR) ----------
@app.route("/users")
def users():
    redir = exigir_login()
    if redir:
        return redir

    cnx = ligar_bd()
    cur = cnx.cursor(dictionary=True)

    cur.execute("SELECT id, username, role, created_at FROM users ORDER BY id DESC")
    lista_users = cur.fetchall()

    cur.close()
    cnx.close()

    return render_template("users.html", users=lista_users)


# ---------- CRUD (APENAS ADMIN) ----------
@app.route("/novo", methods=["GET", "POST"])
def user_novo():
    redir = exigir_admin()
    if redir:
        return redir

    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"].strip()
        role = request.form["role"].strip()

        cnx = ligar_bd()
        cursor = cnx.cursor()

        try:
            cursor.execute(
                "INSERT INTO users (username, password, role) VALUES (%s, %s, %s)",
                (username, password, role),
            )
            cnx.commit()
            flash("Utilizador criado com sucesso!")
        except mysql.connector.Error as err:
            flash(f"Erro ao criar: {err}")
        finally:
            cursor.close()
            cnx.close()

        return redirect(url_for("users"))

    return render_template("user_form.html", titulo="Novo utilizador", utilizador=None)


@app.route("/editar/<int:id>", methods=["GET", "POST"])
def user_editar(id):
    redir = exigir_admin()
    if redir:
        return redir

    cnx = ligar_bd()
    cursor = cnx.cursor(dictionary=True)

    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"].strip()
        role = request.form["role"].strip()

        cursor2 = cnx.cursor()
        try:
            cursor2.execute(
                "UPDATE users SET username=%s, password=%s, role=%s WHERE id=%s",
                (username, password, role, id),
            )
            cnx.commit()
            flash("Utilizador atualizado com sucesso!")
        except mysql.connector.Error as err:
            flash(f"Erro ao atualizar: {err}")
        finally:
            cursor2.close()
            cursor.close()
            cnx.close()

        return redirect(url_for("users"))

    cursor.execute("SELECT id, username, password, role FROM users WHERE id=%s", (id,))
    utilizador = cursor.fetchone()

    cursor.close()
    cnx.close()

    if not utilizador:
        flash("Utilizador não encontrado.")
        return redirect(url_for("users"))

    return render_template(
        "user_form.html", titulo="Editar utilizador", utilizador=utilizador
    )


@app.route("/apagar/<int:id>", methods=["POST"])
def user_apagar(id):
    redir = exigir_admin()
    if redir:
        return redir

    cnx = ligar_bd()
    cursor = cnx.cursor()

    try:
        cursor.execute("DELETE FROM users WHERE id=%s", (id,))
        cnx.commit()
        flash("Utilizador apagado com sucesso!")
    except mysql.connector.Error as err:
        flash(f"Erro ao apagar: {err}")
    finally:
        cursor.close()
        cnx.close()

    return redirect(url_for("users"))

# ---------- ANIMAIS ----------
@app.route("/animais")
def animais():
    redir = exigir_login()
    if redir:
        return redir

    cnx = ligar_bd()
    cur = cnx.cursor(dictionary=True)

    # Admin/Staff vêem todos os animais
    if e_admin() or e_staff():
        cur.execute(
            "SELECT id, cliente_id, nome, especie, raca, data_nascimento, created_at "
            "FROM animais ORDER BY id DESC"
        )
        is_admin_or_staff = True
    else:
        cliente_id = session.get("cliente_id")
        cur.execute(
            "SELECT id, cliente_id, nome, especie, raca, data_nascimento, created_at "
            "FROM animais WHERE cliente_id=%s ORDER BY id DESC",
            (cliente_id,)
        )
        is_admin_or_staff = False

    lista_animais = cur.fetchall()
    cur.close()
    cnx.close()

    return render_template("animais.html", animais=lista_animais, is_admin_or_staff=is_admin_or_staff)


@app.route("/animais/novo", methods=["GET", "POST"])
def animais_novo():
    redir = exigir_login()
    if redir:
        return redir
    
    if not e_admin() and not e_staff():
        flash("Acesso negado.")
        return redirect(url_for("dashboard"))

    cnx = ligar_bd()
    cur = cnx.cursor(dictionary=True)

    # Pegamos todos os clientes para o select
    cur.execute("SELECT id, nome FROM clientes ORDER BY nome ASC")
    clientes = cur.fetchall()

    if request.method == "POST":
        cliente_id = request.form["cliente_id"]  # vem do select
        nome = request.form["nome"].strip()
        especie = request.form["especie"].strip()
        raca = request.form["raca"].strip()
        data_nascimento = request.form["data_nascimento"].strip()

        try:
            cur.execute(
                "INSERT INTO animais (cliente_id, nome, especie, raca, data_nascimento, created_at) "
                "VALUES (%s, %s, %s, %s, %s, NOW())",
                (cliente_id, nome, especie, raca, data_nascimento),
            )
            cnx.commit()
            flash("Animal adicionado com sucesso!")
            return redirect(url_for("animais"))

        except mysql.connector.Error as err:
            flash(f"Erro ao adicionar novo animal: {err}")
            return redirect(url_for("animais"))

    cur.close()
    cnx.close()

    return render_template("animais_form.html", titulo="Novo Animal", clientes=clientes)



# ---------- CONSULTAS (LISTAR) ----------
@app.route("/consultas")
def consultas():
    redir = exigir_login()
    if redir:
        return redir

    cnx = ligar_bd()
    cur = cnx.cursor(dictionary=True)

    cur.execute(
        "SELECT id, animal_id, data_hora, motivo, notas, created_at FROM consultas ORDER BY id DESC"
    )
    lista_consultas = cur.fetchall()

    cur.close()
    cnx.close()

    return render_template("consultas.html", consultas=lista_consultas)


@app.route("/clientes/novo", methods=["GET", "POST"])
def cliente_novo():
    redir = exigir_admin()
    if redir:
        return redir

    if request.method == "POST":
        nome = request.form["nome"].strip()
        telefone = request.form["telefone"].strip()
        email = request.form["email"].strip()
        morada = request.form["morada"].strip()
        password = request.form["password"]

        cnx = ligar_bd()
        cur = cnx.cursor()

        try:
            # Inserir na tabela clientes
            cur.execute(
                "INSERT INTO clientes (nome, password, telefone, email, morada) "
                "VALUES (%s, %s, %s, %s, %s)",
                (nome, password, telefone, email, morada)
            )
            cliente_id = cur.lastrowid  # pega o id do cliente recém-criado

            # Inserir na tabela users (login do cliente)
            cur.execute(
                "INSERT INTO users (username, password, role, cliente_id) VALUES (%s, %s, %s, %s)",
                (nome, password, "cliente", cliente_id)
            )

            cnx.commit()
            flash("Cliente criado com sucesso!")

        except mysql.connector.Error as err:
            flash(f"Erro ao criar cliente: {err}")

        finally:
            cur.close()
            cnx.close()

        return redirect(url_for("clientes"))

    # GET: formulário vazio
    return render_template("clientes_form.html", titulo="Novo cliente")



@app.route("/login/editar/<int:id>", methods=["GET", "POST"])
def cliente_editar(id):
    redir = exigir_admin()
    if redir:
        return redir

    cnx = ligar_bd()
    cur = cnx.cursor(dictionary=True)

    if request.method == "POST":
        nome = request.form["nome"].strip()
        telefone = request.form["telefone"].strip()
        email = request.form["email"].strip()
        morada = request.form["morada"].strip()

        cur2 = cnx.cursor()
        try:
            cur2.execute(
                "UPDATE clientes SET nome=%s, telefone=%s, email=%s, morada=%s WHERE id=%s",
                (nome, telefone, email, morada, id),
            )
            cnx.commit()
            if cur2.rowcount == 0:
                flash("Não foi possível atualizar (ID não encontrado).")
            else:
                flash("Cliente atualizado com sucesso!")
        except mysql.connector.Error as err:
            flash(f"Erro ao atualizar cliente: {err}")
        finally:
            cur2.close()
            cur.close()
            cnx.close()

        return redirect(url_for("clientes"))

    # GET: buscar login
    cur.execute(
        "SELECT id, nome, telefone, email, morada FROM clientes WHERE id=%s", (id,)
    )
    login_row = cur.fetchone()
    cur.close()
    cnx.close()

    if not login_row:
        flash("Login não encontrado.")
        return redirect(url_for("users"))

    return render_template(
        "clientes_form.html", titulo="Editar cliente", login=login_row
    )


@app.route("/cliente/apagar/<int:id>", methods=["POST"])
def cliente_apagar(id):
    redir = exigir_admin()
    if redir:
        return redir

    cnx = ligar_bd()
    cur = cnx.cursor()
    try:
        cur.execute("DELETE FROM clientes WHERE id=%s", (id,))
        cnx.commit()
        if cur.rowcount == 0:
            flash("Não existe cliente com esse ID.")
        else:
            flash("Cliente apagado com sucesso!")
    except mysql.connector.Error as err:
        flash(f"Erro ao apagar cliente: {err}")
    finally:
        cur.close()
        cnx.close()

    return redirect(url_for("clientes"))




if __name__ == "__main__":
    app.run(debug=True)
