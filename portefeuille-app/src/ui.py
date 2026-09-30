"""Éléments d'interface partagés : couleurs, en-têtes, cartes, contexte."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from src import data as D

COULEURS = {"Rouge": "#D64545", "Orange": "#E8A317", "Vert": "#2E9E5B"}
BLEU = "#1F3864"
GRIS = "#8A94A6"
PV_C, EV_C, AC_C = "#8A94A6", "#1F6FEB", "#D64545"

CSS = """
<style>
.block-container {padding-top: 2rem; padding-bottom: 3rem; max-width: 1300px;}
[data-testid="stMetricValue"] {font-size: 1.6rem;}
.carte {border-radius: 10px; padding: 14px 16px; background: #F4F6FA;
        border-left: 5px solid #1F3864; min-height: 150px; box-sizing: border-box;}
.carte .lib {font-size: .8rem; color: #5B6475; text-transform: uppercase; letter-spacing: .03em;
             line-height: 1.3; min-height: 2.6em;}
.carte .val {font-size: 1.45rem; white-space: nowrap; font-weight: 700; color: #1F3864; line-height: 1.3;}
.carte .sous {font-size: .8rem; color: #5B6475;}
.badge {display:inline-block; padding: 2px 10px; border-radius: 12px; color: white;
        font-size: .78rem; font-weight: 600;}
.message {background: #EEF3FB; border-radius: 10px; padding: 12px 16px; margin-bottom: 8px;
          border-left: 4px solid #1F6FEB;}
</style>
"""


def entete(titre: str, sous_titre: str | None = None) -> None:
    st.markdown(CSS, unsafe_allow_html=True)
    ctx = contexte()
    st.title(titre)
    txt = f"Situation au **{D.fmt_date(ctx['date'])}** · montants en millions de FCFA · données synthétiques"
    if sous_titre:
        txt = f"{sous_titre}  \n{txt}"
    st.caption(txt)


def carte(libelle: str, valeur: str, sous: str = "", couleur: str = BLEU) -> str:
    return (f'<div class="carte" style="border-left-color:{couleur}">'
            f'<div class="lib">{libelle}</div><div class="val">{valeur}</div>'
            f'<div class="sous">{sous}</div></div>')


def cartes(items: list[tuple]) -> None:
    cols = st.columns(len(items))
    for col, item in zip(cols, items):
        col.markdown(carte(*item), unsafe_allow_html=True)


def badge(statut: str) -> str:
    return f'<span class="badge" style="background:{COULEURS.get(statut, GRIS)}">{statut}</span>'


def style_statut(val: str) -> str:
    c = COULEURS.get(val)
    return f"background-color:{c}; color:white; font-weight:600" if c else ""


def contexte() -> dict:
    return st.session_state["ctx"]


def libelle_produit(ev: pd.DataFrame) -> dict[str, str]:
    return {r.code: f"{r.code} – {r.produit}" for r in ev.itertuples()}


def plotly_defaut(fig, hauteur: int = 380):
    fig.update_layout(template="plotly_white", height=hauteur, margin=dict(l=10, r=10, t=50, b=10),
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
                      font=dict(family="Inter, Arial, sans-serif", size=13),
                      separators=", ")
    return fig


def ligne_date(fig, date, texte: str = "Date de situation"):
    """Trait vertical à la date de situation (compatible axes dates)."""
    x = pd.Timestamp(date)
    fig.add_shape(type="line", x0=x, x1=x, y0=0, y1=1, yref="paper",
                  line=dict(color=BLEU, dash="dot", width=1.5))
    fig.add_annotation(x=x, y=1, yref="paper", text=texte, showarrow=False,
                       yanchor="bottom", font=dict(size=11, color=BLEU))
    return fig
