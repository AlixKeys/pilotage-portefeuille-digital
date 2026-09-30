import streamlit as st

from src import data as D
from src import note as N
from src import ui

ui.entete("Note de comité", "Générée automatiquement à partir des données du mois. À relire et compléter avant envoi.")
ctx = ui.contexte()
c = N.contenu(ctx)
md = N.markdown(c)

c1, c2, c3 = st.columns(3)
nom = f"note_comite_{ctx['date']:%Y_%m}"
c1.download_button("Télécharger en Word", N.word(c), f"{nom}.docx",
                   "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                   icon=":material/description:", width="stretch")
c2.download_button("Télécharger en Markdown", md.encode("utf-8"), f"{nom}.md", "text/markdown",
                   icon=":material/code:", width="stretch")
c3.download_button("Exporter les calculs (Excel)", N.excel(ctx), f"calculs_portefeuille_{ctx['date']:%Y_%m}.xlsx",
                   "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                   icon=":material/table:", width="stretch")

with st.container(border=True):
    st.markdown(md)
