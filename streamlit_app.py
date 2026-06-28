"""Démo — Base de connaissance produits Pramac.

Application Streamlit autonome : lit la base SQLite embarquée (``pramac.sqlite``).
- Recherche : filtres famille / catégorie / carburant / puissance / mot-clé + fiche complète
- Recherche IA : question en langage naturel → Gemini → filtres + recommandations (PRD Étape 8)
- Données : accès complet aux tables produits & caractéristiques (export CSV)
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

import gemini_search

DB_PATH = Path(__file__).parent / "pramac.sqlite"

st.set_page_config(page_title="Pramac — Base de connaissance produits", page_icon="⚡", layout="wide")


@st.cache_resource
def get_conn() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH, check_same_thread=False)


@st.cache_data
def load_products() -> pd.DataFrame:
    return pd.read_sql("SELECT * FROM products", get_conn())


@st.cache_data
def load_all_attributes() -> pd.DataFrame:
    return pd.read_sql("SELECT * FROM attributes", get_conn())


@st.cache_data
def load_attributes(product_uuid: str) -> pd.DataFrame:
    return pd.read_sql(
        "SELECT groupe, attribut, valeur, unite, source FROM attributes WHERE product_uuid = ?",
        get_conn(), params=(product_uuid,),
    )


@st.cache_data
def keyword_uuids(term: str) -> set[str]:
    like = f"%{term}%"
    rows = get_conn().execute(
        "SELECT DISTINCT product_uuid FROM attributes WHERE attribut LIKE ? OR valeur LIKE ?",
        (like, like),
    ).fetchall()
    return {r[0] for r in rows}


def apply_filters(df, *, search="", familles=None, categories=None, fuels=None,
                  kva_lo=None, kva_hi=None, keywords=None, only_power=False):
    mask = pd.Series(True, index=df.index)
    if search:
        term = search.strip().lower()
        hit = (df["nom"].str.lower().str.contains(term, na=False)
               | df["categorie"].str.lower().str.contains(term, na=False)
               | df["product_uuid"].isin(keyword_uuids(search.strip())))
        mask &= hit
    for kw in keywords or []:
        k = kw.strip().lower()
        if not k:
            continue
        mask &= (df["nom"].str.lower().str.contains(k, na=False)
                 | df["categorie"].str.lower().str.contains(k, na=False)
                 | df["product_uuid"].isin(keyword_uuids(kw.strip())))
    if familles:
        mask &= df["famille"].isin(familles)
    if categories:
        mask &= df["categorie"].isin(categories)
    if fuels:
        mask &= df["carburant"].isin(fuels)
    if only_power:
        mask &= df["puissance_kva"].notna()
    if kva_lo is not None:
        mask &= (df["puissance_kva"].ge(kva_lo) if only_power
                 else (df["puissance_kva"].ge(kva_lo) | df["puissance_kva"].isna()))
    if kva_hi is not None:
        mask &= df["puissance_kva"].le(kva_hi) | df["puissance_kva"].isna()
    return df[mask]


def product_card(prod):
    if isinstance(prod["image"], str) and prod["image"].startswith("http"):
        st.image(prod["image"], width=220)
    st.markdown(f"### {prod['nom']}")
    meta = [f"**Famille :** {prod['famille']}"]
    if prod["categorie"]:
        meta.append(f"**Catégorie :** {prod['categorie']}")
    if pd.notna(prod["puissance_kva"]):
        meta.append(f"**Puissance :** {prod['puissance_kva']:.0f} kVA")
    if isinstance(prod["carburant"], str) and prod["carburant"]:
        meta.append(f"**Carburant :** {prod['carburant']}")
    if isinstance(prod["sku"], str) and prod["sku"]:
        meta.append(f"**SKU :** {prod['sku']}")
    st.markdown("  \n".join(meta))
    if isinstance(prod["url"], str) and prod["url"].startswith("http"):
        st.markdown(f"[Voir sur pramac.com ↗]({prod['url']})")

    attrs = load_attributes(prod["product_uuid"])
    if attrs.empty:
        st.info("Aucune caractéristique technique extraite pour ce produit.")
        return
    st.markdown(f"#### Caractéristiques techniques ({len(attrs)})")
    for i, (groupe, block) in enumerate(attrs.groupby("groupe", dropna=False)):
        title = str(groupe) if pd.notna(groupe) else "Autres"
        with st.expander(f"{title} ({len(block)})", expanded=i < 3):
            table = block[["attribut", "valeur", "unite"]].rename(
                columns={"attribut": "Caractéristique", "valeur": "Valeur", "unite": "Unité"})
            st.dataframe(table, use_container_width=True, hide_index=True)


products = load_products()
FAMILLES = sorted(products["famille"].dropna().unique())
CATEGORIES = sorted(c for c in products["categorie"].dropna().unique())
FUELS = sorted(f for f in products["carburant"].dropna().unique())
KVA_MAX = int(products["puissance_kva"].dropna().max())

st.title("⚡ Pramac — Base de connaissance produits")
st.caption(
    f"{len(products)} produits · {int(products['nb_attributs'].sum())} caractéristiques · "
    f"Générateurs · Manutention · Stockage énergie — démo MVP"
)

tab_search, tab_ai, tab_data = st.tabs(["🔎 Recherche", "🤖 Recherche IA (Gemini)", "📊 Données complètes"])

# ============================ TAB 1 — Recherche ============================
with tab_search:
    with st.sidebar:
        st.header("Filtres")
        search = st.text_input("Recherche", placeholder="nom, caractéristique, valeur…")
        sel_fam = st.multiselect("Famille", FAMILLES)
        sel_cat = st.multiselect("Catégorie", CATEGORIES)
        sel_fuel = st.multiselect("Carburant", FUELS)
        only_power = st.checkbox("Uniquement avec puissance connue", value=False)
        kva_range = st.slider("Puissance (kVA)", 0, KVA_MAX, (0, KVA_MAX), step=10)
        sort_by = st.selectbox("Trier par", ["Nom", "Puissance (décroissant)", "Nb. caractéristiques"])

    lo, hi = kva_range
    filtered = apply_filters(
        products, search=search, familles=sel_fam, categories=sel_cat, fuels=sel_fuel,
        kva_lo=lo if lo > 0 else None, kva_hi=hi if hi < KVA_MAX else None, only_power=only_power,
    )
    if sort_by == "Nom":
        filtered = filtered.sort_values("nom")
    elif sort_by == "Puissance (décroissant)":
        filtered = filtered.sort_values("puissance_kva", ascending=False, na_position="last")
    else:
        filtered = filtered.sort_values("nb_attributs", ascending=False)

    left, right = st.columns([3, 2], gap="large")
    with left:
        st.subheader(f"Résultats — {len(filtered)} produit(s)")
        base_cols = ["nom", "famille", "categorie", "puissance_kva", "carburant", "nb_attributs"]
        extra = st.multiselect(
            "Colonnes supplémentaires",
            [c for c in products.columns if c not in base_cols + ["product_uuid", "image"]])
        view = filtered[base_cols + extra].rename(columns={
            "nom": "Produit", "famille": "Famille", "categorie": "Catégorie",
            "puissance_kva": "kVA", "carburant": "Carburant", "nb_attributs": "Specs"})
        st.dataframe(view, use_container_width=True, hide_index=True, height=460)
    with right:
        st.subheader("Fiche produit")
        if filtered.empty:
            st.info("Aucun produit ne correspond aux filtres.")
        else:
            choice = st.selectbox("Sélectionner un produit", filtered["nom"].tolist())
            product_card(filtered[filtered["nom"] == choice].iloc[0])

# ========================= TAB 2 — Recherche IA ============================
with tab_ai:
    st.subheader("Recherche en langage naturel")
    st.caption("Ex : « groupe électrogène diesel silencieux > 50 kVA pour data center », "
               "« chariot pour allée étroite », « stockage outdoor avec microgrid »")
    question = st.text_input("Votre besoin", key="ai_q",
                             placeholder="Décrivez votre besoin métier ou technique…")
    go = st.button("Rechercher avec l'IA", type="primary")

    key = gemini_search.get_api_key()
    if go and not key:
        st.error("Clé Gemini absente. Ajoutez `GEMINI_API_KEY` dans les secrets Streamlit "
                 "(Settings → Secrets) ou la variable d'environnement.")
    elif go and question.strip():
        with st.spinner("Analyse de la demande par Gemini…"):
            try:
                f = gemini_search.nl_to_filters(question, key)
            except Exception as e:
                st.error(f"Erreur Gemini : {e}")
                f = None
        if f is not None:
            st.write("**Filtres déduits :**", {k: v for k, v in f.items() if v})
            # Filtres durs fiables : famille + puissance. Carburant/mots-clés = signaux souples.
            base = apply_filters(
                products, familles=[f["famille"]] if f.get("famille") else None,
                kva_lo=f.get("kva_min"), kva_hi=f.get("kva_max"),
                only_power=bool(f.get("kva_min") or f.get("kva_max")),
            )
            if f.get("fuel"):
                fueled = base[base["carburant"] == f["fuel"]]
                base = fueled if not fueled.empty else base  # ne pas vider si carburant inconnu

            kws = [k for k in (f.get("keywords") or []) if k.strip()]
            kw_hit_uuids = set()
            for kw in kws:
                kw_hit_uuids |= keyword_uuids(kw.strip())

            def _kw_score(row):
                hay = f"{row['nom']} {row['categorie'] or ''}".lower()
                s = sum(1 for kw in kws if kw.lower() in hay)
                if row["product_uuid"] in kw_hit_uuids:
                    s += 1
                return s

            base = base.copy()
            base["_score"] = base.apply(_kw_score, axis=1)
            res = base.sort_values(
                ["_score", "puissance_kva"], ascending=[False, False], na_position="last")

            lines = [
                f"- {r.nom} — {r.famille} — "
                f"{(str(int(r.puissance_kva)) + ' kVA') if pd.notna(r.puissance_kva) else 'n/a'} — "
                f"{r.carburant or 'n/a'} — {r.categorie or ''}"
                for r in res.head(25).itertuples()
            ]
            with st.spinner("Recommandation…"):
                try:
                    st.markdown("### Recommandation")
                    st.markdown(gemini_search.recommend(question, lines, key))
                except Exception as e:
                    st.warning(f"Recommandation indisponible : {e}")
            st.markdown(f"### Produits correspondants ({len(res)})")
            st.dataframe(
                res[["nom", "famille", "categorie", "puissance_kva", "carburant"]].rename(
                    columns={"nom": "Produit", "famille": "Famille", "categorie": "Catégorie",
                             "puissance_kva": "kVA", "carburant": "Carburant"}),
                use_container_width=True, hide_index=True)

# ========================= TAB 3 — Données complètes =======================
with tab_data:
    st.subheader("Table produits")
    st.caption(f"{len(products)} lignes · toutes les colonnes")
    st.dataframe(products, use_container_width=True, hide_index=True, height=300)
    st.download_button("⬇ Télécharger products.csv", products.to_csv(index=False),
                       "products.csv", "text/csv")

    st.divider()
    attrs_all = load_all_attributes()
    st.subheader("Table caractéristiques")
    st.caption(f"{len(attrs_all)} lignes · 1 ligne = 1 attribut produit")
    cfilter = st.text_input("Filtrer les caractéristiques (libellé ou valeur)", key="attr_filter")
    shown = attrs_all
    if cfilter:
        t = cfilter.lower()
        shown = attrs_all[attrs_all["attribut"].str.lower().str.contains(t, na=False)
                          | attrs_all["valeur"].str.lower().str.contains(t, na=False)]
    st.dataframe(shown[["groupe", "attribut", "valeur", "unite", "source"]],
                 use_container_width=True, hide_index=True, height=320)
    st.caption(f"{len(shown)} ligne(s) affichée(s)")
    st.download_button("⬇ Télécharger attributes.csv", attrs_all.to_csv(index=False),
                       "attributes.csv", "text/csv")

st.divider()
st.caption("Données extraites du catalogue public pramac.com · MVP de démonstration. "
           "Source de vérité cible : PostgreSQL · interface métier : Notion.")
