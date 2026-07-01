"""SpecLift — generatore diff → requisiti EARS ancorati (MVP).

Architettura a "sandwich deterministico": sette stadi, uno solo è giudizio LLM
(la stesura EARS, delegata alla capacità `requirements` di Sertor); gli altri sei
sono deterministici e testabili. Ogni requisito è ancorato a `file:righe` + simbolo
+ (eventuale) test, e ogni àncora è verificata deterministicamente.
"""

__version__ = "0.1.0"
