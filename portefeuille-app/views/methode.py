import streamlit as st

from src import data as D
from src import ui

ui.entete("Données & méthode", "Tout ce qu'il faut pour vérifier les calculs ou réutiliser l'outil.")
ctx = ui.contexte()
s = ctx["seuils"]

st.markdown("#### Contexte")
st.markdown(
    "Une direction générale suit **10 produits digitaux** d'une entreprise fictive. Chaque mois, l'analyste du PMO "
    "doit dire quels produits avancent, lesquels dérapent, et où agir. Les données sont **synthétiques**.")

st.markdown("#### Méthode")
st.markdown(f"""
1. **Valeur acquise** à la date de situation : PV = budget × avancement prévu ; EV = budget × avancement réel ;
   AC = dépenses cumulées.
2. **Indicateurs** : SPI = EV / PV (délais) ; CPI = EV / AC (coûts) ; coût final estimé EAC = budget / CPI ;
   écart à terminaison VAC = budget − EAC ; TCPI = (budget − EV) / (budget − AC).
3. **Statut** (règles modifiables dans la barre latérale) :
   - **Rouge** si SPI ou CPI < {D.fmt_idx(s.rouge)}, ou si un jalon critique a plus de {s.jalon_rouge} jours de retard ;
   - **Orange** si SPI ou CPI < {D.fmt_idx(s.orange)}, ou si un jalon critique a plus de {s.jalon_orange} jours de retard ;
   - **Vert** sinon.
4. **Risques** : criticité = probabilité × impact (1 à 9) ; élevé à partir de 6. Une action est en retard si son
   échéance est dépassée et que le risque n'est pas clos.
5. **Priorisation** : score sur 100 combinant statut, dépassement attendu, priorité métier et risques élevés.
6. **Prévisions** : dates de fin selon les jalons, le SPI et la tendance des 3 derniers mois ; coût final selon
   trois hypothèses (écart ponctuel, tendance de coût, coût × délais).
""")
st.info("Les jalons reflètent la dernière situation connue : quand vous choisissez un mois passé, les indicateurs "
        "financiers sont recalculés à cette date, mais les retards de jalons restent ceux d'aujourd'hui.")

st.markdown("#### Réutiliser l'outil avec vos données")
st.markdown("Chargez un fichier Excel dans la barre latérale. Il doit contenir ces onglets et ces colonnes :")
for onglet, cols in D.COLS.items():
    st.markdown(f"- **{onglet}** : " + ", ".join(f"`{c}`" for c in cols))
st.download_button("Télécharger le fichier d'exemple", D.DEFAULT_FILE.read_bytes(),
                   "Portefeuille_Produits_Digitaux_Donnees.xlsx", icon=":material/download:")

st.markdown("#### Données brutes")
data = ctx["data"]
onglets = st.tabs(["Projets", "Jalons", "Suivi mensuel", "Risques", "KPIs produit"])
for tab, cle in zip(onglets, ["projets", "jalons", "suivi", "risques", "kpis"]):
    tab.dataframe(data[cle], hide_index=True, width="stretch")
