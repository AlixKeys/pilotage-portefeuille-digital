import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src import data as D
from src import ui

ui.entete("Prévisions de fin et de coût",
          "Trois méthodes indépendantes : quand elles divergent, c'est un signal à creuser.")
ctx = ui.contexte()
ev, prev = ctx["ev"], ctx["prev"]

with st.expander("Les trois méthodes", expanded=False):
    st.markdown(
        "- **Jalons** : date de lancement estimée par l'équipe projet (vision « terrain »).\n"
        "- **SPI** : durée prévue ÷ SPI. Si le projet avance à 80 % du rythme prévu, il durera 1/0,8 = 1,25 fois plus longtemps.\n"
        "- **Tendance** : on prolonge la vitesse d'avancement des 3 derniers mois jusqu'à 100 %.\n\n"
        "Le **scénario prudent** retient la date la plus tardive des trois.")

en_cours = prev[~prev["lance"]]
glisse = en_cours[en_cours["glissement_j"] > 0]
ui.cartes([
    ("Produits lancés", str(int(prev["lance"].sum())), f"sur {len(prev)}", ui.COULEURS["Vert"]),
    ("Lancements qui glissent", str(len(glisse)), "scénario prudent vs date prévue", ui.COULEURS["Rouge"]),
    ("Glissement maximal", f"{D.fmt_nb(en_cours['glissement_j'].max())} j",
     en_cours.loc[en_cours["glissement_j"].idxmax(), "produit"] if len(en_cours) else ""),
    ("Coût final (prudent)", D.fmt_m(ev["eac_combine"].sum()), "méthode coût × délais", ui.COULEURS["Orange"]),
])

# --------------------------------------------------------- Dates
st.markdown("#### Date de lancement selon chaque méthode")
p = en_cours.sort_values("fin_prevue")
lib = p["code"] + " " + p["produit"]
fig = go.Figure()
styles = [("fin_prevue", "Prévue", "line-ns", ui.BLEU, 16), ("fin_jalons", "Jalons", "circle", "#1F6FEB", 11),
          ("fin_spi", "SPI", "square", ui.COULEURS["Orange"], 10), ("fin_tendance", "Tendance 3 mois", "diamond", "#7B61FF", 11)]
for col, nom, symb, coul, taille in styles:
    fig.add_scatter(x=p[col], y=lib, mode="markers", name=nom,
                    marker=dict(symbol=symb, size=taille, color=coul, line=dict(width=2 if symb == "line-ns" else 0, color=coul)),
                    hovertemplate=f"{nom} : %{{x|%d/%m/%Y}}<extra></extra>")
for x in p.itertuples():
    dates = [d for d in (x.fin_prevue, x.fin_jalons, x.fin_spi, x.fin_tendance) if pd.notna(d)]
    fig.add_shape(type="line", x0=min(dates), x1=max(dates), y0=f"{x.code} {x.produit}", y1=f"{x.code} {x.produit}",
                  line=dict(color="#C9D3E3", width=6), layer="below")
ui.ligne_date(fig, ctx["date"])
fig.update_layout(xaxis=dict(type="date", title="", tickformat="%m/%Y"), yaxis=dict(title="", autorange="reversed"))
st.plotly_chart(ui.plotly_defaut(fig, 420), width="stretch")

t = p[["code", "produit", "statut", "fin_prevue", "fin_jalons", "fin_spi", "fin_tendance", "vitesse", "pire_cas", "glissement_j"]]
st.dataframe(
    t.style.map(ui.style_statut, subset=["statut"]), hide_index=True, width="stretch",
    column_config={
        "code": "Code", "produit": "Produit", "statut": "Statut",
        **{c: st.column_config.DateColumn(l, format="DD/MM/YYYY") for c, l in [
            ("fin_prevue", "Prévue"), ("fin_jalons", "Jalons"), ("fin_spi", "SPI"),
            ("fin_tendance", "Tendance"), ("pire_cas", "Scénario prudent")]},
        "vitesse": "Vitesse récente", "glissement_j": st.column_config.NumberColumn("Glissement (j)"),
    })

# Signaux de divergence
alertes, plus_tot = [], []
for x in p.itertuples():
    if pd.notna(x.fin_tendance) and pd.notna(x.fin_jalons) and (x.fin_tendance - x.fin_jalons).days > 45:
        alertes.append(f"<b>{x.code} – {x.produit}</b> : la tendance réelle mène au {D.fmt_date(x.fin_tendance)}, "
                       f"soit {(x.fin_tendance - x.fin_jalons).days} jours après la date annoncée par l'équipe "
                       f"({D.fmt_date(x.fin_jalons)}). L'estimation du planning paraît optimiste.")
    if pd.notna(x.fin_tendance) and pd.notna(x.fin_jalons) and (x.fin_jalons - x.fin_tendance).days > 45:
        plus_tot.append(f"{x.code} ({D.fmt_date(x.fin_tendance)} contre {D.fmt_date(x.fin_jalons)})")
if plus_tot:
    alertes.append("<b>Rythme récent plus rapide que le planning</b> pour " + ", ".join(plus_tot) +
                   ". Soit le planning est prudent, soit l'avancement déclaré est surestimé : "
                   "à vérifier en revue de projet avant d'annoncer une date plus tôt.")
if alertes:
    st.markdown("#### Signaux à creuser")
    for a in alertes:
        st.markdown(f'<div class="message">{a}</div>', unsafe_allow_html=True)

# --------------------------------------------------------- Coûts
st.markdown("#### Coût final estimé selon trois hypothèses")
c = ev.sort_values("vac")
fig = go.Figure()
fig.add_bar(x=c["code"], y=c["budget"], name="Budget", marker_color="#C9D3E3")
for col, nom, coul in [("eac_atypique", "Écart ponctuel (optimiste)", "#8FB3F0"),
                       ("eac", "Tendance de coût (BAC / CPI)", "#1F6FEB"),
                       ("eac_combine", "Coût × délais (prudent)", ui.COULEURS["Rouge"])]:
    fig.add_bar(x=c["code"], y=c[col], name=nom, marker_color=coul)
fig.update_layout(barmode="group", yaxis_title="M FCFA", hovermode="x unified")
st.plotly_chart(ui.plotly_defaut(fig, 400), width="stretch")
tot = {k: ev[k].sum() for k in ("budget", "eac_atypique", "eac", "eac_combine")}
st.markdown(
    f"Selon l'hypothèse retenue, le portefeuille coûterait entre **{D.fmt_m(tot['eac_atypique'])}** "
    f"et **{D.fmt_m(tot['eac_combine'])}**, pour un budget de {D.fmt_m(tot['budget'])}. "
    f"L'hypothèse centrale (tendance de coût) donne **{D.fmt_m(tot['eac'])}**, soit un dépassement de "
    f"{D.fmt_m(tot['eac'] - tot['budget'])}. Prévoir une réserve d'au moins ce montant, ou arbitrer "
    "(page *Simulation d'arbitrage*).")
