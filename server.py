import os
import random
import string
import json
from http import cookies
from http.server import HTTPServer, SimpleHTTPRequestHandler
from string import Template
from urllib.parse import parse_qs, urlparse

try:
    import psycopg
except ImportError:  # pragma: no cover - depends on environment
    psycopg = None

DATA_DIR = os.path.dirname(__file__)
TEMPLATE_DIR = os.path.join(DATA_DIR, 'templates')
DATA_STORE = os.path.join(DATA_DIR, 'data')
USERS_FILE = os.path.join(DATA_STORE, 'users.json')
ORDERS_FILE = os.path.join(DATA_STORE, 'orders.json')
DATABASE_URL = os.environ.get('DATABASE_URL') or os.environ.get('POSTGRES_URL') or 'postgresql://postgres:postgres@localhost:5432/vithi'

sessions = {}
carts = {}
wishlist = {}
users = {}
orders = []
db_connection = None
db_ready = False


def ensure_data_dir():
    try:
        os.makedirs(DATA_STORE, exist_ok=True)
    except Exception:
        pass


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
    global users, orders, db_ready
    ensure_data_dir()
    legacy_users = load_json_file(USERS_FILE, {})
    legacy_orders = load_json_file(ORDERS_FILE, [])

    connection = connect_to_postgres()
    if connection is None:
        users = legacy_users
        orders = legacy_orders
        db_ready = False
        return False

    with connection.cursor() as cursor:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                email TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                phone TEXT,
                password TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id BIGSERIAL PRIMARY KEY,
                product_name TEXT NOT NULL,
                total TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            )
        ''')

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

    return True


def load_users_from_db():
    connection = connect_to_postgres()
    if connection is None:
        return {}
    with connection.cursor() as cursor:
        cursor.execute('SELECT name, email, phone, password FROM users ORDER BY created_at')
        rows = cursor.fetchall()
    return {row[1]: {'name': row[0], 'email': row[1], 'phone': row[2], 'password': row[3]} for row in rows}


def load_orders_from_db():
    connection = connect_to_postgres()
    if connection is None:
        return []
    with connection.cursor() as cursor:
        cursor.execute('SELECT product_name, total, created_at FROM orders ORDER BY id')
        rows = cursor.fetchall()
    return [{'productName': row[0], 'total': row[1], 'createdAt': row[2]} for row in rows]


def save_user_to_db(user_record):
    connection = connect_to_postgres()
    if connection is None:
        return False
    with connection.cursor() as cursor:
        cursor.execute(
            '''
            INSERT INTO users (email, name, phone, password)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (email) DO UPDATE SET
                name = EXCLUDED.name,
                phone = EXCLUDED.phone,
                password = EXCLUDED.password
            ''',
            (user_record['email'], user_record['name'], user_record.get('phone', ''), user_record['password'])
        )
    return True


def save_order_to_db(order_record):
    connection = connect_to_postgres()
    if connection is None:
        return False
    with connection.cursor() as cursor:
        cursor.execute(
            'INSERT INTO orders (product_name, total, created_at) VALUES (%s, %s, %s)',
            (order_record['productName'], order_record['total'], order_record.get('createdAt'))
        )
    return True


initialize_persistence()

products = [
    {
        'id': 1,
        'name': 'Organic Turmeric Powder',
        'price': 249,
        'description': 'Pure, earthy spice with antioxidant-rich wellness benefits.',
        'image': 'https://images.unsplash.com/photo-1506126613408-eca07ce68773?auto=format&fit=crop&w=900&q=80'
    },
    {
        'id': 2,
        'name': 'Botanical Face Serum',
        'price': 599,
        'description': 'Lightweight nourishment for calm, glowing, healthy skin.',
        'image': 'https://images.unsplash.com/photo-1501004318641-b39e6451bec6?auto=format&fit=crop&w=900&q=80'
    },
    {
        'id': 3,
        'name': 'Wildflower Organic Honey',
        'price': 399,
        'description': 'Pure sweetness with floral richness and natural goodness.',
        'image': 'https://images.unsplash.com/photo-1490645935967-10de6ba17061?auto=format&fit=crop&w=900&q=80'
    }
]


def load_template(name):
    path = os.path.join(TEMPLATE_DIR, name)
    with open(path, 'r', encoding='utf-8') as handle:
        return handle.read()


def make_template(name, **context):
    body = Template(load_template(name)).substitute(**context)
    header = Template(load_template('partials/header.html')).substitute(**context)
    footer = Template(load_template('partials/footer.html')).substitute(**context)
    return Template(load_template('base.html')).substitute(title=context.get('title', 'Vithi Organics'), header=header, content=body, footer=footer)


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


def generate_session_id():
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(32))


def get_cookie_value(cookie_header, name):
    if not cookie_header:
        return None
    cookie = cookies.SimpleCookie()
    cookie.load(cookie_header)
    value = cookie.get(name)
    return value.value if value else None


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


def render_index(user):
    cards = []
    for product in products:
        cards.append(
            f'<article class="card product-card">'
            f'<a class="product-link" href="/products/{product["id"]}"><img src="{product["image"]}" alt="{product["name"]}" /></a>'
            f'<div class="card-body">'
            f'<h3><a href="/products/{product["id"]}">{product["name"]}</a></h3>'
            f'<p>{product["description"]}</p>'
            f'<div class="price-row"><strong>₹{product["price"]}</strong><div class="actions">'
            f'<form method="post" action="/cart/add" style="display:inline;">'
            f'<input type="hidden" name="productId" value="{product["id"]}" />'
            f'<button class="btn btn-primary" type="submit">Add to Cart</button>'
            f'</form></div></div>'
            f'</div></article>'
        )
    return make_template('index.html', title='Vithi Organics', product_cards=''.join(cards), user_name=user['name'].split()[0] if user else '', login_label='Logout' if user else 'Login', login_href='/logout' if user else '/login')


def render_product(user, product):
    return make_template('product.html', title=product['name'], product_name=product['name'], product_description=product['description'], product_price=product['price'], product_image=product['image'], product_id=product['id'], user_name=user['name'].split()[0] if user else '', login_label='Logout' if user else 'Login', login_href='/logout' if user else '/login')


def render_cart(user, cart_items):
    if not cart_items:
        cart_rows = '<p class="login-copy">Your cart is empty. Add a few organic essentials to get started.</p>'
        item_count = 0
        subtotal = 0
        shipping = 0
        tax = 0
        total = 0
    else:
        rows = []
        subtotal = 0
        for product_id, quantity in cart_items.items():
            product = next((item for item in products if str(item['id']) == str(product_id)), None)
            if not product:
                continue
            line_total = product['price'] * quantity
            subtotal += line_total
            rows.append(
                f'<div class="cart-item">'
                f'<img src="{product["image"]}" alt="{product["name"]}" />'
                f'<div class="item-details"><h3>{product["name"]}</h3><p style="color: var(--muted); font-size: 0.9rem;">Qty {quantity} • ₹{product["price"]}</p></div>'
                f'<strong>₹{line_total}</strong>'
                f'</div>'
            )
        cart_rows = ''.join(rows)
        item_count = sum(cart_items.values())
        shipping = 0 if subtotal >= 1000 else 150
        tax = round(subtotal * 0.08)
        total = subtotal + shipping + tax

    return make_template(
        'cart.html',
        title='Cart',
        cart_rows=cart_rows,
        item_count=item_count,
        subtotal=subtotal,
        shipping=shipping,
        tax=tax,
        total=total,
        user_name=user['name'].split()[0] if user else '',
        login_label='Logout' if user else 'Login',
        login_href='/logout' if user else '/login'
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
        user_name=user['name'].split()[0] if user else '',
        login_label='Logout' if user else 'Login',
        login_href='/logout' if user else '/login'
    )


def render_login(user, error=''):
    return make_template('login.html', title='Login', error_block='' if not error else f'<p class="error-message">{error}</p>', user_name=user['name'].split()[0] if user else '', login_label='Logout' if user else 'Login', login_href='/logout' if user else '/login')


def render_register(user, error=''):
    return make_template('register.html', title='Create Account', error_block='' if not error else f'<p class="error-message">{error}</p>', user_name=user['name'].split()[0] if user else '', login_label='Logout' if user else 'Login', login_href='/logout' if user else '/login')


def render_orders(user):
    if not orders:
        order_rows = '<p class="login-copy">You have no orders yet.</p>'
    else:
        rows = []
        for order in orders:
            rows.append(f'<li style="margin-bottom:0.6rem;"><strong>{order["productName"]}</strong> — ₹{order["total"]} on {order["createdAt"]}</li>')
        order_rows = f'<ul style="padding-left: 1rem; color: var(--muted);">{"".join(rows)}</ul>'
    return make_template('orders.html', title='Orders', order_rows=order_rows, user_name=user['name'].split()[0] if user else '', login_label='Logout' if user else 'Login', login_href='/logout' if user else '/login')


class VithiHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        # Ensure static assets resolve from the project directory regardless of launch cwd.
        super().__init__(*args, directory=DATA_DIR, **kwargs)

    def do_GET(self):
        user = get_user_from_cookie(self.headers.get('Cookie'))
        parsed = urlparse(self.path)
        path = parsed.path

        if path == '/':
            self.respond_html(render_index(user))
            return
        if path.startswith('/products/'):
            product_id = path.split('/')[-1]
            try:
                product = next(item for item in products if str(item['id']) == product_id)
            except StopIteration:
                self.send_error(404, 'Product not found')
                return
            self.respond_html(render_product(user, product))
            return
        if path == '/login':
            self.respond_html(render_login(user))
            return
        if path == '/register':
            self.respond_html(render_register(user))
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
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length).decode('utf-8')
        data = parse_qs(body)
        user = get_user_from_cookie(self.headers.get('Cookie'))

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
            if user_record and user_record['password'] == password:
                session_id = generate_session_id()
                sessions[session_id] = email
                self.send_response(302)
                self.send_header('Location', '/')
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
            phone = data.get('phone', [''])[0].strip()
            if not fullname or not email or not password:
                self.respond_html(render_register(user, error='Please complete all required fields.'))
                return
            if email in users:
                self.respond_html(render_register(user, error='Account already exists.'))
                return
            users[email] = {'name': fullname, 'email': email, 'phone': phone, 'password': password}
            if db_ready:
                save_user_to_db(users[email])
            else:
                save_json_file(USERS_FILE, users)
            self.send_response(302)
            self.send_header('Location', '/login')
            self.end_headers()
            return

        if path == '/orders':
            product_name = data.get('productName', [''])[0]
            total = data.get('total', [''])[0]
            order_record = {'productName': product_name, 'total': total, 'createdAt': self.date_time_string()}
            orders.append(order_record)
            if db_ready:
                save_order_to_db(order_record)
            else:
                save_json_file(ORDERS_FILE, orders)
            self.send_response(302)
            self.send_header('Location', '/orders')
            self.end_headers()
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

    def respond_html(self, content):
        encoded = content.encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(encoded)))
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
                'loc': f"{base}/product?id={product['id']}",
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
