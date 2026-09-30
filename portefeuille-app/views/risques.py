import numpy as np
import plotly.graph_objects as go
import streamlit as st

from src import data as D
from src import ui

ui.entete("Registre des risques", "Criticité = probabilité × impact (échelle 1 à 3).")
ctx = ui.contexte()
r = ctx["risques"]
ouverts = r[r["statut"] != "Clos"]

ui.cartes([
    ("Risques ouverts", str(len(ouverts)), f"{len(r)} au registre"),
    ("Risques élevés", str(int((ouverts["criticite"] >= 6).sum())), "criticité ≥ 6", ui.COULEURS["Rouge"]),
    ("Actions en retard", str(int(r["action_en_retard"].sum())), "échéance dépassée, non close", ui.COULEURS["Rouge"]),
    ("Produits concernés", str(ouverts["code"].nunique()), "au moins un risque ouvert"),
])

c1, c2 = st.columns([1.1, 1])
with c1:
    st.markdown("#### Matrice des risques ouverts")
    z = np.zeros((3, 3))
    txt = [["" for _ in range(3)] for _ in range(3)]
    for x in ouverts.itertuples():
        z[int(x.proba) - 1][int(x.impact) - 1] += 1
        txt[int(x.proba) - 1][int(x.impact) - 1] += f"{x.id} ({x.code})<br>"
    crit = np.outer([1, 2, 3], [1, 2, 3])
    fig = go.Figure(go.Heatmap(
        z=crit, x=["Impact 1", "Impact 2", "Impact 3"], y=["Proba 1", "Proba 2", "Proba 3"],
        colorscale=[[0, "#DDEFE3"], [0.35, "#FBE7B5"], [1, "#F3B5B5"]], showscale=False,
        text=txt, texttemplate="%{text}", textfont=dict(size=12), hoverinfo="skip"))
    st.plotly_chart(ui.plotly_defaut(fig, 400), width="stretch")
with c2:
    st.markdown("#### Exposition par produit")
    g = (ouverts.groupby(["code", "produit"])["criticite"].sum().reset_index()
         .sort_values("criticite"))
    fig = go.Figure(go.Bar(x=g["criticite"], y=g["code"] + " " + g["produit"], orientation="h",
                           marker_color=ui.BLEU, text=g["criticite"], textposition="outside", cliponaxis=False))
    fig.update_layout(xaxis_title="Criticité cumulée des risques ouverts")
    st.plotly_chart(ui.plotly_defaut(fig, 400), width="stretch")

retard = r[r["action_en_retard"]]
if len(retard):
    st.error("**Actions correctives en retard** — à relancer auprès des responsables avant le prochain comité :\n\n" +
             "\n".join(f"- **{x.id}** · {x.produit} : {x.action} — {x.responsable}, échue depuis "
                       f"{int(x.jours_depassement)} jours" for x in retard.itertuples()))

st.markdown("#### Registre")
f1, f2 = st.columns(2)
niveaux = f1.multiselect("Niveau", ["Élevé", "Moyen", "Faible"], default=["Élevé", "Moyen", "Faible"])
statuts = f2.multiselect("Statut", sorted(r["statut"].unique()), default=[s for s in r["statut"].unique() if s != "Clos"])
t = r[r["niveau"].isin(niveaux) & r["statut"].isin(statuts)].sort_values(["criticite", "echeance"], ascending=[False, True])


def couleur_niveau(v):
    return {"Élevé": "background-color:#F3B5B5", "Moyen": "background-color:#FBE7B5",
            "Faible": "background-color:#DDEFE3"}.get(v, "")


st.dataframe(
    t[["id", "produit", "description", "proba", "impact", "criticite", "niveau", "responsable",
       "action", "statut", "echeance", "action_en_retard"]].style.map(couleur_niveau, subset=["niveau"]),
    hide_index=True, width="stretch",
    column_config={
        "id": "ID", "produit": "Produit", "description": "Risque", "proba": "P", "impact": "I",
        "criticite": "P × I", "niveau": "Niveau", "responsable": "Responsable", "action": "Action corrective",
        "statut": "Statut", "echeance": st.column_config.DateColumn("Échéance", format="DD/MM/YYYY"),
        "action_en_retard": st.column_config.CheckboxColumn("En retard"),
    })
