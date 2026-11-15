import os
import re
import secrets
import unicodedata
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from functools import wraps

import pymysql
from pymysql.cursors import DictCursor
from flask import Flask, jsonify, redirect, request, send_from_directory, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

BASE = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, static_folder=None)
app.secret_key = os.getenv('FLASK_SECRET_KEY') or secrets.token_hex(32)
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax')
app.json.ensure_ascii = False  # accents lisibles dans les réponses JSON

DB = dict(host=os.getenv('DB_HOST', 'localhost'),
          user=os.getenv('DB_USER', 'root'),
          password=os.getenv('DB_PASSWORD', ''),
          database=os.getenv('DB_NAME', 'ecoplate_db'),
          charset='utf8mb4', cursorclass=DictCursor)

ROLES = ('individual', 'organization')
ORG_TYPES = ('association', 'hotel', 'restaurant')
EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
RECIPE_SEEDS = (
    ('Omelette aux tomates', 'Une omelette simple avec des tomates fondantes et de l’oignon.', ('œuf', 'tomate', 'oignon')),
    ('Pâtes à la tomate', 'Des pâtes accompagnées d’une sauce rapide à la tomate et à l’ail.', ('pâtes', 'tomate', 'ail')),
    ('Salade croquante', 'Une salade fraîche à base de légumes de saison.', ('laitue', 'tomate', 'concombre', 'carotte')),
    ('Soupe de légumes', 'Une soupe réconfortante de carottes, pommes de terre et oignons.', ('carotte', 'pommes de terre', 'oignon', 'bouillon')),
    ('Riz sauté aux légumes', 'Du riz sauté avec des œufs et des légumes.', ('riz', 'œuf', 'carotte', 'oignon')),
    ('Gratin de pommes de terre', 'Des pommes de terre gratinées avec du fromage et de la crème.', ('pommes de terre', 'fromage', 'crème')),
    ('Tartines tomate-fromage', 'Du pain grillé garni de tomate et de fromage.', ('pain', 'tomate', 'fromage')),
    ('Crêpes maison', 'Une pâte à crêpes classique avec des ingrédients du placard.', ('farine', 'lait', 'œuf')),
    ('Salade de pâtes', 'Une salade froide de pâtes, légumes et fromage.', ('pâtes', 'tomate', 'concombre', 'fromage')),
    ('Poulet aux légumes', 'Du poulet accompagné de légumes cuits au four.', ('poulet', 'carotte', 'pommes de terre', 'oignon')),
    ('Curry de lentilles', 'Des lentilles mijotées avec tomate, oignon et riz.', ('lentilles', 'tomate', 'oignon', 'riz')),
    ('Sandwich au thon', 'Un sandwich frais au thon et aux crudités.', ('pain', 'thon', 'tomate', 'laitue')),
    ('Galettes de carottes', 'Des galettes dorées à base de carottes et d’œuf.', ('carotte', 'œuf', 'farine')),
    ('Smoothie banane', 'Un smoothie rapide à la banane, au lait et au yaourt.', ('banane', 'lait', 'yaourt')),
    ('Ratatouille simple', 'Des légumes mijotés ensemble avec de la tomate.', ('courgette', 'aubergine', 'tomate', 'oignon')),
    ('Poisson au citron et riz', 'Du poisson servi avec du riz et une touche de citron.', ('poisson', 'citron', 'riz')),
    ('Pommes au four', 'Des pommes doucement cuites avec du sucre et de la cannelle.', ('pomme', 'sucre', 'cannelle')),
    ('Quiche fromage-oignon', 'Une quiche familiale au fromage et à l’oignon.', ('œuf', 'lait', 'fromage', 'oignon')),
)


def get_conn():
    return pymysql.connect(**DB)


def ensure_schema():
    """Ajoute les tables et la colonne de compte sans effacer les anciennes données."""
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
              id INT AUTO_INCREMENT PRIMARY KEY,
              email VARCHAR(254) NOT NULL UNIQUE,
              full_name VARCHAR(150) NULL,
              password_hash VARCHAR(255) NOT NULL,
              role ENUM('individual', 'organization') NOT NULL,
              created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            ) CHARACTER SET utf8mb4
        """)
        # Ajoute le nom aux bases déjà créées sans modifier les comptes existants.
        cur.execute("""
            SELECT COLUMN_NAME FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA=%s AND TABLE_NAME='users'
        """, (DB['database'],))
        user_columns = {row['COLUMN_NAME'] for row in cur.fetchall()}
        if 'full_name' not in user_columns:
            cur.execute("ALTER TABLE users ADD COLUMN full_name VARCHAR(150) NULL AFTER email")

        cur.execute("""
            CREATE TABLE IF NOT EXISTS organizations (
              id INT AUTO_INCREMENT PRIMARY KEY,
              user_id INT NOT NULL UNIQUE,
              name VARCHAR(150) NOT NULL,
              organization_type ENUM('association', 'hotel', 'restaurant') NOT NULL,
              address VARCHAR(255) NOT NULL,
              phone VARCHAR(30) NOT NULL,
              FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            ) CHARACTER SET utf8mb4
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS announcements (
              id INT AUTO_INCREMENT PRIMARY KEY,
              organization_id INT NOT NULL,
              food_name VARCHAR(100) NOT NULL,
              quantity_total INT NOT NULL,
              quantity_available INT NOT NULL,
              normal_price DECIMAL(10,2) NOT NULL,
              reduced_price DECIMAL(10,2) NOT NULL,
              deadline DATE NOT NULL,
              description TEXT NOT NULL,
              created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
              updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
              INDEX idx_announcements_org_created (organization_id, created_at),
              INDEX idx_announcements_offers (deadline, quantity_available),
              FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE
            ) CHARACTER SET utf8mb4
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS reservations (
              id INT AUTO_INCREMENT PRIMARY KEY,
              announcement_id INT NOT NULL,
              user_id INT NOT NULL,
              quantity INT NOT NULL,
              created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
              INDEX idx_reservations_user (user_id, created_at),
              FOREIGN KEY (announcement_id) REFERENCES announcements(id) ON DELETE CASCADE,
              FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            ) CHARACTER SET utf8mb4
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS recipes (
              id INT AUTO_INCREMENT PRIMARY KEY,
              name VARCHAR(150) NOT NULL UNIQUE,
              description TEXT NOT NULL
            ) CHARACTER SET utf8mb4
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS recipe_ingredients (
              id INT AUTO_INCREMENT PRIMARY KEY,
              recipe_id INT NOT NULL,
              ingredient_name VARCHAR(100) NOT NULL,
              UNIQUE KEY uq_recipe_ingredient (recipe_id, ingredient_name),
              FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
            ) CHARACTER SET utf8mb4
        """)

        cur.executemany(
            "INSERT IGNORE INTO recipes (name, description) VALUES (%s, %s)",
            [(name, description) for name, description, _ in RECIPE_SEEDS])
        recipe_names = [name for name, _, _ in RECIPE_SEEDS]
        placeholders = ','.join(['%s'] * len(recipe_names))
        cur.execute(
            f"SELECT id, name FROM recipes WHERE name IN ({placeholders})",
            recipe_names)
        recipe_ids = {row['name']: row['id'] for row in cur.fetchall()}
        ingredient_rows = [
            (recipe_ids[name], ingredient)
            for name, _, ingredients in RECIPE_SEEDS
            for ingredient in ingredients
        ]
        cur.executemany(
            "INSERT IGNORE INTO recipe_ingredients (recipe_id, ingredient_name) VALUES (%s, %s)",
            ingredient_rows)

        cur.execute("""
            SELECT COLUMN_NAME FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA=%s AND TABLE_NAME='aliment'
        """, (DB['database'],))
        columns = {row['COLUMN_NAME'] for row in cur.fetchall()}
        if 'user_id' not in columns:
            cur.execute("ALTER TABLE aliment ADD COLUMN user_id INT NULL AFTER id_aliment")

        cur.execute("""
            SELECT INDEX_NAME FROM information_schema.STATISTICS
            WHERE TABLE_SCHEMA=%s AND TABLE_NAME='aliment' AND INDEX_NAME='idx_aliment_user_status'
        """, (DB['database'],))
        if not cur.fetchone():
            cur.execute("ALTER TABLE aliment ADD INDEX idx_aliment_user_status (user_id, statut, date_peremption)")

        cur.execute("""
            SELECT CONSTRAINT_NAME FROM information_schema.TABLE_CONSTRAINTS
            WHERE CONSTRAINT_SCHEMA=%s AND TABLE_NAME='aliment'
              AND CONSTRAINT_NAME='fk_aliment_user'
        """, (DB['database'],))
        if not cur.fetchone():
            cur.execute("""
                ALTER TABLE aliment ADD CONSTRAINT fk_aliment_user
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            """)
        conn.commit()


def current_user():
    """Renvoie les informations non sensibles conservées dans la session Flask."""
    user_id = session.get('user_id')
    role = session.get('role')
    if user_id and role in ROLES:
        return {'id': user_id, 'email': session.get('email'), 'role': role}
    return None


def destination_for(user):
    return 'food.html' if user['role'] == 'individual' else 'organization-dashboard.html'


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user():
            if request.path.startswith('/api/'):
                return jsonify(error='Veuillez vous connecter pour continuer.'), 401
            return redirect(url_for('account_type'))
        return view(*args, **kwargs)
    return wrapped


def role_required(role):
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            if current_user()['role'] != role:
                if request.path.startswith('/api/'):
                    return jsonify(error='Vous n’avez pas accès à cette fonction.'), 403
                return redirect('/' + destination_for(current_user()))
            return view(*args, **kwargs)
        return wrapped
    return decorator


def parse_date(value, default=None):
    """Convertit 'AAAA-MM-JJ' en date ; renvoie default si invalide."""
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError):
        return default


def norm(text):
    """Normalise un nom d'ingrédient pour comparer 'Tomates' et 'tomate', 'Œufs' et 'oeuf'."""
    t = str(text).lower().strip().replace('œ', 'oe').replace('æ', 'ae')
    t = unicodedata.normalize('NFD', t)
    t = ''.join(ch for ch in t if not unicodedata.combining(ch))
    t = re.sub(r'\s+', ' ', t)
    t = re.sub(r'\b(\w{4,})s\b', r'\1', t)
    if len(t) > 3 and t[-1] == 'x':
        t = t[:-1]
    return t


def announcement_input(data):
    """Valide et normalise les champs communs à la création et à la modification."""
    if not isinstance(data, dict):
        return None
    name = data.get('food_name')
    description = data.get('description', '')
    deadline_value = data.get('deadline')
    quantity_value = data.get('quantity_total')
    if (not isinstance(name, str) or not isinstance(description, str)
            or not isinstance(deadline_value, str) or isinstance(quantity_value, bool)):
        return None

    name = name.strip()
    description = description.strip()
    deadline = parse_date(deadline_value)
    try:
        quantity = int(quantity_value)
        if isinstance(quantity_value, float) and not quantity_value.is_integer():
            return None
        normal_price = Decimal(str(data.get('normal_price')))
        reduced_price = Decimal(str(data.get('reduced_price')))
        if (normal_price != normal_price.quantize(Decimal('0.01'))
                or reduced_price != reduced_price.quantize(Decimal('0.01'))):
            return None
    except (TypeError, ValueError, InvalidOperation):
        return None

    max_price = Decimal('99999999.99')
    if (not name or len(name) > 100 or len(description) > 2000
            or not deadline or quantity < 1 or quantity > 2147483647
            or not normal_price.is_finite() or not reduced_price.is_finite()
            or normal_price < 0 or reduced_price < 0
            or normal_price > max_price or reduced_price > max_price
            or reduced_price > normal_price):
        return None
    return {
        'food_name': name,
        'description': description,
        'quantity_total': quantity,
        'normal_price': normal_price,
        'reduced_price': reduced_price,
        'deadline': deadline,
    }


ANNOUNCEMENT_SELECT = """
    SELECT a.id, a.organization_id, a.food_name, a.quantity_total,
           a.quantity_available, a.normal_price, a.reduced_price,
           a.deadline, a.description, a.created_at,
           o.name AS organization_name, o.organization_type,
           o.address AS organization_address,
           CASE WHEN a.quantity_available = 0 THEN 'sold_out'
                WHEN a.deadline < CURDATE() THEN 'expired'
                ELSE 'active' END AS status
    FROM announcements a
    JOIN organizations o ON o.id = a.organization_id
"""


def serialize_announcement(row):
    row['normal_price'] = format(row['normal_price'], '.2f')
    row['reduced_price'] = format(row['reduced_price'], '.2f')
    row['deadline'] = row['deadline'].isoformat()
    row['created_at'] = row['created_at'].isoformat()
    return row


def get_organization_id(cursor):
    cursor.execute("SELECT id FROM organizations WHERE user_id=%s", (current_user()['id'],))
    organization = cursor.fetchone()
    return organization['id'] if organization else None


# ---------- Pages et fichiers statiques ----------
@app.route('/')
def home():
    user = current_user()
    if user:
        return redirect('/' + destination_for(user))
    return redirect(url_for('account_type'))


@app.route('/account-type.html')
def account_type():
    user = current_user()
    if user:
        return redirect('/' + destination_for(user))
    return send_from_directory(BASE, 'account-type.html')


@app.route('/auth.html')
def auth_page():
    user = current_user()
    if user:
        return redirect('/' + destination_for(user))
    return send_from_directory(BASE, 'auth.html')


@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify(ok=True)


@app.route('/api/session')
def session_info():
    return jsonify(user=current_user())


@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error='Les informations du compte sont invalides.'), 400
    email = str(data.get('email', '')).strip().lower()
    password = data.get('password', '')
    role = data.get('role')
    if not isinstance(password, str) or not EMAIL_RE.fullmatch(email) or len(email) > 254:
        return jsonify(error='Veuillez saisir une adresse courriel valide.'), 400
    if len(password) < 8 or len(password) > 256:
        return jsonify(error='Le mot de passe doit contenir entre 8 et 256 caractères.'), 400
    if role not in ROLES:
        return jsonify(error='Le type de compte sélectionné est invalide.'), 400

    # Seuls les nouveaux comptes individuels doivent fournir un nom complet.
    org = None
    full_name = None
    if role == 'individual':
        name = data.get('full_name')
        if not isinstance(name, str) or not name.strip() or len(name.strip()) > 150:
            return jsonify(error='Veuillez saisir votre nom complet (150 caractères maximum).'), 400
        full_name = name.strip()

    if role == 'organization':
        name = data.get('name')
        organization_type = data.get('organization_type')
        address = data.get('address')
        phone = data.get('phone')
        if not all(isinstance(value, str) for value in (name, organization_type, address, phone)):
            return jsonify(error='Veuillez renseigner les informations valides de votre organisation.'), 400
        org = {
            'name': name.strip(),
            'type': organization_type,
            'address': address.strip(),
            'phone': phone.strip(),
        }
        if (not org['name'] or len(org['name']) > 150
                or org['type'] not in ORG_TYPES
                or not org['address'] or len(org['address']) > 255
                or not org['phone'] or len(org['phone']) > 30):
            return jsonify(error='Veuillez renseigner les informations valides de votre organisation.'), 400

    try:
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (email, full_name, password_hash, role) VALUES (%s, %s, %s, %s)",
                (email, full_name, generate_password_hash(password), role))
            user_id = cur.lastrowid
            if org:
                cur.execute(
                    "INSERT INTO organizations (user_id, name, organization_type, address, phone) "
                    "VALUES (%s, %s, %s, %s, %s)",
                    (user_id, org['name'], org['type'], org['address'], org['phone']))
            conn.commit()
    except pymysql.err.IntegrityError as error:
        if error.args and error.args[0] == 1062:
            return jsonify(error='Cette adresse courriel est déjà utilisée.'), 409
        raise

    session.clear()
    session.update(user_id=user_id, email=email, role=role)
    user = current_user()
    return jsonify(ok=True, redirect='/' + destination_for(user)), 201


@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error='Les informations de connexion sont invalides.'), 400
    email = str(data.get('email', '')).strip().lower()
    password = data.get('password', '')
    role = data.get('role')
    if not isinstance(password, str) or not email or len(email) > 254 or role not in ROLES:
        return jsonify(error='Adresse courriel ou mot de passe incorrect.'), 401

    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT id, email, password_hash, role FROM users WHERE email=%s", (email,))
        user = cur.fetchone()
    if (not user or user['role'] != role
            or not check_password_hash(user['password_hash'], password)):
        return jsonify(error='Adresse courriel ou mot de passe incorrect.'), 401

    session.clear()
    session.update(user_id=user['id'], email=user['email'], role=user['role'])
    return jsonify(ok=True, redirect='/' + destination_for(current_user()))


@app.route('/<path:filename>')
def files(filename):
    if filename.rsplit('.', 1)[-1].lower() not in ('html', 'css', 'js', 'png', 'jpg', 'svg', 'ico', 'webp'):
        return 'Introuvable', 404

    user = current_user()
    if filename == 'index.html':
        if not user:
            return redirect(url_for('account_type'))
        if user['role'] != 'individual':
            return redirect('/' + destination_for(user))

    page_roles = {
        'food.html': 'individual',
        'recipes.html': 'individual',
        'impact.html': 'individual',
        'offers.html': ('individual', 'organization'),
        'organization-dashboard.html': 'organization',
    }
    required_role = page_roles.get(filename)
    if required_role:
        if not user:
            return redirect(url_for('account_type'))
        allowed_roles = required_role if isinstance(required_role, tuple) else (required_role,)
        if user['role'] not in allowed_roles:
            return redirect('/' + destination_for(user))
    return send_from_directory(BASE, filename)


# ---------- API : aliments ----------
@app.route('/api/food', methods=['GET'])
@role_required('individual')
def get_food():
    with get_conn() as c, c.cursor() as cur:
        cur.execute("SELECT id_aliment, nom, quantite, date_peremption FROM aliment "
                    "WHERE user_id=%s AND statut='available' ORDER BY date_peremption, nom",
                    (current_user()['id'],))
        rows = cur.fetchall()
    for r in rows:
        r['date_peremption'] = r['date_peremption'].isoformat() if r['date_peremption'] else None
    return jsonify(rows)


@app.route('/api/food', methods=['POST'])
@role_required('individual')
def add_food():
    d = request.get_json(force=True, silent=True) or {}
    nom = str(d.get('nom', '')).strip()[:100]
    dt = parse_date(d.get('date_peremption'))
    try:
        qte = int(d.get('quantite', 0))
    except (TypeError, ValueError):
        qte = 0
    if not nom or qte < 1 or not dt:
        return jsonify(error='Veuillez renseigner un nom, une quantité (≥ 1) et une date valide.'), 400
    with get_conn() as c, c.cursor() as cur:
        cur.execute("INSERT INTO aliment (user_id, nom, quantite, date_peremption) VALUES (%s,%s,%s,%s)",
                    (current_user()['id'], nom, qte, dt))
        c.commit()
        new_id = cur.lastrowid
    return jsonify(ok=True, id=new_id), 201


@app.route('/api/food/<int:food_id>', methods=['PATCH'])
@role_required('individual')
def update_status(food_id):
    """Marque un aliment comme consommé ou jeté."""
    d = request.get_json(force=True, silent=True) or {}
    statut = d.get('statut')
    if statut not in ('consumed', 'wasted'):
        return jsonify(error='Statut invalide'), 400
    today = parse_date(d.get('today'), date.today())
    with get_conn() as c, c.cursor() as cur:
        cur.execute("UPDATE aliment SET statut=%s, date_statut=%s "
                    "WHERE id_aliment=%s AND user_id=%s AND statut='available'",
                    (statut, today, food_id, current_user()['id']))
        c.commit()
    return jsonify(ok=True)


@app.route('/api/food/<int:food_id>', methods=['DELETE'])
@role_required('individual')
def delete_food(food_id):
    with get_conn() as c, c.cursor() as cur:
        cur.execute("DELETE FROM aliment WHERE id_aliment=%s AND user_id=%s",
                    (food_id, current_user()['id']))
        c.commit()
    return jsonify(ok=True)


# ---------- API : annonces et réservations ----------
@app.route('/api/organization/announcements', methods=['GET'])
@role_required('organization')
def organization_announcements():
    with get_conn() as conn, conn.cursor() as cur:
        organization_id = get_organization_id(cur)
        if not organization_id:
            return jsonify(error='Profil organisation introuvable.'), 403
        cur.execute(ANNOUNCEMENT_SELECT + " WHERE a.organization_id=%s ORDER BY a.created_at DESC",
                    (organization_id,))
        rows = cur.fetchall()
        # Le filtre par organisation empêche de révéler les réservations d'autrui.
        cur.execute("""
            SELECT r.announcement_id,
                   COALESCE(NULLIF(u.full_name, ''), u.email) AS reserver_name,
                   r.quantity, r.created_at
            FROM reservations r
            JOIN announcements a ON a.id=r.announcement_id
            JOIN users u ON u.id=r.user_id
            WHERE a.organization_id=%s
            ORDER BY r.created_at DESC
        """, (organization_id,))
        reservations = cur.fetchall()
    reservations_by_announcement = {}
    for reservation in reservations:
        reservation['created_at'] = reservation['created_at'].isoformat()
        reservations_by_announcement.setdefault(reservation['announcement_id'], []).append({
            'reserver_name': reservation['reserver_name'],
            'quantity': reservation['quantity'],
            'created_at': reservation['created_at'],
        })
    for row in rows:
        row['reservations'] = reservations_by_announcement.get(row['id'], [])
    return jsonify([serialize_announcement(row) for row in rows])


@app.route('/api/organization/announcements', methods=['POST'])
@role_required('organization')
def create_announcement():
    data = announcement_input(request.get_json(silent=True))
    if not data:
        return jsonify(error='Vérifiez les champs de l’annonce et le prix réduit.'), 400
    if data['deadline'] < date.today():
        return jsonify(error='La date limite doit être aujourd’hui ou ultérieure.'), 400
    with get_conn() as conn, conn.cursor() as cur:
        organization_id = get_organization_id(cur)
        if not organization_id:
            return jsonify(error='Profil organisation introuvable.'), 403
        cur.execute(
            "INSERT INTO announcements "
            "(organization_id, food_name, quantity_total, quantity_available, normal_price, "
            "reduced_price, deadline, description) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
            (organization_id, data['food_name'], data['quantity_total'], data['quantity_total'],
             data['normal_price'], data['reduced_price'], data['deadline'], data['description']))
        conn.commit()
        announcement_id = cur.lastrowid
    return jsonify(ok=True, id=announcement_id), 201


@app.route('/api/organization/announcements/<int:announcement_id>', methods=['PUT'])
@role_required('organization')
def update_announcement(announcement_id):
    data = announcement_input(request.get_json(silent=True))
    if not data:
        return jsonify(error='Vérifiez les champs de l’annonce et le prix réduit.'), 400
    with get_conn() as conn, conn.cursor() as cur:
        organization_id = get_organization_id(cur)
        if not organization_id:
            return jsonify(error='Profil organisation introuvable.'), 403
        cur.execute(
            "SELECT quantity_total, quantity_available FROM announcements "
            "WHERE id=%s AND organization_id=%s FOR UPDATE",
            (announcement_id, organization_id))
        existing = cur.fetchone()
        if not existing:
            return jsonify(error='Annonce introuvable.'), 404
        already_reserved = existing['quantity_total'] - existing['quantity_available']
        if data['quantity_total'] < already_reserved:
            return jsonify(error='La quantité ne peut pas être inférieure aux réservations déjà faites.'), 400
        available = data['quantity_total'] - already_reserved
        cur.execute(
            "UPDATE announcements SET food_name=%s, quantity_total=%s, quantity_available=%s, "
            "normal_price=%s, reduced_price=%s, deadline=%s, description=%s "
            "WHERE id=%s AND organization_id=%s",
            (data['food_name'], data['quantity_total'], available, data['normal_price'],
             data['reduced_price'], data['deadline'], data['description'],
             announcement_id, organization_id))
        conn.commit()
    return jsonify(ok=True)


@app.route('/api/organization/announcements/<int:announcement_id>', methods=['DELETE'])
@role_required('organization')
def delete_announcement(announcement_id):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "DELETE a FROM announcements a JOIN organizations o ON o.id=a.organization_id "
            "WHERE a.id=%s AND o.user_id=%s",
            (announcement_id, current_user()['id']))
        deleted = cur.rowcount
        conn.commit()
    if not deleted:
        return jsonify(error='Annonce introuvable.'), 404
    return jsonify(ok=True)


@app.route('/api/announcements', methods=['GET'])
@login_required
def available_announcements():
    search = request.args.get('q', '').strip()[:100]
    organization_type = request.args.get('organization_type', '')
    status = request.args.get('status', 'active')
    if organization_type and organization_type not in ORG_TYPES:
        return jsonify(error='Type d’organisation invalide.'), 400
    if status not in ('active', 'sold_out', 'expired', 'all'):
        return jsonify(error='Filtre de statut invalide.'), 400
    organization_filter = ''
    params = [search, '%' + search + '%', organization_type, organization_type]
    if current_user()['role'] == 'organization':
        # Les particuliers voient toutes les offres, une organisation exclut les siennes.
        with get_conn() as conn, conn.cursor() as cur:
            organization_id = get_organization_id(cur)
        if not organization_id:
            return jsonify(error='Profil organisation introuvable.'), 403
        organization_filter = "AND a.organization_id <> %s"
        params.append(organization_id)
    query = ANNOUNCEMENT_SELECT + """
        WHERE (%s='' OR a.food_name LIKE %s)
          AND (%s='' OR o.organization_type=%s)
          """ + organization_filter + """
          AND (%s='all' OR
               (CASE WHEN a.quantity_available = 0 THEN 'sold_out'
                     WHEN a.deadline < CURDATE() THEN 'expired'
                     ELSE 'active' END)=%s)
        ORDER BY (a.deadline < CURDATE()), a.deadline, a.reduced_price, a.created_at DESC
    """
    params.extend([status, status])
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(query, params)
        rows = cur.fetchall()
    return jsonify([serialize_announcement(row) for row in rows])


@app.route('/api/announcements/<int:announcement_id>/reservations', methods=['POST'])
@role_required('individual')
def reserve_announcement(announcement_id):
    data = request.get_json(silent=True)
    quantity_value = data.get('quantity') if isinstance(data, dict) else None
    if isinstance(quantity_value, bool):
        return jsonify(error='La quantité réservée doit être un nombre positif.'), 400
    try:
        quantity = int(quantity_value)
        if isinstance(quantity_value, float) and not quantity_value.is_integer():
            raise ValueError
    except (TypeError, ValueError):
        return jsonify(error='La quantité réservée doit être un nombre positif.'), 400
    if quantity < 1 or quantity > 2147483647:
        return jsonify(error='La quantité réservée doit être un nombre positif.'), 400

    with get_conn() as conn, conn.cursor() as cur:
        # Le verrou garantit que deux réservations simultanées ne dépassent pas le stock.
        cur.execute(
            "SELECT quantity_available, deadline < CURDATE() AS expired "
            "FROM announcements WHERE id=%s FOR UPDATE",
            (announcement_id,))
        announcement = cur.fetchone()
        if not announcement:
            return jsonify(error='Annonce introuvable.'), 404
        if announcement['quantity_available'] == 0:
            return jsonify(error='Cette annonce est épuisée.'), 409
        if announcement['expired']:
            return jsonify(error='Cette annonce a expiré.'), 409
        if quantity > announcement['quantity_available']:
            return jsonify(error='La quantité demandée n’est plus disponible.'), 409

        cur.execute(
            "UPDATE announcements SET quantity_available=quantity_available-%s WHERE id=%s",
            (quantity, announcement_id))
        cur.execute(
            "INSERT INTO reservations (announcement_id, user_id, quantity) VALUES (%s,%s,%s)",
            (announcement_id, current_user()['id'], quantity))
        conn.commit()
        available = announcement['quantity_available'] - quantity
    return jsonify(ok=True, quantity_available=available), 201


# ---------- API : recettes ----------
@app.route('/api/recipes', methods=['GET'])
@role_required('individual')
def get_recipes():
    today = date.today()
    urgent_until = today + timedelta(days=3)
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT id, name, description FROM recipes ORDER BY id")
        recipes = cur.fetchall()
        cur.execute("SELECT recipe_id, ingredient_name FROM recipe_ingredients ORDER BY id")
        ingredients = cur.fetchall()
        cur.execute(
            "SELECT nom, date_peremption FROM aliment "
            "WHERE user_id=%s AND statut='available'",
            (current_user()['id'],))
        foods = cur.fetchall()

    ingredients_by_recipe = {}
    for row in ingredients:
        ingredients_by_recipe.setdefault(row['recipe_id'], []).append(row['ingredient_name'])
    foods_by_name = {}
    for food in foods:
        foods_by_name.setdefault(norm(food['nom']), []).append(food['date_peremption'])

    suggestions = []
    for recipe in recipes:
        recipe_ingredients = ingredients_by_recipe.get(recipe['id'], [])
        have, missing, urgent, urgent_dates = [], [], [], []
        for ingredient in recipe_ingredients:
            dates = foods_by_name.get(norm(ingredient), [])
            if not dates:
                missing.append(ingredient)
                continue
            have.append(ingredient)
            ingredient_dates = [expiry for expiry in dates if expiry]
            expiring_soon = [expiry for expiry in ingredient_dates if today <= expiry <= urgent_until]
            if expiring_soon:
                urgent.append(ingredient)
                urgent_dates.extend(expiring_soon)

        percentage = round(len(have) / len(recipe_ingredients) * 100) if recipe_ingredients else 0
        soonest_expiry = min(urgent_dates) if urgent_dates else None
        suggestions.append({
            'id_recette': recipe['id'],
            'nom': recipe['name'],
            'description': recipe['description'],
            'ingredients': recipe_ingredients,
            'have': have,
            'missing': missing,
            'percentage': percentage,
            'urgent': urgent,
            'soonest_expiry': soonest_expiry.isoformat() if soonest_expiry else None,
            'feasible': bool(recipe_ingredients) and not missing,
        })

    suggestions.sort(key=lambda recipe: (
        -(len(recipe['have']) / len(recipe['ingredients']) if recipe['ingredients'] else 0),
        -len(recipe['urgent']),
        recipe['soonest_expiry'] or '9999-12-31',
        recipe['nom'].casefold(),
    ))
    return jsonify(suggestions)


# ---------- API : impact ----------
@app.route('/api/impact', methods=['GET'])
@role_required('individual')
def impact():
    today = parse_date(request.args.get('today'), date.today())
    with get_conn() as c, c.cursor() as cur:
        cur.execute("SELECT statut, date_peremption, date_statut FROM aliment WHERE user_id=%s",
                    (current_user()['id'],))
        rows = cur.fetchall()

    consumed = [r for r in rows if r['statut'] == 'consumed']
    wasted = [r for r in rows if r['statut'] == 'wasted']
    available = [r for r in rows if r['statut'] == 'available']
    # « Sauvé » = consommé au plus tard à sa date de péremption
    saved = [r for r in consumed
             if r['date_statut'] and r['date_peremption'] and r['date_statut'] <= r['date_peremption']]
    soon = [r for r in available if r['date_peremption'] and r['date_peremption'] <= today + timedelta(days=3)]
    closed = len(consumed) + len(wasted)

    # 6 dernières semaines (lundi → dimanche)
    monday = today - timedelta(days=today.weekday())
    weeks = []
    for k in range(5, -1, -1):
        start = monday - timedelta(weeks=k)
        end = start + timedelta(days=6)
        weeks.append({
            'debut': start.isoformat(),
            'consommes': sum(1 for r in consumed if r['date_statut'] and start <= r['date_statut'] <= end),
            'gaspilles': sum(1 for r in wasted if r['date_statut'] and start <= r['date_statut'] <= end),
        })

    return jsonify(
        total=len(rows), disponibles=len(available), consommes=len(consumed),
        gaspilles=len(wasted), sauves=len(saved), a_surveiller=len(soon),
        taux=round(len(saved) / closed * 100) if closed else None,
        semaines=weeks)


if __name__ == '__main__':
    ensure_schema()
    app.run(host='0.0.0.0', port=5000, debug=os.getenv('FLASK_DEBUG', '1') == '1')
