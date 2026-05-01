"""E-Commerce Agent — Gère Shopify, Amazon, Etsy, WooCommerce, TikTok Shop."""
import json
from pathlib import Path
from .base_agent import BaseAgent

CONFIG_FILE = Path(__file__).parent.parent / "config" / "stores.json"

PLATFORMS = {
    "shopify":     {"name": "Shopify",     "emoji": "🛍️"},
    "amazon":      {"name": "Amazon",      "emoji": "📦"},
    "etsy":        {"name": "Etsy",        "emoji": "🎨"},
    "woocommerce": {"name": "WooCommerce", "emoji": "🛒"},
    "tiktok_shop": {"name": "TikTok Shop", "emoji": "🎵"},
    "ebay":        {"name": "eBay",        "emoji": "🏷️"},
}


class ECommerceAgent(BaseAgent):
    def __init__(self):
        super().__init__("E-Commerce Manager", "🛒", "Gestion boutiques en ligne")
        self._stores = self._load_stores()

    # ── Gestion des boutiques ───────────────────────────────────────────────
    def add_store(self, name: str, platform: str, api_key: str = "",
                  api_secret: str = "", store_url: str = ""):
        store = {
            "name": name, "platform": platform,
            "api_key": api_key, "api_secret": api_secret,
            "store_url": store_url, "active": True,
        }
        self._stores[name] = store
        self._save_stores()
        p = PLATFORMS.get(platform, {})
        self.success(f"Boutique ajoutée : {p.get('emoji','')} {name} sur {p.get('name', platform)}")

    def list_stores(self):
        self.header("Boutiques enregistrées")
        if not self._stores:
            print("  Aucune boutique. Utilisez add_store() pour en ajouter.")
            return
        for name, s in self._stores.items():
            p = PLATFORMS.get(s["platform"], {})
            status = "🟢" if s.get("active") else "🔴"
            print(f"  {status}  {p.get('emoji','')} {name:<30} {p.get('name', s['platform']):<15} {s.get('store_url','')}")

    # ── Gestion produits ────────────────────────────────────────────────────
    def create_product(self, store_name: str, product: dict) -> dict:
        store = self._stores.get(store_name)
        if not store:
            self.error(f"Boutique inconnue : {store_name}")
            return {}
        platform = store["platform"]
        self.log(f"Création produit [{store_name}] : {product.get('title','?')}")

        if platform == "shopify":
            return self._shopify_create(store, product)
        elif platform == "woocommerce":
            return self._woo_create(store, product)
        elif platform == "etsy":
            return self._etsy_create(store, product)
        elif platform == "amazon":
            self.warn("Amazon nécessite Seller Central — génération de fiche en mode draft.")
            return self._amazon_draft(product)
        else:
            self.warn(f"Platform {platform} : création manuelle requise. Fiche générée.")
            return {"draft": True, "product": product, "platform": platform}

    def generate_product_listing(self, title: str, description: str, price: float,
                                  category: str, tags: list, images: list = None) -> dict:
        self.header(f"Génération fiche produit — {title}")
        listing = {
            "title":       title,
            "description": description,
            "price":       price,
            "category":    category,
            "tags":        tags,
            "images":      images or [],
            "variants":    [{"title": "Default", "price": price, "inventory_quantity": 100}],
            "seo_title":   title[:70],
            "seo_description": description[:320],
        }
        self.success(f"Fiche produit générée : {title[:50]}")
        return listing

    def bulk_list(self, store_name: str, products: list) -> list:
        self.log(f"Publication bulk : {len(products)} produits → [{store_name}]")
        results = []
        for i, p in enumerate(products, 1):
            self.log(f"[{i}/{len(products)}] {p.get('title','?')[:40]}")
            result = self.create_product(store_name, p)
            results.append(result)
        self.success(f"{len(results)} produits traités")
        return results

    def get_sales_report(self, store_name: str) -> dict:
        self.header(f"Rapport de ventes — {store_name}")
        # Placeholder — à connecter avec l'API de chaque plateforme
        report = {
            "store": store_name,
            "note": "Connectez vos API keys pour obtenir les vraies données.",
            "demo": {
                "total_orders": 0,
                "total_revenue": 0.0,
                "top_products": [],
            }
        }
        print(f"  💡 Pour activer : ajoutez vos API keys via add_store()")
        return report

    # ── Platform integrations ───────────────────────────────────────────────
    def _shopify_create(self, store: dict, product: dict) -> dict:
        try:
            import requests
            url = f"https://{store['api_key']}:{store['api_secret']}@{store['store_url']}/admin/api/2024-01/products.json"
            payload = {"product": {
                "title":        product.get("title"),
                "body_html":    product.get("description",""),
                "tags":         ",".join(product.get("tags",[])),
                "variants":     product.get("variants", [{"price": product.get("price",0)}]),
            }}
            resp = requests.post(url, json=payload, timeout=15)
            if resp.status_code in (200, 201):
                data = resp.json()["product"]
                self.success(f"Shopify : produit créé ID={data['id']}")
                return data
            else:
                self.error(f"Shopify erreur {resp.status_code}")
                return {"error": resp.text}
        except Exception as e:
            self.error(f"Shopify : {e}")
            return {"error": str(e)}

    def _woo_create(self, store: dict, product: dict) -> dict:
        try:
            from woocommerce import API
            wcapi = API(url=store["store_url"], consumer_key=store["api_key"],
                        consumer_secret=store["api_secret"], version="wc/v3")
            data = {"name": product.get("title"), "type": "simple",
                    "regular_price": str(product.get("price", 0)),
                    "description": product.get("description",""),
                    "tags": [{"name": t} for t in product.get("tags",[])]}
            resp = wcapi.post("products", data).json()
            self.success(f"WooCommerce : produit créé ID={resp.get('id','?')}")
            return resp
        except Exception as e:
            self.error(f"WooCommerce : {e}")
            return {"error": str(e)}

    def _etsy_create(self, store: dict, product: dict) -> dict:
        self.warn("Etsy API v3 : utilisez le dashboard Etsy pour la création manuelle.")
        self.log(f"Fiche draft prête : {product.get('title','?')}")
        return {"draft": True, "product": product, "platform": "etsy"}

    def _amazon_draft(self, product: dict) -> dict:
        self.log("Fiche Amazon générée en mode draft (upload via Seller Central).")
        return {"draft": True, "product": product, "platform": "amazon"}

    def _load_stores(self):
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE) as f:
                return json.load(f)
        return {}

    def _save_stores(self):
        with open(CONFIG_FILE, "w") as f:
            json.dump(self._stores, f, indent=2, ensure_ascii=False)
