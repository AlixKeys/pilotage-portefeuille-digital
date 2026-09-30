import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src import data as D
from src import ui

ui.entete("Planning & jalons", "Dates prévues contre dates réelles ou estimées, jalon par jalon.")
ctx = ui.contexte()
ev, data, seuils = ctx["ev"], ctx["data"], ctx["seuils"]
j = data["jalons"].merge(ev[["code", "produit", "statut"]].rename(columns={"statut": "statut_produit"}), on="code")

en_retard = j[j["retard_j"] > 0]
crit = j[j["critique"] & (j["retard_j"] > seuils.jalon_rouge)]
ui.cartes([
    ("Jalons suivis", str(len(j)), f"{int((j['statut'] == 'Terminé').sum())} terminés"),
    ("Jalons en retard", str(len(en_retard)), "date réelle ou estimée > date prévue", ui.COULEURS["Orange"]),
    ("Jalons critiques > seuil", str(len(crit)), f"retard > {seuils.jalon_rouge} jours", ui.COULEURS["Rouge"]),
    ("Retard moyen des lancements", f"{D.fmt_nb(j[j['jalon'] == 'Lancement']['retard_j'].clip(lower=0).mean())} j",
     "sur les 10 produits"),
])

# --------------------------------------------------------- Diagramme de Gantt
st.markdown("#### Calendrier : prévu contre estimé")
p = ev[["code", "produit", "debut", "fin_prevue", "statut"]].merge(
    j[j["jalon"] == "Lancement"][["code", "reelle"]].rename(columns={"reelle": "fin_estimee"}), on="code")
p = p.sort_values("debut", ascending=False)
lib = p["code"] + " " + p["produit"]
fig = go.Figure()
fig.add_bar(y=lib, x=(p["fin_prevue"] - p["debut"]).dt.days * 86400000, base=p["debut"], orientation="h",
            name="Prévu", marker_color="#C9D3E3", width=0.35, offset=-0.38,
            hovertemplate="%{y}<br>Prévu : %{base|%d/%m/%Y} → %{customdata|%d/%m/%Y}<extra></extra>",
            customdata=p["fin_prevue"])
fig.add_bar(y=lib, x=(p["fin_estimee"] - p["debut"]).dt.days * 86400000, base=p["debut"], orientation="h",
            name="Réel / estimé", marker_color=[ui.COULEURS[s] for s in p["statut"]], width=0.35, offset=0.02,
            hovertemplate="%{y}<br>Estimé : %{base|%d/%m/%Y} → %{customdata|%d/%m/%Y}<extra></extra>",
            customdata=p["fin_estimee"])
jj = j.merge(p[["code"]], on="code")
jj = jj[jj["critique"]]
fig.add_scatter(y=jj["code"] + " " + jj["produit"], x=jj["reelle"], mode="markers", name="Jalon critique",
                marker=dict(symbol="diamond", size=9, color=ui.BLEU, line=dict(color="white", width=1)),
                customdata=jj[["jalon", "retard_j"]],
                hovertemplate="%{customdata[0]} : %{x|%d/%m/%Y} (retard %{customdata[1]} j)<extra></extra>")
fig.update_layout(barmode="overlay", xaxis=dict(type="date", title="", tickformat="%m/%Y", dtick="M2"), yaxis=dict(title=""))
ui.ligne_date(fig, ctx["date"])
st.plotly_chart(ui.plotly_defaut(fig, 520), width="stretch")

# --------------------------------------------------------- Retards par étape
st.markdown("#### À quelle étape les projets dérapent-ils ?")
ordre = ["Cadrage", "Conception", "Développement", "Recette", "Lancement"]
pivot = j.pivot_table(index="code", columns="jalon", values="retard_j").reindex(columns=ordre)
pivot.index = [f"{c} {data['projets'].set_index('code').loc[c, 'produit']}" for c in pivot.index]
fig = go.Figure(go.Heatmap(z=pivot.values, x=pivot.columns, y=pivot.index, colorscale=[
    [0, "#2E9E5B"], [0.15, "#F4F6FA"], [0.45, "#E8A317"], [1, "#D64545"]],
    zmin=-10, zmax=max(60, float(pivot.max().max())), text=pivot.values.astype(int), texttemplate="%{text} j",
    colorbar=dict(title="Retard (j)")))
fig.update_layout(yaxis=dict(autorange="reversed"))
st.plotly_chart(ui.plotly_defaut(fig, 440), width="stretch")
glisse = pivot.diff(axis=1).clip(lower=0).sum().drop("Cadrage")
st.caption(f"Le retard s'accumule surtout à l'étape **{glisse.idxmax()}** "
           f"({D.fmt_nb(glisse.max())} jours de retard supplémentaires cumulés sur le portefeuille). "
           "C'est l'étape à outiller en priorité : découpage plus fin, revues de sprint, disponibilité des équipes.")

# --------------------------------------------------------- Liste des jalons en retard
st.markdown("#### Jalons en retard")
seul_crit = st.toggle("Afficher seulement les jalons critiques", value=False)
t = en_retard[en_retard["critique"]] if seul_crit else en_retard
st.dataframe(
    t.sort_values("retard_j", ascending=False)[
        ["id", "produit", "jalon", "prevue", "reelle", "retard_j", "statut", "critique", "statut_produit"]]
    .style.map(ui.style_statut, subset=["statut_produit"]),
    hide_index=True, width="stretch",
    column_config={
        "id": "Jalon", "produit": "Produit", "jalon": "Étape",
        "prevue": st.column_config.DateColumn("Prévu", format="DD/MM/YYYY"),
        "reelle": st.column_config.DateColumn("Réel / estimé", format="DD/MM/YYYY"),
        "retard_j": st.column_config.NumberColumn("Retard (jours)"),
        "statut": "Statut du jalon", "critique": st.column_config.CheckboxColumn("Critique"),
        "statut_produit": "Statut produit",
    })
