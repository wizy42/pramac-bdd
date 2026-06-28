"""Recherche métier par LLM (Gemini) — PRD Étape 8.

Traduit une question en langage naturel en filtres structurés, puis demande au
modèle de classer/expliquer la liste courte de produits correspondants.
La clé est lue depuis ``st.secrets`` ou la variable d'environnement ``GEMINI_API_KEY``.
"""

from __future__ import annotations

import json
import os

import requests

MODEL = "gemini-2.5-flash"
_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def get_api_key() -> str | None:
    key = os.environ.get("GEMINI_API_KEY")
    if key:
        return key
    try:  # st.secrets n'existe qu'en contexte Streamlit
        import streamlit as st

        return st.secrets.get("GEMINI_API_KEY")
    except Exception:
        return None


def _call(prompt: str, key: str, json_mode: bool = False, model: str = MODEL) -> str:
    config: dict = {"temperature": 0}
    if json_mode:
        config["responseMimeType"] = "application/json"
    resp = requests.post(
        _ENDPOINT.format(model=model),
        headers={"x-goog-api-key": key, "Content-Type": "application/json"},
        json={"contents": [{"parts": [{"text": prompt}]}], "generationConfig": config},
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]


FILTER_PROMPT = """Tu es un assistant de recherche produit Pramac. Convertis la question en filtres JSON.
Familles possibles: "Générateur", "Manutention", "Stockage énergie", "Autre", ou null.
Carburants possibles: "Diesel", "Gasoline", "Natural Gas", "Liquid Propane Gas", "Petrol", ou null.
Renvoie UNIQUEMENT ce JSON:
{{"famille": string|null, "kva_min": number|null, "kva_max": number|null,
 "fuel": string|null, "keywords": [string]}}
"keywords" = mots techniques/métier utiles à filtrer sur le nom/les caractéristiques
(ex: "silencieux", "secours", "data center", "télécom", "portable", "triphasé").
Question: {question}"""

RANK_PROMPT = """Tu es expert produits Pramac. La question utilisateur est:
"{question}"

Voici les produits candidats (nom — famille — puissance kVA — carburant — catégorie):
{shortlist}

Recommande les 3 à 5 meilleurs produits. Pour chacun: **nom** puis une phrase de
justification concrète liée à la question. Si rien ne correspond vraiment, dis-le.
Réponds en français, en markdown concis."""


def nl_to_filters(question: str, key: str) -> dict:
    raw = _call(FILTER_PROMPT.format(question=question), key, json_mode=True)
    try:
        out = json.loads(raw)
    except json.JSONDecodeError:
        return {"famille": None, "kva_min": None, "kva_max": None, "fuel": None, "keywords": []}
    out.setdefault("keywords", [])
    return out


def recommend(question: str, shortlist_lines: list[str], key: str) -> str:
    if not shortlist_lines:
        return "_Aucun produit ne correspond aux filtres déduits._"
    shortlist = "\n".join(shortlist_lines[:25])
    return _call(RANK_PROMPT.format(question=question, shortlist=shortlist), key)
