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
    return "user_id" in session or "cliente_id" in session


def exigir_admin():
    return session.get("role") == "admin"


def e_staff():
    return session.get("role") == "staff"


def e_cliente():
    return session.get("role") == "cliente"


def exigir_login():
    if not esta_logado():
        return redirect(url_for("login"))
    return None


# ---------- LOGIN ----------
@app.route("/login", methods=["GET", "POST"])
def login():
    #se houver acionamento do metodo post no html atravez de um submit
    #request.form que contem os dados enviados pelo form
    #request.form[username] captura o foi digitado conform o input do HTML
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]

    #depois que esta salvo nas variaveis o sistema vai ate a base de dados
    #saca todos os dados dentro do select desde que o username exista e 
    # esteja em conformidade com o que foi digitado salva os dados em um dicionario
        try:
            cnx = ligar_bd()
            cur = cnx.cursor(dictionary=True)

            cur.execute(
                "SELECT id, username, password, role FROM users WHERE username=%s",
                (username,)
            )

            user = cur.fetchone()

        except mysql.connector.Error as err:
            flash(f"Erro ao tentar login: {err}")
            return redirect(url_for("login"))

        finally:
            cur.close()
            cnx.close()

        # validação simples pega o que foi salvo em fetchone para validacao
        #caso seja true ele guarda os dados abaixo na session
        if user and user["password"] == password:
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]
            return redirect(url_for("dashboard"))
        else:
            flash("Username ou password incorretos.")
            return redirect(url_for("login"))

    #abaixo ele monta o HTML e envia para o HTML, que contem o form e recebe
    #os dadsos do utilizador
    return render_template("login.html", titulo="Login de funcionários")



@app.route("/logout")
def logout():
    session.clear()
    return redirect(
        url_for("index", username="username", role="role")
    )  # volta à página inicial


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

    info = {}

    cnx = ligar_bd()
    cur = cnx.cursor(dictionary=True)

    try:
        if e_cliente():
            cliente_id = session.get("cliente_id")
            cur.execute(
                "SELECT id, nome, telefone, email, created_at FROM clientes WHERE id=%s",
                (cliente_id,),
            )
            cliente = cur.fetchone()

            cur.execute(
                "SELECT id, username, password, created_at, role FROM users WHERE cliente_id=%s",
                (cliente_id,),
            )
            user = cur.fetchone()

            info = {
                "id": cliente["id"] if cliente else None,
                "nome": cliente["nome"] if cliente else None,
                "telefone": cliente["telefone"] if cliente else None,
                "email": cliente["email"] if cliente else None,
                "username": user["username"] if user else None,
                "password": user["password"] if user else None,
                "created_at": user["created_at"] if user else cliente.get("created_at"),
                "role": user["role"] if user else "cliente",
            }

        else:  # admin ou staff
            user_id = session.get("user_id")
            cur.execute(
                "SELECT id, username, password, cliente_id, created_at, role FROM users WHERE id=%s",
                (user_id,),
            )
            user = cur.fetchone()

            info = {
                "id": user["id"] if user else None,
                "username": user["username"] if user else None,
                "password": user["password"] if user else None,
                "created_at": user["created_at"] if user else None,
                "role": user["role"] if user else None,
            }

            cliente_id = user["cliente_id"] if user else None
            if cliente_id:
                cur.execute(
                    "SELECT nome, telefone, email FROM clientes WHERE id=%s",
                    (cliente_id,),
                )
                cliente = cur.fetchone()
                if cliente:
                    info.update(
                        {
                            "nome": cliente["nome"],
                            "telefone": cliente["telefone"],
                            "email": cliente["email"],
                        }
                    )
    finally:
        cur.close()
        cnx.close()

    return render_template(
        "dashboard.html",
        titulo="Dashboard",
        username=info.get("username"),
        role=info.get("role"),
    )


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

    # Admin e Staff veem todos
    if session.get("role") in ["admin", "staff"]:
        cur.execute("SELECT id, cliente_id, nome, especie, raca, data_nascimento, created_at " \
        "FROM animais ORDER BY id DESC ")
        
        is_admin_or_staff = True

    # Cliente vê apenas os seus
    else:
        cliente_id = session.get("cliente_id")
        cur.execute(" SELECT id, cliente_id, nome, especie, raca, data_nascimento, created_at " \
        "FROM animais WHERE cliente_id = %s ORDER BY id DESC ", (cliente_id,))
        is_admin_or_staff = False

    lista_animais = cur.fetchall()
    cur.close()
    cnx.close()

    return render_template("animais.html",
                           animais=lista_animais,
                           is_admin_or_staff=is_admin_or_staff)


@app.route("/animais/novo", methods=["GET", "POST"])
def animais_novo():
    if session.get("role") not in ["admin", "staff"]:
        flash("Acesso negado.")
        return redirect(url_for("dashboard"))

    cnx = ligar_bd()
    cur = cnx.cursor(dictionary=True)

    cur.execute("SELECT id, nome FROM clientes ORDER BY nome")
    clientes = cur.fetchall()

    if request.method == "POST":
        cliente_id = request.form["cliente_id"]
        nome = request.form["nome"]
        especie = request.form["especie"]
        raca = request.form["raca"]
        data_nascimento = request.form["data_nascimento"]

        cur.execute(" INSERT INTO animais (cliente_id, nome, especie, raca, data_nascimento, " \
        "created_at) VALUES (%s, %s, %s, %s, %s, NOW()", (cliente_id, nome, especie, raca, data_nascimento))

        cnx.commit()
        flash("Animal criado com sucesso!")
        return redirect(url_for("animais"))

    return render_template("animais_form.html", clientes=clientes, titulo="Novo Animal")


@app.route("/animais/editar/<int:id>", methods=["GET", "POST"])
def animais_editar(id):
    if session.get("role") not in ["admin", "staff"]:
        flash("Acesso negado.")
        return redirect(url_for("dashboard"))

    cnx = ligar_bd()
    cur = cnx.cursor(dictionary=True)

    if request.method == "POST":
        cliente_id = request.form["cliente_id"]
        nome = request.form["nome"]
        especie = request.form["especie"]
        raca = request.form["raca"]
        data_nascimento = request.form["data_nascimento"]

        cliente_id = int(request.form["cliente_id"])

        cur.execute("""
            UPDATE animais
            SET cliente_id=%s,
            nome=%s,
            especie=%s,
            raca=%s,
            data_nascimento=%s
        WHERE id=%s
        """, (cliente_id, nome, especie, raca, data_nascimento, id))


        cnx.commit()
        flash("Animal atualizado!")
        return redirect(url_for("animais"))

    cur.execute("SELECT * FROM animais WHERE id=%s", (id,))
    animal = cur.fetchone()

    cur.execute("SELECT id, nome FROM clientes ORDER BY nome")
    clientes = cur.fetchall()

    return render_template("animais_form.html", animal=animal, clientes=clientes, titulo="Editar Animal")


@app.route("/animais/apagar/<int:id>", methods=["POST"])
def animais_apagar(id):
    if session.get("role") not in ["admin", "staff"]:
        flash("Acesso negado.")
        return redirect(url_for("dashboard"))

    cnx = ligar_bd()
    cur = cnx.cursor()

    cur.execute("DELETE FROM animais WHERE id=%s", (id,))
    cnx.commit()

    flash("Animal removido com sucesso!")
    return redirect(url_for("animais"))


# ---------- CONSULTAS ANIMAIS ----------
@app.route("/consultas")
def consultas():
    redir = exigir_login()
    if redir:
        return redir

    cnx = ligar_bd()
    cur = cnx.cursor(dictionary=True)

    # ADMIN E STAFF VEEM TODAS
    if session.get("role") in ["admin", "staff"]:
        cur.execute("""
            SELECT c.*, a.nome AS animal_nome
            FROM consultas c
            JOIN animais a ON c.animal_id = a.id
            ORDER BY c.data_hora DESC
        """)
    else:
        # CLIENTE SÓ VÊ CONSULTAS DOS SEUS ANIMAIS
        cliente_id = session.get("cliente_id")
        cur.execute("""
            SELECT c.*, a.nome AS animal_nome
            FROM consultas c
            JOIN animais a ON c.animal_id = a.id
            WHERE a.cliente_id = %s
            ORDER BY c.data_hora DESC
        """, (cliente_id,))

    lista_consultas = cur.fetchall()
    cur.close()
    cnx.close()

    return render_template("consultas.html", consultas=lista_consultas)


@app.route("/consultas/nova", methods=["GET", "POST"])
def consulta_nova():
    redir = exigir_login()
    if redir:
        return redir

    if e_cliente():
        flash("Clientes não podem criar consultas.")
        return redirect(url_for("consultas"))

    cnx = ligar_bd()
    cur = cnx.cursor(dictionary=True)

    cur.execute("SELECT id, nome FROM animais ORDER BY nome")
    animais = cur.fetchall()

    if request.method == "POST":
        animal_id = request.form["animal_id"]
        data_hora = request.form["data_hora"]
        motivo = request.form["motivo"]
        notas = request.form["notas"]

        cur2 = cnx.cursor()
        cur2.execute(
            "INSERT INTO consultas (animal_id, data_hora, motivo, notas, created_at) VALUES (%s,%s,%s,%s,NOW())",
            (animal_id, data_hora, motivo, notas),
        )
        cnx.commit()

        flash("Consulta criada com sucesso!")
        return redirect(url_for("consultas"))

    cur.close()
    cnx.close()
    return render_template("consulta_form.html", titulo="Nova Consulta", animais=animais, consulta=None)


@app.route("/consultas/editar/<int:id>", methods=["GET", "POST"])
def consulta_editar(id):
    redir = exigir_login()
    if redir:
        return redir

    if e_cliente():
        flash("Clientes não podem editar consultas.")
        return redirect(url_for("consultas"))

    cnx = ligar_bd()
    cur = cnx.cursor(dictionary=True)

    cur.execute("SELECT * FROM consultas WHERE id=%s", (id,))
    consulta = cur.fetchone()

    cur.execute("SELECT id, nome FROM animais ORDER BY nome")
    animais = cur.fetchall()

    if request.method == "POST":
        animal_id = request.form["animal_id"]
        data_hora = request.form["data_hora"]
        motivo = request.form["motivo"]
        notas = request.form["notas"]

        cur2 = cnx.cursor()
        cur2.execute(
            "UPDATE consultas SET animal_id=%s, data_hora=%s, motivo=%s, notas=%s WHERE id=%s",
            (animal_id, data_hora, motivo, notas, id),
        )
        cnx.commit()

        flash("Consulta atualizada com sucesso!")
        return redirect(url_for("consultas"))

    cur.close()
    cnx.close()
    return render_template("consulta_form.html", titulo="Editar Consulta", consulta=consulta, animais=animais)

@app.route("/consultas/apagar/<int:id>", methods=["POST"])
def consulta_apagar(id):
    redir = exigir_login()
    if redir:
        return redir

    if not exigir_admin() and not e_staff():
        flash("Apenas staff ou admin podem apagar consultas.")
        return redirect(url_for("consultas"))

    cnx = ligar_bd()
    cur = cnx.cursor()
    cur.execute("DELETE FROM consultas WHERE id=%s", (id,))
    cnx.commit()
    cur.close()
    cnx.close()

    flash("Consulta apagada com sucesso!")
    return redirect(url_for("consultas"))

# ---------- CLIENTES ----------


@app.route("/clientes_login", methods=["GET", "POST"])
def cliente_login():
    if request.method == "POST":
        email = request.form["email"].strip()
        password = request.form["password"].strip()

        cnx = ligar_bd()
        cur = cnx.cursor(dictionary=True)

        # Buscar cliente pelo email
        cur.execute("SELECT id, nome, email FROM clientes WHERE email=%s", (email,))
        cliente = cur.fetchone()

        if not cliente:
            flash("Email ou senha inválidos.")
            return redirect(url_for("cliente_login"))

        # Buscar login na tabela users
        cur.execute(
            "SELECT password, role FROM users WHERE cliente_id=%s", (cliente["id"],)
        )
        user = cur.fetchone()

        cur.close()
        cnx.close()

        # Verifica se existe login e se a senha confere
        if not user or user["password"] != password:
            flash("Email ou senha inválidos.")
            return redirect(url_for("cliente_login"))

        # Aqui cria a sessão
        session["cliente_id"] = cliente["id"]
        session["cliente_nome"] = cliente["nome"]
        session["role"] = user["role"]

        flash("Login realizado com sucesso!")
        return redirect(url_for("dashboard"))

    return render_template("clientes_login.html", titulo="Login Cliente")


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
        password = "12345678"

        cnx = ligar_bd()
        cur = cnx.cursor()

        cur1 = cnx.cursor()
        cur1.execute(
            "SELECT email FROM clientes WHERE email=%s",
            (email),
        )
        cliente = cur1.fetchone()

        if cliente == email:
            flash("Ja existe um cliente com esse email...")
            return render_template("cliente_novo")

        try:
            # Inserir na tabela clientes
            cur.execute(
                "INSERT INTO clientes (nome, telefone, email, morada) "
                "VALUES (%s, %s, %s, %s)",
                (nome, telefone, email, morada),
            )
            cliente_id = cur.lastrowid  # pega o id do cliente recém-criado

            # Inserir na tabela users (login do cliente)
            cur.execute(
                "INSERT INTO users (username, password, role, cliente_id) VALUES (%s, %s, %s, %s)",
                (nome, password, "cliente", cliente_id),
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
        return redirect(url_for("clientes"))


    return render_template("clientes_form.html",titulo="Editar cliente",cliente=login_row   
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
