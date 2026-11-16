"""Import dei dati del dimensionamento della propulsione (cartella sorella Dimensionamento_Sistema_Propulsivo).

Il caso si sceglie con DIMENSIONAMENTO["massa_kg"] e DIMENSIONAMENTO["statore"] in input_S4.py:
si cercano in ../Dimensionamento_Sistema_Propulsivo/risultati/ i casi con quella massa (1_spinta/spinta.json),
completi e con la ventola arrivata a convergenza; DIMENSIONAMENTO["caso"] sceglie a mano se ce n'è più di uno.

Fonti, per ogni caso:
    1_spinta/spinta.json                       massa, distanza, tempo, ugelli, margine, disturbo, spinta per ugello
    2_venturi/00_sintesi/risultati.json        geometria del condotto (diametri, lunghezze), perdite, densità
    4_sistema/00_sintesi/curva_potenza.json    curva giri -> spinta dell'ugello, potenza, salto di pressione, portata
    4_sistema/04_cfd/condotto_con_ventola.json spinta con la ventola vera / spinta con il disco uniforme
    4_sistema/00_sintesi/confronto_statore.json giri, potenza e coppia sul veicolo con e senza statore
    3_ventola/00_sintesi/report.json           pale, profilo, mozzo, stato della convergenza
    3_ventola/00_sintesi/confronto_pale.json   inerzia delle pale della scelta

Un dato mancante ferma la run con un errore che dice quale file e quale campo.
"""
import json
import math
import os

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RADICE_PREDEFINITA = os.path.join(os.path.dirname(ROOT), "Dimensionamento_Sistema_Propulsivo", "risultati")

FILE = {
    "spinta": "1_spinta/spinta.json",
    "venturi": "2_venturi/00_sintesi/risultati.json",
    "curva": "4_sistema/00_sintesi/curva_potenza.json",
    "cfd": "4_sistema/04_cfd/condotto_con_ventola.json",
    "statore": "4_sistema/00_sintesi/confronto_statore.json",
    "ventola": "3_ventola/00_sintesi/report.json",
    "pale": "3_ventola/00_sintesi/confronto_pale.json",
}


def _leggi(cartella, chiave):
    p = os.path.join(cartella, FILE[chiave])
    if not os.path.exists(p):
        raise ValueError(f"dimensionamento: manca il file {p}")
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def _campo(d, *chiavi, file=""):
    x = d
    for k in chiavi:
        if not isinstance(x, dict) or k not in x:
            raise ValueError(f"dimensionamento: nel file {file} manca il campo {'.'.join(chiavi)}")
        x = x[k]
    return x


def _completo(cartella):
    return all(os.path.exists(os.path.join(cartella, f)) for f in FILE.values())


def _convergente(cartella):
    try:
        r = _leggi(cartella, "ventola")
        return str(r["runs"][0]["status"]).startswith("converged")
    except Exception:
        return False


def casi_disponibili(radice=None):
    """[(nome, massa_kg, completo, ventola_convergente)] dei casi del dimensionamento."""
    radice = radice or RADICE_PREDEFINITA
    out = []
    if not os.path.isdir(radice):
        return out
    for nome in sorted(os.listdir(radice)):
        c = os.path.join(radice, nome)
        f = os.path.join(c, FILE["spinta"])
        if not os.path.exists(f):
            continue
        try:
            with open(f, encoding="utf-8") as fh:
                m = float(json.load(fh)["input"]["massa"])
        except Exception:
            continue
        out.append((nome, m, _completo(c), _convergente(c)))
    return out


def trova_caso(massa_kg, nome=None, radice=None):
    """Cartella del caso: per nome, oppure l'unico caso completo e convergente con quella massa."""
    radice = radice or RADICE_PREDEFINITA
    if not os.path.isdir(radice):
        raise ValueError(f"dimensionamento: non trovo la cartella dei risultati {radice} "
                         f"(deve stare in ../Dimensionamento_Sistema_Propulsivo/risultati/)")
    casi = casi_disponibili(radice)
    if nome:
        c = os.path.join(radice, nome)
        if not _completo(c):
            raise ValueError(f"dimensionamento: il caso '{nome}' non esiste o è incompleto in {radice}")
        return c
    buoni = [n for n, m, comp, conv in casi if abs(m - massa_kg) < 1e-9 and comp and conv]
    if len(buoni) == 1:
        return os.path.join(radice, buoni[0])
    elenco = "; ".join(f"{n} ({m:g} kg, {'completo' if comp else 'incompleto'}, "
                       f"{'ventola convergente' if conv else 'ventola NON convergente'})" for n, m, comp, conv in casi)
    if not buoni:
        raise ValueError(f"dimensionamento: nessun caso completo e convergente con massa {massa_kg:g} kg. Casi: {elenco}")
    raise ValueError(f"dimensionamento: più casi con massa {massa_kg:g} kg ({', '.join(buoni)}): "
                     f"sceglilo con DIMENSIONAMENTO['caso']. Casi: {elenco}")


def carica(massa_kg, statore, nome=None, radice=None, usa_spinta_ventola_vera=True):
    """Dati del caso scelto, già pronti per l'analisi (unità: mm, N, W, giri/min, kg/m^3)."""
    cart = trova_caso(massa_kg, nome, radice)
    sp = _leggi(cart, "spinta")
    ve = _leggi(cart, "venturi")
    cu = _leggi(cart, "curva")
    cfd = _leggi(cart, "cfd")
    st = _leggi(cart, "statore")
    vt = _leggi(cart, "ventola")
    pa = _leggi(cart, "pale")
    inp = _campo(sp, "input", file=FILE["spinta"])
    geo = _campo(ve, "geometria", file=FILE["venturi"])
    ven = _campo(ve, "ventola", file=FILE["venturi"])
    per = _campo(ve, "perdite", file=FILE["venturi"])
    # curva giri -> spinta, potenza, ...: solo i punti calcolati
    righe = [r for r in _campo(cu, "righe", file=FILE["curva"])
             if r.get("rpm", 0) > 0 and all(isinstance(r.get(k), (int, float)) and math.isfinite(r[k])
                                            for k in ("potenza_albero_W", "spinta_ugello_N", "dp_assiale_Pa",
                                                      "portata_m3_s", "coppia_Nm"))]
    righe.sort(key=lambda r: r["rpm"])
    if len(righe) < 3:
        raise ValueError(f"dimensionamento: nel file {FILE['curva']} ci sono meno di 3 punti validi")
    curva = {k: np.array([r[c] for r in righe], float) for k, c in
             (("rpm", "rpm"), ("P_W", "potenza_albero_W"), ("T_N", "spinta_ugello_N"), ("dp_Pa", "dp_assiale_Pa"),
              ("Q_m3_s", "portata_m3_s"), ("coppia_Nm", "coppia_Nm"))}
    if np.any(np.diff(curva["T_N"]) <= 0):
        raise ValueError(f"dimensionamento: nel file {FILE['curva']} la spinta non cresce con i giri")
    # ventola vera / disco uniforme
    T_vera = float(_campo(cfd, "spinta_con_ventola_N", file=FILE["cfd"]))
    T_disco = float(_campo(cfd, "spinta_disco_uniforme_N", file=FILE["cfd"]))
    f_vera = T_vera / T_disco if usa_spinta_ventola_vera else 1.0
    # statore: la curva è quella del progetto (statore come nel caso); le varianti scalano giri e potenza
    var = {bool(v["statore"]): v for v in _campo(st, "varianti", file=FILE["statore"])}
    statore_progetto = bool(_campo(vt, "best", "cases", file=FILE["ventola"])[0].get("stator_enabled", True))
    if statore not in var or statore_progetto not in var:
        raise ValueError(f"dimensionamento: nel file {FILE['statore']} manca la variante statore = {statore}")
    vp, vs = var[statore_progetto], var[statore]
    k_rpm = vs["rpm"] / vp["rpm"]
    k_P = vs["potenza_albero_W"] / vp["potenza_albero_W"]
    coppia_netta_su_rotore = vs["coppia_netta_Nm"] / max(vs["coppia_rotore_Nm"], 1e-12)
    # pale e inerzia
    des = _campo(vt, "best", "design", file=FILE["ventola"])
    scelta = _campo(pa, "scelta", file=FILE["pale"])
    pale = _campo(pa, "pale", file=FILE["pale"])
    riga = [r for r in _campo(pa, "righe", file=FILE["pale"]) if r.get("nome") == "inerzia delle pale [kg m^2]"]
    if not riga:
        raise ValueError(f"dimensionamento: nel file {FILE['pale']} manca la riga 'inerzia delle pale [kg m^2]'")
    J_pale = float(riga[0]["valori"][pale.index(scelta)])
    rho_rif = float(_campo(ven, "densita_kg_m3", file=FILE["venturi"]))
    Q_prog = float(_campo(ven, "portata_m3_s", file=FILE["venturi"]))
    D_us = float(_campo(geo, "D_uscita_m", file=FILE["venturi"])) * 1000
    return {
        "caso": os.path.basename(cart), "cartella": cart, "statore": bool(statore),
        "massa_kg": float(inp["massa"]), "distanza_m": float(inp["distanza"]), "tempo_s": float(inp["tempo"]),
        "n_ugelli": int(inp["n_ugelli"]), "fattore_margine": float(inp["fattore_margine"]),
        "disturbo_residuo_g": float(inp.get("disturbo_residuo_g", 0.0)), "profilo": inp.get("profilo"),
        "T_totale_N": float(_campo(sp, "T_totale_N", file=FILE["spinta"])),
        "T_ugello_N": float(_campo(sp, "T_ugello_N", file=FILE["spinta"])),
        "D_ventola_mm": float(_campo(geo, "D_ventola_m", file=FILE["venturi"])) * 1000,
        "D_ingresso_mm": float(_campo(geo, "D_ingresso_m", file=FILE["venturi"])) * 1000,
        "D_uscita_mm": D_us,
        "D_interno_max_mm": float(_campo(geo, "D_interno_max_mm", file=FILE["venturi"])),
        "D_esterno_tubo_mm": float(_campo(geo, "D_esterno_tubo_mm", file=FILE["venturi"])),
        "L_tubo_mm": float(_campo(geo, "L_tubo_mm", file=FILE["venturi"])),
        "L_condotto_mm": float(_campo(geo, "L_condotto_m", file=FILE["venturi"])) * 1000,
        "z_ventola_mm": float(_campo(ven, "z_centro_ventola_m", file=FILE["venturi"])) * 1000,
        "L_ventola_mm": float(_campo(ven, "L_ventola_m", file=FILE["venturi"])) * 1000,
        "rho_rif": rho_rif, "Q_progetto_m3_s": Q_prog,
        "V_uscita_progetto_m_s": Q_prog / (math.pi * (D_us / 1000) ** 2 / 4),
        "dp_progetto_Pa": float(_campo(ven, "dp_disk_Pa", file=FILE["venturi"])),
        "perdite_Pa": {"imbocco": float(per.get("imbocco_Pa", 0.0)), "disco": float(per.get("disco_Pa", 0.0)),
                       "valle": float(per.get("valle_Pa", 0.0))},
        "curva": curva, "fattore_ventola_vera": f_vera,
        "k_rpm_statore": k_rpm, "k_P_statore": k_P, "coppia_netta_su_rotore": coppia_netta_su_rotore,
        "pale": int(des.get("blade_count", scelta)), "profilo_pala": des.get("profile"),
        "D_mozzo_mm": float(des.get("hub_diameter_m", 0.0)) * 1000, "J_pale_kgm2": J_pale,
    }


# =========================================================================
# Propulsore del dimensionamento: punto di funzionamento per una spinta data
# =========================================================================
def punto(dim, F_N, rho, eps_perdite=0.0, frazione_intercettata=0.0):
    """Giri, potenza all'albero, coppia, portata, salto di pressione per avere F_N di spinta netta da un ugello.

    Modello (stesso condotto e stessa ventola del dimensionamento, curva a geometria fissa):
      - spinta netta = spinta dell'ugello x (1 - frazione del getto intercettata dal telaio);
      - spinta dell'ugello = spinta della curva x fattore ventola vera / disco uniforme (CFD del dimensionamento);
      - densità diversa da quella della curva: a giri fissi spinta e salto di pressione ~ rho, potenza ~ rho;
      - perdite aggiunte (prolunghe del condotto) = eps x salto di pressione del condotto, entrambe ~ Q^2:
        a pari portata (quindi a pari spinta) la ventola deve dare (1 + eps) volte il salto di pressione,
        cioè giri x sqrt(1 + eps) e potenza x (1 + eps) (stima a rendimento invariato);
      - statore: giri e potenza scalati con il confronto con/senza statore del dimensionamento.
    Ritorna None se la spinta supera la curva.
    """
    cu = dim["curva"]
    f_int = min(max(frazione_intercettata, 0.0), 0.95)
    T_curva = F_N / (1 - f_int) / dim["fattore_ventola_vera"] * dim["rho_rif"] / rho
    if T_curva > cu["T_N"][-1]:
        return None
    T_curva = max(T_curva, 0.0)
    rpm0 = float(np.interp(T_curva, cu["T_N"], cu["rpm"]))
    P0 = float(np.interp(T_curva, cu["T_N"], cu["P_W"]))
    Q = float(np.interp(T_curva, cu["T_N"], cu["Q_m3_s"]))
    dp0 = float(np.interp(T_curva, cu["T_N"], cu["dp_Pa"]))
    k = 1.0 + max(eps_perdite, 0.0)
    rpm = rpm0 * math.sqrt(k) * dim["k_rpm_statore"]
    P = P0 * rho / dim["rho_rif"] * k * dim["k_P_statore"]
    omega = rpm * 2 * math.pi / 60
    coppia = P / omega if omega > 0 else 0.0
    return {"rpm": rpm, "P_albero_W": P, "coppia_Nm": coppia, "Q_m3_s": Q, "dp_Pa": dp0 * rho / dim["rho_rif"] * k,
            "spinta_ugello_N": F_N / (1 - f_int), "coppia_corpo_Nm": coppia * dim["coppia_netta_su_rotore"]}


def spinta_netta_max(dim, rpm, rho, eps_perdite=0.0, frazione_intercettata=0.0):
    """Spinta netta di un ugello ai giri dati (giri oltre la curva: estrapolazione ~ giri^2)."""
    cu = dim["curva"]
    rpm0 = rpm / math.sqrt(1.0 + max(eps_perdite, 0.0)) / dim["k_rpm_statore"]
    if rpm0 <= cu["rpm"][-1]:
        T = float(np.interp(rpm0, cu["rpm"], cu["T_N"]))
    else:
        T = float(cu["T_N"][-1] * (rpm0 / cu["rpm"][-1]) ** 2)
    f_int = min(max(frazione_intercettata, 0.0), 0.95)
    return T * dim["fattore_ventola_vera"] * rho / dim["rho_rif"] * (1 - f_int)


def eps_prolunghe(dim, L_ingresso_mm, L_uscita_mm, nu=1.5e-5):
    """Perdita per attrito dei tratti dritti aggiunti, in frazione del salto di pressione del condotto (Blasius)."""
    eps = 0.0
    Q = dim["Q_progetto_m3_s"]
    for L, D in ((L_ingresso_mm, dim["D_ingresso_mm"]), (L_uscita_mm, dim["D_uscita_mm"])):
        if L <= 0:
            continue
        Dm = D / 1000
        V = Q / (math.pi * Dm ** 2 / 4)
        Re = V * Dm / nu
        lam = 0.3164 * Re ** -0.25 if Re > 2300 else 64 / max(Re, 1.0)
        eps += lam * (L / 1000) / Dm * 0.5 * dim["rho_rif"] * V ** 2 / dim["dp_progetto_Pa"]
    return eps
