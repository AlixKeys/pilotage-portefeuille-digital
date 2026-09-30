"""Pilotage d'un portefeuille de produits digitaux — application Streamlit.

Lancer en local :  streamlit run app.py
"""
import pandas as pd
import streamlit as st

from src import data as D

st.set_page_config(page_title="Pilotage du portefeuille digital", page_icon="📊",
                   layout="wide", initial_sidebar_state="expanded")


@st.cache_data(show_spinner=False)
def charger(contenu: bytes | None):
    return D.load_data(contenu)


# ---------------------------------------------------------------- Barre latérale
with st.sidebar:
    st.markdown("### 📊 Portefeuille digital")
    fichier = st.file_uploader("Charger vos propres données (.xlsx, même structure)", type=["xlsx"])
    try:
        data = charger(fichier.getvalue() if fichier else None)
        if fichier:
            st.success("Fichier chargé.")
    except ValueError as err:
        st.error(f"{err}\n\nLes données d'exemple sont affichées.")
        data = charger(None)

    dates = D.dates_situation(data)
    mois_fr = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août",
               "Septembre", "Octobre", "Novembre", "Décembre"]
    date = st.selectbox("Date de situation", dates, index=len(dates) - 1,
                        format_func=lambda d: f"Fin {mois_fr[d.month - 1].lower()} {d.year}",
                        help="Revenez sur un mois passé pour voir comment la situation a évolué.")

    with st.expander("Règles de statut", expanded=False):
        rouge = st.slider("SPI ou CPI sous… → Rouge", 0.70, 0.95, 0.85, 0.01)
        orange = st.slider("SPI ou CPI sous… → Orange", 0.80, 1.00, 0.95, 0.01)
        j_rouge = st.number_input("Retard jalon critique (jours) → Rouge", 0, 180, 30, 5)
        j_orange = st.number_input("Retard jalon critique (jours) → Orange", 0, 180, 15, 5)
        if orange < rouge:
            st.warning("Le seuil orange doit être au-dessus du seuil rouge : ils ont été inversés.")
            rouge, orange = orange, rouge
        if j_orange > j_rouge:
            j_rouge, j_orange = j_orange, j_rouge

    st.caption("Projet de démonstration — données synthétiques d'une entreprise fictive.")

seuils = D.Seuils(rouge=rouge, orange=orange, jalon_rouge=int(j_rouge), jalon_orange=int(j_orange))
ev = D.evm(data, date, seuils)
st.session_state["ctx"] = {
    "data": data, "date": pd.Timestamp(date), "seuils": seuils, "ev": ev,
    "risques": D.table_risques(data, date),
    "prev": D.previsions(data, date, ev),
}

# ---------------------------------------------------------------- Navigation
pages = {
    "Pilotage": [
        st.Page("views/synthese.py", title="Synthèse", icon=":material/dashboard:", default=True),
        st.Page("views/valeur_acquise.py", title="Valeur acquise", icon=":material/trending_up:"),
        st.Page("views/planning.py", title="Planning & jalons", icon=":material/calendar_month:"),
        st.Page("views/risques.py", title="Risques", icon=":material/warning:"),
        st.Page("views/kpis.py", title="KPIs produit", icon=":material/monitoring:"),
    ],
    "Aide à la décision": [
        st.Page("views/previsions.py", title="Prévisions", icon=":material/query_stats:"),
        st.Page("views/simulation.py", title="Simulation d'arbitrage", icon=":material/tune:"),
        st.Page("views/note.py", title="Note de comité", icon=":material/description:"),
    ],
    "Référence": [
        st.Page("views/methode.py", title="Données & méthode", icon=":material/database:"),
    ],
}
st.navigation(pages).run()
