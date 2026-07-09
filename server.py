import os
import random
import string
import json
import html
import hmac
import hashlib
import re
from datetime import datetime
from http import cookies
from http.server import HTTPServer, SimpleHTTPRequestHandler
from string import Template
from urllib.parse import parse_qs, urlparse, quote, unquote

try:
    import psycopg
except ImportError:  # pragma: no cover - depends on environment
    psycopg = None

DATA_DIR = os.path.dirname(__file__)
TEMPLATE_DIR = os.path.join(DATA_DIR, 'templates')
ADMIN_DIR = os.path.join(DATA_DIR, 'admin')
ADMIN_TEMPLATE_DIR = os.path.join(ADMIN_DIR, 'templates')
ADMIN_DATA_DIR = os.path.join(ADMIN_DIR, 'data')
DATA_STORE = os.path.join(DATA_DIR, 'data')
USERS_FILE = os.path.join(DATA_STORE, 'users.json')
ORDERS_FILE = os.path.join(DATA_STORE, 'orders.json')
REVIEWS_FILE = os.path.join(DATA_STORE, 'reviews.json')
LEGACY_SUBSCRIBERS_FILE = os.path.join(DATA_STORE, 'subscribers.json')
SUBSCRIBERS_FILE = os.path.join(ADMIN_DATA_DIR, 'subscribers.json')
ADMIN_AUTH_FILE = os.path.join(ADMIN_DATA_DIR, 'auth.json')
CATEGORIES_FILE = os.path.join(ADMIN_DATA_DIR, 'categories.json')
CATEGORY_IMAGE_DIR = os.path.join(DATA_DIR, 'assets', 'category-images')
DATABASE_URL = os.environ.get('DATABASE_URL') or os.environ.get('POSTGRES_URL') or 'postgresql://postgres:postgres@localhost:5432/vithi'
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')
ADMIN_PASSWORD_HASH = os.environ.get('ADMIN_PASSWORD_HASH', '').strip()

sessions = {}
admin_sessions = {}
admin_login_csrf = {}
carts = {}
wishlist = {}
users = {}
orders = []
reviews = []
subscribers = []
categories = []
admin_auth = {'username': ADMIN_USERNAME, 'password_hash': ''}
db_connection = None
db_ready = False


def ensure_data_dir():
    try:
        os.makedirs(DATA_STORE, exist_ok=True)
        os.makedirs(ADMIN_DATA_DIR, exist_ok=True)
        os.makedirs(ADMIN_TEMPLATE_DIR, exist_ok=True)
        os.makedirs(CATEGORY_IMAGE_DIR, exist_ok=True)
    except Exception:
        pass


def make_password_hash(password, salt=None, iterations=260000):
    if salt is None:
        salt = os.urandom(16).hex()
    digest = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), iterations).hex()
    return f'pbkdf2_sha256${iterations}${salt}${digest}'


def verify_password_hash(password, encoded):
    try:
        algorithm, iteration_text, salt, expected = encoded.split('$', 3)
        if algorithm != 'pbkdf2_sha256':
            return False
        iterations = int(iteration_text)
    except ValueError:
        return False
    actual = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), iterations).hex()
    return hmac.compare_digest(actual, expected)


def is_password_hash(value):
    return str(value).startswith('pbkdf2_sha256$')


def verify_user_password(password, stored_value):
    stored_text = str(stored_value or '')
    if is_password_hash(stored_text):
        return verify_password_hash(password, stored_text)
    return hmac.compare_digest(password, stored_text)


def initialize_admin_auth():
    global admin_auth
    ensure_data_dir()

    if ADMIN_PASSWORD_HASH:
        admin_auth = {'username': ADMIN_USERNAME, 'password_hash': ADMIN_PASSWORD_HASH}
        return

    existing = load_json_file(ADMIN_AUTH_FILE, {})
    username = str(existing.get('username', ADMIN_USERNAME)).strip() or ADMIN_USERNAME
    stored_hash = str(existing.get('password_hash', '')).strip()

    if not stored_hash:
        stored_hash = make_password_hash(ADMIN_PASSWORD)
        save_json_file(ADMIN_AUTH_FILE, {'username': username, 'password_hash': stored_hash})

    admin_auth = {'username': username, 'password_hash': stored_hash}


def load_json_file(path, default):
    try:
        with open(path, 'r', encoding='utf-8') as fh:
            return json.load(fh)
    except Exception:
        return default


def save_json_file(path, data):
    try:
        with open(path, 'w', encoding='utf-8') as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
    except Exception:
        pass


def connect_to_postgres():
    global db_connection, db_ready
    if psycopg is None:
        return None
    if db_connection is not None:
        return db_connection
    try:
        db_connection = psycopg.connect(DATABASE_URL, autocommit=True)
        db_ready = True
        return db_connection
    except Exception as exc:  # pragma: no cover - environment-specific
        db_ready = False
        print(f'PostgreSQL unavailable, using JSON fallback: {exc}')
        return None


def initialize_persistence():
    global users, orders, reviews, subscribers, db_ready
    ensure_data_dir()
    legacy_users = load_json_file(USERS_FILE, {})
    legacy_orders = load_json_file(ORDERS_FILE, [])
    legacy_reviews = load_json_file(REVIEWS_FILE, [])
    legacy_subscribers = load_json_file(LEGACY_SUBSCRIBERS_FILE, [])
    current_subscribers = load_json_file(SUBSCRIBERS_FILE, [])
    if isinstance(current_subscribers, list) and current_subscribers:
        legacy_subscribers = current_subscribers

    connection = connect_to_postgres()
    if connection is None:
        users = legacy_users
        orders = legacy_orders
        reviews = legacy_reviews
        subscribers = legacy_subscribers
        save_json_file(REVIEWS_FILE, reviews)
        save_json_file(SUBSCRIBERS_FILE, subscribers)
        db_ready = False
        return False

    with connection.cursor() as cursor:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                email TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                phone TEXT,
                address TEXT,
                password TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id BIGSERIAL PRIMARY KEY,
                product_name TEXT NOT NULL,
                total TEXT NOT NULL,
                user_email TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS subscriptions (
                id BIGSERIAL PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS product_reviews (
                id BIGSERIAL PRIMARY KEY,
                product_id BIGINT NOT NULL,
                user_email TEXT NOT NULL,
                user_name TEXT NOT NULL,
                rating INTEGER NOT NULL,
                comment TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT NOW(),
                UNIQUE (product_id, user_email)
            )
        ''')
        cursor.execute('ALTER TABLE users ADD COLUMN IF NOT EXISTS address TEXT')
        cursor.execute('ALTER TABLE orders ADD COLUMN IF NOT EXISTS user_email TEXT')

    users = load_users_from_db()
    if not users and legacy_users:
        for user in legacy_users.values():
            save_user_to_db(user)
        users = load_users_from_db()

    orders = load_orders_from_db()
    if not orders and legacy_orders:
        for order in legacy_orders:
            save_order_to_db(order)
        orders = load_orders_from_db()

    reviews = load_reviews_from_db()
    if not reviews and legacy_reviews:
        for review in legacy_reviews:
            if isinstance(review, dict):
                save_review_to_db(review)
        reviews = load_reviews_from_db()

    subscribers = load_subscriptions_from_db()
    if not subscribers and legacy_subscribers:
        for entry in legacy_subscribers:
            if isinstance(entry, dict):
                email = entry.get('email', '').strip().lower()
            else:
                email = str(entry).strip().lower()
            if email:
                save_subscription_to_db(email)
        subscribers = load_subscriptions_from_db()

    return True


def load_users_from_db():
    connection = connect_to_postgres()
    if connection is None:
        return {}
    with connection.cursor() as cursor:
        cursor.execute('SELECT name, email, phone, address, password FROM users ORDER BY created_at')
        rows = cursor.fetchall()
    return {
        row[1]: {
            'name': row[0],
            'email': row[1],
            'phone': row[2],
            'address': row[3] or '',
            'password': row[4]
        }
        for row in rows
    }


def load_orders_from_db():
    connection = connect_to_postgres()
    if connection is None:
        return []
    with connection.cursor() as cursor:
        cursor.execute('SELECT product_name, total, user_email, created_at FROM orders ORDER BY id')
        rows = cursor.fetchall()
    return [{'productName': row[0], 'total': row[1], 'userEmail': row[2] or '', 'createdAt': row[3]} for row in rows]


def save_user_to_db(user_record):
    connection = connect_to_postgres()
    if connection is None:
        return False
    with connection.cursor() as cursor:
        cursor.execute(
            '''
            INSERT INTO users (email, name, phone, address, password)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (email) DO UPDATE SET
                name = EXCLUDED.name,
                phone = EXCLUDED.phone,
                address = EXCLUDED.address,
                password = EXCLUDED.password
            ''',
            (
                user_record['email'],
                user_record['name'],
                user_record.get('phone', ''),
                user_record.get('address', ''),
                user_record['password']
            )
        )
    return True


def save_order_to_db(order_record):
    connection = connect_to_postgres()
    if connection is None:
        return False
    with connection.cursor() as cursor:
        cursor.execute(
            'INSERT INTO orders (product_name, total, user_email, created_at) VALUES (%s, %s, %s, %s)',
            (
                order_record['productName'],
                order_record['total'],
                order_record.get('userEmail', ''),
                order_record.get('createdAt')
            )
        )
    return True


def load_reviews_from_db():
    connection = connect_to_postgres()
    if connection is None:
        return []
    with connection.cursor() as cursor:
        cursor.execute(
            'SELECT product_id, user_email, user_name, rating, comment, created_at FROM product_reviews ORDER BY created_at DESC, id DESC'
        )
        rows = cursor.fetchall()
    return [
        {
            'productId': int(row[0]),
            'userEmail': row[1],
            'userName': row[2],
            'rating': int(row[3]),
            'comment': row[4],
            'createdAt': row[5]
        }
        for row in rows
    ]


def save_review_to_db(review_record):
    connection = connect_to_postgres()
    if connection is None:
        return False
    with connection.cursor() as cursor:
        cursor.execute(
            '''
            INSERT INTO product_reviews (product_id, user_email, user_name, rating, comment, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (product_id, user_email) DO UPDATE SET
                user_name = EXCLUDED.user_name,
                rating = EXCLUDED.rating,
                comment = EXCLUDED.comment,
                created_at = EXCLUDED.created_at
            ''',
            (
                review_record['productId'],
                review_record['userEmail'],
                review_record['userName'],
                review_record['rating'],
                review_record['comment'],
                review_record.get('createdAt')
            )
        )
    return True


def has_user_reviewed(product_id, user_email):
    for review in reviews:
        if str(review.get('productId')) == str(product_id) and review.get('userEmail', '').lower() == user_email.lower():
            return True
    return False


def update_user_address_in_db(email, address):
    connection = connect_to_postgres()
    if connection is None:
        return False
    with connection.cursor() as cursor:
        cursor.execute('UPDATE users SET address=%s WHERE email=%s', (address, email))
    return True


def load_subscriptions_from_db():
    connection = connect_to_postgres()
    if connection is None:
        return []
    with connection.cursor() as cursor:
        cursor.execute('SELECT email, created_at FROM subscriptions ORDER BY created_at DESC')
        rows = cursor.fetchall()
    return [{'email': row[0], 'createdAt': row[1]} for row in rows]


def save_subscription_to_db(email):
    connection = connect_to_postgres()
    if connection is None:
        return False
    with connection.cursor() as cursor:
        cursor.execute(
            '''
            INSERT INTO subscriptions (email)
            VALUES (%s)
            ON CONFLICT (email) DO UPDATE SET
                created_at = NOW()
            ''',
            (email,)
        )
    return True


def save_subscription_local(email):
    normalized = email.strip().lower()
    if not normalized:
        return False
    for entry in subscribers:
        if entry.get('email', '').lower() == normalized:
            return True
    subscribers.append({'email': normalized, 'createdAt': datetime.now().isoformat(timespec='seconds')})
    save_json_file(SUBSCRIBERS_FILE, subscribers)
    return True


def is_valid_email(value):
    value = value.strip()
    if '@' not in value:
        return False
    local, _, domain = value.partition('@')
    return bool(local and domain and '.' in domain)


initialize_persistence()
initialize_admin_auth()

products = [
    {
        'id': 1,
        'categoryId': 1,
        'name': 'Organic Turmeric Powder',
        'price': 249,
        'weightKg': 1.0,
        'description': 'Pure, earthy spice with antioxidant-rich wellness benefits.',
        'image': 'https://images.unsplash.com/photo-1506126613408-eca07ce68773?auto=format&fit=crop&w=900&q=80'
    },
    {
        'id': 2,
        'categoryId': 2,
        'name': 'Botanical Face Serum',
        'price': 599,
        'weightKg': 1.0,
        'description': 'Lightweight nourishment for calm, glowing, healthy skin.',
        'image': 'https://images.unsplash.com/photo-1501004318641-b39e6451bec6?auto=format&fit=crop&w=900&q=80'
    },
    {
        'id': 3,
        'categoryId': 3,
        'name': 'Wildflower Organic Honey',
        'price': 399,
        'weightKg': 1.0,
        'description': 'Pure sweetness with floral richness and natural goodness.',
        'image': 'https://images.unsplash.com/photo-1490645935967-10de6ba17061?auto=format&fit=crop&w=900&q=80'
    }
]


def slugify(value):
    slug = re.sub(r'[^a-zA-Z0-9]+', '-', value.strip().lower()).strip('-')
    return slug or 'category'


def initialize_categories():
    global categories
    ensure_data_dir()
    stored = load_json_file(CATEGORIES_FILE, [])
    if isinstance(stored, list) and stored:
        categories = stored
        return

    now = datetime.now().isoformat(timespec='seconds')
    default_admin = admin_auth.get('username', ADMIN_USERNAME)
    categories = [
        {
            'id': 1,
            'name': 'Organic Spices',
            'descriptionHtml': '<p>Pure and traditional spice blends for daily wellness.</p>',
            'displayOrder': 1,
            'imagePath': '/assets/category-images/organic-spices.png',
            'createdAt': now,
            'modifiedAt': now,
            'createdBy': default_admin,
            'modifiedBy': default_admin,
            'status': 'online',
            'seoSlug': 'organic-spices',
            'metaTitle': 'Organic Spices',
            'metaDescription': 'Discover naturally sourced organic spices for healthy cooking.',
            'metaKeywords': 'organic spices, turmeric, natural masala',
            'canonicalUrl': ''
        },
        {
            'id': 2,
            'name': 'Natural Skin Care',
            'descriptionHtml': '<p>Botanical care products for clean and radiant skin.</p>',
            'displayOrder': 2,
            'imagePath': '/assets/category-images/natural-skin-care.png',
            'createdAt': now,
            'modifiedAt': now,
            'createdBy': default_admin,
            'modifiedBy': default_admin,
            'status': 'online',
            'seoSlug': 'natural-skin-care',
            'metaTitle': 'Natural Skin Care',
            'metaDescription': 'Explore botanical skin care made from natural ingredients.',
            'metaKeywords': 'skin care, botanical serum, natural beauty',
            'canonicalUrl': ''
        },
        {
            'id': 3,
            'name': 'Organic Sweeteners',
            'descriptionHtml': '<p>Healthy sweet alternatives with authentic taste.</p>',
            'displayOrder': 3,
            'imagePath': '/assets/category-images/organic-sweeteners.png',
            'createdAt': now,
            'modifiedAt': now,
            'createdBy': default_admin,
            'modifiedBy': default_admin,
            'status': 'online',
            'seoSlug': 'organic-sweeteners',
            'metaTitle': 'Organic Sweeteners',
            'metaDescription': 'Choose healthier natural sweeteners for your family.',
            'metaKeywords': 'organic honey, sweetener, healthy sugar alternative',
            'canonicalUrl': ''
        }
    ]
    save_json_file(CATEGORIES_FILE, categories)


def next_category_id():
    if not categories:
        return 1
    return max(int(item.get('id', 0)) for item in categories) + 1


def get_category_by_id(category_id):
    for category in categories:
        if str(category.get('id')) == str(category_id):
            return category
    return None


def has_products_for_category(category_id):
    for product in products:
        if str(product.get('categoryId')) == str(category_id):
            return True
    return False


initialize_categories()


def load_template(name):
    path = os.path.join(TEMPLATE_DIR, name)
    with open(path, 'r', encoding='utf-8') as handle:
        return handle.read()


def load_admin_template(name):
    path = os.path.join(ADMIN_TEMPLATE_DIR, name)
    with open(path, 'r', encoding='utf-8') as handle:
        return handle.read()


def make_template(name, **context):
    context.setdefault('meta_description', 'Vithi Organics offers trusted organic essentials for healthy living.')
    context.setdefault('meta_keywords', 'organic, wellness, natural, healthy')
    context.setdefault('meta_robots', 'index,follow')
    context.setdefault('canonical_url', '')
    context.setdefault('search_action', '/')
    context.setdefault('search_query', '')
    body = Template(load_template(name)).substitute(**context)
    header = Template(load_template('partials/header.html')).substitute(**context)
    footer = Template(load_template('partials/footer.html')).substitute(**context)
    return Template(load_template('base.html')).substitute(
        title=context.get('title', 'Vithi Organics'),
        meta_description=context.get('meta_description', ''),
        meta_keywords=context.get('meta_keywords', ''),
        meta_robots=context.get('meta_robots', 'index,follow'),
        canonical_url=context.get('canonical_url', ''),
        header=header,
        content=body,
        footer=footer,
    )


def get_user_from_cookie(cookie_header):
    if not cookie_header:
        return None
    cookie = cookies.SimpleCookie()
    cookie.load(cookie_header)
    session_id = cookie.get('vithi_session')
    if not session_id:
        return None
    user_email = sessions.get(session_id.value)
    return users.get(user_email)


def get_admin_from_cookie(cookie_header):
    if not cookie_header:
        return None
    cookie = cookies.SimpleCookie()
    cookie.load(cookie_header)
    session_id = cookie.get('vithi_admin_session')
    if not session_id:
        return None
    return admin_sessions.get(session_id.value)


def get_cookie_value(cookie_header, key):
    if not cookie_header:
        return ''
    cookie = cookies.SimpleCookie()
    cookie.load(cookie_header)
    entry = cookie.get(key)
    return entry.value if entry else ''


def generate_session_id():
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(32))


def generate_captcha_challenge():
    left = random.randint(1, 9)
    right = random.randint(1, 9)
    return f'What is {left} + {right}?', str(left + right)


def generate_image_captcha():
    allowed = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
    token = ''.join(random.choice(allowed) for _ in range(5))
    lines = []
    for _ in range(4):
        x1 = random.randint(0, 220)
        y1 = random.randint(8, 64)
        x2 = random.randint(0, 220)
        y2 = random.randint(8, 64)
        stroke = random.choice(['#3d7a42', '#7b5b3a', '#c7a24b', '#566a7f'])
        lines.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" stroke-width="2" opacity="0.6" />')
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="260" height="80" viewBox="0 0 260 80">'
        '<rect width="260" height="80" rx="12" fill="#f7f2e8" />'
        f'{"".join(lines)}'
        '<g font-family="Arial, Helvetica, sans-serif" font-size="30" font-weight="700" letter-spacing="5">'
    )
    start_x = 28
    for index, char in enumerate(token):
        rotate = random.randint(-18, 18)
        y = random.randint(42, 55)
        fill = random.choice(['#204b2b', '#7b5b3a', '#0b2a16'])
        svg += f'<text x="{start_x + index * 42}" y="{y}" transform="rotate({rotate} {start_x + index * 42} {y})" fill="{fill}">{char}</text>'
    svg += '</g></svg>'
    return 'data:image/svg+xml;charset=UTF-8,' + quote(svg), token


def parse_post_form(handler):
    content_type = handler.headers.get('Content-Type', '')
    length = int(handler.headers.get('Content-Length', 0))
    raw_body = handler.rfile.read(length)

    if not content_type.startswith('multipart/form-data'):
        return parse_qs(raw_body.decode('utf-8')), {}

    boundary_match = re.search(r'boundary=([^;]+)', content_type)
    if not boundary_match:
        return {}, {}
    boundary = boundary_match.group(1).strip().strip('"').encode('utf-8')

    data = {}
    files = {}
    marker = b'--' + boundary
    for part in raw_body.split(marker):
        part = part.strip()
        if not part or part == b'--':
            continue

        head, sep, content = part.partition(b'\r\n\r\n')
        if not sep:
            continue

        content = content.rstrip(b'\r\n')
        headers = head.decode('utf-8', errors='ignore').split('\r\n')
        disposition = ''
        for header_line in headers:
            if header_line.lower().startswith('content-disposition:'):
                disposition = header_line
                break
        if not disposition:
            continue

        name_match = re.search(r'name="([^"]+)"', disposition)
        if not name_match:
            continue
        field_name = name_match.group(1)

        filename_match = re.search(r'filename="([^"]*)"', disposition)
        if filename_match:
            files[field_name] = {
                'filename': filename_match.group(1),
                'content': content,
            }
        else:
            data[field_name] = [content.decode('utf-8', errors='ignore')]

    return data, files


def get_template_user_context(user):
    if user:
        return {
            'user_name': user['name'].split()[0],
            'login_label': 'My Home',
            'login_href': '/user/home',
            'auth_secondary': '<a href="/logout" class="icon-link">Logout</a>'
        }
    return {
        'user_name': '',
        'login_label': 'Login',
        'login_href': '/login',
        'auth_secondary': ''
    }


def get_cart_items(cookie_header):
    cart_session_id = get_cookie_value(cookie_header, 'vithi_cart_session')
    if not cart_session_id:
        return {}
    return carts.get(cart_session_id, {})


def get_wishlist_items(cookie_header):
    wishlist_session_id = get_cookie_value(cookie_header, 'vithi_wishlist_session')
    if not wishlist_session_id:
        return {}
    return wishlist.get(wishlist_session_id, {})


def get_online_categories():
    visible = [item for item in categories if item.get('status', 'online') == 'online']
    return sorted(visible, key=lambda item: int(item.get('displayOrder', 999999)))


def get_category_by_slug(slug):
    normalized = slug.strip().lower()
    for category in categories:
        if category.get('seoSlug', '').strip().lower() == normalized:
            return category
    return None


def get_products_for_category(category_id):
    return [item for item in products if str(item.get('categoryId')) == str(category_id)]


def pick_category_image(category, category_products):
    image_path = str(category.get('imagePath', '')).strip()
    if image_path.startswith('/'):
        disk_path = os.path.join(DATA_DIR, image_path.lstrip('/'))
        if os.path.exists(disk_path):
            return image_path
    elif image_path:
        return image_path

    if category_products:
        return str(category_products[0].get('image', ''))
    return 'https://images.unsplash.com/photo-1512621776951-a57141f2eefd?auto=format&fit=crop&w=900&q=80'


def build_product_card(product):
    weight_label = f'{float(product.get("weightKg", 1.0)):.2f} kg'
    return (
        f'<article class="card product-card">'
        f'<a class="product-link" href="/products/{product["id"]}"><img src="{product["image"]}" alt="{product["name"]}" /></a>'
        f'<div class="card-body">'
        f'<h3><a href="/products/{product["id"]}">{product["name"]}</a></h3>'
        f'<p>{product["description"]}</p>'
        f'<span class="card-meta">Weight: {weight_label}</span>'
        f'<div class="price-row"><strong>₹{product["price"]}</strong><div class="actions">'
        f'<form method="post" action="/cart/add" style="display:inline;">'
        f'<input type="hidden" name="productId" value="{product["id"]}" />'
        f'<button class="btn btn-primary" type="submit">Add to Cart</button>'
        f'</form>'
        f'<form method="post" action="/wishlist/add" style="display:inline;">'
        f'<input type="hidden" name="productId" value="{product["id"]}" />'
        f'<button class="btn product-wishlist-btn wishlist-icon-btn" type="submit" aria-label="Add to wishlist" title="Add to wishlist">&#9829;</button>'
        f'</form></div></div>'
        f'</div></article>'
    )


def get_recently_viewed_ids(cookie_header):
    raw = get_cookie_value(cookie_header, 'vithi_recently_viewed')
    if not raw:
        return []
    known_ids = {str(item.get('id')) for item in products}
    unique_ids = []
    for token in raw.split(','):
        item_id = token.strip()
        if item_id and item_id in known_ids and item_id not in unique_ids:
            unique_ids.append(item_id)
    return unique_ids[:8]


def build_recently_viewed_cookie(cookie_header, product_id):
    seen = get_recently_viewed_ids(cookie_header)
    pid = str(product_id)
    seen = [item for item in seen if item != pid]
    seen.insert(0, pid)
    return ','.join(seen[:8])


def render_recently_viewed_block(cookie_header):
    viewed_ids = get_recently_viewed_ids(cookie_header)
    if not viewed_ids:
        return ''

    cards = []
    for item_id in viewed_ids:
        product = next((item for item in products if str(item['id']) == item_id), None)
        if product is None:
            continue
        cards.append(build_product_card(product))

    if not cards:
        return ''

    return (
        '<section class="section container recently-viewed-section">'
        '<div class="section-heading"><p class="eyebrow">Recently Viewed</p><h2>Pick Up Where You Left Off</h2></div>'
        f'<div class="card-grid product-grid">{"".join(cards)}</div>'
        '</section>'
    )


def render_index(user, cookie_header='', query=None):
    query = query or {}
    product_cards = ''.join(build_product_card(item) for item in products)

    category_cards = []
    for category in get_online_categories():
        category_products = get_products_for_category(category.get('id'))
        description_text = re.sub(r'<[^>]+>', '', str(category.get('descriptionHtml', ''))).strip()
        category_image = pick_category_image(category, category_products)
        category_cards.append(
            f'<article class="card category-card">'
            f'<a href="/category/{html.escape(category.get("seoSlug", ""))}">'
            f'<img src="{html.escape(category_image)}" alt="{html.escape(category.get("name", "Category"))}" />'
            '</a>'
            '<div class="card-body">'
            f'<h3><a href="/category/{html.escape(category.get("seoSlug", ""))}">{html.escape(category.get("name", "Category"))}</a></h3>'
            f'<p>{html.escape(description_text or "Explore this category")}</p>'
            f'<span>{len(category_products)} products</span>'
            '</div></article>'
        )

    status = query.get('status', [''])[0].strip().lower()
    requested_category = query.get('category', [''])[0].strip()
    category_status_block = ''
    if status == 'notfound' and requested_category:
        category_status_block = '<p class="error-message">Requested category is unavailable right now. Please choose another category.</p>'

    return make_template(
        'index.html',
        title='Vithi Organics',
        product_cards=product_cards,
        category_cards=''.join(category_cards),
        recently_viewed_block=render_recently_viewed_block(cookie_header),
        category_status_block=category_status_block,
        **get_template_user_context(user)
    )


def render_category_page(user, cookie_header, category, query):
    search_query = query.get('q', [''])[0].strip()
    sort_key = query.get('sort', ['featured'])[0].strip().lower() or 'featured'
    page_text = query.get('page', ['1'])[0].strip()

    try:
        current_page = int(page_text)
    except ValueError:
        current_page = 1
    current_page = max(1, current_page)

    category_products = get_products_for_category(category.get('id'))
    filtered = category_products[:]
    if search_query:
        token = search_query.lower()
        filtered = [
            item for item in filtered
            if token in item.get('name', '').lower() or token in item.get('description', '').lower()
        ]

    if sort_key == 'name_asc':
        filtered.sort(key=lambda item: item.get('name', '').lower())
    elif sort_key == 'name_desc':
        filtered.sort(key=lambda item: item.get('name', '').lower(), reverse=True)
    elif sort_key == 'price_low':
        filtered.sort(key=lambda item: float(item.get('price', 0)))
    elif sort_key == 'price_high':
        filtered.sort(key=lambda item: float(item.get('price', 0)), reverse=True)
    else:
        sort_key = 'featured'

    per_page = 10
    total = len(filtered)
    total_pages = max(1, (total + per_page - 1) // per_page)
    if current_page > total_pages:
        current_page = total_pages
    start = (current_page - 1) * per_page
    page_products = filtered[start:start + per_page]

    if page_products:
        product_cards = ''.join(build_product_card(item) for item in page_products)
    else:
        product_cards = '<article class="card category-empty-card"><div class="card-body"><h3>No products found</h3><p>Try a different search term or browse another category.</p></div></article>'

    pagination_links = []
    for page in range(1, total_pages + 1):
        href = f'/category/{quote(category.get("seoSlug", ""))}?page={page}&sort={quote(sort_key)}&q={quote(search_query)}'
        css_class = 'active' if page == current_page else ''
        pagination_links.append(f'<a class="{css_class}" href="{href}">{page}</a>')
    pagination_block = ''.join(pagination_links) if pagination_links else '<span class="active">1</span>'

    sidebar_links = []
    current_slug = category.get('seoSlug', '')
    for item in get_online_categories():
        slug = item.get('seoSlug', '')
        css_class = 'category-link-active' if slug == current_slug else ''
        sidebar_links.append(
            f'<a class="{css_class}" href="/category/{quote(slug)}">{html.escape(item.get("name", "Category"))}</a>'
        )
    sidebar_links_block = ''.join(sidebar_links) or '<p class="login-copy">No active categories.</p>'

    search_matches = []
    if search_query:
        token = search_query.lower()
        in_category = [
            item for item in category_products
            if token in item.get('name', '').lower() or token in item.get('description', '').lower()
        ]
        other = [
            item for item in products
            if str(item.get('categoryId')) != str(category.get('id')) and (token in item.get('name', '').lower() or token in item.get('description', '').lower())
        ]

        for item in in_category[:5]:
            search_matches.append(
                f'<a class="search-match-item" href="/products/{item["id"]}">'
                f'<img src="{item["image"]}" alt="{html.escape(item["name"])}" />'
                f'<div><strong>{html.escape(item["name"])}</strong><small>In this category</small></div>'
                '</a>'
            )
        for item in other[:5]:
            search_matches.append(
                f'<a class="search-match-item" href="/products/{item["id"]}">'
                f'<img src="{item["image"]}" alt="{html.escape(item["name"])}" />'
                f'<div><strong>{html.escape(item["name"])}</strong><small>Similar result</small></div>'
                '</a>'
            )
    search_match_items = ''.join(search_matches) if search_matches else '<p class="login-copy">Search to see matching products.</p>'

    recommended = [item for item in products if str(item.get('categoryId')) != str(category.get('id'))][:4]
    recommended_items = []
    for item in recommended:
        recommended_items.append(
            f'<a class="search-match-item" href="/products/{item["id"]}">'
            f'<img src="{item["image"]}" alt="{html.escape(item["name"])}" />'
            f'<div><strong>{html.escape(item["name"])}</strong><small>₹{item["price"]}</small></div>'
            '</a>'
        )
    recommended_block = ''.join(recommended_items) if recommended_items else '<p class="login-copy">No recommendations available.</p>'

    result_summary = f'Showing {len(page_products)} of {total} result(s)'
    category_description = category.get('descriptionHtml', '') or '<p>Explore this curated collection.</p>'
    category_image = pick_category_image(category, category_products)

    canonical = category.get('canonicalUrl', '').strip() or f'/category/{category.get("seoSlug", "")}'

    return make_template(
        'category.html',
        title=category.get('metaTitle', '') or category.get('name', 'Category'),
        meta_description=category.get('metaDescription', '') or f'Explore {category.get("name", "")}.',
        meta_keywords=category.get('metaKeywords', '') or 'organic category',
        canonical_url=canonical,
        search_action=f'/category/{quote(category.get("seoSlug", ""))}',
        category_status_block='',
        category_name=html.escape(category.get('name', 'Category')),
        category_slug=quote(category.get('seoSlug', '')),
        category_description=category_description,
        category_total_count=len(category_products),
        category_image=html.escape(category_image),
        category_result_summary=result_summary,
        category_product_cards=product_cards,
        category_pagination=pagination_block,
        sidebar_category_links=sidebar_links_block,
        search_match_items=search_match_items,
        recommended_items=recommended_block,
        search_query=html.escape(search_query),
        sort_featured_selected='selected' if sort_key == 'featured' else '',
        sort_name_asc_selected='selected' if sort_key == 'name_asc' else '',
        sort_name_desc_selected='selected' if sort_key == 'name_desc' else '',
        sort_price_low_selected='selected' if sort_key == 'price_low' else '',
        sort_price_high_selected='selected' if sort_key == 'price_high' else '',
        recently_viewed_block=render_recently_viewed_block(cookie_header),
        **get_template_user_context(user)
    )


def render_product(user, product, cookie_header='', review_message=''):
    product_weight = f'{float(product.get("weightKg", 1.0)):.2f} kg'
    product_reviews = [item for item in reviews if str(item.get('productId')) == str(product['id'])]
    review_count = len(product_reviews)
    avg_rating = 0
    if review_count:
        avg_rating = round(sum(int(item.get('rating', 0)) for item in product_reviews) / review_count, 1)

    if product_reviews:
        rows = []
        for entry in product_reviews:
            reviewer = html.escape(str(entry.get('userName', 'Customer')))
            rating = int(entry.get('rating', 0))
            comment = html.escape(str(entry.get('comment', '')))
            created_at = html.escape(str(entry.get('createdAt', '')))
            rows.append(
                f'<article class="product-review-item">'
                f'<div class="product-review-head"><strong>{reviewer}</strong><span>{"★" * rating}{"☆" * (5 - rating)}</span></div>'
                f'<p>{comment}</p>'
                f'<small>{created_at}</small>'
                f'</article>'
            )
        review_rows = ''.join(rows)
    else:
        review_rows = '<p class="login-copy">No ratings yet. Be the first to review this product.</p>'

    if not user:
        review_form_block = '<p class="login-copy">Please <a class="text-link" href="/login">login</a> to add your rating and comment.</p>'
    elif has_user_reviewed(product['id'], user['email']):
        review_form_block = '<p class="status-message">You have already reviewed this product.</p>'
    else:
        review_form_block = (
            '<form class="product-review-form" method="post" action="/reviews/add">'
            f'<input type="hidden" name="productId" value="{product["id"]}" />'
            '<label for="rating">Rating</label>'
            '<select id="rating" name="rating" required>'
            '<option value="">Choose</option>'
            '<option value="5">5 - Excellent</option>'
            '<option value="4">4 - Very Good</option>'
            '<option value="3">3 - Good</option>'
            '<option value="2">2 - Fair</option>'
            '<option value="1">1 - Poor</option>'
            '</select>'
            '<label for="comment">Comment</label>'
            '<textarea id="comment" name="comment" rows="4" maxlength="500" placeholder="Share your experience" required></textarea>'
            '<button class="btn btn-primary" type="submit">Submit Review</button>'
            '</form>'
        )

    message_block = ''
    if review_message == 'success':
        message_block = '<p class="status-message">Thanks. Your review was submitted successfully.</p>'
    elif review_message == 'exists':
        message_block = '<p class="error-message">You can only review this product once.</p>'
    elif review_message == 'invalid':
        message_block = '<p class="error-message">Please provide a valid rating and comment.</p>'

    return make_template(
        'product.html',
        title=product['name'],
        product_name=product['name'],
        product_description=product['description'],
        product_price=product['price'],
        product_weight=product_weight,
        product_image=product['image'],
        product_id=product['id'],
        average_rating='--' if not review_count else f'{avg_rating}',
        review_count=review_count,
        product_review_rows=review_rows,
        review_form_block=review_form_block,
        review_message_block=message_block,
        recently_viewed_block=render_recently_viewed_block(cookie_header),
        **get_template_user_context(user)
    )


def render_cart(user, cart_items):
    if not cart_items:
        cart_rows = '<p class="login-copy">Your cart is empty. Add a few organic essentials to get started.</p>'
        item_count = 0
        total_weight = 0
        subtotal = 0
        shipping = 0
        tax = 0
        total = 0
    else:
        rows = []
        subtotal = 0
        total_weight = 0
        for product_id, quantity in cart_items.items():
            product = next((item for item in products if str(item['id']) == str(product_id)), None)
            if not product:
                continue
            weight_kg = float(product.get('weightKg', 1.0))
            line_total = product['price'] * quantity
            subtotal += line_total
            total_weight += weight_kg * quantity
            rows.append(
                f'<div class="cart-item">'
                f'<img src="{product["image"]}" alt="{product["name"]}" />'
                f'<div class="item-details"><h3>{product["name"]}</h3><p style="color: var(--muted); font-size: 0.9rem;">Qty {quantity} • ₹{product["price"]}</p></div>'
                f'<strong>₹{line_total}</strong>'
                f'</div>'
            )
        cart_rows = ''.join(rows)
        item_count = sum(cart_items.values())
        shipping = round(total_weight * 70)
        tax = round(subtotal * 0.08)
        total = subtotal + shipping + tax

    return make_template(
        'cart.html',
        title='Cart',
        cart_rows=cart_rows,
        item_count=item_count,
        total_weight=f'{total_weight:.2f}',
        subtotal=subtotal,
        shipping=shipping,
        tax=tax,
        total=total,
        **get_template_user_context(user)
    )


def render_wishlist(user, wishlist_items):
    if not wishlist_items:
        wishlist_rows = '<p class="login-copy">Your wishlist is empty. Save a few favorites and come back anytime.</p>'
        item_count = 0
    else:
        rows = []
        for product_id, quantity in wishlist_items.items():
            product = next((item for item in products if str(item['id']) == str(product_id)), None)
            if not product:
                continue
            rows.append(
                f'<article class="wishlist-item">'
                f'<img src="{product["image"]}" alt="{product["name"]}" />'
                f'<div class="wishlist-item-body">'
                f'<div class="wishlist-item-top"><div><h3>{product["name"]}</h3><p>{product["description"]}</p></div><span class="badge">Best Seller</span></div>'
                f'<div class="wishlist-item-meta"><span>Organic</span><strong>₹{product["price"]}</strong></div>'
                f'<div class="wishlist-item-actions"><form method="post" action="/wishlist/move" style="display:inline;"><input type="hidden" name="productId" value="{product_id}" /><button class="btn btn-primary" type="submit">Move to cart</button></form></div>'
                f'</div></article>'
            )
        wishlist_rows = ''.join(rows)
        item_count = sum(wishlist_items.values())

    return make_template(
        'wishlist.html',
        title='Wishlist',
        wishlist_rows=wishlist_rows,
        item_count=item_count,
        **get_template_user_context(user)
    )


def render_login(user, error=''):
    return make_template(
        'login.html',
        title='Login',
        error_block='' if not error else f'<p class="error-message">{html.escape(error)}</p>',
        **get_template_user_context(user)
    )


def render_register(user, error='', fullname='', email='', phone=''):
    captcha_image, captcha_expected = generate_image_captcha()
    return make_template(
        'register.html',
        title='Create Account',
        error_block='' if not error else f'<p class="error-message">{html.escape(error)}</p>',
        fullname=html.escape(fullname),
        email=html.escape(email),
        phone=html.escape(phone),
        captcha_image=captcha_image,
        captcha_expected=captcha_expected,
        **get_template_user_context(user)
    )


def render_orders(user):
    visible_orders = orders
    if user:
        visible_orders = [order for order in orders if order.get('userEmail') == user['email']]

    if not visible_orders:
        order_rows = '<p class="login-copy">You have no orders yet.</p>'
    else:
        rows = []
        for order in visible_orders:
            product_name = html.escape(str(order.get('productName', 'Item')))
            total = html.escape(str(order.get('total', '0')))
            created_at = html.escape(str(order.get('createdAt', '')))
            rows.append(f'<li style="margin-bottom:0.6rem;"><strong>{product_name}</strong> — ₹{total} on {created_at}</li>')
        order_rows = f'<ul style="padding-left: 1rem; color: var(--muted);">{"".join(rows)}</ul>'
    return make_template('orders.html', title='Orders', order_rows=order_rows, **get_template_user_context(user))


def render_user_home(user, cookie_header='', message=''):
    user_orders = [order for order in orders if order.get('userEmail') == user['email']]
    if not user_orders:
        order_rows = '<p class="login-copy">No previous orders yet. Your future purchases will appear here.</p>'
    else:
        items = []
        for order in user_orders:
            product_name = html.escape(str(order.get('productName', 'Item')))
            total = html.escape(str(order.get('total', '0')))
            created_at = html.escape(str(order.get('createdAt', '')))
            items.append(
                f'<li><strong>{product_name}</strong><span>₹{total}</span><small>{created_at}</small></li>'
            )
        order_rows = f'<ul class="order-history-list">{"".join(items)}</ul>'

    return make_template(
        'user_home.html',
        title='My Home',
        message_block='' if not message else f'<p class="status-message">{html.escape(message)}</p>',
        user_name_full=html.escape(user.get('name', '')),
        user_email=html.escape(user.get('email', '')),
        user_phone=html.escape(user.get('phone', '')),
        address_value=html.escape(user.get('address', '')),
        order_rows=order_rows,
        recently_viewed_block=render_recently_viewed_block(cookie_header),
        **get_template_user_context(user)
    )


def render_admin_template(name, **context):
    content = Template(load_admin_template(name)).substitute(**context)
    is_authenticated = bool(context.get('is_authenticated', True))
    sidebar_block = ''
    topbar_block = ''
    if is_authenticated:
        sidebar_block = (
            '<aside class="admin-sidebar">'
            '<a class="admin-brand" href="/admin/subscribers">Vithi Admin</a>'
            '<nav class="admin-nav">'
            '<a href="/admin/categories">Categories</a>'
            '<a href="/admin/subscribers">Subscribers</a>'
            '<a href="/" target="_blank" rel="noopener noreferrer">Open Storefront</a>'
            '</nav>'
            '</aside>'
        )
        topbar_block = (
            '<header class="admin-topbar">'
            f'<p>Signed in as <strong>{html.escape(context.get("admin_user", "Admin"))}</strong></p>'
            '<a class="admin-logout" href="/admin/logout">Logout</a>'
            '</header>'
        )
    return Template(load_admin_template('base.html')).substitute(
        title=context.get('title', 'Admin'),
        admin_user=context.get('admin_user', 'Admin'),
        shell_class='' if is_authenticated else 'admin-shell-login',
        sidebar_block=sidebar_block,
        topbar_block=topbar_block,
        content=content
    )


def render_admin_login(csrf_token, error=''):
    return render_admin_template(
        'login.html',
        title='Admin Login',
        admin_user='Admin',
        is_authenticated=False,
        csrf_token=csrf_token,
        error_block='' if not error else f'<p class="admin-error">{html.escape(error)}</p>'
    )


def render_admin_subscribers(admin_user):
    if not subscribers:
        rows = '<tr><td colspan="2">No subscribers yet.</td></tr>'
    else:
        items = []
        for entry in subscribers:
            email = html.escape(str(entry.get('email', '')))
            created_at = html.escape(str(entry.get('createdAt', '')))
            items.append(f'<tr><td>{email}</td><td>{created_at}</td></tr>')
        rows = ''.join(items)

    return render_admin_template(
        'subscribers.html',
        title='Subscribers Admin',
        admin_user=admin_user,
        subscriber_count=str(len(subscribers)),
        subscriber_rows=rows
    )


def render_admin_categories(admin_user, query):
    status_filter = query.get('status', ['all'])[0].strip().lower() or 'all'
    sort_by = query.get('sort', ['display_order'])[0].strip().lower() or 'display_order'
    edit_id = query.get('edit', [''])[0].strip()
    message = query.get('msg', [''])[0]
    error = query.get('error', [''])[0]

    visible = categories[:]
    if status_filter in ('online', 'offline'):
        visible = [item for item in visible if item.get('status', 'online') == status_filter]

    if sort_by == 'name':
        visible.sort(key=lambda item: item.get('name', '').lower())
    elif sort_by == 'created_date':
        visible.sort(key=lambda item: item.get('createdAt', ''), reverse=True)
    else:
        visible.sort(key=lambda item: int(item.get('displayOrder', 999999)))

    rows = []
    for item in visible:
        category_id = str(item.get('id', ''))
        name = html.escape(str(item.get('name', '')))
        slug = html.escape(str(item.get('seoSlug', '')))
        status = item.get('status', 'online')
        status_label = 'Online' if status == 'online' else 'Offline'
        status_class = 'admin-status-online' if status == 'online' else 'admin-status-offline'
        image_path = html.escape(str(item.get('imagePath', '')))
        display_order = html.escape(str(item.get('displayOrder', '')))
        created_at = html.escape(str(item.get('createdAt', '')))
        modified_at = html.escape(str(item.get('modifiedAt', '')))
        created_by = html.escape(str(item.get('createdBy', '')))
        modified_by = html.escape(str(item.get('modifiedBy', '')))

        rows.append(
            f'<tr>'
            f'<td>{category_id}</td>'
            f'<td>{name}</td>'
            f'<td>{slug}</td>'
            f'<td>{display_order}</td>'
            f'<td><span class="admin-status-chip {status_class}">{status_label}</span></td>'
            f'<td><code>{image_path}</code></td>'
            f'<td>{created_at}<br/><small>by {created_by}</small></td>'
            f'<td>{modified_at}<br/><small>by {modified_by}</small></td>'
            f'<td class="admin-actions">'
            f'<a class="admin-link-btn" href="/admin/categories?edit={category_id}&status={status_filter}&sort={sort_by}">Edit</a>'
            f'<form method="post" action="/admin/categories/toggle" style="display:inline;">'
            f'<input type="hidden" name="id" value="{category_id}" />'
            f'<input type="hidden" name="status" value="{"offline" if status == "online" else "online"}" />'
            f'<button type="submit" class="admin-link-btn">{"Set Offline" if status == "online" else "Set Online"}</button>'
            f'</form>'
            f'<form method="post" action="/admin/categories/delete" style="display:inline;" onsubmit="return confirm(\'Are you sure you want to delete this category?\')">'
            f'<input type="hidden" name="id" value="{category_id}" />'
            f'<button type="submit" class="admin-link-btn admin-link-danger">Delete</button>'
            f'</form>'
            f'</td>'
            f'</tr>'
        )

    category_rows = ''.join(rows) if rows else '<tr><td colspan="9">No categories found.</td></tr>'

    if edit_id:
        selected = get_category_by_id(edit_id)
        if selected is None:
            edit_id = ''
            selected = {}
    else:
        selected = {}

    form_status = selected.get('status', 'online')
    form_image = str(selected.get('imagePath', ''))
    form_message = ''
    if message:
        form_message = f'<p class="admin-success">{html.escape(message)}</p>'
    elif error:
        form_message = f'<p class="admin-error">{html.escape(error)}</p>'

    return render_admin_template(
        'categories.html',
        title='Category Management',
        admin_user=admin_user,
        category_rows=category_rows,
        category_count=str(len(categories)),
        form_message=form_message,
        form_id=str(selected.get('id', 'Auto-generated')),
        form_name=html.escape(str(selected.get('name', ''))),
        form_description=html.escape(str(selected.get('descriptionHtml', ''))),
        form_display_order=html.escape(str(selected.get('displayOrder', '1'))),
        form_image_path=html.escape(form_image),
        form_created_at=html.escape(str(selected.get('createdAt', '-'))),
        form_modified_at=html.escape(str(selected.get('modifiedAt', '-'))),
        form_created_by=html.escape(str(selected.get('createdBy', '-'))),
        form_modified_by=html.escape(str(selected.get('modifiedBy', '-'))),
        form_slug=html.escape(str(selected.get('seoSlug', ''))),
        form_meta_title=html.escape(str(selected.get('metaTitle', ''))),
        form_meta_description=html.escape(str(selected.get('metaDescription', ''))),
        form_meta_keywords=html.escape(str(selected.get('metaKeywords', ''))),
        form_canonical_url=html.escape(str(selected.get('canonicalUrl', ''))),
        status_online_selected='selected' if form_status == 'online' else '',
        status_offline_selected='selected' if form_status == 'offline' else '',
        edit_hidden_id=f'<input type="hidden" name="id" value="{selected.get("id", "")}" />' if selected else '',
        sort_display_selected='selected' if sort_by == 'display_order' else '',
        sort_name_selected='selected' if sort_by == 'name' else '',
        sort_created_selected='selected' if sort_by == 'created_date' else '',
        filter_all_selected='selected' if status_filter == 'all' else '',
        filter_online_selected='selected' if status_filter == 'online' else '',
        filter_offline_selected='selected' if status_filter == 'offline' else '',
        image_preview_block=f'<img src="{html.escape(form_image)}" alt="Category image preview" class="admin-image-preview" />' if form_image else '<p class="admin-helper">No image uploaded yet.</p>'
    )


class VithiHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        # Ensure static assets resolve from the project directory regardless of launch cwd.
        super().__init__(*args, directory=DATA_DIR, **kwargs)

    def do_GET(self):
        user = get_user_from_cookie(self.headers.get('Cookie'))
        admin_user = get_admin_from_cookie(self.headers.get('Cookie'))
        parsed = urlparse(self.path)
        path = parsed.path

        if path == '/':
            self.respond_html(render_index(user, self.headers.get('Cookie'), parse_qs(parsed.query)))
            return
        if path.startswith('/category/'):
            slug = unquote(path[len('/category/'):]).strip().strip('/')
            category = get_category_by_slug(slug)
            if category is None or category.get('status', 'online') != 'online':
                self.redirect(f'/?category={quote(slug)}&status=notfound')
                return
            self.respond_html(render_category_page(user, self.headers.get('Cookie'), category, parse_qs(parsed.query)))
            return
        if path.startswith('/products/'):
            product_id = path.split('/')[-1]
            try:
                product = next(item for item in products if str(item['id']) == product_id)
            except StopIteration:
                self.send_error(404, 'Product not found')
                return
            params = parse_qs(parsed.query)
            review_message = params.get('review', [''])[0]
            recently_cookie_value = build_recently_viewed_cookie(self.headers.get('Cookie'), product['id'])
            cookie = cookies.SimpleCookie()
            cookie['vithi_recently_viewed'] = recently_cookie_value
            cookie['vithi_recently_viewed']['path'] = '/'
            self.respond_html(
                render_product(user, product, self.headers.get('Cookie'), review_message=review_message),
                extra_headers=[('Set-Cookie', cookie.output(header=''))]
            )
            return
        if path == '/login':
            if user:
                self.redirect('/user/home')
                return
            self.respond_html(render_login(user))
            return
        if path == '/register':
            if user:
                self.redirect('/user/home')
                return
            self.respond_html(render_register(user))
            return
        if path == '/admin':
            if admin_user:
                self.redirect('/admin/subscribers')
            else:
                self.redirect('/admin/login')
            return
        if path == '/admin/login':
            if admin_user:
                self.redirect('/admin/subscribers')
                return
            self.respond_admin_login_with_csrf()
            return
        if path == '/admin/logout':
            self.logout_admin()
            return
        if path == '/user/home':
            if not user:
                self.redirect('/login')
                return
            params = parse_qs(parsed.query)
            message = ''
            if params.get('updated', [''])[0] == '1':
                message = 'Address updated successfully.'
            self.respond_html(render_user_home(user, self.headers.get('Cookie'), message=message))
            return
        if path == '/admin/subscribers':
            if not admin_user:
                self.redirect('/admin/login')
                return
            self.respond_html(render_admin_subscribers(admin_user))
            return
        if path == '/admin/categories':
            if not admin_user:
                self.redirect('/admin/login')
                return
            self.respond_html(render_admin_categories(admin_user, parse_qs(parsed.query)))
            return
        if path == '/cart':
            self.respond_html(render_cart(user, get_cart_items(self.headers.get('Cookie'))))
            return
        if path == '/wishlist':
            self.respond_html(render_wishlist(user, get_wishlist_items(self.headers.get('Cookie'))))
            return
        if path == '/orders':
            self.respond_html(render_orders(user))
            return
        if path == '/logout':
            self.logout()
            return
        if path == '/sitemap.xml':
            self.respond_sitemap()
            return
        return super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        data, files = parse_post_form(self)
        user = get_user_from_cookie(self.headers.get('Cookie'))
        admin_user = get_admin_from_cookie(self.headers.get('Cookie'))

        if path == '/admin/login':
            username = data.get('username', [''])[0].strip()
            password = data.get('password', [''])[0]
            form_token = data.get('csrf_token', [''])[0]
            cookie_token = get_cookie_value(self.headers.get('Cookie'), 'vithi_admin_csrf')
            if not form_token or not cookie_token or form_token != cookie_token or form_token not in admin_login_csrf:
                self.respond_admin_login_with_csrf(error='Security check failed. Please try again.')
                return
            del admin_login_csrf[form_token]

            if username == admin_auth['username'] and verify_password_hash(password, admin_auth['password_hash']):
                session_id = generate_session_id()
                admin_sessions[session_id] = username
                self.send_response(302)
                self.send_header('Location', '/admin/subscribers')
                c = cookies.SimpleCookie()
                c['vithi_admin_session'] = session_id
                c['vithi_admin_session']['path'] = '/'
                c['vithi_admin_session']['httponly'] = True
                self.send_header('Set-Cookie', c.output(header=''))
                self.end_headers()
                return
            self.respond_admin_login_with_csrf(error='Invalid admin credentials.')
            return

        if path == '/admin/categories/save':
            if not admin_user:
                self.redirect('/admin/login')
                return

            category_id = data.get('id', [''])[0].strip()
            name = data.get('name', [''])[0].strip()
            description_html = data.get('descriptionHtml', [''])[0].strip()
            display_order_text = data.get('displayOrder', [''])[0].strip()
            status = data.get('status', ['online'])[0].strip().lower()
            seo_slug = ''
            meta_title = data.get('metaTitle', [''])[0].strip()
            meta_description = data.get('metaDescription', [''])[0].strip()
            meta_keywords = data.get('metaKeywords', [''])[0].strip()
            canonical_url = data.get('canonicalUrl', [''])[0].strip()
            image_path = data.get('imagePath', [''])[0].strip()

            try:
                display_order = int(display_order_text)
            except ValueError:
                display_order = 0

            if not name:
                self.redirect('/admin/categories?error=Category+Name+is+mandatory.')
                return
            if display_order < 1:
                self.redirect('/admin/categories?error=Display+Order+must+be+a+positive+integer.')
                return
            if status not in ('online', 'offline'):
                status = 'online'
            seo_slug = slugify(name)

            for item in categories:
                if str(item.get('id')) != category_id and item.get('name', '').strip().lower() == name.lower():
                    self.redirect('/admin/categories?error=Category+Name+must+be+unique.')
                    return
                if str(item.get('id')) != category_id and item.get('seoSlug', '').strip().lower() == seo_slug.lower():
                    self.redirect('/admin/categories?error=SEO+URL+slug+must+be+unique.')
                    return

            uploaded = files.get('image')
            if uploaded and uploaded.get('filename'):
                _, ext = os.path.splitext(uploaded['filename'])
                safe_name = f'{slugify(name)}-{int(datetime.now().timestamp())}{ext.lower() or ".png"}'
                target_path = os.path.join(CATEGORY_IMAGE_DIR, safe_name)
                with open(target_path, 'wb') as out:
                    out.write(uploaded.get('content', b''))
                image_path = f'/assets/category-images/{safe_name}'

            if not image_path:
                self.redirect('/admin/categories?error=Category+Image+is+mandatory.')
                return

            now = datetime.now().isoformat(timespec='seconds')
            actor = admin_user
            if category_id:
                category = get_category_by_id(category_id)
                if not category:
                    self.redirect('/admin/categories?error=Category+not+found.')
                    return
                category.update({
                    'name': name,
                    'descriptionHtml': description_html,
                    'displayOrder': display_order,
                    'imagePath': image_path,
                    'modifiedAt': now,
                    'modifiedBy': actor,
                    'status': status,
                    'seoSlug': seo_slug,
                    'metaTitle': meta_title,
                    'metaDescription': meta_description,
                    'metaKeywords': meta_keywords,
                    'canonicalUrl': canonical_url,
                })
                save_json_file(CATEGORIES_FILE, categories)
                self.redirect(f'/admin/categories?edit={category_id}&msg={quote("Category updated successfully.")}')
                return

            new_id = next_category_id()
            categories.append({
                'id': new_id,
                'name': name,
                'descriptionHtml': description_html,
                'displayOrder': display_order,
                'imagePath': image_path,
                'createdAt': now,
                'modifiedAt': now,
                'createdBy': actor,
                'modifiedBy': actor,
                'status': status or 'online',
                'seoSlug': seo_slug,
                'metaTitle': meta_title,
                'metaDescription': meta_description,
                'metaKeywords': meta_keywords,
                'canonicalUrl': canonical_url,
            })
            save_json_file(CATEGORIES_FILE, categories)
            self.redirect(f'/admin/categories?edit={new_id}&msg={quote("Category created successfully.")}')
            return

        if path == '/admin/categories/toggle':
            if not admin_user:
                self.redirect('/admin/login')
                return
            category_id = data.get('id', [''])[0].strip()
            next_status = data.get('status', ['online'])[0].strip().lower()
            category = get_category_by_id(category_id)
            if not category:
                self.redirect('/admin/categories?error=Category+not+found.')
                return
            category['status'] = 'online' if next_status == 'online' else 'offline'
            category['modifiedAt'] = datetime.now().isoformat(timespec='seconds')
            category['modifiedBy'] = admin_user
            save_json_file(CATEGORIES_FILE, categories)
            self.redirect('/admin/categories?msg=Category+status+updated.')
            return

        if path == '/admin/categories/delete':
            if not admin_user:
                self.redirect('/admin/login')
                return
            category_id = data.get('id', [''])[0].strip()
            category = get_category_by_id(category_id)
            if not category:
                self.redirect('/admin/categories?error=Category+not+found.')
                return
            if has_products_for_category(category_id):
                self.redirect('/admin/categories?error=This+category+cannot+be+deleted+because+it+contains+one+or+more+products.+Please+move+or+delete+the+associated+products+before+deleting+the+category.')
                return
            categories[:] = [item for item in categories if str(item.get('id')) != category_id]
            save_json_file(CATEGORIES_FILE, categories)
            self.redirect('/admin/categories?msg=Category+deleted+successfully.')
            return

        if path == '/cart/add':
            cookie_header = self.headers.get('Cookie')
            cart_session_id = get_cookie_value(cookie_header, 'vithi_cart_session')
            if not cart_session_id:
                cart_session_id = generate_session_id()
            if cart_session_id not in carts:
                carts[cart_session_id] = {}
            product_id = data.get('productId', [''])[0]
            if product_id:
                carts[cart_session_id][product_id] = carts[cart_session_id].get(product_id, 0) + 1
            self.send_response(302)
            self.send_header('Location', '/cart')
            c = cookies.SimpleCookie()
            c['vithi_cart_session'] = cart_session_id
            c['vithi_cart_session']['path'] = '/'
            self.send_header('Set-Cookie', c.output(header=''))
            self.end_headers()
            return

        if path == '/wishlist/add':
            cookie_header = self.headers.get('Cookie')
            wishlist_session_id = get_cookie_value(cookie_header, 'vithi_wishlist_session')
            if not wishlist_session_id:
                wishlist_session_id = generate_session_id()
            if wishlist_session_id not in wishlist:
                wishlist[wishlist_session_id] = {}
            product_id = data.get('productId', [''])[0]
            if product_id:
                wishlist[wishlist_session_id][product_id] = wishlist[wishlist_session_id].get(product_id, 0) + 1
            self.send_response(302)
            self.send_header('Location', '/wishlist')
            c = cookies.SimpleCookie()
            c['vithi_wishlist_session'] = wishlist_session_id
            c['vithi_wishlist_session']['path'] = '/'
            self.send_header('Set-Cookie', c.output(header=''))
            self.end_headers()
            return

        if path == '/wishlist/move':
            cookie_header = self.headers.get('Cookie')
            wishlist_session_id = get_cookie_value(cookie_header, 'vithi_wishlist_session')
            cart_session_id = get_cookie_value(cookie_header, 'vithi_cart_session')
            if not cart_session_id:
                cart_session_id = generate_session_id()
            if cart_session_id not in carts:
                carts[cart_session_id] = {}
            if wishlist_session_id and wishlist_session_id in wishlist:
                product_id = data.get('productId', [''])[0]
                if product_id and product_id in wishlist[wishlist_session_id]:
                    carts[cart_session_id][product_id] = carts[cart_session_id].get(product_id, 0) + 1
                    del wishlist[wishlist_session_id][product_id]
                    if not wishlist[wishlist_session_id]:
                        del wishlist[wishlist_session_id]
            self.send_response(302)
            self.send_header('Location', '/cart')
            c = cookies.SimpleCookie()
            c['vithi_cart_session'] = cart_session_id
            c['vithi_cart_session']['path'] = '/'
            self.send_header('Set-Cookie', c.output(header=''))
            self.end_headers()
            return

        if path == '/login':
            email = data.get('email', [''])[0].strip()
            password = data.get('password', [''])[0]
            user_record = users.get(email)
            if user_record and verify_user_password(password, user_record.get('password', '')):
                if not is_password_hash(user_record.get('password', '')):
                    user_record['password'] = make_password_hash(password)
                    users[email] = user_record
                    if db_ready:
                        save_user_to_db(user_record)
                    else:
                        save_json_file(USERS_FILE, users)
                session_id = generate_session_id()
                sessions[session_id] = email
                self.send_response(302)
                self.send_header('Location', '/user/home')
                c = cookies.SimpleCookie()
                c['vithi_session'] = session_id
                c['vithi_session']['path'] = '/'
                self.send_header('Set-Cookie', c.output(header=''))
                self.end_headers()
                return
            self.respond_html(render_login(user, error='Invalid email or password'))
            return

        if path == '/register':
            fullname = data.get('fullname', [''])[0].strip()
            email = data.get('email', [''])[0].strip()
            password = data.get('password', [''])[0]
            confirm_password = data.get('confirm_password', [''])[0]
            phone = data.get('phone', [''])[0].strip()
            captcha_expected = data.get('captcha_expected', [''])[0].strip()
            captcha_answer = data.get('captcha_answer', [''])[0].strip().upper()
            if not fullname or not email or not password:
                self.respond_html(render_register(user, error='Please complete all required fields.', fullname=fullname, email=email, phone=phone))
                return
            if password != confirm_password:
                self.respond_html(render_register(user, error='Password and confirm password do not match.', fullname=fullname, email=email, phone=phone))
                return
            if not captcha_expected or captcha_answer != captcha_expected.upper():
                self.respond_html(render_register(user, error='Captcha verification failed. Please try again.', fullname=fullname, email=email, phone=phone))
                return
            if email in users:
                self.respond_html(render_register(user, error='Account already exists.', fullname=fullname, email=email, phone=phone))
                return
            users[email] = {
                'name': fullname,
                'email': email,
                'phone': phone,
                'address': '',
                'password': make_password_hash(password)
            }
            if db_ready:
                save_user_to_db(users[email])
            else:
                save_json_file(USERS_FILE, users)
            session_id = generate_session_id()
            sessions[session_id] = email
            self.send_response(302)
            self.send_header('Location', '/user/home')
            c = cookies.SimpleCookie()
            c['vithi_session'] = session_id
            c['vithi_session']['path'] = '/'
            self.send_header('Set-Cookie', c.output(header=''))
            self.end_headers()
            return

        if path == '/user/address':
            if not user:
                self.redirect('/login')
                return
            address = data.get('address', [''])[0].strip()
            user['address'] = address
            users[user['email']] = user
            if db_ready:
                update_user_address_in_db(user['email'], address)
            else:
                save_json_file(USERS_FILE, users)
            self.redirect('/user/home?updated=1')
            return

        if path == '/orders':
            product_name = data.get('productName', [''])[0]
            total = data.get('total', [''])[0]
            order_record = {
                'productName': product_name,
                'total': total,
                'userEmail': user['email'] if user else '',
                'createdAt': self.date_time_string()
            }
            orders.append(order_record)
            if db_ready:
                save_order_to_db(order_record)
            else:
                save_json_file(ORDERS_FILE, orders)
            self.send_response(302)
            self.send_header('Location', '/orders')
            self.end_headers()
            return

        if path == '/reviews/add':
            product_id = data.get('productId', [''])[0].strip()
            rating_text = data.get('rating', [''])[0].strip()
            comment = data.get('comment', [''])[0].strip()

            product = next((item for item in products if str(item['id']) == product_id), None)
            if not product:
                self.send_error(404, 'Product not found')
                return
            if not user:
                self.redirect('/login')
                return

            try:
                rating = int(rating_text)
            except ValueError:
                rating = 0

            if rating < 1 or rating > 5 or not comment:
                self.redirect(f'/products/{product_id}?review=invalid')
                return
            if has_user_reviewed(product_id, user['email']):
                self.redirect(f'/products/{product_id}?review=exists')
                return

            review_record = {
                'productId': int(product_id),
                'userEmail': user['email'],
                'userName': user.get('name', 'Customer'),
                'rating': rating,
                'comment': comment[:500],
                'createdAt': self.date_time_string()
            }
            reviews.append(review_record)
            if db_ready:
                save_review_to_db(review_record)
                reviews[:] = load_reviews_from_db()
            else:
                save_json_file(REVIEWS_FILE, reviews)

            self.redirect(f'/products/{product_id}?review=success')
            return

        if path == '/subscribe':
            email = data.get('email', [''])[0].strip().lower()
            if not is_valid_email(email):
                self.redirect('/')
                return
            if db_ready:
                saved = save_subscription_to_db(email)
                if saved:
                    subscribers[:] = load_subscriptions_from_db()
            else:
                save_subscription_local(email)
            self.redirect('/')
            return

        self.send_error(404, 'Not found')

    def logout(self):
        cookie_header = self.headers.get('Cookie')
        if cookie_header:
            cookie = cookies.SimpleCookie()
            cookie.load(cookie_header)
            session_id = cookie.get('vithi_session')
            if session_id and session_id.value in sessions:
                del sessions[session_id.value]
        self.send_response(302)
        self.send_header('Location', '/')
        c = cookies.SimpleCookie()
        c['vithi_session'] = ''
        c['vithi_session']['path'] = '/'
        c['vithi_session']['expires'] = 'Thu, 01 Jan 1970 00:00:00 GMT'
        self.send_header('Set-Cookie', c.output(header=''))
        self.end_headers()

    def logout_admin(self):
        cookie_header = self.headers.get('Cookie')
        if cookie_header:
            cookie = cookies.SimpleCookie()
            cookie.load(cookie_header)
            session_id = cookie.get('vithi_admin_session')
            if session_id and session_id.value in admin_sessions:
                del admin_sessions[session_id.value]
        self.send_response(302)
        self.send_header('Location', '/admin/login')
        c = cookies.SimpleCookie()
        c['vithi_admin_session'] = ''
        c['vithi_admin_session']['path'] = '/'
        c['vithi_admin_session']['expires'] = 'Thu, 01 Jan 1970 00:00:00 GMT'
        self.send_header('Set-Cookie', c.output(header=''))
        c2 = cookies.SimpleCookie()
        c2['vithi_admin_csrf'] = ''
        c2['vithi_admin_csrf']['path'] = '/admin'
        c2['vithi_admin_csrf']['expires'] = 'Thu, 01 Jan 1970 00:00:00 GMT'
        self.send_header('Set-Cookie', c2.output(header=''))
        self.end_headers()

    def respond_admin_login_with_csrf(self, error=''):
        csrf_token = generate_session_id()
        admin_login_csrf[csrf_token] = datetime.now().isoformat(timespec='seconds')
        c = cookies.SimpleCookie()
        c['vithi_admin_csrf'] = csrf_token
        c['vithi_admin_csrf']['path'] = '/admin'
        c['vithi_admin_csrf']['httponly'] = True
        self.respond_html(render_admin_login(csrf_token=csrf_token, error=error), extra_headers=[('Set-Cookie', c.output(header=''))])

    def redirect(self, location):
        self.send_response(302)
        self.send_header('Location', location)
        self.end_headers()

    def respond_html(self, content, extra_headers=None):
        encoded = content.encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(encoded)))
        if extra_headers:
            for header, value in extra_headers:
                self.send_header(header, value)
        self.end_headers()
        self.wfile.write(encoded)

    def respond_sitemap(self):
        from datetime import datetime
        from urllib.parse import quote
        base = os.environ.get('SITE_URL', 'http://localhost:8000').rstrip('/')
        today = datetime.utcnow().strftime('%Y-%m-%d')
        static_urls = ['', '/cart', '/login', '/register']
        urls = []
        for p in static_urls:
            urls.append({'loc': f'{base}{p}', 'lastmod': today, 'priority': '0.8' if p == '' else '0.6'})
        for product in products:
            urls.append({
                'loc': f"{base}/products/{product['id']}",
                'lastmod': today,
                'priority': '0.7'
            })
        for category in get_online_categories():
            urls.append({
                'loc': f"{base}/category/{quote(category.get('seoSlug', ''))}",
                'lastmod': today,
                'priority': '0.7'
            })
        body = ['<?xml version="1.0" encoding="UTF-8"?>']
        body.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
        for u in urls:
            body.append('  <url>')
            body.append(f"    <loc>{u['loc']}</loc>")
            body.append(f"    <lastmod>{u['lastmod']}</lastmod>")
            body.append('    <changefreq>weekly</changefreq>')
            body.append(f"    <priority>{u['priority']}</priority>")
            body.append('  </url>')
        body.append('</urlset>')
        encoded = ('\n'.join(body)).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/xml; charset=utf-8')
        self.send_header('Content-Length', str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


if __name__ == '__main__':
    host = '0.0.0.0'
    port = int(os.environ.get('PORT', 8000))
    try:
        server = HTTPServer((host, port), VithiHandler)
    except OSError as exc:
        if exc.errno == 98:
            print(f'Port {port} is already in use. Stop the existing server or run with a different port, for example: PORT={port + 1} ./.venv/bin/python server.py')
            raise SystemExit(1) from exc
        raise
    print(f'Vithi Organics server running on http://{host}:{port}')
    server.serve_forever()
