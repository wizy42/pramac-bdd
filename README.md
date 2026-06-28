# Pramac — Base de connaissance produits (démo MVP)

Démo Streamlit autonome de recherche dans le catalogue produits Pramac.

- **407 produits** dédupliqués, **4 737 caractéristiques techniques**
- 3 familles : Générateur · Manutention · Stockage énergie
- **Recherche** : filtres famille / catégorie / carburant / puissance (kVA) / mot-clé,
  fiche produit complète (toutes les specs groupées), sélecteur de colonnes
- **Recherche IA (Gemini)** : question en langage naturel → filtres déduits + recommandations
- **Données complètes** : tables produits & caractéristiques entières, export CSV

Les données sont embarquées dans `pramac.sqlite` (aucune base externe requise).

## Lancer en local

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Clé Gemini (onglet Recherche IA)

L'onglet IA lit la clé depuis `GEMINI_API_KEY`.

- **En local** : créer `.streamlit/secrets.toml` avec `GEMINI_API_KEY = "votre_clé"`
  (déjà ignoré par git), ou exporter la variable d'environnement.
- **Sur Streamlit Cloud** : app → **Settings → Secrets** → coller
  `GEMINI_API_KEY = "votre_clé"`. Modèle utilisé : `gemini-2.5-flash`.

Sans clé, les onglets Recherche et Données fonctionnent ; seul l'onglet IA est désactivé.

## Déploiement (Streamlit Community Cloud — gratuit)

1. Aller sur https://share.streamlit.io
2. « Create app » → sélectionner ce dépôt
3. Main file path : `streamlit_app.py`
4. Deploy — l'app est en ligne en ~1 min.

Coût : **0 €** (tier gratuit, base SQLite embarquée, pas de serveur à maintenir).

---
Données extraites du catalogue public pramac.com. Pipeline complet (crawler,
extraction, normalisation, PostgreSQL, sync Notion, enrichissement LLM/PDF) dans
le projet principal.
