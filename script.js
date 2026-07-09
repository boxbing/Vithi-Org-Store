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
