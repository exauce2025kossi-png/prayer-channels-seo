"""SEO Agent — Optimise titres, descriptions, tags et analyse les tendances."""
from .base_agent import BaseAgent


TRENDING_NICHES = {
    "kids":        ["baby shark", "nursery rhymes", "abc song", "kids songs", "toddler learning"],
    "african":     ["african music", "afrobeat", "nollywood", "african movie", "lagos story"],
    "disney":      ["disney songs", "cartoon music", "animation", "fairy tale", "princess song"],
    "3d":          ["3d animation", "cgi", "motion graphics", "3d cartoon", "anime 3d"],
    "music":       ["music video", "new song", "official video", "lyrics", "trending music"],
    "motivational":["motivation", "success mindset", "daily motivation", "self improvement"],
    "ecommerce":   ["buy online", "best price", "free shipping", "top product", "review"],
}


class SEOAgent(BaseAgent):
    def __init__(self):
        super().__init__("SEO Agent", "📊", "Optimisation SEO & Analytics")

    def optimize_video_metadata(self, title: str, topic: str, style: str,
                                 language: str = "en") -> dict:
        self.header(f"Optimisation SEO — {title[:40]}")
        trending = TRENDING_NICHES.get(style, [])
        tags = self._build_tags(topic, style, language, trending)
        opt_title = self._optimize_title(title, style)
        description = self._build_description(title, topic, style, language, tags)
        score = self._seo_score(opt_title, tags, description)

        result = {
            "title":       opt_title,
            "description": description,
            "tags":        tags,
            "seo_score":   score,
            "language":    language,
        }
        self.success(f"SEO Score : {score}/100 | {len(tags)} tags | Titre : {len(opt_title)} chars")
        return result

    def optimize_product_seo(self, product_name: str, category: str,
                              platform: str, language: str = "en") -> dict:
        self.header(f"SEO Produit — {product_name}")
        tags = self._build_product_tags(product_name, category, platform)
        title = self._optimize_product_title(product_name, category, platform)
        description = self._build_product_description(product_name, category, tags)
        score = self._seo_score(title, tags, description)

        result = {"title": title, "description": description,
                  "tags": tags, "seo_score": score}
        self.success(f"SEO Score produit : {score}/100")
        return result

    def trending_keywords(self, niche: str) -> list:
        self.header(f"Mots-clés tendance — {niche}")
        keywords = TRENDING_NICHES.get(niche, [])
        if not keywords:
            keywords = [niche, f"best {niche}", f"{niche} 2026", f"{niche} viral"]
        for kw in keywords:
            print(f"  🔥 {kw}")
        return keywords

    def analyze_title(self, title: str) -> dict:
        score = 0
        feedback = []
        if 40 <= len(title) <= 70:
            score += 30
            feedback.append("✅ Longueur parfaite (40-70 chars)")
        elif len(title) < 40:
            score += 15
            feedback.append("⚠️  Titre trop court — ajoutez des mots-clés")
        else:
            score += 20
            feedback.append("⚠️  Titre trop long — raccourcissez")

        if any(e in title for e in ["🎵","🎬","🔥","⭐","✨","💪","🌍"]):
            score += 20
            feedback.append("✅ Emoji présent — attire l'attention")
        else:
            feedback.append("💡 Ajoutez un emoji au début du titre")

        power_words = ["best","top","amazing","viral","free","now","how","why","new"]
        if any(w in title.lower() for w in power_words):
            score += 20
            feedback.append("✅ Power word détecté")
        else:
            feedback.append("💡 Ajoutez un power word (Best, Top, Free...)")

        if "|" in title or "—" in title or ":" in title:
            score += 15
            feedback.append("✅ Séparateur présent — bonne structure")

        if any(str(y) in title for y in range(2024, 2027)):
            score += 15
            feedback.append("✅ Année présente — boost SEO")

        self.header(f"Analyse titre — Score {min(score,100)}/100")
        for fb in feedback:
            print(f"  {fb}")
        return {"score": min(score, 100), "feedback": feedback}

    # ── Helpers ─────────────────────────────────────────────────────────────
    def _build_tags(self, topic, style, language, trending):
        base = [topic, f"{topic} song", f"{topic} {style}", f"{style} songs",
                "kids songs", "nursery rhymes", f"{language} songs", "2026",
                "new video", "subscribe"] + trending[:5]
        return list(dict.fromkeys(base))[:30]

    def _build_product_tags(self, product, category, platform):
        return [product, category, f"best {product}", f"buy {product}",
                f"{product} {platform}", "free shipping", "top rated", "2026",
                f"{product} review", f"{category} shop"]

    def _optimize_title(self, title, style):
        if len(title) < 40:
            extras = {"kids":"| Fun Kids Song","disney":"| Magic Animation",
                      "african":"| African Story","3d":"| 3D Animation",
                      "music":"| Official Video","motivational":"| Daily Motivation",
                      "news":"| Explained"}
            title = f"{title} {extras.get(style,'| Watch Now')}"
        if len(title) > 100:
            title = title[:97] + "..."
        return title

    def _optimize_product_title(self, product, category, platform):
        return f"Premium {product.title()} | Best {category} | Free Shipping"[:100]

    def _build_description(self, title, topic, style, language, tags):
        desc = f"🎵 {title}\n\n"
        desc += f"Welcome to our {style} channel! Today's video: {topic}\n\n"
        desc += "✅ New video every day!\n✅ Subscribe for more!\n✅ Hit the 🔔 bell!\n\n"
        desc += f"#{' #'.join(tags[:10])}"
        return desc[:5000]

    def _build_product_description(self, product, category, tags):
        return (f"🛍️ Premium {product} — Best quality in {category}!\n\n"
                f"✅ Fast worldwide shipping\n✅ 30-day money back guarantee\n"
                f"✅ Trusted by thousands of customers\n\n"
                f"#{' #'.join(tags[:8])}")

    def _seo_score(self, title, tags, description):
        score = 0
        if 40 <= len(title) <= 100: score += 25
        if len(tags) >= 10: score += 25
        if len(description) >= 200: score += 25
        if any(e in title for e in ["🎵","🎬","🔥","⭐","✨"]): score += 15
        if "#" in description: score += 10
        return min(score, 100)
