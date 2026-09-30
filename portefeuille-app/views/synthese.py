import plotly.graph_objects as go
import streamlit as st

from src import data as D
from src import ui

ui.entete("Pilotage du portefeuille de produits digitaux",
          "Quels produits avancent, lesquels dérapent, et où agir en priorité.")
ctx = ui.contexte()
ev, risques = ctx["ev"], ctx["risques"]

nb = ev["statut"].value_counts()
budget, eac = ev["budget"].sum(), ev["eac"].sum()
ecart = eac - budget
retard = int(risques["action_en_retard"].sum())

ui.cartes([
    ("Produits en rouge", str(nb.get("Rouge", 0)), f"sur {len(ev)} produits suivis", ui.COULEURS["Rouge"]),
    ("Produits en orange", str(nb.get("Orange", 0)), "à surveiller", ui.COULEURS["Orange"]),
    ("Produits en vert", str(nb.get("Vert", 0)), "dans les seuils", ui.COULEURS["Vert"]),
    ("Budget total", f"{D.fmt_nb(budget)} M", "M FCFA, enveloppe validée"),
    ("Coût final estimé", f"{D.fmt_nb(eac)} M", f"écart {D.fmt_m(ecart, signe=True)} ({D.fmt_pct(ecart / budget, signe=True)})",
     ui.COULEURS["Rouge"] if ecart > 0 else ui.COULEURS["Vert"]),
    ("Actions en retard", str(retard), "actions correctives échues", ui.COULEURS["Rouge"] if retard else ui.COULEURS["Vert"]),
])

st.markdown("#### Ce qu'il faut retenir")
for m in D.messages_cles(ev, risques):
    st.markdown(f'<div class="message">{m}</div>', unsafe_allow_html=True)

st.markdown("#### Les trois produits à débloquer en priorité")
top = ev[ev["statut"] != "Vert"].sort_values("score_priorite", ascending=False).head(3)
cols = st.columns(3)
for col, (rang, r) in zip(cols, enumerate(top.itertuples(), start=1)):
    with col.container(border=True):
        st.markdown(f"**{rang}. {r.code} – {r.produit}** &nbsp; {ui.badge(r.statut)}", unsafe_allow_html=True)
        st.caption(f"{r.direction} · {r.po} · priorité {r.priorite} · score {D.fmt_nb(r.score_priorite, 1)}/100")
        a, b, c = st.columns(3)
        a.metric("SPI", D.fmt_idx(r.spi))
        b.metric("CPI", D.fmt_idx(r.cpi))
        c.metric("Dépassement", D.fmt_nb(max(0, -r.vac)) + " M")
        st.markdown(f"**Pourquoi :** {r.motif}")
        action = r.action_prioritaire if isinstance(r.action_prioritaire, str) else "Définir un plan d'action"
        st.markdown(f"**Action à arbitrer :** {action}")
with st.expander("Comment le classement est calculé"):
    st.markdown(
        "Score sur 100 : **statut** (rouge 40, orange 20) + **dépassement attendu** (jusqu'à 25, plafonné à 100 M) "
        "+ **priorité métier** (P1 15, P2 7,5) + **risques élevés ouverts** (10 par risque, 20 max). "
        "L'action proposée est celle du risque ouvert le plus critique du produit.")

st.markdown("#### Budget et coût final estimé par produit")
g = ev.sort_values("vac")
fig = go.Figure()
fig.add_bar(y=g["code"] + " " + g["produit"], x=g["budget"], name="Budget", orientation="h",
            marker_color="#C9D3E3")
fig.add_bar(y=g["code"] + " " + g["produit"], x=g["eac"], name="Coût final estimé", orientation="h",
            marker_color=[ui.COULEURS[s] for s in g["statut"]],
            text=[f"+{D.fmt_nb(-v)} M" if v < -0.5 else "" for v in g["vac"]], textposition="outside", cliponaxis=False)
fig.update_layout(barmode="group", xaxis_title="M FCFA", yaxis=dict(autorange="reversed"))
st.plotly_chart(ui.plotly_defaut(fig, 470), width="stretch")

st.markdown("#### Tableau du portefeuille")
tab = ev[["code", "produit", "direction", "priorite", "budget", "reel", "spi", "cpi", "eac", "vac", "statut", "motif"]]
st.dataframe(
    tab.style.map(ui.style_statut, subset=["statut"]),
    hide_index=True, width="stretch",
    column_config={
        "code": "Code", "produit": "Produit", "direction": "Direction", "priorite": "Priorité",
        "budget": st.column_config.NumberColumn("Budget (M)", format="%.0f"),
        "reel": st.column_config.ProgressColumn("Avancement réel", format="percent", min_value=0, max_value=1),
        "spi": st.column_config.NumberColumn("SPI", format="%.2f", help="Indice de performance des délais = EV / PV"),
        "cpi": st.column_config.NumberColumn("CPI", format="%.2f", help="Indice de performance des coûts = EV / AC"),
        "eac": st.column_config.NumberColumn("Coût final estimé (M)", format="%.0f"),
        "vac": st.column_config.NumberColumn("Écart à terminaison (M)", format="%.0f"),
        "statut": "Statut", "motif": "Motif du statut",
    })
