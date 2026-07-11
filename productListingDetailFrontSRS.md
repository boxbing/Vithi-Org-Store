# SRS: Product Listing / Product Detail Page (Storefront)

## Overview
The Product Detail Page shall display complete information about an individual product when a user clicks on a product from the Homepage, Category Listing Page, Search Results, Wishlist, Best Selling Products, Recommended Products, or any other storefront section.

The page shall provide customers with complete product information, including product images, product name, brand, category, pricing, stock availability, rich-text description, YouTube video, reviews, similar products, and best-selling products.

The page shall be modern, responsive, SEO-optimized, mobile-friendly, fast-loading, and compatible with the future Vithi Organics Store mobile application.

---

## 1. Header
The website header shall remain consistent with the rest of the storefront and include:
- Website Logo
- Main Navigation Menu
- Product Search
- User Account / Login
- Wishlist
- Shopping Cart

The header shall follow the same design and functionality defined in the Homepage and Category Listing Page specifications.

## 2. Breadcrumb Navigation
The Product Detail Page shall display breadcrumb navigation.

Example:
Home -> Category Name -> Product Name

Example:
Home -> Organic Juices -> Organic Amla Juice 1 Litre

Each applicable breadcrumb item shall be clickable.

The breadcrumb structure should be dynamically generated based on the product's associated Category.

## 3. Product Image Gallery
The Product Detail Page shall display up to 5 product images uploaded through the Product Management Admin Panel.

The gallery shall include:
- One large Primary Product Image
- Thumbnail previews of all available product images
- Clicking a thumbnail shall change the Primary Image
- Image zoom functionality is recommended
- Mobile users should be able to swipe between images
- Images shall maintain an appropriate aspect ratio without distortion

The first image shall be treated as the default Primary Product Image unless another uploaded image has been explicitly designated as primary.

Images shall be optimized for web delivery and use WebP or another modern format wherever supported.

## 4. Product Basic Information
The following information shall be prominently displayed:
- Product Name
- Brand Name
- Category Name
- Customer Rating
- Number of Reviews
- Product Availability
- Product Weight / Size

Brand and Category may be clickable to their corresponding listing pages.

## 5. Product Pricing
The Product Detail Page shall display:
- MRP
- Selling Price
- Discount Percentage, if applicable
- Amount Saved, where applicable

If no discount applies, only the applicable Selling Price should be prominently displayed.

Pricing shall be dynamically retrieved from the Product Management module.

## 6. GST Information
Where applicable, the page may display: Inclusive of all taxes.

## 7. Stock Availability
The product's current availability shall be displayed clearly.

Available statuses:
- In Stock
- Out of Stock

If Units in Stock is greater than zero, status shall be In Stock.
If Units in Stock equals zero, status shall be Out of Stock.

For Out of Stock products:
- Add to Cart shall be disabled
- A clear Out of Stock message shall be displayed
- Notify Me When Available may be added later

## 8. Quantity Selector
For In Stock products, customers shall be able to select quantity using:
- Minus button
- Quantity value
- Plus button

Quantity shall not exceed available stock or configured purchase limits.

## 9. Add to Cart
A prominent Add to Cart button shall be displayed for In Stock products.

On click:
- Product is added to cart with selected quantity
- Header cart count updates
- User receives visual confirmation
- User remains on Product Detail Page

## 10. Buy Now
A prominent Buy Now button is recommended.

On click:
- Product and selected quantity are added to cart
- Customer proceeds directly to cart or checkout flow

## 11. Wishlist
The Product Detail Page shall include Wishlist controls to add/remove and reflect current state.

If login is required, unauthenticated users should be prompted to log in or register.

## 12. Product Description
Rich-text HTML description from Admin shall be rendered with formatting support, Unicode, Hindi, and emojis.

Stored HTML shall be safely sanitized before rendering.

## 13. YouTube Product Video
If configured, display responsive YouTube embed with correct aspect ratio and lazy loading where appropriate.

If no video configured, hide section.

## 14. Product Reviews and Ratings
Display:
- Average rating
- Total review count
- Recent reviews (initially 3 to 5)
- Reviewer name, rating, text, date
- View All Reviews action
- Review submission flow per moderation rules

## 15. Similar Products
Display Online similar products based on same category, brand, tags, or similar attributes.

Current product shall be excluded.

## 16. Best Selling Products
Display Online best-selling products based on sales and merchandising rules.

## 17. Product Card Requirements
Cards in recommendation sections shall include:
- Primary image
- Product name
- Price and discount price
- Rating
- Stock status
- Add to Cart
- Wishlist

Image aspect ratio should remain 1:1.

## 18. Product URL and Slug
Use SEO-friendly unique slug URL.

Example:
- Name: Organic Amla Juice 1 Litre
- Slug: organic-amla-juice-1-litre
- URL: /product/organic-amla-juice-1-litre

## 19. SEO Requirements
Each Product Detail Page shall dynamically generate:
- HTML title
- Meta description
- Meta keywords
- Canonical URL

## 20. Open Graph Requirements
Each Online Product Detail Page shall generate:
- Open Graph title
- Open Graph description
- Open Graph image (primary image)

Preferred social image target is about 1200 x 630.

## 21. Structured Data
Generate Schema.org Product structured data with product, offer, rating, and review fields where available.

## 22. Offline Product Behaviour
Offline products:
- Shall not appear on public storefront listings/search/recommendations
- Direct URL access should redirect to Homepage or show Product Unavailable page per final business rule
- Should not be indexable while unavailable

## 23. Product Not Found
For invalid/non-existent slug, show Product Not Found page or redirect per business rule.

Recommended page content:
- Clear not found message
- Continue Shopping CTA
- Popular Categories
- Best Selling Products

## 24. Functional Requirements Summary
The Product Detail Page shall support complete online product details, image gallery, price/stock, quantity selection, add-to-cart, buy-now, wishlist, reviews, recommendations, SEO metadata, Open Graph metadata, and structured data.

## 25. Performance Requirements
- Responsive across mobile, tablet, desktop
- Target load time < 2s under normal conditions
- Optimize Core Web Vitals
- Lazy-load below-fold media only
- Do not lazy-load main above-fold product image
- Use optimized modern image formats where supported
- Lazy-load YouTube embed where appropriate
- Minimize unnecessary JavaScript
- Prevent layout shifts
- Optimize recommendation queries
- Cache suitable product data where practical

## 26. Future Enhancements
Potential enhancements:
- Notify Me When Available
- Product Comparison
- Recently Viewed
- Frequently Bought Together
- Variants (size/weight/flavor/packaging)
- Subscription / Repeat Delivery
- Product Q&A
- Verified Purchase badges
- Review media
- Social sharing
- Estimated delivery date by PIN
- AI recommendations
- Related blog articles
- Product badges (New, Best Seller, Sale, Organic Certified)

## Compatibility
This specification is compatible with Product Management, Category Management, Brand Management, Search, Category Listing, Homepage Product Grid, Cart/Checkout, Order Management, Reviews, and future Mobile App APIs.

All storefront product information shall be dynamically retrieved from Product Management using Product ID, with Category and Brand relationships maintained via Category ID and Brand ID.

Terminology note:
This document defines a single-product page and aligns with Product Detail Page terminology, while also covering related listing context requirements provided in scope.
