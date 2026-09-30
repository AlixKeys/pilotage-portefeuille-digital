import plotly.graph_objects as go
import streamlit as st

from src import data as D
from src import ui

ui.entete("Simulation d'arbitrage",
          "Testez des décisions avant le comité : suspendre un produit, exiger un plan de redressement, fixer une réserve.")
ctx = ui.contexte()
ev = ctx["ev"]
lib = ui.libelle_produit(ev)
lances = set(ctx["prev"].loc[ctx["prev"]["lance"], "code"])
actifs = ev[(ev["reel"] < 0.999) & ~ev["code"].isin(lances)]

c1, c2 = st.columns([1, 1.3])
with c1:
    st.markdown("##### 1. Produits à suspendre")
    suspendus = st.multiselect(
        "On arrête les dépenses : le coût final devient ce qui a déjà été dépensé.",
        actifs["code"].tolist(), format_func=lib.get, placeholder="Aucun produit suspendu",
        help="Utile pour libérer du budget sur un produit peu prioritaire (P3) ou sans perspective de redressement.")
    st.markdown("##### 3. Réserve disponible")
    reserve = st.number_input("Enveloppe de réserve (M FCFA)", 0, 1000, 100, 10)
with c2:
    st.markdown("##### 2. Plans de redressement")
    st.caption("Pour chaque produit hors budget, fixez le CPI visé sur le reste à faire "
               "(1,00 = le reste est réalisé exactement au coût prévu).")
    cibles = {}
    for r in actifs[(actifs["cpi"] < 0.99) & ~actifs["code"].isin(suspendus)].sort_values("vac").itertuples():
        depart = float(round(r.cpi, 2))
        v = st.slider(f"{lib[r.code]} — CPI actuel {D.fmt_idx(r.cpi)}", 0.70, 1.10, depart, 0.01,
                      key=f"cpi_{r.code}")
        if abs(v - depart) > 1e-9:
            cibles[r.code] = v

sim = D.simuler(ev, suspendus, cibles)
avant = sim["eac"].sum() - sim["budget"].sum()
apres = sim["eac_simule"].sum() - sim["budget"].sum()
couvert = apres <= reserve

st.divider()
ui.cartes([
    ("Dépassement actuel", D.fmt_m(avant, signe=True), "au rythme observé", ui.COULEURS["Rouge"] if avant > 0 else ui.COULEURS["Vert"]),
    ("Dépassement après décisions", D.fmt_m(apres, signe=True), f"gain {D.fmt_m(avant - apres)}",
     ui.COULEURS["Rouge"] if apres > reserve else ui.COULEURS["Vert"]),
    ("Réserve", D.fmt_m(reserve), "couvre le dépassement" if couvert else f"manque {D.fmt_m(apres - reserve)}",
     ui.COULEURS["Vert"] if couvert else ui.COULEURS["Rouge"]),
])

# Cascade : dépassement actuel -> effet de chaque décision -> dépassement final
etapes, valeurs = ["Dépassement actuel"], [avant]
for r in sim[sim["decision"] != "—"].itertuples():
    etapes.append(f"{r.code} · {'suspension' if r.decision == 'Suspendu' else 'redressement'}")
    valeurs.append(r.eac_simule - r.eac)
fig = go.Figure(go.Waterfall(
    x=etapes + ["Après décisions"], y=valeurs + [0], measure=["absolute"] + ["relative"] * (len(valeurs) - 1) + ["total"],
    text=[D.fmt_nb(v) for v in valeurs] + [D.fmt_nb(apres)], textposition="outside",
    increasing=dict(marker_color=ui.COULEURS["Rouge"]), decreasing=dict(marker_color=ui.COULEURS["Vert"]),
    totals=dict(marker_color=ui.BLEU), connector=dict(line=dict(color=ui.GRIS))))
fig.add_hline(y=reserve, line_dash="dash", line_color=ui.COULEURS["Orange"],
              annotation_text=f"Réserve {D.fmt_nb(reserve)} M", annotation_position="top right")
fig.update_layout(yaxis_title="Dépassement (M FCFA)", showlegend=False)
st.plotly_chart(ui.plotly_defaut(fig, 420), width="stretch")

if not suspendus and not cibles:
    st.info("Aucune décision simulée pour l'instant : choisissez un produit à suspendre ou ajustez un CPI cible.")
else:
    phrase = (f"Avec ces décisions, le dépassement passe de **{D.fmt_m(avant)}** à **{D.fmt_m(apres)}**. ")
    phrase += ("La réserve de " + D.fmt_m(reserve) + " suffit à le couvrir." if couvert else
               f"Il reste **{D.fmt_m(apres - reserve)}** à trouver au-delà de la réserve.")
    if couvert:
        st.success(phrase)
    else:
        st.warning(phrase)
    irrealistes = [c for c, v in cibles.items() if v - ev.set_index("code").loc[c, "cpi"] > 0.10]
    if irrealistes:
        st.caption("⚠️ Gain de CPI de plus de 0,10 visé pour " + ", ".join(irrealistes) +
                   " : c'est ambitieux. Il faut un plan concret (renfort, réduction de périmètre, renégociation).")

with st.expander("Détail par produit"):
    st.dataframe(sim[["code", "produit", "statut", "budget", "ac", "eac", "eac_simule", "decision"]],
                 hide_index=True, width="stretch",
                 column_config={"code": "Code", "produit": "Produit", "statut": "Statut",
                                "budget": st.column_config.NumberColumn("Budget", format="%.0f"),
                                "ac": st.column_config.NumberColumn("Déjà dépensé", format="%.0f"),
                                "eac": st.column_config.NumberColumn("Coût final actuel", format="%.0f"),
                                "eac_simule": st.column_config.NumberColumn("Coût final simulé", format="%.0f"),
                                "decision": "Décision"})
