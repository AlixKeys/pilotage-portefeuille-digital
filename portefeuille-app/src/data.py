"""Moteur de calcul du portefeuille : chargement, valeur acquise, statuts,
jalons, risques, prévisions et scénarios.

Ce module ne dépend pas de Streamlit : il peut être testé ou réutilisé seul.
"""
from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FILE = ROOT / "data" / "Portefeuille_Produits_Digitaux_Donnees.xlsx"

# Colonnes attendues dans chaque onglet -> nom interne
COLS: dict[str, dict[str, str]] = {
    "Projets": {
        "Code": "code", "Produit": "produit", "Catégorie": "categorie",
        "Direction porteuse": "direction", "Product Owner": "po",
        "Date début": "debut", "Date fin prévue": "fin_prevue",
        "Budget (M FCFA)": "budget", "Priorité": "priorite",
    },
    "Jalons": {
        "Code produit": "code", "ID jalon": "id", "Jalon": "jalon",
        "Date prévue": "prevue", "Date réelle / estimée": "reelle",
        "Statut": "statut", "Jalon critique": "critique",
    },
    "Suivi_mensuel": {
        "Code produit": "code", "Fin de mois": "mois",
        "Avancement prévu (cumulé)": "prevu", "Avancement réel (cumulé)": "reel",
        "Dépenses cumulées (M FCFA)": "ac",
    },
    "Risques": {
        "Code produit": "code", "ID risque": "id", "Description": "description",
        "Probabilité (1-3)": "proba", "Impact (1-3)": "impact",
        "Responsable": "responsable", "Action corrective": "action",
        "Statut": "statut", "Échéance action": "echeance",
    },
    "KPIs_produit": {
        "Code produit": "code", "Produit": "produit", "Indicateur": "indicateur",
        "Mois": "mois", "Cible": "cible", "Réel": "reel",
    },
}
KEYS = {"Projets": "projets", "Jalons": "jalons", "Suivi_mensuel": "suivi",
        "Risques": "risques", "KPIs_produit": "kpis"}


@dataclass(frozen=True)
class Seuils:
    """Règles écrites du statut Rouge / Orange / Vert."""
    rouge: float = 0.85          # SPI ou CPI sous ce seuil -> Rouge
    orange: float = 0.95         # SPI ou CPI sous ce seuil -> Orange
    jalon_rouge: int = 30        # retard d'un jalon critique (jours) -> Rouge
    jalon_orange: int = 15       # retard d'un jalon critique (jours) -> Orange


# --------------------------------------------------------------------------
# Chargement
# --------------------------------------------------------------------------
def load_data(content: bytes | None = None) -> dict[str, pd.DataFrame]:
    """Lit le classeur (fichier par défaut ou fichier chargé par l'utilisateur)."""
    src = io.BytesIO(content) if content else DEFAULT_FILE
    try:
        xl = pd.ExcelFile(src, engine="openpyxl")
    except Exception as exc:  # fichier corrompu ou pas un .xlsx
        raise ValueError(f"Fichier illisible : {exc}") from exc

    missing = [s for s in COLS if s not in xl.sheet_names]
    if missing:
        raise ValueError("Onglets manquants : " + ", ".join(missing))

    out: dict[str, pd.DataFrame] = {}
    for sheet, mapping in COLS.items():
        df = xl.parse(sheet)
        df.columns = [str(c).strip() for c in df.columns]
        miss = [c for c in mapping if c not in df.columns]
        if miss:
            raise ValueError(f"Onglet « {sheet} » : colonnes manquantes : {', '.join(miss)}")
        df = df[list(mapping)].rename(columns=mapping).dropna(how="all").reset_index(drop=True)
        out[KEYS[sheet]] = df

    p = out["projets"]
    p["code"] = p["code"].astype(str).str.strip()
    for c in ("debut", "fin_prevue"):
        p[c] = pd.to_datetime(p[c])
    p["budget"] = pd.to_numeric(p["budget"])
    p["priorite"] = p["priorite"].astype(str).str.strip()

    j = out["jalons"]
    j["code"] = j["code"].astype(str).str.strip()
    for c in ("prevue", "reelle"):
        j[c] = pd.to_datetime(j[c])
    j["critique"] = j["critique"].astype(str).str.strip().str.lower().isin(["oui", "yes", "true", "1"])
    j["retard_j"] = (j["reelle"] - j["prevue"]).dt.days

    s = out["suivi"]
    s["code"] = s["code"].astype(str).str.strip()
    s["mois"] = pd.to_datetime(s["mois"])
    for c in ("prevu", "reel", "ac"):
        s[c] = pd.to_numeric(s[c])

    r = out["risques"]
    r["code"] = r["code"].astype(str).str.strip()
    r["echeance"] = pd.to_datetime(r["echeance"])
    r["proba"] = pd.to_numeric(r["proba"])
    r["impact"] = pd.to_numeric(r["impact"])
    r["statut"] = r["statut"].astype(str).str.strip()

    k = out["kpis"]
    k["code"] = k["code"].astype(str).str.strip()
    k["mois"] = pd.to_datetime(k["mois"])
    for c in ("cible", "reel"):
        k[c] = pd.to_numeric(k[c])

    return out


def dates_situation(data: dict[str, pd.DataFrame]) -> list[pd.Timestamp]:
    return sorted(pd.Timestamp(d) for d in data["suivi"]["mois"].unique())


# --------------------------------------------------------------------------
# Risques
# --------------------------------------------------------------------------
def niveau_risque(crit: float) -> str:
    if crit >= 6:
        return "Élevé"
    if crit >= 3:
        return "Moyen"
    return "Faible"


def table_risques(data: dict[str, pd.DataFrame], date: pd.Timestamp) -> pd.DataFrame:
    r = data["risques"].copy()
    r["criticite"] = r["proba"] * r["impact"]
    r["niveau"] = r["criticite"].apply(niveau_risque)
    r["action_en_retard"] = (r["statut"] != "Clos") & (r["echeance"] < pd.Timestamp(date))
    r["jours_depassement"] = np.where(
        r["action_en_retard"], (pd.Timestamp(date) - r["echeance"]).dt.days, 0)
    return r.merge(data["projets"][["code", "produit"]], on="code", how="left")


# --------------------------------------------------------------------------
# Valeur acquise et statuts
# --------------------------------------------------------------------------
def _statut(spi: float, cpi: float, retard: float, s: Seuils) -> tuple[str, str]:
    """Renvoie (statut, motif lisible)."""
    motifs_r, motifs_o = [], []
    for nom, v in (("SPI", spi), ("CPI", cpi)):
        if pd.notna(v) and v < s.rouge:
            motifs_r.append(f"{nom} {v:.2f} < {s.rouge:.2f}".replace(".", ","))
        elif pd.notna(v) and v < s.orange:
            motifs_o.append(f"{nom} {v:.2f} < {s.orange:.2f}".replace(".", ","))
    if retard > s.jalon_rouge:
        motifs_r.append(f"jalon critique +{int(retard)} j")
    elif retard > s.jalon_orange:
        motifs_o.append(f"jalon critique +{int(retard)} j")
    if motifs_r:
        return "Rouge", " ; ".join(motifs_r + motifs_o)
    if motifs_o:
        return "Orange", " ; ".join(motifs_o)
    return "Vert", "Dans les seuils"


def evm(data: dict[str, pd.DataFrame], date: pd.Timestamp, seuils: Seuils = Seuils()) -> pd.DataFrame:
    """Indicateurs de valeur acquise par produit à une date de situation."""
    date = pd.Timestamp(date)
    snap = data["suivi"][data["suivi"]["mois"] == date][["code", "prevu", "reel", "ac"]]
    df = data["projets"].merge(snap, on="code", how="inner")

    df["pv"] = df["budget"] * df["prevu"]
    df["ev"] = df["budget"] * df["reel"]
    df["spi"] = np.where(df["pv"] > 0, df["ev"] / df["pv"], np.nan)
    df["cpi"] = np.where(df["ac"] > 0, df["ev"] / df["ac"], np.nan)
    df["sv"] = df["ev"] - df["pv"]
    df["cv"] = df["ev"] - df["ac"]
    # Trois méthodes classiques d'estimation du coût final
    df["eac"] = df["budget"] / df["cpi"]                                   # tendance de coût maintenue
    df["eac_atypique"] = df["ac"] + (df["budget"] - df["ev"])              # écart ponctuel, reste au budget
    df["eac_combine"] = df["ac"] + (df["budget"] - df["ev"]) / (df["cpi"] * df["spi"])  # coût + délais
    df["vac"] = df["budget"] - df["eac"]
    df["etc"] = df["eac"] - df["ac"]
    reste = df["budget"] - df["ac"]
    df["tcpi"] = np.where(reste > 0, (df["budget"] - df["ev"]) / reste, np.nan)

    # Jalons critiques : retard maximal (jours) connu à ce jour
    j = data["jalons"]
    crit = j[j["critique"]].groupby("code")["retard_j"].max().rename("retard_critique")
    df = df.merge(crit, on="code", how="left")
    df["retard_critique"] = df["retard_critique"].fillna(0).clip(lower=0)

    # Risques
    r = table_risques(data, date)
    ouverts = r[r["statut"] != "Clos"]
    df = df.merge(ouverts[ouverts["criticite"] >= 6].groupby("code").size().rename("risques_eleves"),
                  on="code", how="left")
    df = df.merge(r[r["action_en_retard"]].groupby("code").size().rename("actions_en_retard"),
                  on="code", how="left")
    df[["risques_eleves", "actions_en_retard"]] = df[["risques_eleves", "actions_en_retard"]].fillna(0).astype(int)

    st = df.apply(lambda x: _statut(x["spi"], x["cpi"], x["retard_critique"], seuils), axis=1)
    df["statut"] = [a for a, _ in st]
    df["motif"] = [b for _, b in st]

    # Action proposée = action du risque ouvert le plus critique
    top = (ouverts.sort_values(["criticite", "echeance"], ascending=[False, True])
           .drop_duplicates("code")[["code", "action", "id"]]
           .rename(columns={"action": "action_prioritaire", "id": "risque_prioritaire"}))
    df = df.merge(top, on="code", how="left")

    df["score_priorite"] = score_priorite(df)
    df["date"] = date
    return df.sort_values("code").reset_index(drop=True)


def score_priorite(df: pd.DataFrame) -> pd.Series:
    """Score 0-100 pour classer les produits à débloquer.

    40 pts statut (Rouge 40, Orange 20) + 25 pts dépassement attendu (plafonné à 100 M)
    + 15 pts priorité métier (P1 15, P2 7,5) + 20 pts risques élevés ouverts (10 par risque, max 2).
    """
    statut = df["statut"].map({"Rouge": 40, "Orange": 20}).fillna(0)
    depassement = 25 * (-df["vac"]).clip(lower=0, upper=100) / 100
    prio = df["priorite"].map({"P1": 15, "P2": 7.5}).fillna(0)
    risques = 10 * df["risques_eleves"].clip(upper=2)
    return (statut + depassement + prio + risques).round(1)


def historique(data: dict[str, pd.DataFrame], seuils: Seuils = Seuils()) -> pd.DataFrame:
    return pd.concat([evm(data, d, seuils) for d in dates_situation(data)], ignore_index=True)


def portefeuille_mensuel(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Courbe en S du portefeuille : PV, EV, AC cumulés par mois (M FCFA)."""
    s = data["suivi"].merge(data["projets"][["code", "budget"]], on="code")
    s["pv"] = s["budget"] * s["prevu"]
    s["ev"] = s["budget"] * s["reel"]
    g = s.groupby("mois")[["pv", "ev", "ac"]].sum().reset_index()
    g["spi"] = g["ev"] / g["pv"]
    g["cpi"] = g["ev"] / g["ac"]
    return g


# --------------------------------------------------------------------------
# Prévisions de date de fin
# --------------------------------------------------------------------------
def previsions(data: dict[str, pd.DataFrame], date: pd.Timestamp, ev: pd.DataFrame) -> pd.DataFrame:
    """Compare quatre dates de fin : prévue, estimée par les jalons,
    estimée par le SPI, et projetée par la tendance des 3 derniers mois."""
    date = pd.Timestamp(date)
    s = data["suivi"][data["suivi"]["mois"] <= date].sort_values(["code", "mois"])
    j = data["jalons"].sort_values(["code", "prevue"])
    derniers = j.groupby("code").tail(1).set_index("code")

    rows = []
    for _, p in ev.iterrows():
        code = p["code"]
        g = s[s["code"] == code]
        lanc = derniers.loc[code] if code in derniers.index else None
        lance = lanc is not None and str(lanc["statut"]).strip().lower() == "terminé"
        fin_jalons = lanc["reelle"] if lanc is not None else pd.NaT

        duree = (p["fin_prevue"] - p["debut"]).days
        fin_spi = (p["debut"] + pd.Timedelta(days=round(duree / p["spi"]))
                   if pd.notna(p["spi"]) and p["spi"] > 0 else pd.NaT)

        increments = g["reel"].diff().dropna().tail(3)
        vitesse = increments.mean() if len(increments) else np.nan
        if lance or p["reel"] >= 0.999:
            fin_tendance, commentaire = fin_jalons, "Lancé"
        elif pd.notna(vitesse) and vitesse > 0.005:
            mois_restants = (1 - p["reel"]) / vitesse
            fin_tendance = date + pd.Timedelta(days=round(mois_restants * 30.44))
            commentaire = f"{vitesse * 100:.1f} pts/mois".replace(".", ",")
        else:
            fin_tendance, commentaire = pd.NaT, "Avancement à l'arrêt"

        candidats = [d for d in (fin_jalons, fin_spi, fin_tendance) if pd.notna(d)]
        pire = max(candidats) if candidats and not lance else fin_jalons
        rows.append({
            "code": code, "produit": p["produit"], "statut": p["statut"],
            "fin_prevue": p["fin_prevue"], "fin_jalons": fin_jalons,
            "fin_spi": fin_spi if not lance else pd.NaT,
            "fin_tendance": fin_tendance, "vitesse": commentaire, "lance": lance,
            "pire_cas": pire,
            "glissement_j": (pire - p["fin_prevue"]).days if pd.notna(pire) else np.nan,
        })
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# Simulation d'arbitrage
# --------------------------------------------------------------------------
def simuler(ev: pd.DataFrame, suspendus: list[str], cpi_cibles: dict[str, float]) -> pd.DataFrame:
    """Recalcule le coût final estimé selon les décisions simulées.

    - Produit suspendu : on arrête les dépenses, coût final = dépenses déjà engagées.
    - CPI cible : le reste à faire (budget - EV) est réalisé avec ce CPI.
    """
    df = ev[["code", "produit", "statut", "budget", "ev", "ac", "cpi", "eac"]].copy()
    df["eac_simule"] = df["eac"]
    for code, cible in cpi_cibles.items():
        m = df["code"] == code
        if cible and cible > 0:
            df.loc[m, "eac_simule"] = df.loc[m, "ac"] + (df.loc[m, "budget"] - df.loc[m, "ev"]) / cible
    m = df["code"].isin(suspendus)
    df.loc[m, "eac_simule"] = df.loc[m, "ac"]
    df["decision"] = np.where(m, "Suspendu",
                              np.where(df["code"].isin(list(cpi_cibles)), "Plan de redressement", "—"))
    return df


# --------------------------------------------------------------------------
# Messages clés (utilisés par la synthèse et la note de comité)
# --------------------------------------------------------------------------
def messages_cles(ev: pd.DataFrame, risques: pd.DataFrame) -> list[str]:
    msgs = []
    rouges = ev[ev["statut"] == "Rouge"]
    budget_total = ev["budget"].sum()
    dep_total = (-ev["vac"]).clip(lower=0).sum()
    if len(rouges):
        part_budget = rouges["budget"].sum() / budget_total
        part_dep = (-rouges["vac"]).clip(lower=0).sum() / dep_total if dep_total else 0
        msgs.append(
            f"{pluriel(len(rouges), 'produit en rouge', 'produits en rouge')} ({', '.join(rouges['code'])}) "
            f"{'représente' if len(rouges) == 1 else 'représentent'} "
            f"{part_budget:.0%} du budget mais {part_dep:.0%} du dépassement attendu."
            .replace("%", " %"))
    ecart = ev["eac"].sum() - budget_total
    msgs.append(
        f"Au rythme actuel, le portefeuille coûterait {fmt_m(ev['eac'].sum())} pour un budget de "
        f"{fmt_m(budget_total)}, soit {fmt_m(ecart, signe=True)} "
        f"({fmt_pct(ecart / budget_total, signe=True)}).")
    retard = risques[risques["action_en_retard"]]
    if len(retard):
        codes = sorted(retard["code"].unique())
        rouges_concernes = [c for c in codes if c in set(rouges["code"])]
        txt = (f"{pluriel(len(retard), 'action corrective a', 'actions correctives ont')} dépassé leur échéance "
               f"({', '.join(retard['id'])})")
        if rouges_concernes and len(rouges_concernes) == len(codes):
            txt += " et concernent toutes des produits en rouge : le suivi des actions est un levier immédiat."
        else:
            txt += "."
        msgs.append(txt)
    verts = ev[ev["statut"] == "Vert"]
    if len(verts):
        msgs.append(f"{pluriel(len(verts), 'produit est', 'produits sont')} dans les seuils ({', '.join(verts['code'])}) "
                    "et ne demandent pas d'arbitrage ce mois-ci.")
    return msgs


# --------------------------------------------------------------------------
# Formatage (français)
# --------------------------------------------------------------------------
def pluriel(n: int, sing: str, plur: str) -> str:
    return f"{n} {sing if n == 1 else plur}"


def fmt_nb(x: float, dec: int = 0) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "—"
    s = f"{x:,.{dec}f}".replace(",", " ").replace(".", ",")
    return s


def fmt_m(x: float, signe: bool = False) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "—"
    txt = fmt_nb(abs(x))
    if signe:
        txt = ("+" if x > 0 else "−" if x < 0 else "") + txt
    elif x < 0:
        txt = "−" + txt
    return f"{txt} M FCFA"


def fmt_pct(x: float, dec: int = 1, signe: bool = False) -> str:
    if x is None or pd.isna(x):
        return "—"
    txt = f"{x * 100:{'+' if signe else ''}.{dec}f}".replace(".", ",").replace("-", "−")
    return f"{txt} %"


def fmt_idx(x: float) -> str:
    return "—" if x is None or pd.isna(x) else f"{x:.2f}".replace(".", ",")


def fmt_date(d) -> str:
    return "—" if d is None or pd.isna(d) else pd.Timestamp(d).strftime("%d/%m/%Y")
