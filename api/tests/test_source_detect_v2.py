import pytest

from app.services import source_detect_service


def test_detect_v2_jsonld_product():
    html = """
    <html>
      <head>
        <title>Product Page</title>
        <script type="application/ld+json">
          {
            "@context": "https://schema.org",
            "@type": "Product",
            "name": "Test Product",
            "url": "https://example.com/p/test-product",
            "image": "https://example.com/img.jpg",
            "offers": { "@type": "Offer", "price": "9.99", "priceCurrency": "USD" }
          }
        </script>
      </head>
      <body>...</body>
    </html>
    """

    res = source_detect_service.detect_from_html(html, used_url="https://example.com/p/test-product")
    assert res["signals"]["jsonld_count"] >= 1
    assert res["signals"]["has_Product"] is True
    assert res["detected_strategy"] == "jsonld_product"

    extract = res["suggested_extract"]
    assert extract["strategy"] == "jsonld"
    assert extract["jsonld"]["mode"] == "Product"
    assert extract["fields"]["title"]["path"] == "name"
    assert extract["fields"]["url"]["path"] == "url"


def test_detect_v2_woocommerce_category_suggests_selectors():
    html = """
    <html>
      <head>
        <title>Shop</title>
        <link rel="stylesheet" href="/wp-content/themes/storefront/style.css">
      </head>
      <body class="woocommerce woocommerce-page">
        <ul class="products">
          <li class="product">
            <a class="woocommerce-LoopProduct-link" href="/product/alpha">
              <h2 class="woocommerce-loop-product__title">Alpha</h2>
              <span class="price"><span class="woocommerce-Price-amount amount">$10</span></span>
              <img class="attachment-woocommerce_thumbnail" src="/img/a.jpg" />
            </a>
          </li>
          <li class="product">
            <a class="woocommerce-LoopProduct-link" href="/product/bravo">
              <h2 class="woocommerce-loop-product__title">Bravo</h2>
              <span class="price"><span class="woocommerce-Price-amount amount">$20</span></span>
              <img class="attachment-woocommerce_thumbnail" src="/img/b.jpg" />
            </a>
          </li>
          <li class="product">
            <a class="woocommerce-LoopProduct-link" href="/product/charlie">
              <h2 class="woocommerce-loop-product__title">Charlie</h2>
              <span class="price"><span class="woocommerce-Price-amount amount">$30</span></span>
              <img class="attachment-woocommerce_thumbnail" src="/img/c.jpg" />
            </a>
          </li>
          <li class="product">
            <a class="woocommerce-LoopProduct-link" href="/product/delta">
              <h2 class="woocommerce-loop-product__title">Delta</h2>
              <span class="price"><span class="woocommerce-Price-amount amount">$40</span></span>
              <img class="attachment-woocommerce_thumbnail" src="/img/d.jpg" />
            </a>
          </li>
        </ul>
      </body>
    </html>
    """

    res = source_detect_service.detect_from_html(html, used_url="https://example.com/shop")
    assert res["detected_strategy"] == "woocommerce"

    extract = res["suggested_extract"]
    assert extract["strategy"] == "generic_html_list"
    assert extract["list"]["item_selector"]
    assert extract["fields"]["url"]["selector"]
    assert extract["fields"]["title"]["selector"]


def test_detect_v2_shopify_collection_suggests_selectors_and_products_json():
    used_url = "https://example.myshopify.com/collections/wheels"
    html = """
    <html>
      <head>
        <title>Collection</title>
        <script src="https://cdn.shopify.com/s/files/1/0000/0001/t/1/assets/theme.js"></script>
      </head>
      <body>
        <div class="product-card">
          <a href="/products/alpha">
            <h3 class="product-card__title">Alpha</h3>
          </a>
          <span class="price">$10</span>
          <img src="https://cdn.shopify.com/s/files/1/0000/0001/products/a.jpg" />
        </div>
        <div class="product-card">
          <a href="/products/bravo">
            <h3 class="product-card__title">Bravo</h3>
          </a>
          <span class="price">$20</span>
          <img src="https://cdn.shopify.com/s/files/1/0000/0001/products/b.jpg" />
        </div>
        <div class="product-card">
          <a href="/products/charlie">
            <h3 class="product-card__title">Charlie</h3>
          </a>
          <span class="price">$30</span>
          <img src="https://cdn.shopify.com/s/files/1/0000/0001/products/c.jpg" />
        </div>
        <div class="product-card">
          <a href="/products/delta">
            <h3 class="product-card__title">Delta</h3>
          </a>
          <span class="price">$40</span>
          <img src="https://cdn.shopify.com/s/files/1/0000/0001/products/d.jpg" />
        </div>
      </body>
    </html>
    """

    res = source_detect_service.detect_from_html(html, used_url=used_url)
    assert res["detected_strategy"] == "shopify"

    extract = res["suggested_extract"]
    assert extract["strategy"] == "generic_html_list"
    assert extract["list"]["item_selector"]
    assert extract["fields"]["url"]["selector"]
    assert extract["fields"]["title"]["selector"]

    assert "shopify" in extract
    assert extract["shopify"]["products_json_url"].endswith("/products.json")


def test_detect_v2_generic_html_list_cards_suggests_selectors():
    html = """
    <html>
      <head><title>Listings</title></head>
      <body>
        <div class="card listing-item">
          <a class="link" href="/item/1">
            <img class="image" src="/img/1.jpg" />
            <h3 class="title">Item 1</h3>
          </a>
          <div class="price">$12</div>
        </div>
        <div class="card listing-item">
          <a class="link" href="/item/2">
            <img class="image" src="/img/2.jpg" />
            <h3 class="title">Item 2</h3>
          </a>
          <div class="price">$34</div>
        </div>
        <div class="card listing-item">
          <a class="link" href="/item/3">
            <img class="image" src="/img/3.jpg" />
            <h3 class="title">Item 3</h3>
          </a>
          <div class="price">$56</div>
        </div>
        <div class="card listing-item">
          <a class="link" href="/item/4">
            <img class="image" src="/img/4.jpg" />
            <h3 class="title">Item 4</h3>
          </a>
          <div class="price">$78</div>
        </div>
      </body>
    </html>
    """

    res = source_detect_service.detect_from_html(html, used_url="https://example.com/listings")
    assert res["detected_strategy"] == "generic_html_list"

    extract = res["suggested_extract"]
    assert extract["strategy"] == "generic_html_list"
    assert extract["list"]["item_selector"]
    assert extract["fields"]["url"]["selector"]
    assert extract["fields"]["title"]["selector"]

