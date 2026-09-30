# Pilotage d'un portefeuille de produits digitaux

Application Streamlit qui aide une direction générale à répondre chaque mois à trois questions :
**quels produits avancent, lesquels dérapent, et où agir en priorité.**

> Projet de démonstration réalisé avec des **données synthétiques** d'une entreprise fictive (10 produits digitaux,
> 2 860 M FCFA de budget).

![Aperçu](docs/apercu.png)

## Ce que fait l'application

| Page | Question à laquelle elle répond |
|---|---|
| **Synthèse** | Combien de produits en rouge, quel dépassement attendu, quels 3 produits débloquer en premier ? |
| **Valeur acquise** | Chaque produit avance-t-il au rythme et au coût prévus ? (SPI, CPI, courbe en S, TCPI) |
| **Planning & jalons** | Où en est le calendrier, et à quelle étape les projets dérapent-ils ? |
| **Risques** | Quels risques sont critiques, et quelles actions correctives sont en retard ? |
| **KPIs produit** | Les produits lancés atteignent-ils leurs objectifs d'adoption ? |
| **Prévisions** | Quand chaque produit sera-t-il vraiment lancé, et combien coûtera le portefeuille ? (3 méthodes) |
| **Simulation d'arbitrage** | Que se passe-t-il si l'on suspend un produit ou impose un plan de redressement ? |
| **Note de comité** | Note de synthèse générée automatiquement, téléchargeable en Word, Markdown et Excel |
| **Données & méthode** | Formules, règles de statut, données brutes, chargement de vos propres données |

Les règles de statut (seuils SPI/CPI, retard des jalons critiques) se règlent dans la barre latérale, et l'on peut
revenir sur n'importe quel mois passé.

## Méthode

- **Valeur acquise** : PV = budget × avancement prévu ; EV = budget × avancement réel ; AC = dépenses cumulées.
- **SPI = EV / PV** (délais), **CPI = EV / AC** (coûts), **EAC = budget / CPI** (coût final estimé),
  **VAC = budget − EAC**, **TCPI = (budget − EV) / (budget − AC)**.
- **Statut** : rouge si SPI ou CPI < 0,85 ou jalon critique en retard de plus de 30 jours ; orange si < 0,95 ou
  plus de 15 jours ; vert sinon.
- **Risques** : criticité = probabilité × impact (1 à 9), élevé à partir de 6.
- **Priorisation** : score sur 100 (statut 40, dépassement 25, priorité métier 15, risques élevés 20).
- **Prévisions de fin** : date estimée par les jalons, par le SPI (durée prévue ÷ SPI) et par la tendance
  d'avancement des 3 derniers mois.

## Lancer l'application en local (Windows)

```powershell
cd portefeuille-app
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

L'application s'ouvre sur http://localhost:8501.

## Déployer

### Option 1 — Render (depuis GitHub)

1. Créez un dépôt GitHub et poussez-y tout le dossier.
2. Sur [render.com](https://render.com) : **New → Blueprint**, choisissez le dépôt. Le fichier `render.yaml`
   configure tout automatiquement.
3. Sans Blueprint : **New → Web Service**, puis
   - Build command : `pip install -r requirements.txt`
   - Start command : `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`

En offre gratuite, le service se met en veille après 15 minutes d'inactivité : le premier chargement peut prendre
environ une minute.

### Option 2 — Streamlit Community Cloud (gratuit, le plus simple)

Sur [share.streamlit.io](https://share.streamlit.io), connectez votre compte GitHub, choisissez le dépôt et le
fichier `app.py`, puis cliquez sur **Deploy**.

## Utiliser vos propres données

Chargez un fichier `.xlsx` depuis la barre latérale. Il doit contenir les onglets `Projets`, `Jalons`,
`Suivi_mensuel`, `Risques` et `KPIs_produit`, avec les mêmes colonnes que le fichier d'exemple du dossier `data/`
(téléchargeable depuis la page *Données & méthode*).

## Structure

```
app.py              point d'entrée : barre latérale, calculs, navigation
src/data.py         moteur de calcul (indépendant de Streamlit)
src/note.py         génération de la note de comité (Word, Markdown, Excel)
src/ui.py           éléments d'interface partagés
views/              une page par fichier
data/               fichier Excel d'exemple
```

## Stack

Python · Streamlit · pandas · Plotly · openpyxl · python-docx
