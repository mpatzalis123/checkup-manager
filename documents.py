"""
Παραγωγή εντύπων σε PDF:
  - Εντολή εκτέλεσης Check-up (ένα ανά παραπεμπτικό)
  - Έντυπο συγκατάθεσης προς το διαγνωστικό κέντρο
  - Συνοδευτική κατάσταση για τον ιατρό εργασίας
"""

import os
from datetime import date

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

import config

# --- Γραμματοσειρές ------------------------------------------------------
# Χρειάζονται γραμματοσειρές με ελληνικούς χαρακτήρες. Οι ενσωματωμένες του
# reportlab δεν τους έχουν. Ψάχνουμε τις DejaVu σε συνηθισμένες διαδρομές
# ώστε ο κώδικας να τρέχει σε Linux, macOS και σε containers.

ΔΙΑΔΡΟΜΕΣ = [
    "/usr/share/fonts/truetype/dejavu",
    "/usr/share/fonts/dejavu",
    "/usr/share/fonts/TTF",
    "/usr/local/share/fonts",
    "/Library/Fonts",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts"),
]

ΑΡΧΕΙΑ = {
    "Body": "DejaVuSerif.ttf",
    "Body-B": "DejaVuSerif-Bold.ttf",
    "Sans": "DejaVuSans.ttf",
    "Sans-B": "DejaVuSans-Bold.ttf",
}


def _βρες_γραμματοσειρα(αρχειο):
    for δ in ΔΙΑΔΡΟΜΕΣ:
        p = os.path.join(δ, αρχειο)
        if os.path.exists(p):
            return p
    return None


def _καταχωρηση_γραμματοσειρων():
    λειπουν = []
    for ονομα, αρχειο in ΑΡΧΕΙΑ.items():
        p = _βρες_γραμματοσειρα(αρχειο)
        if p:
            pdfmetrics.registerFont(TTFont(ονομα, p))
        else:
            λειπουν.append(αρχειο)
    if λειπουν:
        raise RuntimeError(
            "Δεν βρέθηκαν οι γραμματοσειρές: " + ", ".join(λειπουν) +
            ". Σε Debian/Ubuntu: apt install fonts-dejavu-core. "
            "Εναλλακτικά, αντίγραψέ τις στον υποφάκελο fonts/.")


_καταχωρηση_γραμματοσειρων()

W, H = A4


# ---------------------------------------------------------------- helpers

def _κωδικος_φορμας(φυλο, ετη, ειδος):
    if ειδος != "ΓΕΝΙΚΕΣ":
        return ""
    if φυλο == "ΑΝΔΡΑΣ":
        return "Α>=50" if ετη >= 50 else "Α<50"
    if ετη >= 50:
        return "Γ>=50"
    if ετη >= 40:
        return "Γ>=40 & <50"
    return "Γ<40"


def _τυπωσε_γραμμες(c, κειμενα, x, y, font="Body", size=10, leading=5.6 * mm):
    c.setFont(font, size)
    for γρ in κειμενα:
        c.drawString(x, y, γρ)
        y -= leading
    return y


def _wrap(c, κειμενο, πλατος, font="Body", size=9.5):
    λεξεις, γραμμες, τρεχ = κειμενο.split(), [], ""
    for λ in λεξεις:
        δοκ = f"{τρεχ} {λ}".strip()
        if c.stringWidth(δοκ, font, size) <= πλατος:
            τρεχ = δοκ
        else:
            γραμμες.append(τρεχ)
            τρεχ = λ
    if τρεχ:
        γραμμες.append(τρεχ)
    return γραμμες


# ------------------------------------------------- εντολή εκτέλεσης check-up

def _σελιδα_εντολης(c, εργ, παρ, ημερομηνια):
    θηλυκο = εργ["φυλο"] == "ΓΥΝΑΙΚΑ"

    y = H - 30 * mm
    c.setFont("Body", 12)
    c.drawCentredString(W / 2, y, config.ΕΤΑΙΡΕΙΑ)
    c.setLineWidth(0.4)
    c.line(35 * mm, y - 2 * mm, W - 35 * mm, y - 2 * mm)

    y -= 16 * mm
    c.setFont("Body-B", 11)
    c.drawCentredString(W / 2, y, config.ΤΙΤΛΟΣ)

    y -= 16 * mm
    c.setFont("Body", 10.5)
    εισ = ("Παρακαλούμε να κάνετε στην εργαζόμενή μας "
           if θηλυκο else "Παρακαλούμε να κάνετε στον εργαζόμενό μας ")
    c.drawString(28 * mm, y, εισ)
    x = 28 * mm + c.stringWidth(εισ, "Body", 10.5)
    ονομα = f"{εργ['επωνυμο']} {εργ['ονομα']}"
    c.setFont("Body-B", 10.5)
    c.drawString(x, y, ονομα)
    c.setLineWidth(0.3)
    c.line(x, y - 1.2 * mm, x + c.stringWidth(ονομα, "Body-B", 10.5) + 2 * mm,
           y - 1.2 * mm)

    y -= 9 * mm
    c.setFont("Body", 10.5)
    c.drawString(28 * mm, y, "με Α.Μ. ")
    x = 28 * mm + c.stringWidth("με Α.Μ. ", "Body", 10.5)
    αμ = str(εργ["αμ"])
    c.setFont("Body-B", 10.5)
    c.drawString(x, y, αμ)
    c.line(x, y - 1.2 * mm, x + c.stringWidth(αμ, "Body-B", 10.5) + 2 * mm,
           y - 1.2 * mm)
    c.setFont("Body", 10.5)
    c.drawString(x + c.stringWidth(αμ, "Body-B", 10.5) + 4 * mm, y,
                 "τις παρακάτω εξετάσεις:")

    y -= 14 * mm
    εξ = παρ["εξετασεις"]
    μεσο = (len(εξ) + 1) // 2
    for στηλη, xx in ((εξ[:μεσο], 32 * mm), (εξ[μεσο:], 108 * mm)):
        yy = y
        c.setFont("Body", 10)
        for ex in στηλη:
            c.drawString(xx, yy, "\u2022")
            c.drawString(xx + 5 * mm, yy, ex)
            yy -= 6.2 * mm
    y -= μεσο * 6.2 * mm

    y = min(y - 12 * mm, 105 * mm)
    c.setFont("Body-B", 10.5)
    c.drawString(28 * mm, y, f"Ημερομηνία: {ημερομηνια:%d/%m/%Y}")

    y -= 12 * mm
    c.drawCentredString(W * 0.68, y, f"Για την {config.ΕΤΑΙΡΕΙΑ}")

    if config.ΥΠΟΓΡΑΦΗ_ΕΙΚΟΝΑ:
        try:
            c.drawImage(config.ΥΠΟΓΡΑΦΗ_ΕΙΚΟΝΑ, W * 0.58, y - 24 * mm,
                        width=38 * mm, height=20 * mm, mask="auto")
        except Exception:
            pass

    y -= 30 * mm
    c.setFont("Body-B", 10)
    for (ονομ, τιτλ), cx in ((config.ΙΑΤΡΟΣ_ΕΡΓΑΣΙΑΣ, W * 0.30),
                            (config.ΔΙΕΥΘΥΝΤΗΣ, W * 0.72)):
        c.drawCentredString(cx, y, ονομ)
        c.drawCentredString(cx, y - 5 * mm, τιτλ)

    y -= 20 * mm
    c.setFont("Body", 9.5)
    c.drawCentredString(
        W / 2, y,
        f"Επικοινωνήστε για ραντεβού με «{config.ΔΙΑΓΝΩΣΤΙΚΟ}» "
        f"στο τηλέφωνο {config.ΤΗΛΕΦΩΝΟ_ΡΑΝΤΕΒΟΥ}")

    κωδ = _κωδικος_φορμας(εργ["φυλο"], εργ["ετη"], παρ.get("ειδος", "ΓΕΝΙΚΕΣ"))
    if κωδ:
        c.setFont("Body-B", 10)
        c.drawRightString(W - 25 * mm, y - 12 * mm, κωδ)

    c.showPage()


# ------------------------------------------------------ έντυπο συγκατάθεσης

ΚΕΙΜΕΝΟ_ΣΥΓΚΑΤΑΘΕΣΗΣ = [
    ("Σκοπός επεξεργασίας",
     "Η διενέργεια περιοδικού ιατρικού προληπτικού ελέγχου (check-up) στο "
     "πλαίσιο της υποχρέωσης του εργοδότη για την προστασία της υγείας των "
     "εργαζομένων, σύμφωνα με τον ν. 3850/2010."),
    ("Δεδομένα που διαβιβάζονται",
     "Ονοματεπώνυμο, αριθμός μητρώου, φύλο, έτος γέννησης και ο κατάλογος "
     "των εξετάσεων που αντιστοιχούν στο πρόγραμμα του εργαζομένου."),
    ("Αποδέκτης",
     "Το συμβεβλημένο διαγνωστικό κέντρο, αποκλειστικά για την εκτέλεση των "
     "εξετάσεων και την παράδοση των αποτελεσμάτων."),
    ("Πρόσβαση στα αποτελέσματα",
     "Τα αποτελέσματα παραδίδονται στον Ιατρό Εργασίας και στον ίδιο τον "
     "εργαζόμενο. Ο εργοδότης λαμβάνει μόνο τη γνωμάτευση καταλληλότητας, "
     "χωρίς ιατρικά δεδομένα."),
    ("Χρόνος τήρησης",
     "Ο ιατρικός φάκελος τηρείται από την Υπηρεσία Ιατρικής Εργασίας για "
     "όσο διάστημα προβλέπει η κείμενη νομοθεσία."),
    ("Δικαιώματα",
     "Έχετε δικαίωμα πρόσβασης, διόρθωσης, περιορισμού και εναντίωσης, καθώς "
     "και δικαίωμα ανάκλησης της συγκατάθεσης οποτεδήποτε, χωρίς αναδρομική "
     "ισχύ, με αίτηση προς την Υπηρεσία Ιατρικής Εργασίας."),
]


def _σελιδα_συγκαταθεσης(c, εργ, ημερομηνια):
    y = H - 25 * mm
    c.setFont("Sans", 11)
    c.drawCentredString(W / 2, y, config.ΕΤΑΙΡΕΙΑ)
    c.setLineWidth(0.4)
    c.line(30 * mm, y - 2 * mm, W - 30 * mm, y - 2 * mm)

    y -= 13 * mm
    c.setFont("Sans-B", 12)
    c.drawCentredString(W / 2, y, "ΕΝΤΥΠΟ ΕΝΗΜΕΡΩΣΗΣ ΚΑΙ ΣΥΓΚΑΤΑΘΕΣΗΣ")
    y -= 6 * mm
    c.setFont("Sans", 9.5)
    c.drawCentredString(
        W / 2, y, "για τη διαβίβαση δεδομένων υγείας στο διαγνωστικό κέντρο")

    y -= 12 * mm
    c.setFont("Sans-B", 9.5)
    for ετ, τιμη in (("Ονοματεπώνυμο", f"{εργ['επωνυμο']} {εργ['ονομα']}"),
                     ("Αρ. Μητρώου", str(εργ["αμ"])),
                     ("Πρόγραμμα", εργ["προγραμμα"])):
        c.setFont("Sans-B", 9.5)
        c.drawString(25 * mm, y, f"{ετ}:")
        c.setFont("Sans", 9.5)
        c.drawString(58 * mm, y, τιμη)
        y -= 5.5 * mm

    y -= 5 * mm
    for τιτλος, κειμενο in ΚΕΙΜΕΝΟ_ΣΥΓΚΑΤΑΘΕΣΗΣ:
        c.setFont("Sans-B", 9.5)
        c.drawString(25 * mm, y, τιτλος)
        y -= 5 * mm
        c.setFont("Sans", 9)
        for γρ in _wrap(c, κειμενο, W - 55 * mm, "Sans", 9):
            c.drawString(25 * mm, y, γρ)
            y -= 4.6 * mm
        y -= 3 * mm

    y -= 4 * mm
    c.setFont("Sans-B", 9.5)
    c.drawString(25 * mm, y, "Δηλώνω ότι ενημερώθηκα και συναινώ:")
    y -= 9 * mm
    for ετικ in ("ΝΑΙ", "ΟΧΙ"):
        c.rect(27 * mm if ετικ == "ΝΑΙ" else 62 * mm, y - 1 * mm,
               4 * mm, 4 * mm)
        c.setFont("Sans", 9.5)
        c.drawString((33 * mm) if ετικ == "ΝΑΙ" else (68 * mm), y, ετικ)

    y -= 22 * mm
    c.setFont("Sans", 9)
    c.line(25 * mm, y, 95 * mm, y)
    c.line(115 * mm, y, W - 25 * mm, y)
    c.drawString(25 * mm, y - 5 * mm, "Υπογραφή εργαζομένου")
    c.drawString(115 * mm, y - 5 * mm,
                 f"Ημερομηνία: {ημερομηνια:%d/%m/%Y}")

    c.setFont("Sans", 7.5)
    c.drawCentredString(
        W / 2, 15 * mm,
        "Υπεύθυνος Επεξεργασίας: η Εταιρεία. "
        "Επικοινωνία με τον Υπεύθυνο Προστασίας Δεδομένων (DPO) "
        "μέσω της Διεύθυνσης Ανθρώπινου Δυναμικού.")
    c.showPage()


# ------------------------------------------------- συνοδευτική κατάσταση

def _σελιδα_καταστασης(c, αναθεσεις, ημερομηνια, ετος, συνολο):
    y = H - 25 * mm
    c.setFont("Sans-B", 12)
    c.drawString(20 * mm, y, f"ΚΑΤΑΣΤΑΣΗ CHECK-UP {ετος}")
    c.setFont("Sans", 9)
    c.drawRightString(W - 20 * mm, y, f"{ημερομηνια:%d/%m/%Y}")
    y -= 4 * mm
    c.line(20 * mm, y, W - 20 * mm, y)

    y -= 8 * mm
    c.setFont("Sans", 8.5)
    for γρ in _wrap(c,
                    "Προς τον Ιατρό Εργασίας: παρακαλώ ελέγξτε και υπογράψτε "
                    "ψηφιακά τις συνημμένες εντολές εκτέλεσης. Εφόσον το "
                    "διαγνωστικό κέντρο δεν αποδέχεται ψηφιακή υπογραφή, "
                    "απαιτείται εκτύπωση, υπογραφή και σφραγίδα ανά σελίδα.",
                    W - 40 * mm, "Sans", 8.5):
        c.drawString(20 * mm, y, γρ)
        y -= 4.4 * mm

    y -= 6 * mm
    c.setFont("Sans-B", 8.5)
    for ετ, x in (("Α.Μ.", 20), ("Ονοματεπώνυμο", 40),
                  ("Ηλικ.", 105), ("Πρόγραμμα", 118),
                  ("Παραπεμπτικά", 158)):
        c.drawString(x * mm, y, ετ)
    y -= 2 * mm
    c.line(20 * mm, y, W - 20 * mm, y)
    y -= 5 * mm

    c.setFont("Sans", 8)
    for α in αναθεσεις:
        if y < 30 * mm:
            c.showPage()
            y = H - 25 * mm
            c.setFont("Sans", 8)
        c.drawString(20 * mm, y, str(α["αμ"]))
        c.drawString(40 * mm, y, f'{α["επωνυμο"]} {α["ονομα"]}'[:34])
        c.drawString(105 * mm, y, str(α["ετη"]))
        c.drawString(118 * mm, y, α["προγραμμα"].replace("Πρόγραμμα ", ""))
        c.drawString(158 * mm, y,
                     ", ".join(p["κωδικος"] for p in α["παραπεμπτικα"]))
        y -= 4.8 * mm

    y -= 4 * mm
    c.line(20 * mm, y, W - 20 * mm, y)
    y -= 6 * mm
    c.setFont("Sans-B", 9)
    c.drawString(20 * mm, y, f"Σύνολο: {len(αναθεσεις)} εργαζόμενοι")
    c.drawRightString(W - 20 * mm, y, f"Εκτιμώμενο κόστος: {συνολο:,.2f} €")
    c.showPage()


# ------------------------------------------------------------------ public

def παραγωγη(αναθεσεις, αρχειο, ετος, συνολο_κοστους,
             ημερομηνια=None, με_συγκαταθεση=True, με_κατασταση=True):
    """Ένα PDF: κατάσταση + εντολές + έντυπα συγκατάθεσης."""
    ημερομηνια = ημερομηνια or date.today()
    c = canvas.Canvas(αρχειο, pagesize=A4)
    c.setTitle(f"Check-up {ετος}")

    if με_κατασταση:
        _σελιδα_καταστασης(c, αναθεσεις, ημερομηνια, ετος, συνολο_κοστους)
    for α in αναθεσεις:
        for παρ in α["παραπεμπτικα"]:
            _σελιδα_εντολης(c, α, παρ, ημερομηνια)
        if με_συγκαταθεση:
            _σελιδα_συγκαταθεσης(c, α, ημερομηνια)

    c.save()
    return αρχειο
