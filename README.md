# Pramac — Base de connaissance produits (démo MVP)

Démo Streamlit autonome de recherche dans le catalogue produits Pramac.

- **407 produits** dédupliqués, **4 737 caractéristiques techniques**
- Recherche par mot-clé (nom / caractéristique / valeur), filtres par catégorie,
  carburant et puissance (kVA)
- Fiche produit avec image, specs groupées et lien source

Les données sont embarquées dans `pramac.sqlite` (aucune base externe requise).

## Lancer en local

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

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
