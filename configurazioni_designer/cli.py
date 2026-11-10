"""Riga di comando dell'analisi delle configurazioni: input_*.py -> risultati/<caso>/.

Le due run (run_generica.py, run_S4.py) differiscono solo per il file di input, per il nome della run
e per quali grafici di scenario / confronto producono: la sequenza è la stessa.
  1  verifiche fisiche del codice contro risultati noti (si ferma se una fallisce)
  2  per ogni scenario attivo: ottimizzazione di lato, diametro, varianti geometriche,
     Venturi, ventola e motore; valutazione di spazio, perdite, controllo,
     dinamica del propulsore (da ../Dinamica_Sistema_Propulsivo, vedi core/ponte_dinamica.py),
     struttura, massa, realizzabilità
  3  risultati/<caso>/: 00_sintesi (RISULTATO.md, riepilogo.json), 01_grafici, 02_excel, 03_dati,
     più caso.json, input_usato.py, log.txt
"""
import argparse
import copy
import datetime as dt
import os
import sys
import time
import traceback

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))     # cartella del progetto
for _flusso in (sys.stdout, sys.stderr):        # accenti e simboli anche nella console di Windows
    try:
        _flusso.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

from .core.config import carica, impronta                           # noqa: E402
from .core import caso as CA                                         # noqa: E402
from .ottimizzazione import ottimizza_scenario                       # noqa: E402
from .export import grafici as GR                                    # noqa: E402
from .export import report_excel as XL                               # noqa: E402
from .export import sintesi as SI                                    # noqa: E402
from . import verifiche as VF                                        # noqa: E402
from .fluido.ventole import libreria_motori, libreria_ventole        # noqa: E402

# gruppi di grafici di scenario (vedi grafici_scenario)
TUTTI_I_GRUPPI = {"viste", "sezioni", "profili", "ventola", "spinta", "perdite", "dinamica", "struttura", "ingestione"}


def grafici_scenario(r, cfg, cartella, formati, log, gruppi=TUTTI_I_GRUPPI):
    out = []
    sid = r["scenario"]["id"]
    o = r["ottimo"]
    base = os.path.join(cartella, "01_grafici", sid)
    tit = f"{sid} — {r['scenario']['nome']} — lato L = {o['L']:.0f} mm"
    try:
        if "viste" not in gruppi:
            raise StopIteration
        out += [("viste", p) for p in GR.grafico_viste(o["geometria"], cfg, tit, os.path.join(base, "01_viste_layout"), formati)]
    except StopIteration:
        pass
    except Exception:
        log("   (viste non disegnate)\n" + traceback.format_exc())
    if "sezioni" in gruppi and o["geometria"]["layout"].solidi:
        try:
            out += [("sezioni", p) for p in GR.grafico_sezioni(o["geometria"], cfg, tit, os.path.join(base, "10_sezioni_struttura"), formati)]
        except Exception:
            log("   (sezioni non disegnate)\n" + traceback.format_exc())
    c = o.get("completo")
    if not c:
        return out
    a = o["aero"]
    cl = max(a["classi"], key=lambda x: x["P_el"])
    un = copy.deepcopy(cl["unita_rete"])
    arie = cfg["arie"]
    amb = cfg["ambiente_progetto"]
    N_req, N_lim = cl["N_req"], cl["N_lim"]
    N_lista = [0.5 * N_req, 0.75 * N_req, N_req] + ([N_lim] if N_lim > 1.05 * N_req else [])
    mot = libreria_motori(cfg["motori"])[c["motore"]]
    Z = libreria_ventole(cfg["tipi_ventola"])[c["tipo_ventola"]].Z
    passi = [
        ("profili", lambda: GR.grafico_profili(un, arie, N_lista, amb, tit, os.path.join(base, "02_profili_giri"), formati)),
        ("profili", lambda: GR.grafico_profili_ambienti(un, arie, N_req, tit, os.path.join(base, "03_profili_ambienti"), formati)),
        ("ventola", lambda: GR.grafico_mappa_ventola(un, arie, amb, N_req, N_lim, tit, os.path.join(base, "04_mappa_ventola"), formati)),
        ("spinta", lambda: GR.grafico_spinta_giri(un, arie, mot, cfg, N_req, N_lim, cl["F_unita"], tit, os.path.join(base, "05_spinta_giri_potenza"), formati)),
        ("perdite", lambda: GR.grafico_perdite_unita(cl, tit, os.path.join(base, "06_perdite"), formati)),
        ("dinamica", lambda: GR.grafico_salita(c["storia_salita"], N_req, c["t_salita_90"], tit, os.path.join(base, "07_salita_spinta"), formati, c["t_inversione"])),
        ("struttura", lambda: GR.grafico_campbell(c["f1_Hz"], Z, N_req, N_lim, tit, os.path.join(base, "08_campbell"), formati)),
        ("ingestione", lambda: GR.grafico_ingestione(c["ingestione_per_comando"], cfg, tit, os.path.join(base, "09_ingestione"), formati)),
    ]
    for gruppo, f in passi:
        if gruppo not in gruppi:
            continue
        try:
            out += [(gruppo, p) for p in f()]
        except Exception:
            log(f"   (grafico {gruppo} non disegnato)\n" + traceback.format_exc())
    return out


def nome_automatico(nome_run, cfg, scenari, imp):
    m, g = cfg["missione"], cfg["geometria"]
    return (f"{nome_run}_F{m['spinta_per_asse_N']:.2f}N_L{g['lato_cubo_min_mm']:.0f}-{g['lato_cubo_max_mm']:.0f}"
            f"_{cfg['ambiente_progetto']}_{len(scenari)}scenari_h{imp}")


def run(input_file, nome_run, gruppi=TUTTI_I_GRUPPI, con_confronto=True, veloce=False):
    """Esegue una run; ritorna la cartella del caso (None se una verifica fisica fallisce).

    gruppi: grafici di scenario da produrre; con_confronto: grafici di confronto tra scenari.
    """
    t0 = time.time()
    cfg, scenari, _ = carica(input_file)
    es = cfg["esecuzione"]

    # 1. verifiche fisiche ------------------------------------------------------
    if es.get("verifiche_fisiche", True):
        print("Verifiche fisiche del codice...")
        ok, tot = VF.esegui()
        print(f"   {ok}/{tot} verifiche superate\n")
        if ok < tot:
            print("Una verifica fisica è fallita: l'analisi non parte, i risultati non sarebbero affidabili.")
            return None

    # 2. analisi ----------------------------------------------------------------
    if veloce or es.get("modalita", "completa") == "veloce":
        cfg["ottimizzazione"]["diametri_mm"] = cfg["ottimizzazione"]["diametri_mm"][::2]
        cfg["ottimizzazione"]["sigma"] = [0.8, 1.0]
        cfg["lati_cubo_mm"] = cfg["lati_cubo_mm"][::2]
        es["modalita"] = "veloce"
        es["risoluzione_voxel_mm"] = max(es["risoluzione_voxel_mm"], 6.0)
        for s in scenari:
            if "varianti_geometria" in s:
                s["varianti_geometria"] = {k: v[::2] for k, v in s["varianti_geometria"].items()}
    imp = impronta(cfg, scenari)
    base_out = os.path.join(ROOT, es.get("cartella_output", "risultati"))
    os.makedirs(base_out, exist_ok=True)
    nome = CA.nome_caso(cfg["caso"], nome_automatico(nome_run, cfg, scenari, imp))
    cart = CA.prepara(base_out, nome, imp, cfg["caso"]["sovrascrivi"], input_file)
    flog = open(os.path.join(cart, "log.txt"), "w", encoding="utf-8")

    def log(msg):
        print(msg)
        flog.write(msg + "\n")
        flog.flush()

    mis = cfg["missione"]
    log(f"Esecuzione {nome_run} (input: {os.path.basename(input_file)}): {cart}")
    log(f"Spinta richiesta per asse: {mis['spinta_per_asse_N']:.3f} N ({mis['origine_spinta']}, "
        f"massa {mis['massa_per_spinta_kg']} kg)")
    log(f"Massa: obiettivo {mis['massa_obiettivo_kg']:.2f} kg, massima ammessa {mis['massa_massima_kg']:.2f} kg")
    log(f"Ambiente di progetto: {cfg['ambiente_progetto']}  rho = {cfg['aria_progetto'].rho:.4f} kg/m³")
    lati = cfg["lati_cubo_mm"]
    log(f"Lato del cubo: intervallo {cfg['geometria']['lato_cubo_min_mm']:.0f}-{cfg['geometria']['lato_cubo_max_mm']:.0f} mm, "
        f"passo {cfg['geometria']['lato_cubo_passo_mm']:.0f} mm: {len(lati)} lati analizzati per ogni scenario "
        f"({', '.join(f'{x:.0f}' for x in lati)})")
    risultati = []
    for sc in scenari:
        log(f"\n== {sc['id']}: {sc['nome']}")
        try:
            risultati.append(ottimizza_scenario(sc, cfg, log))
        except Exception:
            log("   ERRORE nello scenario:\n" + traceback.format_exc())

    # 3. grafici, Excel, dati -----------------------------------------------------
    formati = es["formato_grafici"]
    grafici = []
    log("\nGrafici per scenario...")
    for r in risultati:
        grafici += [(f"{r['scenario']['id']} · {g}", p) for g, p in grafici_scenario(r, cfg, cart, formati, log, gruppi)]
    if con_confronto:
        log("Grafici di confronto...")
        cart_conf = os.path.join(cart, "01_grafici", "confronto")
        os.makedirs(cart_conf, exist_ok=True)
        try:
            grafici += [("confronto", p) for p in GR.confronto(risultati, cfg, cart_conf, formati)]
        except Exception:
            log("   (confronto non completo)\n" + traceback.format_exc())
    info = {"cartella": nome, "data": f"{dt.datetime.now():%d/%m/%Y %H:%M}", "impronta": imp}
    log("Excel di confronto...")
    XL.scrivi(os.path.join(cart, "02_excel", "Confronto_scenari.xlsx"), risultati, cfg, scenari, info, grafici)
    SI.scrivi_progetti(risultati, os.path.join(cart, "03_dati", "progetti.csv"))
    riep = SI.ottimi(risultati)
    SI.scrivi_riepilogo(riep, cfg, info, os.path.join(cart, "00_sintesi", "riepilogo.json"))
    vinc = SI.vincitore(riep)
    SI.scrivi_risultato(riep, cfg, scenari, info, nome_run,
                        [os.path.relpath(p, cart).replace(os.sep, "/") for _, p in grafici],
                        os.path.join(cart, "00_sintesi", "RISULTATO.md"))
    CA.registra(base_out, {"data": info["data"], "caso": nome, "impronta": imp, "run": nome_run,
                           "scenari": len(scenari), "vincitore": vinc, "durata_s": round(time.time() - t0)})

    # riepilogo a schermo -----------------------------------------------------------
    log("\nRIEPILOGO (progetto ottimo di ogni scenario, dal migliore)")
    log(f"  {'scenario':<26}{'punteggio':>10}{'L':>7}{'D':>7}{'potenza':>12}{'libero':>8}{'massa':>9}  stato")
    for x in sorted(riep, key=lambda x: -(x["punteggio_totale"] or -1)):
        stato = "ammissibile" if x["ammissibile"] else "NON ammissibile: " + "; ".join(x["violazioni"] or ["—"])
        pt = f"{x['punteggio_totale']:.3f}" if x["punteggio_totale"] is not None else "—"
        P = f"{x['P_asse_W']:.0f} W/asse" if x["P_asse_W"] else "—"
        m = f"{x['massa_totale_kg']:.2f} kg" if x["massa_totale_kg"] else "—"
        log(f"  {x['scenario']:<26}{pt:>10}{x['L_mm']:>5.0f}mm{x['D_mm']:>5.0f}mm{P:>12}{x['libero_dopo']:>8.0%}{m:>9}  {stato}")
        lim = SI.al_limite(x, cfg["geometria"])
        if lim:
            log(f"  {'':<26}   ATTENZIONE: il lato ottimo è al limite {lim} dell'intervallo: "
                f"l'ottimo vero potrebbe stare fuori, valuta di allargarlo")
        if x["variante"]:
            log(f"  {'':<26}   ottimo con: " + ", ".join(f"{k} = {v}" for k, v in x["variante"].items()))
        if x["condotto"]:
            log(f"  {'':<26}   condotto: {x['condotto']}")
        for a in (x.get("avvisi") or []):
            log(f"  {'':<26}   avviso: {a}")
    log("\nLATO OTTIMO DEL CUBO (per ogni scenario, dentro l'intervallo analizzato)")
    for x in sorted(riep, key=lambda x: -(x["punteggio_totale"] or -1)):
        log(f"  {x['scenario']:<26} L = {x['L_mm']:.0f} mm" + ("" if x["ammissibile"] else "   (progetto non ammissibile)"))
    log(f"\nVincitore tra gli ammissibili: {vinc}")
    log(f"Sintesi: {os.path.join(cart, '00_sintesi', 'RISULTATO.md')}")
    log(f"Finito in {time.time() - t0:.0f} s. Risultati in {cart}")
    flog.close()
    return cart


def main(nome_run, file_input_predefinito, descrizione, gruppi=TUTTI_I_GRUPPI, con_confronto=True, argv=None):
    """Riga di comando comune delle run: --input, --veloce."""
    ap = argparse.ArgumentParser(description=descrizione, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", default=os.path.join(ROOT, file_input_predefinito),
                    help=f"file di input (predefinito: {file_input_predefinito})")
    ap.add_argument("--veloce", action="store_true", help="come ESECUZIONE['modalita'] = 'veloce'")
    args = ap.parse_args(sys.argv[1:] if argv is None else argv)
    try:
        cart = run(args.input, nome_run, gruppi, con_confronto, args.veloce)
    except ValueError as e:
        print(f"Errore: {e}")
        return 1
    return 0 if cart else 2
