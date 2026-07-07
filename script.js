const menuToggle = document.querySelector('.menu-toggle');
const mainNav = document.querySelector('.main-nav');

if (menuToggle && mainNav) {
  menuToggle.addEventListener('click', () => {
    const isOpen = mainNav.classList.toggle('open');
    menuToggle.setAttribute('aria-expanded', String(isOpen));
  });
}

// Mobile search toggle behavior
const mobileSearchToggle = document.querySelector('.mobile-search-toggle');
const mobileSearchForm = document.querySelector('.mobile-search-form');
const mobileSearchClose = document.querySelector('.mobile-search-close');
const mobileSearchInput = document.querySelector('.mobile-search-input');

if (mobileSearchToggle && mobileSearchForm) {
  mobileSearchToggle.addEventListener('click', () => {
    mobileSearchForm.classList.toggle('open');
    if (mobileSearchForm.classList.contains('open')) {
      setTimeout(() => mobileSearchInput && mobileSearchInput.focus(), 100);
    }
  });
}

if (mobileSearchClose && mobileSearchForm) {
  mobileSearchClose.addEventListener('click', () => {
    mobileSearchForm.classList.remove('open');
  });
}

const slides = Array.from(document.querySelectorAll('.hero .slide'));
const dotsContainer = document.querySelector('.slider-dots');

if (slides.length && dotsContainer) {
  slides.forEach((_, index) => {
    const dot = document.createElement('button');
    dot.type = 'button';
    dot.setAttribute('aria-label', `Go to slide ${index + 1}`);
    if (index === 0) dot.classList.add('active');
    dot.addEventListener('click', () => showSlide(index));
    dotsContainer.appendChild(dot);
  });

  const dots = Array.from(dotsContainer.children);
  let currentSlide = 0;

  function showSlide(index) {
    slides.forEach((slide, slideIndex) => {
      slide.classList.toggle('active', slideIndex === index);
    });
    dots.forEach((dot, dotIndex) => {
      dot.classList.toggle('active', dotIndex === index);
    });
    currentSlide = index;
  }

  setInterval(() => {
    currentSlide = (currentSlide + 1) % slides.length;
    showSlide(currentSlide);
  }, 6000);
}

const STORAGE_KEY = 'vithi-users';
const AUTH_KEY = 'vithi-auth';

function getUsers() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
  } catch {
    return [];
  }
}

function saveUsers(users) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(users));
}

function setAuthUser(user) {
  localStorage.setItem(AUTH_KEY, JSON.stringify(user));
}

function clearAuthUser() {
  localStorage.removeItem(AUTH_KEY);
}

function updateHeaderForAuth() {
  const authLink = document.querySelector('.header-actions .icon-link[href="login.html"]');
  if (!authLink) return;

  const authUser = JSON.parse(localStorage.getItem(AUTH_KEY) || 'null');
  if (authUser) {
    authLink.textContent = 'Hi, ' + authUser.name.split(' ')[0];
    authLink.href = '#';
    authLink.addEventListener('click', (event) => {
      event.preventDefault();
      clearAuthUser();
      updateHeaderForAuth();
      window.location.href = 'login.html';
    }, { once: true });
  } else {
    authLink.textContent = 'Login';
    authLink.href = 'login.html';
  }
}

const loginForm = document.querySelector('.auth-form');
if (loginForm && window.location.pathname.includes('login.html')) {
  loginForm.addEventListener('submit', (event) => {
    event.preventDefault();
    const emailInput = document.querySelector('#email');
    const passwordInput = document.querySelector('#password');
    const users = getUsers();
    const user = users.find((candidate) => candidate.email === emailInput.value.trim() && candidate.password === passwordInput.value);

    if (!user) {
      alert('No account found with that email and password.');
      return;
    }

    setAuthUser(user);
    updateHeaderForAuth();
    window.location.href = 'index.html';
  });
}

const registerForm = document.querySelector('.auth-form');
if (registerForm && window.location.pathname.includes('register.html')) {
  registerForm.addEventListener('submit', (event) => {
    event.preventDefault();
    const fullName = document.querySelector('#fullname')?.value.trim() || '';
    const email = document.querySelector('#email')?.value.trim() || '';
    const phone = document.querySelector('#phone')?.value.trim() || '';
    const password = document.querySelector('#password')?.value || '';
    const confirmPassword = document.querySelector('#confirm-password')?.value || '';

    if (!fullName || !email || !password) {
      alert('Please complete the required fields.');
      return;
    }

    if (password !== confirmPassword) {
      alert('Passwords do not match.');
      return;
    }

    const users = getUsers();
    if (users.some((user) => user.email === email)) {
      alert('An account with this email already exists.');
      return;
    }

    users.push({ name: fullName, email, phone, password });
    saveUsers(users);
    setAuthUser({ name: fullName, email, phone, password });
    updateHeaderForAuth();
    window.location.href = 'index.html';
  });
}

updateHeaderForAuth();
