"""SYNTHEA - enrichissement de la base de connaissance depuis l interface.

Les 57 CSV de data/lexicons/ ne sont pas figes : ce module permet de les
completer sans toucher au code ni relancer un script.

  - ajouter un terme metier dans n importe quel lexique sectoriel
  - ajouter un metier au referentiel
  - ajouter une formule, un sigle, une entree multilingue
  - importer un CSV entier et le fusionner (sans doublon)
  - creer un nouveau lexique sectoriel
  - regenerer toute la base a partir des scripts build_0*.py
  - sauvegarder et telecharger l ensemble

Chaque ecriture fait d abord une copie de securite dans data/lexicons/_backup/,
puis vide les caches de lecture pour que l application voie immediatement les
nouvelles entrees.
"""
from __future__ import annotations

import csv
import io
import os
import shutil
import zipfile

from . import lexicons, utils

BACKUP = os.path.join(utils.LEXICONS, "_backup")
METIERS = "00_metiers_referentiel.csv"


# --------------------------------------------------------------- caches
def recharger() -> None:
    """Vide tous les caches de lecture de core.lexicons."""
    for nom in dir(lexicons):
        fn = getattr(lexicons, nom)
        if callable(fn) and hasattr(fn, "cache_clear"):
            try:
                fn.cache_clear()
            except Exception:
                pass


# --------------------------------------------------------------- lecture
def lire(fichier: str) -> tuple[list[str], list[dict]]:
    chemin = os.path.join(utils.LEXICONS, fichier)
    if not os.path.exists(chemin):
        return [], []
    with open(chemin, newline="", encoding="utf-8") as fh:
        lecteur = csv.DictReader(fh)
        return list(lecteur.fieldnames or []), [dict(r) for r in lecteur]


def fichiers() -> list[str]:
    return lexicons.catalogue()


def fichiers_sectoriels() -> list[str]:
    return [f for f in fichiers() if "_lex_" in f]


def colonnes(fichier: str) -> list[str]:
    entetes, _ = lire(fichier)
    return entetes


# -------------------------------------------------------------- ecriture
def _sauvegarder(fichier: str) -> str:
    os.makedirs(BACKUP, exist_ok=True)
    src = os.path.join(utils.LEXICONS, fichier)
    if not os.path.exists(src):
        return ""
    dst = os.path.join(BACKUP, f"{os.path.splitext(fichier)[0]}-{utils.stamp()}.csv")
    shutil.copy2(src, dst)
    return dst


def _ecrire(fichier: str, entetes: list[str], lignes: list[dict]) -> None:
    chemin = os.path.join(utils.LEXICONS, fichier)
    tmp = chemin + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=entetes, quoting=csv.QUOTE_MINIMAL,
                           extrasaction="ignore")
        w.writeheader()
        for r in lignes:
            w.writerow({k: r.get(k, "") for k in entetes})
    os.replace(tmp, chemin)
    recharger()


def _cle(ligne: dict, entetes: list[str]) -> str:
    """Cle de dedoublonnage : premiere colonne porteuse de la ligne."""
    for c in ("terme_fr", "code", "sigle", "fr", "cle", "nom", "pays",
              "expression", "verbe_fr", "ht", "mot", "terme"):
        if c in entetes and str(ligne.get(c, "")).strip():
            return utils.normalize(str(ligne[c]))
    return utils.normalize(" ".join(str(ligne.get(c, "")) for c in entetes[:2]))


def ajouter_lignes(fichier: str, nouvelles: list[dict],
                   remplacer_doublons: bool = False) -> dict:
    """Ajoute des lignes a un CSV existant, en evitant les doublons."""
    entetes, lignes = lire(fichier)
    if not entetes:
        return {"ok": False, "message": f"fichier introuvable ou vide : {fichier}"}

    index = {_cle(l, entetes): i for i, l in enumerate(lignes)}
    ajoutees = remplacees = ignorees = 0
    for n in nouvelles:
        n = {k: ("" if v is None else str(v).strip()) for k, v in n.items()}
        if not any(n.get(c) for c in entetes):
            continue
        k = _cle(n, entetes)
        if k and k in index:
            if remplacer_doublons:
                lignes[index[k]] = {**lignes[index[k]], **{c: n.get(c, "") for c in entetes
                                                           if n.get(c)}}
                remplacees += 1
            else:
                ignorees += 1
            continue
        lignes.append(n)
        index[k] = len(lignes) - 1
        ajoutees += 1

    if not (ajoutees or remplacees):
        return {"ok": False, "message": "aucune ligne nouvelle : tout etait deja present",
                "ajoutees": 0, "remplacees": 0, "ignorees": ignorees}

    copie = _sauvegarder(fichier)
    _ecrire(fichier, entetes, lignes)
    return {
        "ok": True,
        "fichier": fichier,
        "ajoutees": ajoutees,
        "remplacees": remplacees,
        "ignorees": ignorees,
        "total": len(lignes),
        "sauvegarde": os.path.basename(copie) if copie else "",
        "message": (f"{ajoutees} ligne(s) ajoutee(s)"
                    + (f", {remplacees} mise(s) a jour" if remplacees else "")
                    + (f", {ignorees} doublon(s) ignore(s)" if ignorees else "")
                    + f". Le fichier compte maintenant {len(lignes)} lignes."),
    }


def supprimer_ligne(fichier: str, valeur_cle: str) -> dict:
    entetes, lignes = lire(fichier)
    if not entetes:
        return {"ok": False, "message": "fichier introuvable"}
    cible = utils.normalize(valeur_cle)
    restantes = [l for l in lignes if _cle(l, entetes) != cible]
    if len(restantes) == len(lignes):
        return {"ok": False, "message": f"« {valeur_cle} » introuvable dans {fichier}"}
    _sauvegarder(fichier)
    _ecrire(fichier, entetes, restantes)
    return {"ok": True, "message": f"« {valeur_cle} » supprime. "
                                   f"{len(restantes)} lignes restantes."}


# ----------------------------------------------------- ajouts specialises
def ajouter_terme(fichier: str, terme: str, registre: str, definition: str,
                  en: str = "", es: str = "", pt: str = "", ht: str = "",
                  metiers: str = "") -> dict:
    entetes, _ = lire(fichier)
    secteur = ""
    _, lignes = lire(fichier)
    if lignes:
        secteur = lignes[0].get("secteur", "")
    return ajouter_lignes(fichier, [{
        "terme_fr": terme, "registre": registre or "technique",
        "definition_fr": definition, "en": en, "es": es, "pt": pt, "ht": ht,
        "secteur": secteur, "metiers": metiers,
    }])


def ajouter_metier(metier: str, secteur: str, famille: str = "",
                   en: str = "", es: str = "", pt: str = "", ht: str = "",
                   mots_cles: str = "") -> dict:
    _, lignes = lire(METIERS)
    codes = [l.get("code", "") for l in lignes if l.get("code", "").startswith("MET")]
    num = max((int(c[3:]) for c in codes if c[3:].isdigit()), default=0) + 1
    return ajouter_lignes(METIERS, [{
        "code": f"MET{num:03d}", "metier_fr": metier, "secteur": secteur,
        "famille": famille, "en": en, "es": es, "pt": pt, "ht": ht,
        "mots_cles": mots_cles,
    }])


def creer_lexique(nom_secteur: str, termes: list[dict] | None = None) -> dict:
    """Cree un nouveau lexique sectoriel vide ou pre-rempli."""
    slug = utils.slugify(nom_secteur).replace("-", "_")
    if not slug:
        return {"ok": False, "message": "nom de secteur vide"}
    existants = [f for f in fichiers() if "_lex_" in f]
    numeros = []
    for f in existants:
        tete = f.split("_", 1)[0]
        if tete.isdigit():
            numeros.append(int(tete))
    numero = max(numeros, default=0) + 1
    fichier = f"{numero:02d}_lex_{slug}.csv"
    chemin = os.path.join(utils.LEXICONS, fichier)
    if os.path.exists(chemin):
        return {"ok": False, "message": f"{fichier} existe deja"}
    entetes = ["terme_fr", "registre", "definition_fr", "en", "es", "pt", "ht",
               "secteur", "metiers"]
    lignes = []
    for t in (termes or []):
        lignes.append({**{c: "" for c in entetes}, **t, "secteur": slug})
    with open(chemin, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=entetes, quoting=csv.QUOTE_MINIMAL,
                           extrasaction="ignore")
        w.writeheader()
        for l in lignes:
            w.writerow(l)
    recharger()
    return {"ok": True, "fichier": fichier,
            "message": f"Lexique « {slug} » cree ({len(lignes)} terme(s)). "
                       f"Il est immediatement interrogeable."}


# ----------------------------------------------------------- import CSV
def importer(fichier_cible: str, contenu: bytes,
             remplacer_doublons: bool = False) -> dict:
    """Fusionne un CSV importe dans un fichier existant de la base."""
    entetes_cible, _ = lire(fichier_cible)
    if not entetes_cible:
        return {"ok": False, "message": "fichier cible introuvable"}
    texte = contenu.decode("utf-8", "replace")
    try:
        delim = csv.Sniffer().sniff(texte[:4000], delimiters=",;\t|").delimiter
    except Exception:
        delim = ";" if texte[:4000].count(";") > texte[:4000].count(",") else ","
    lecteur = csv.DictReader(io.StringIO(texte), delimiter=delim)
    champs = [c for c in (lecteur.fieldnames or [])]
    communs = [c for c in champs if c in entetes_cible]
    if not communs:
        return {"ok": False,
                "message": "aucune colonne en commun. Colonnes attendues : "
                           + ", ".join(entetes_cible)}
    nouvelles = [dict(r) for r in lecteur]
    res = ajouter_lignes(fichier_cible, nouvelles, remplacer_doublons)
    res["colonnes_reconnues"] = communs
    res["colonnes_ignorees"] = [c for c in champs if c not in entetes_cible]
    return res


# ------------------------------------------------------------ regeneration
def regenerer() -> dict:
    """Relance les scripts build_0*.py qui fabriquent les CSV de reference.

    Attention : cette operation reecrit les fichiers livres avec la plateforme.
    Les ajouts faits depuis l interface dans ces memes fichiers sont perdus ;
    une copie de securite complete est donc faite au prealable.
    """
    import runpy
    import sys

    racine = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dossier = os.path.join(racine, "scripts")
    if not os.path.isdir(dossier):
        return {"ok": False, "message": "dossier scripts/ absent de l installation"}

    archive = archiver()
    os.makedirs(BACKUP, exist_ok=True)
    chemin_archive = os.path.join(BACKUP, f"base-avant-regeneration-{utils.stamp()}.zip")
    with open(chemin_archive, "wb") as fh:
        fh.write(archive)

    modules = ["build_01_metiers.py", "build_02_lexiques_a.py", "build_03_lexiques_b.py",
               "build_04_lexiques_c.py", "build_05_langue_contextes.py"]
    sys.path.insert(0, dossier)
    faits, erreurs = [], []
    for m in modules:
        chemin = os.path.join(dossier, m)
        if not os.path.exists(chemin):
            erreurs.append(f"{m} absent")
            continue
        try:
            runpy.run_path(chemin, run_name="__main__")
            faits.append(m)
        except Exception as exc:
            erreurs.append(f"{m} : {exc.__class__.__name__}: {exc}")
    recharger()
    st = lexicons.stats()
    return {
        "ok": not erreurs,
        "scripts_executes": faits,
        "erreurs": erreurs,
        "fichiers": st["fichiers_csv"],
        "lignes": st["lignes_totales"],
        "sauvegarde": os.path.basename(chemin_archive),
        "message": (f"{len(faits)} script(s) executes : {st['fichiers_csv']} fichiers, "
                    f"{st['lignes_totales']} lignes. Copie de securite conservee."
                    + (f" Erreurs : {' | '.join(erreurs)}" if erreurs else "")),
    }


# ------------------------------------------------------------- archivage
def archiver() -> bytes:
    """Archive ZIP de toute la base de lexiques."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(os.listdir(utils.LEXICONS)):
            chemin = os.path.join(utils.LEXICONS, f)
            if os.path.isfile(chemin) and f.endswith(".csv"):
                z.write(chemin, arcname=f)
    return buf.getvalue()


def sauvegardes() -> list[dict]:
    if not os.path.isdir(BACKUP):
        return []
    out = []
    for f in sorted(os.listdir(BACKUP), reverse=True)[:40]:
        chemin = os.path.join(BACKUP, f)
        out.append({"fichier": f, "Ko": round(os.path.getsize(chemin) / 1024, 1)})
    return out


def restaurer(nom_sauvegarde: str) -> dict:
    """Remet en place une copie de securite d un fichier."""
    src = os.path.join(BACKUP, nom_sauvegarde)
    if not os.path.exists(src):
        return {"ok": False, "message": "sauvegarde introuvable"}
    base = nom_sauvegarde.rsplit("-", 2)[0] + ".csv"
    cible = os.path.join(utils.LEXICONS, base)
    shutil.copy2(src, cible)
    recharger()
    return {"ok": True, "message": f"{base} restaure depuis {nom_sauvegarde}."}
