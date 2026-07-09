const express = require('express');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 8001;

app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views'));

app.use(express.static(__dirname));
app.use(express.urlencoded({ extended: true }));
app.use(express.json());

const products = [
  {
    id: 1,
    name: 'Organic Turmeric Powder',
    price: 249,
    description: 'Pure, earthy spice with antioxidant-rich wellness benefits.',
    image: 'https://images.unsplash.com/photo-1506126613408-eca07ce68773?auto=format&fit=crop&w=900&q=80',
    category: 'Wellness'
  },
  {
    id: 2,
    name: 'Botanical Face Serum',
    price: 599,
    description: 'Lightweight nourishment for calm, glowing, healthy skin.',
    image: 'https://images.unsplash.com/photo-1501004318641-b39e6451bec6?auto=format&fit=crop&w=900&q=80',
    category: 'Skincare'
  },
  {
    id: 3,
    name: 'Wildflower Organic Honey',
    price: 399,
    description: 'Pure sweetness with floral richness and natural goodness.',
    image: 'https://images.unsplash.com/photo-1490645935967-10de6ba17061?auto=format&fit=crop&w=900&q=80',
    category: 'Pantry'
  }
];

const users = [];
const sessions = new Map();

function createSessionId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

function parseCookies(req) {
  const cookieHeader = req.headers.cookie;
  if (!cookieHeader) {
    return {};
  }

  return cookieHeader.split(';').reduce((cookies, pair) => {
    const separatorIndex = pair.indexOf('=');
    if (separatorIndex === -1) {
      return cookies;
    }

    const key = pair.slice(0, separatorIndex).trim();
    const value = decodeURIComponent(pair.slice(separatorIndex + 1).trim());
    cookies[key] = value;
    return cookies;
  }, {});
}

function setSessionCookie(res, sessionId) {
  const cookieValue = `sid=${sessionId}; Path=/; HttpOnly; SameSite=Lax`;
  const existing = res.getHeader('Set-Cookie');

  if (!existing) {
    res.setHeader('Set-Cookie', cookieValue);
    return;
  }

  if (Array.isArray(existing)) {
    res.setHeader('Set-Cookie', [...existing, cookieValue]);
    return;
  }

  res.setHeader('Set-Cookie', [existing, cookieValue]);
}

function getSession(req, res) {
  if (req.session) {
    return req.session;
  }

  const cookies = parseCookies(req);
  let sessionId = cookies.sid;

  if (!sessionId || !sessions.has(sessionId)) {
    sessionId = createSessionId();
    sessions.set(sessionId, { cart: [], wishlist: [], orders: [] });
    setSessionCookie(res, sessionId);
  }

  req.session = sessions.get(sessionId);
  return req.session;
}

function normalizeProductId(rawProductId) {
  const productId = Number(rawProductId);
  return Number.isInteger(productId) ? productId : null;
}

function getProductById(rawProductId) {
  const productId = normalizeProductId(rawProductId);
  if (productId === null) {
    return null;
  }
  return products.find((item) => item.id === productId) || null;
}

function addToCart(session, rawProductId, quantity = 1) {
  const product = getProductById(rawProductId);
  if (!product) {
    return false;
  }

  const safeQuantity = Math.max(1, Number(quantity) || 1);
  const existingItem = session.cart.find((entry) => entry.productId === product.id);

  if (existingItem) {
    existingItem.quantity += safeQuantity;
  } else {
    session.cart.push({ productId: product.id, quantity: safeQuantity });
  }

  return true;
}

function buildCartItems(session) {
  return session.cart
    .map((entry) => {
      const product = getProductById(entry.productId);
      if (!product) {
        return null;
      }

      const lineTotal = product.price * entry.quantity;
      return {
        productId: product.id,
        quantity: entry.quantity,
        product,
        lineTotal
      };
    })
    .filter(Boolean);
}

function buildCartSummary(cartItems) {
  const subtotal = cartItems.reduce((sum, item) => sum + item.lineTotal, 0);
  const tax = subtotal > 0 ? Math.round(subtotal * 0.12) : 0;
  const shipping = 0;
  const total = subtotal + tax + shipping;

  return { subtotal, tax, shipping, total };
}

function buildWishlistItems(session) {
  return session.wishlist
    .map((productId) => getProductById(productId))
    .filter(Boolean);
}

app.use((req, res, next) => {
  const session = getSession(req, res);
  res.locals.cartCount = session.cart.reduce((count, item) => count + item.quantity, 0);
  res.locals.wishlistCount = session.wishlist.length;
  next();
});

app.get('/', (req, res) => {
  res.render('index', { title: 'Vithi Organics', products });
});

app.get('/products/:id', (req, res) => {
  const product = getProductById(req.params.id);
  if (!product) {
    return res.status(404).send('Product not found');
  }
  res.render('product', { title: product.name, product });
});

app.get('/login', (req, res) => {
  res.render('login', { title: 'Login' });
});

app.post('/login', (req, res) => {
  const { email, password } = req.body;
  const user = users.find((entry) => entry.email === email && entry.password === password);
  if (!user) {
    return res.render('login', { title: 'Login', error: 'Invalid email or password' });
  }
  res.redirect('/');
});

app.get('/register', (req, res) => {
  res.render('register', { title: 'Create Account' });
});

app.post('/register', (req, res) => {
  const { fullname, email, password, phone } = req.body;
  if (!fullname || !email || !password) {
    return res.render('register', { title: 'Create Account', error: 'Please complete all required fields.' });
  }
  if (users.some((user) => user.email === email)) {
    return res.render('register', { title: 'Create Account', error: 'Account already exists.' });
  }
  users.push({ name: fullname, email, phone, password });
  res.redirect('/login');
});

app.get('/cart', (req, res) => {
  const session = getSession(req, res);
  const cartItems = buildCartItems(session);
  const summary = buildCartSummary(cartItems);
  res.render('cart', { title: 'Cart', cartItems, summary });
});

app.post('/cart/add', (req, res) => {
  const session = getSession(req, res);
  const productId = req.body.productId || req.query.productId;
  addToCart(session, productId, req.body.quantity);
  res.redirect('/cart');
});

app.post('/cart/update', (req, res) => {
  const session = getSession(req, res);
  const product = getProductById(req.body.productId);
  const quantity = Math.max(0, Number(req.body.quantity) || 0);

  if (!product) {
    return res.redirect('/cart');
  }

  if (quantity === 0) {
    session.cart = session.cart.filter((entry) => entry.productId !== product.id);
  } else {
    const cartItem = session.cart.find((entry) => entry.productId === product.id);
    if (cartItem) {
      cartItem.quantity = quantity;
    }
  }

  return res.redirect('/cart');
});

app.post('/cart/remove', (req, res) => {
  const session = getSession(req, res);
  const product = getProductById(req.body.productId);

  if (product) {
    session.cart = session.cart.filter((entry) => entry.productId !== product.id);
  }

  res.redirect('/cart');
});

app.get('/wishlist', (req, res) => {
  const session = getSession(req, res);
  const wishlistItems = buildWishlistItems(session);
  res.render('wishlist', { title: 'Wishlist', wishlistItems });
});

app.post('/wishlist/add', (req, res) => {
  const session = getSession(req, res);
  const product = getProductById(req.body.productId);

  if (product && !session.wishlist.includes(product.id)) {
    session.wishlist.push(product.id);
  }

  res.redirect('/wishlist');
});

app.post('/wishlist/remove', (req, res) => {
  const session = getSession(req, res);
  const product = getProductById(req.body.productId);

  if (product) {
    session.wishlist = session.wishlist.filter((productId) => productId !== product.id);
  }

  res.redirect('/wishlist');
});

app.post('/wishlist/move-to-cart', (req, res) => {
  const session = getSession(req, res);
  const product = getProductById(req.body.productId);

  if (product) {
    addToCart(session, product.id, 1);
    session.wishlist = session.wishlist.filter((productId) => productId !== product.id);
  }

  res.redirect('/wishlist');
});

app.post('/wishlist/add-all-to-cart', (req, res) => {
  const session = getSession(req, res);

  session.wishlist.forEach((productId) => {
    addToCart(session, productId, 1);
  });
  session.wishlist = [];

  res.redirect('/cart');
});

app.get('/orders', (req, res) => {
  const session = getSession(req, res);
  res.render('orders', { title: 'Orders', orders: session.orders });
});

app.post('/orders', (req, res) => {
  const session = getSession(req, res);
  const cartItems = buildCartItems(session);
  const summary = buildCartSummary(cartItems);

  if (cartItems.length > 0) {
    const productName = cartItems.map((item) => item.product.name).join(', ');
    session.orders.push({ productName, total: summary.total, createdAt: new Date().toISOString() });
    session.cart = [];
    return res.redirect('/orders');
  }

  const { productName, total } = req.body;
  if (productName && total) {
    session.orders.push({ productName, total, createdAt: new Date().toISOString() });
  }
  res.redirect('/orders');
});

if (require.main === module) {
  app.listen(PORT, () => {
    console.log(`Vithi Organics Node runtime (secondary) running on http://localhost:${PORT}`);
  });
}

module.exports = { app };
