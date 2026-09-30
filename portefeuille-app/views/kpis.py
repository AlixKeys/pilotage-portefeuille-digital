import plotly.graph_objects as go
import streamlit as st

from src import data as D
from src import ui

ui.entete("KPIs produit", "Les produits lancés atteignent-ils leurs objectifs d'adoption ?")
ctx = ui.contexte()
k = ctx["data"]["kpis"]
k = k[k["mois"] <= ctx["date"]].copy()
if k.empty:
    st.info("Aucun produit n'était encore lancé à cette date.")
    st.stop()

k["atteinte"] = k["reel"] / k["cible"]
dernier = k.sort_values("mois").groupby(["code", "indicateur"]).tail(1)


def fmt_val(v, ref):
    return D.fmt_pct(v, 0) if ref <= 1 else (D.fmt_nb(v, 1) if ref < 10 else D.fmt_nb(v))


st.markdown("#### Dernière valeur connue")
cols = st.columns(len(dernier))
for col, x in zip(cols, dernier.itertuples()):
    couleur = ui.COULEURS["Vert"] if x.atteinte >= 1 else ui.COULEURS["Orange"] if x.atteinte >= 0.9 else ui.COULEURS["Rouge"]
    col.markdown(ui.carte(f"{x.code} · {x.indicateur}", fmt_val(x.reel, x.cible),
                          f"cible {fmt_val(x.cible, x.cible)} · atteinte {D.fmt_pct(x.atteinte, 0)}", couleur),
                 unsafe_allow_html=True)

st.markdown("#### Évolution cible contre réel")
series = k.groupby(["code", "indicateur"])
multi = [(c, i) for (c, i), g in series if len(g) > 1]
if multi:
    cols = st.columns(len(multi))
    for col, (code, ind) in zip(cols, multi):
        g = k[(k["code"] == code) & (k["indicateur"] == ind)]
        fig = go.Figure()
        fig.add_bar(x=g["mois"], y=g["reel"], name="Réel",
                    marker_color=[ui.COULEURS["Vert"] if a >= 1 else ui.COULEURS["Orange"] for a in g["atteinte"]])
        fig.add_scatter(x=g["mois"], y=g["cible"], name="Cible", mode="lines", line=dict(color=ui.BLEU, dash="dash"))
        fig.update_layout(title=f"{code} · {ind}", xaxis=dict(tickformat="%m/%Y", dtick="M1"),
                          yaxis=dict(tickformat=".0%" if g["cible"].max() <= 1 else ",.0f"))
        col.plotly_chart(ui.plotly_defaut(fig, 330), width="stretch")

st.markdown("#### Lecture")
for x in dernier.itertuples():
    if x.atteinte >= 1:
        st.markdown(f"- ✅ **{x.produit} — {x.indicateur}** : objectif atteint ({D.fmt_pct(x.atteinte, 0)}).")
    else:
        prec = k[(k["code"] == x.code) & (k["indicateur"] == x.indicateur)].sort_values("mois")
        tendance = ""
        if len(prec) > 1:
            gain = prec["atteinte"].iloc[-1] - prec["atteinte"].iloc[0]
            tendance = (f" La progression est nette (+{D.fmt_nb(gain * 100)} points depuis le lancement) : "
                        "l'objectif est à portée." if gain > 0.05 else " La progression est lente : à analyser.")
        else:
            tendance = " Un seul point de mesure : suivre la tendance le mois prochain avant de conclure."
        st.markdown(f"- ⚠️ **{x.produit} — {x.indicateur}** : {D.fmt_pct(x.atteinte, 0)} de la cible.{tendance}")
