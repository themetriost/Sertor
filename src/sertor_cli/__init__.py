"""sertor-cli — interfaccia a riga di comando per eseguire le capacità del core.

Layer sottile sopra `sertor_core` (composition root): i comandi fanno parse argomenti → chiamano il
core → formattano l'output. Non duplica le capacità del core (Principio I).
"""
