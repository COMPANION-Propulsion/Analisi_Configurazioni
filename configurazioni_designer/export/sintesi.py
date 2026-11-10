"""Sintesi del caso: progetti.csv (03_dati), riepilogo.json e RISULTATO.md (00_sintesi)."""
import csv
import json
import math

import numpy as np


def _json(o):
    if isinstance(o, dict):
        return {str(k): _json(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_json(v) for v in o]
    if isinstance(o, np.ndarray):
        return [_json(v) for v in o.tolist()]
    if isinstance(o, (np.floating, np.integer)):
        o = o.item()
    if isinstance(o, float) and (math.isinf(o) or math.isnan(o)):
        return None
    if isinstance(o, (str, int, float, bool)) or o is None:
        return o
    return str(o)


def _condotto(layout):
    """Lunghezza e spostamento reali del condotto (mm), se la geometria ha questi parametri."""
    par = layout.parametri
    if "lunghezza_condotto_mm" not in par:
        return None
    return (f"lunghezza {par['lunghezza_condotto_mm']:.0f} mm, spostamento lungo lo spigolo "
            f"{par['spostamento_mm']:+.1f} mm (limite estremità {par['estremita_max_mm']:.0f} mm)")


def scrivi_progetti(risultati, percorso):
    """Una riga per ogni progetto valutato (separatore ;)."""
    with open(percorso, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow(["scenario", "L_mm", "variante", "D_mm", "geometria_ammissibile", "ammissibile", "punteggio", "sigma",
                    "ventola", "motore", "P_asse_W", "libero_dopo", "condotti", "massa_kg", "violazioni"])
        for r in risultati:
            for p in r["progetti"]:
                c, a, g = p.get("completo"), p.get("aero"), p["geometria"]
                w.writerow([r["scenario"]["id"], p["L"], json.dumps(p["variante"]), p["D"], p["geometria_ammissibile"],
                            c["ammissibile"] if c else "", round(c["punteggio_totale"], 4) if c else "",
                            c["sigma"] if c else "", c["tipo_ventola"] if c else "", c["motore"] if c else "",
                            round(a["P_asse_max"], 2) if a else "", round(g["frazione_libera_dopo"], 4),
                            round(g["frazione_condotti"], 4), round(c["massa_totale_kg"], 3) if c else "",
                            "; ".join(c["violazioni"]) if c else ""])
    return percorso


def ottimi(risultati):
    """Il progetto ottimo di ogni scenario, in forma di dizionario semplice."""
    riep = []
    for r in risultati:
        o = r["ottimo"]
        c = o.get("completo")
        riep.append({"scenario": r["scenario"]["id"], "L_mm": o["L"], "D_mm": o["D"], "variante": o["variante"],
                     "ammissibile": bool(c and c["ammissibile"]),
                     "punteggio_totale": c["punteggio_totale"] if c else None,
                     "punteggi": c["punteggi"] if c else None, "violazioni": c["violazioni"] if c else None,
                     "avvisi": c.get("avvisi") if c else None,
                     "P_asse_W": o["aero"]["P_asse_max"] if o.get("aero") else None,
                     "libero_dopo": o["geometria"]["frazione_libera_dopo"],
                     "massa_totale_kg": c["massa_totale_kg"] if c else None,
                     "massa_voci_kg": c["massa"]["voci"] if c else None,
                     "tipo_ventola": c["tipo_ventola"] if c else None, "motore": c["motore"] if c else None,
                     "sigma": c["sigma"] if c else None,
                     "condotto": _condotto(o["geometria"]["layout"])})
    return riep


def vincitore(riep):
    amm = [x for x in riep if x["ammissibile"]]
    return max(amm, key=lambda x: x["punteggio_totale"])["scenario"] if amm else "nessuno ammissibile"


def scrivi_riepilogo(riep, cfg, info, percorso):
    mis = cfg["missione"]
    with open(percorso, "w", encoding="utf-8") as fh:
        json.dump(_json({"esecuzione": info, "lato_cubo_intervallo_mm": [cfg["geometria"]["lato_cubo_min_mm"],
                                                                      cfg["geometria"]["lato_cubo_max_mm"]],
                         "lato_cubo_passo_mm": cfg["geometria"]["lato_cubo_passo_mm"],
                         "spinta_per_asse_N": mis["spinta_per_asse_N"],
                         "massa_obiettivo_kg": mis["massa_obiettivo_kg"], "massa_massima_kg": mis["massa_massima_kg"],
                         "scenari": riep}), fh, indent=2, ensure_ascii=False)
    return percorso


def al_limite(x, g):
    """'inferiore' / 'superiore' se il lato ottimo coincide con un estremo dell'intervallo, altrimenti None."""
    if x["L_mm"] <= g["lato_cubo_min_mm"] + 1e-6:
        return "inferiore"
    if x["L_mm"] >= g["lato_cubo_max_mm"] - 1e-6:
        return "superiore"
    return None


def scrivi_risultato(riep, cfg, scenari, info, nome_run, grafici, percorso):
    """RISULTATO.md: classifica, lato ottimo e numeri chiave di ogni scenario su una pagina."""
    mis, g = cfg["missione"], cfg["geometria"]
    ordinati = sorted(riep, key=lambda x: -(x["punteggio_totale"] or -1))
    nomi = {s["id"]: s["nome"] for s in scenari}
    L = [f"# Analisi delle configurazioni, caso `{info['cartella']}`", "",
         f"Run `{nome_run}` del {info['data']}, impronta degli input `{info['impronta']}`, modalità "
         f"`{cfg['esecuzione'].get('modalita', 'completa')}`.", "",
         "## Input principali", "",
         f"- spinta richiesta per asse {mis['spinta_per_asse_N']:.3f} N ({mis['origine_spinta']}, "
         f"massa {mis['massa_per_spinta_kg']} kg)",
         f"- massa: obiettivo {mis['massa_obiettivo_kg']:.2f} kg, massima ammessa {mis['massa_massima_kg']:.2f} kg",
         f"- ambiente di progetto `{cfg['ambiente_progetto']}`, ρ = {cfg['aria_progetto'].rho:.4f} kg/m³",
         f"- lato del cubo da {g['lato_cubo_min_mm']:.0f} a {g['lato_cubo_max_mm']:.0f} mm, passo "
         f"{g['lato_cubo_passo_mm']:.0f} mm ({', '.join(f'{x:.0f}' for x in cfg['lati_cubo_mm'])})",
         f"- scenari: " + ", ".join(f"`{s['id']}`" for s in scenari), "",
         f"## Vincitore tra gli ammissibili: **{vincitore(riep)}**", "",
         "| scenario | punteggio | lato L [mm] | D [mm] | potenza [W/asse] | spazio libero | massa [kg] | stato |",
         "|---|---|---|---|---|---|---|---|"]
    for x in ordinati:
        stato = "ammissibile" if x["ammissibile"] else "NON ammissibile: " + "; ".join(x["violazioni"] or ["—"])
        pt = f"{x['punteggio_totale']:.3f}" if x["punteggio_totale"] is not None else "—"
        P = f"{x['P_asse_W']:.0f}" if x["P_asse_W"] else "—"
        m = f"{x['massa_totale_kg']:.2f}" if x["massa_totale_kg"] else "—"
        L.append(f"| {x['scenario']} | {pt} | {x['L_mm']:.0f} | {x['D_mm']:.0f} | {P} | {x['libero_dopo']:.0%} | {m} | {stato} |")
    L += [""]
    for x in ordinati:
        L += [f"### {x['scenario']}", "", f"{nomi.get(x['scenario'], '')}", ""]
        lim = al_limite(x, g)
        if lim:
            L.append(f"- **ATTENZIONE**: il lato ottimo è al limite {lim} dell'intervallo: l'ottimo vero potrebbe "
                     "stare fuori, valuta di allargarlo")
        if x["variante"]:
            L.append("- ottimo con: " + ", ".join(f"{k} = {v}" for k, v in x["variante"].items()))
        if x["condotto"]:
            L.append(f"- condotto: {x['condotto']}")
        if x["tipo_ventola"]:
            L.append(f"- ventola `{x['tipo_ventola']}`, motore `{x['motore']}`, σ = {x['sigma']}")
        if x["punteggi"]:
            L.append("- punteggi: " + ", ".join(f"{k} {v:.2f}" for k, v in x["punteggi"].items()
                                                if isinstance(v, (int, float))))
        for a in (x.get("avvisi") or []):
            L.append(f"- avviso: {a}")
        L.append("")
    L += ["## Dove guardare", "",
          "- `02_excel/Confronto_scenari.xlsx`: il file principale (fogli *Classifica*, *Massa*, *Progetto ottimo*, ...)",
          "- `00_sintesi/riepilogo.json`: il progetto ottimo di ogni scenario",
          "- `03_dati/progetti.csv`: ogni progetto valutato, anche gli scartati, con il motivo",
          "- `log.txt`: registro completo della run; `input_usato.py`: copia esatta degli input", "",
          f"Grafici ({len(grafici)}):", ""]
    L += [f"- `{p}`" for p in grafici]
    L.append("")
    with open(percorso, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))
    return percorso
