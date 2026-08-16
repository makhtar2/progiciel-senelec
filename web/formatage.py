"""Formatage des nombres pour l'affichage."""


def fcfa(montant: float, decimales: int = 0) -> str:
    """Formate un montant en francs CFA avec séparateur de milliers."""
    return f"{montant:,.{decimales}f}".replace(",", " ").replace(".", ",") + " F"


def kwh(valeur: float) -> str:
    return f"{valeur:,.0f}".replace(",", " ") + " kWh"


def nombre(valeur: float, decimales: int = 2) -> str:
    return f"{valeur:,.{decimales}f}".replace(",", " ").replace(".", ",")


def kw(valeur: float) -> str:
    txt = f"{valeur:g}".replace(".", ",")
    return f"{txt} kW"


def pourcentage(valeur: float, decimales: int = 1) -> str:
    return f"{valeur * 100:.{decimales}f}".replace(".", ",") + " %"
