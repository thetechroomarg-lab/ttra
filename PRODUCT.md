# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Shoppers in Córdoba, Argentina, almost always on a phone. Two main entry points:
- **From WhatsApp:** someone already chatting with Vlad opens a link he sent (a product, a category, the catalog) to check prices and colors before confirming.
- **From Instagram:** someone discovering the shop through a post, story or ad, deciding whether to trust it enough to write.

Secondary: wholesale clients (mayoristas) who log in to see preferential prices; the delivery rider (cadete) and Vlad himself use separate admin panels that are out of scope for the storefront.

## Product Purpose

THE TECH ROOM ARG sells phones, notebooks/MacBooks, tablets, gaming and accessories. The site lets a visitor find a product, see its price in every accepted currency and its colors, add it to a cart and send the order to Vlad on WhatsApp, where the sale is confirmed and delivery is coordinated. Success is a visitor who trusts the shop and sends the order.

## Positioning

A one-person shop: Vlad sells technology personally and has done so since 2009. The visitor deals with a real, named person, not a faceless store. Prices are competitive and every product shows five ways to pay: dollars cash, dollar transfer, USDT, pesos cash and pesos transfer, plus installments where available.

## Operating Context

- Orders close on WhatsApp; the site prepares the message (cart, delivery address, total).
- Prices in pesos follow the day's dollar rate, shown in the header.
- Same-day delivery in Córdoba with a daily cutoff time.
- Warranty depends on the brand: official Apple warranty (1 year), 3 months Samsung/Motorola/Xiaomi, 6 months notebooks, 1 month gaming/accessories, 30 days used Swap units.

## Capabilities and Constraints

- FastAPI backend with vanilla JS/CSS frontend in `web/static/`. No build step.
- Customer accounts, profile, delivery addresses, order history, wholesale pricing tier, promo codes.
- Catalog by category and brand, search, price range filter, installments filter, product comparison, share links (`/?producto=<name>`).
- Product card images are AI-generated illustrations (disclosed on the catalog).
- Two visual modes exist: Classic (the only one in use, dark) and Fallout (kept in the repo, out of scope, must not be touched).
- Admin and cadete panels are server-rendered and out of scope for the storefront.

## Brand Commitments

- **Logo stays exactly as is:** stacked THE / TECH / ROOM / ARG. in Arial 800 with the red dot.
- **The cats stay:** Vaivén, Fendi and Bitu walk on the header and have their own pages.
- **Vlad is the face:** the "Hola soy Vlad, vendo tecnología desde el año 2009" name tag, his caricature and the first-person, one-person voice (never "nosotros").
- **The 3D phone intro stays** for first-time visitors.
- Headline: "Lo buscás? Lo tenés."
- Never mention suppliers; the stock reads as Vlad's own.

## Evidence on Hand

- Real catalog data (`web/productos.json`), category images (`web/static/category-backgrounds`), product images (`web/static/catalog-images`), Vlad caricature (`web/static/vlad-caricatura.webp`), cat assets.
- Warranty terms (`web/static/garantias.json`).
- No customer testimonials, review counts or sales figures on hand: do not invent any.

## Product Principles

1. Trust before price: a visitor should feel they are dealing with Vlad, a real person, before anything else.
2. Every price, every way to pay: the five prices are the product's answer, always visible and easy to compare.
3. The next step is WhatsApp: every path ends in a clear, low-friction way to send the order.
4. Phone first: the WhatsApp and Instagram visitor is on a phone; desktop is the secondary view.
5. Personality is an asset: the cats, the name tag and the humor are what neighboring shops can't copy.
