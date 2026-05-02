"""Quality Agent — Vérifie la conformité YouTube avant publication."""
from .base_agent import BaseAgent


YT_REQUIREMENTS = {
    "min_title_length":       40,
    "max_title_length":       100,
    "min_description_length": 300,
    "min_tags":               10,
    "min_sections":           3,
    "min_educational_score":  40,
}

DEMONETIZATION_TRIGGERS = [
    ("template", ["generated using a template", "produced in series",
                  "fill in the blank", "repetitive content"]),
    ("slideshow", ["no narration", "no commentary", "scrolling text only",
                   "static background", "no animation"]),
    ("reused",   ["copied from website", "not original", "identical to original"]),
]


class QualityAgent(BaseAgent):
    def __init__(self):
        super().__init__("Quality Agent", "✅", "Conformité YouTube & authenticité")

    def check_video(self, script: dict, style: str) -> dict:
        """Score un script 0-100 sur la conformité YouTube Partenaire."""
        self.header(f"Vérification qualité — {script.get('title','?')[:50]}")
        issues  = []
        bonuses = []
        score   = 0

        title = script.get("title", "")
        desc  = script.get("description", "")
        tags  = script.get("tags", [])
        sects = script.get("sections", [])
        lines = script.get("lyrics", [])
        edu   = script.get("educational_value", "")

        # ── Titre ──────────────────────────────────────────────────────────
        tlen = len(title)
        if YT_REQUIREMENTS["min_title_length"] <= tlen <= YT_REQUIREMENTS["max_title_length"]:
            score += 15
            bonuses.append(f"✅ Titre optimal ({tlen} chars)")
        elif tlen < YT_REQUIREMENTS["min_title_length"]:
            score += 5
            issues.append(f"⚠️ Titre trop court ({tlen} chars — min {YT_REQUIREMENTS['min_title_length']})")
        else:
            score += 10
            issues.append(f"⚠️ Titre trop long ({tlen} chars)")

        if any(e in title for e in ["🎵","🔥","🙏","🌟","✅","💪","🎬","✨"]):
            score += 5
            bonuses.append("✅ Emoji dans le titre")

        if any(str(y) in title for y in range(2024, 2027)):
            score += 5
            bonuses.append("✅ Année dans le titre")

        # ── Description ────────────────────────────────────────────────────
        dlen = len(desc)
        if dlen >= YT_REQUIREMENTS["min_description_length"]:
            score += 20
            bonuses.append(f"✅ Description riche ({dlen} chars)")
        elif dlen >= 150:
            score += 10
            issues.append(f"⚠️ Description courte ({dlen} chars — recommandé 300+)")
        else:
            issues.append(f"❌ Description trop courte ({dlen} chars)")

        if "#" in desc:
            score += 5
            bonuses.append("✅ Hashtags dans la description")

        if "subscribe" in desc.lower() or "abonne" in desc.lower():
            score += 3
            bonuses.append("✅ Call-to-action présent")

        # ── Tags ───────────────────────────────────────────────────────────
        ntags = len(tags)
        if ntags >= YT_REQUIREMENTS["min_tags"]:
            score += 10
            bonuses.append(f"✅ Tags suffisants ({ntags})")
        else:
            issues.append(f"⚠️ Pas assez de tags ({ntags} — min {YT_REQUIREMENTS['min_tags']})")
            score += max(0, ntags * 1)

        # ── Structure & valeur éducative ───────────────────────────────────
        if sects:
            nsects = len(sects)
            sect_types = {s.get("type") for s in sects}

            if nsects >= YT_REQUIREMENTS["min_sections"]:
                score += 10
                bonuses.append(f"✅ Structure variée ({nsects} sections)")
            else:
                issues.append(f"⚠️ Trop peu de sections ({nsects})")

            if "fact" in sect_types or "teaching" in sect_types:
                score += 15
                bonuses.append("✅ Contenu éducatif intégré")
            else:
                issues.append("⚠️ Aucun fait éducatif — risque de démonétisation")

            if "story_intro" in sect_types or "hook" in sect_types or "story" in sect_types:
                score += 10
                bonuses.append("✅ Narration originale présente")
            else:
                issues.append("💡 Ajouter une intro narrative pour plus d'authenticité")

            if "outro" in sect_types or "prayer_cta" in sect_types:
                score += 5
                bonuses.append("✅ Outro avec call-to-action")

            if "declaration" in sect_types or "verse" in sect_types:
                score += 5
                bonuses.append("✅ Déclarations originales")
        else:
            # Script basique sans sections
            if len(lines) > 8:
                score += 5
            issues.append("⚠️ Structure plate — manque de sections variées")

        if edu:
            score += 5
            bonuses.append(f"✅ Valeur éducative : {edu[:60]}...")

        score = min(score, 100)

        # ── Verdict ────────────────────────────────────────────────────────
        if score >= 75:
            verdict = "🟢 EXCELLENT — Conforme YouTube Partenaire"
            risk = "low"
        elif score >= 55:
            verdict = "🟡 BON — Quelques améliorations recommandées"
            risk = "medium"
        elif score >= 35:
            verdict = "🟠 MOYEN — Risque de démonétisation"
            risk = "high"
        else:
            verdict = "🔴 INSUFFISANT — Ne pas publier en l'état"
            risk = "critical"

        self.log(f"Score qualité : {score}/100 — {verdict}")
        for b in bonuses:
            print(f"  {b}")
        for i in issues:
            print(f"  {i}")

        return {
            "score":   score,
            "verdict": verdict,
            "risk":    risk,
            "bonuses": bonuses,
            "issues":  issues,
            "publishable": score >= 55,
        }

    def audit_channel(self, channel_name: str, videos: list) -> dict:
        """Analyse un ensemble de vidéos pour détecter les patterns répétitifs."""
        self.header(f"Audit chaîne — {channel_name}")
        if not videos:
            return {"status": "no_videos"}

        titles   = [v.get("title","") for v in videos]
        avg_len  = sum(len(t) for t in titles) / len(titles)
        unique   = len(set(titles))
        sections = [v.get("structure_type","") for v in videos if v.get("structure_type")]
        diverse  = len(set(sections))

        issues = []
        if unique < len(titles):
            issues.append(f"⚠️ {len(titles)-unique} titres dupliqués détectés")
        if avg_len < 40:
            issues.append("⚠️ Titres en moyenne trop courts")
        if diverse < 2 and len(sections) > 3:
            issues.append("⚠️ Structure identique dans toutes les vidéos — variez !")

        score = min(100, unique * 10 + diverse * 15)
        self.success(f"Audit terminé : {unique}/{len(titles)} vidéos uniques | {diverse} structures différentes")

        return {"channel": channel_name, "total": len(videos), "unique": unique,
                "structure_diversity": diverse, "issues": issues, "diversity_score": score}

    def youtube_compliance_tips(self) -> list:
        tips = [
            "🎯 Chaque vidéo doit apporter une valeur unique — faits, histoire, déclaration",
            "📖 Intégrez des versets bibliques spécifiques au sujet, pas génériques",
            "🎙️ Variez la structure : intro hook → enseignement → déclaration → prière → CTA",
            "🌍 Produire en plusieurs langues montre l'effort créatif réel",
            "📊 Description 300+ chars avec contexte spécifique à chaque vidéo",
            "🏷️ Tags variés et spécifiques à chaque vidéo, pas identiques",
            "⏱️ Vidéos de 3-8 minutes plutôt que 1 minute — plus de valeur perçue",
            "💬 Encourager les commentaires avec une vraie question à la fin",
            "👍 Demander le like en lien avec le contenu ('Like si vous avez reçu cette prière')",
            "🔔 Varier les appels à l'action — ne pas répéter la même phrase",
        ]
        self.header("Conseils conformité YouTube Partenaire")
        for t in tips:
            print(f"  {t}")
        return tips
