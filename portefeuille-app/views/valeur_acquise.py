import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src import data as D
from src import ui

ui.entete("Valeur acquise", "Le projet avance-t-il au rythme prévu, et au coût prévu ?")
ctx = ui.contexte()
ev, data, seuils = ctx["ev"], ctx["data"], ctx["seuils"]

with st.expander("Lire les indicateurs en 30 secondes", expanded=False):
    st.markdown(
        "- **PV** (valeur planifiée) : ce qui aurait dû être réalisé à date, en M FCFA = budget × avancement prévu.\n"
        "- **EV** (valeur acquise) : ce qui a réellement été réalisé = budget × avancement réel.\n"
        "- **AC** (coût réel) : ce qui a été dépensé.\n"
        "- **SPI = EV / PV** : sous 1, le produit est en retard. **CPI = EV / AC** : sous 1, il coûte plus cher que prévu.\n"
        "- **Coût final estimé (EAC)** = budget / CPI, si la tendance de coût se maintient.\n"
        "- **TCPI** : CPI qu'il faudrait tenir sur le reste à faire pour finir dans le budget. Au-dessus de 1,1, c'est rarement réaliste.")

# --------------------------------------------------------- Quadrant SPI / CPI
st.markdown("#### Où se situe chaque produit ?")
fig = px.scatter(ev, x="spi", y="cpi", size="budget", color="statut", text="code",
                 color_discrete_map=ui.COULEURS, size_max=45,
                 hover_data={"produit": True, "budget": ":.0f", "spi": ":.2f", "cpi": ":.2f", "statut": False})
lo = min(ev["spi"].min(), ev["cpi"].min(), seuils.rouge) - 0.05
hi = max(ev["spi"].max(), ev["cpi"].max(), 1.0) + 0.05
fig.add_shape(type="rect", x0=lo, x1=1, y0=lo, y1=1, fillcolor="#D64545", opacity=0.06, line_width=0)
fig.add_hline(y=1, line_dash="dot", line_color=ui.GRIS)
fig.add_vline(x=1, line_dash="dot", line_color=ui.GRIS)
for x, y, t in [(hi - 0.01, hi - 0.01, "En avance, sous le budget"), (lo + 0.01, lo + 0.01, "En retard, au-dessus du budget")]:
    fig.add_annotation(x=x, y=y, text=t, showarrow=False, font=dict(size=11, color=ui.GRIS),
                       xanchor="right" if x > 1 else "left", yanchor="top" if y > 1 else "bottom")
fig.update_traces(textposition="middle center", textfont=dict(color="white", size=11))
fig.update_layout(xaxis=dict(title="SPI — délais", range=[lo, hi]), yaxis=dict(title="CPI — coûts", range=[lo, hi]),
                  legend_title_text="")
st.plotly_chart(ui.plotly_defaut(fig, 480), width="stretch")

# --------------------------------------------------------- Courbe en S
st.markdown("#### Courbe en S")
choix = st.selectbox("Périmètre", ["Portefeuille complet"] + [f"{r.code} – {r.produit}" for r in ev.itertuples()])
if choix == "Portefeuille complet":
    s = D.portefeuille_mensuel(data)
    budget = ev["budget"].sum()
else:
    code = choix.split(" – ")[0]
    b = data["projets"].set_index("code").loc[code, "budget"]
    s = data["suivi"][data["suivi"]["code"] == code].copy()
    s["pv"], s["ev"] = b * s["prevu"], b * s["reel"]
    budget = b
s = s[s["mois"] <= ctx["date"]]
fig = go.Figure()
fig.add_scatter(x=s["mois"], y=s["pv"], name="PV — prévu", line=dict(color=ui.PV_C, dash="dash", width=2))
fig.add_scatter(x=s["mois"], y=s["ev"], name="EV — réalisé", line=dict(color=ui.EV_C, width=3))
fig.add_scatter(x=s["mois"], y=s["ac"], name="AC — dépensé", line=dict(color=ui.AC_C, width=3))
fig.add_hline(y=budget, line_dash="dot", line_color=ui.BLEU,
              annotation_text=f"Budget {D.fmt_m(budget)}", annotation_position="top left")
fig.update_layout(yaxis_title="M FCFA", hovermode="x unified", xaxis=dict(tickformat="%m/%Y", dtick="M1"))
st.plotly_chart(ui.plotly_defaut(fig, 400), width="stretch")
st.caption("Lecture : quand la courbe bleue (réalisé) passe sous la grise (prévu), le produit prend du retard ; "
           "quand la rouge (dépensé) passe au-dessus de la bleue, il coûte plus que ce qu'il produit.")

# --------------------------------------------------------- Tendance SPI/CPI
st.markdown("#### Évolution mois par mois")
h = D.historique(data, seuils)
h = h[h["date"] <= ctx["date"]]
ind = st.radio("Indicateur", ["SPI", "CPI"], horizontal=True)
col = ind.lower()
codes = st.multiselect("Produits", ev["code"].tolist(),
                       default=ev.loc[ev["statut"] != "Vert", "code"].tolist() or ev["code"].tolist()[:4])
fig = px.line(h[h["code"].isin(codes)], x="date", y=col, color="code", markers=True,
              hover_data={"produit": True, col: ":.2f"})
fig.add_hrect(y0=0, y1=seuils.rouge, fillcolor=ui.COULEURS["Rouge"], opacity=0.07, line_width=0)
fig.add_hrect(y0=seuils.rouge, y1=seuils.orange, fillcolor=ui.COULEURS["Orange"], opacity=0.07, line_width=0)
fig.update_layout(yaxis=dict(title=ind, range=[max(0.5, h[col].min() - 0.05), max(1.1, h[col].max() + 0.05)]),
                  xaxis=dict(title="", tickformat="%m/%Y", dtick="M1"), legend_title_text="")
st.plotly_chart(ui.plotly_defaut(fig, 380), width="stretch")

# --------------------------------------------------------- Tableau détaillé
st.markdown("#### Indicateurs détaillés")
st.dataframe(
    ev[["code", "produit", "budget", "pv", "ev", "ac", "sv", "cv", "spi", "cpi",
        "eac", "eac_atypique", "eac_combine", "vac", "tcpi", "statut"]]
    .style.map(ui.style_statut, subset=["statut"]),
    hide_index=True, width="stretch",
    column_config={
        "code": "Code", "produit": "Produit",
        **{c: st.column_config.NumberColumn(lib, format="%.1f") for c, lib in [
            ("budget", "Budget"), ("pv", "PV"), ("ev", "EV"), ("ac", "AC"), ("sv", "Écart délais (SV)"),
            ("cv", "Écart coûts (CV)"), ("eac", "EAC = BAC/CPI"), ("eac_atypique", "EAC si écart ponctuel"),
            ("eac_combine", "EAC coût × délais"), ("vac", "VAC")]},
        "spi": st.column_config.NumberColumn("SPI", format="%.2f"),
        "cpi": st.column_config.NumberColumn("CPI", format="%.2f"),
        "tcpi": st.column_config.NumberColumn("TCPI", format="%.2f",
                                              help="CPI nécessaire sur le reste à faire pour tenir le budget"),
        "statut": "Statut",
    })
lances = set(ctx["prev"].loc[ctx["prev"]["lance"], "code"])
irrealistes = ev[(ev["tcpi"] > 1.1) & (ev["reel"] < 0.999) & ~ev["code"].isin(lances)]
if len(irrealistes):
    st.warning("Budget difficilement tenable pour : " + ", ".join(
        f"**{r.code}** (TCPI {D.fmt_idx(r.tcpi)})" for r in irrealistes.itertuples())
        + ". Il faudrait une efficacité nettement supérieure à celle observée jusqu'ici : prévoir une rallonge ou réduire le périmètre.")
