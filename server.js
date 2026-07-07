const express = require('express');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 8000;

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
const orders = [];

app.get('/', (req, res) => {
  res.render('index', { title: 'Vithi Organics', products });
});

app.get('/products/:id', (req, res) => {
  const product = products.find((item) => item.id === Number(req.params.id));
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
  res.render('cart', { title: 'Cart' });
});

app.get('/wishlist', (req, res) => {
  res.render('wishlist', { title: 'Wishlist' });
});

app.get('/orders', (req, res) => {
  res.render('orders', { title: 'Orders', orders });
});

app.post('/orders', (req, res) => {
  const { productName, total } = req.body;
  orders.push({ productName, total, createdAt: new Date().toISOString() });
  res.redirect('/orders');
});

app.listen(PORT, () => {
  console.log(`Vithi Organics server running on http://localhost:${PORT}`);
});
