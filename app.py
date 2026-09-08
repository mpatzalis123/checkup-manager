"""
Check-up Manager - διαχείριση περιοδικού ιατρικού ελέγχου εργαζομένων.

Τρέξε το με:  streamlit run app.py
"""
import io
from datetime import date

import pandas as pd
import streamlit as st

import config
import costs
import documents
import rules
import schedule

st.set_page_config(page_title="Check-up Manager", page_icon="🩺",
                   layout="wide")

ΑΡΧΕΙΟ_DEMO = "demo_data.xlsx"


# ------------------------------------------------------------------ data

@st.cache_data
def φορτωση(αρχειο):
    df = pd.read_excel(αρχειο)
    df["Ημ/νία γέννησης"] = pd.to_datetime(df["Ημ/νία γέννησης"]).dt.date
    return df


def σε_dict(σειρα):
    return dict(
        αμ=int(σειρα["ΑΜ"]),
        επωνυμο=str(σειρα["Επώνυμο"]),
        ονομα=str(σειρα["Ονομα"]),
        πατρωνυμο=str(σειρα.get("Πατρώνυμο", "") or ""),
        φυλο=str(σειρα["Φύλο"]),
        ημ_γεννησης=σειρα["Ημ/νία γέννησης"],
        χωρος=str(σειρα["ΧΩΡΟΣ"]),
        εξαιρεση_ακοης=bool(σειρα.get("Εξαίρεση ακοής", False)),
    )


# ------------------------------------------------------------------ UI

st.title("🩺 Check-up Manager")
st.caption("Προγραμματισμός περιοδικού ιατρικού ελέγχου και αυτόματη "
           "παραγωγή εντολών εκτέλεσης")

with st.sidebar:
    st.header("Δεδομένα")
    ανεβασμα = st.file_uploader("Αρχείο προσωπικού (.xlsx)", type=["xlsx"])
    πηγη = ανεβασμα if ανεβασμα else ΑΡΧΕΙΟ_DEMO
    if not ανεβασμα:
        st.info("Χρήση συνθετικών δεδομένων επίδειξης.")

    st.header("Παράμετροι")
    ετος = st.number_input("Έτος check-up", 2024, 2035, date.today().year, 1)
    μονο_ενεργοι = st.checkbox("Μόνο ενεργοί εργαζόμενοι", True)
    με_συγκαταθεση = st.checkbox("Έντυπο συγκατάθεσης ανά εργαζόμενο", True)
    με_κατασταση = st.checkbox("Συνοδευτική κατάσταση", True)

try:
    df = φορτωση(πηγη)
except Exception as e:
    st.error(f"Δεν διαβάστηκε το αρχείο: {e}")
    st.stop()

if μονο_ενεργοι and "ΚΑΤΑΣΤΑΣΗ" in df.columns:
    df = df[df["ΚΑΤΑΣΤΑΣΗ"].astype(str).str.startswith("ΕΝΕΡΓΟΣ")]

προσωπικο = [σε_dict(r) for _, r in df.iterrows()]
τελευταια = {int(r["ΑΜ"]): (int(r["Τελευταίο check-up"])
                            if pd.notna(r.get("Τελευταίο check-up")) else None)
             for _, r in df.iterrows()}

οφειλουν, οχι = schedule.λιστα_ετους(προσωπικο, τελευταια, int(ετος))
αναθεσεις = [rules.αναθεση(ε, ημ_αναφορας=date(int(ετος), 12, 31))
             for ε in οφειλουν]
συνολο, αναλυση = costs.κοστος_συνολο(αναθεσεις)

κ1, κ2, κ3, κ4 = st.columns(4)
κ1.metric("Στο αρχείο", len(προσωπικο))
κ2.metric(f"Οφείλουν {int(ετος)}", len(αναθεσεις))
κ3.metric("Παραπεμπτικά",
          sum(len(α["παραπεμπτικα"]) for α in αναθεσεις))
κ4.metric("Εκτιμώμενο κόστος", f"{συνολο:,.0f} €")

καρτ1, καρτ2, καρτ3 = st.tabs(
    ["Λίστα έτους", "Κόστος", "Δεν οφείλουν φέτος"])

with καρτ1:
    if not αναθεσεις:
        st.warning("Κανείς δεν οφείλει check-up αυτό το έτος.")
    else:
        πινακας = pd.DataFrame([{
            "Α.Μ.": α["αμ"],
            "Ονοματεπώνυμο": f'{α["επωνυμο"]} {α["ονομα"]}',
            "Φύλο": α["φυλο"],
            "Ηλικία": α["ετη"],
            "Χώρος": α["χωρος"],
            "Πρόγραμμα": α["προγραμμα"],
            "Παραπεμπτικά": ", ".join(p["κωδικος"]
                                      for p in α["παραπεμπτικα"]),
            "Κόστος (€)": costs.κοστος_εργαζομενου(α),
        } for α in αναθεσεις])
        st.dataframe(πινακας, use_container_width=True, hide_index=True)

with καρτ2:
    if αναλυση:
        κοστ = pd.DataFrame([{
            "Πρόγραμμα": πρ,
            "Άτομα": μ["ατομα"],
            "Κόστος/άτομο (€)": μ["κοστος_ατομου"],
            "Εξαιρέσεις": μ["εξαιρεσεις"],
            "Σύνολο (€)": μ["συνολο"],
        } for πρ, μ in sorted(αναλυση.items())])
        st.dataframe(κοστ, use_container_width=True, hide_index=True)
        st.bar_chart(κοστ.set_index("Πρόγραμμα")["Σύνολο (€)"])

with καρτ3:
    if οχι:
        st.dataframe(pd.DataFrame([{
            "Α.Μ.": ε["αμ"],
            "Ονοματεπώνυμο": f'{ε["επωνυμο"]} {ε["ονομα"]}',
            "Αιτιολογία": ε["αιτιολογια"],
        } for ε in οχι]), use_container_width=True, hide_index=True)

st.divider()
st.subheader("Παραγωγή εντύπων")

if αναθεσεις:
    if st.button("Δημιουργία PDF", type="primary"):
        with st.spinner("Παραγωγή..."):
            buf = io.BytesIO()
            documents.παραγωγη(αναθεσεις, buf, int(ετος), συνολο,
                               με_συγκαταθεση=με_συγκαταθεση,
                               με_κατασταση=με_κατασταση)
            st.session_state["pdf"] = buf.getvalue()

    if "pdf" in st.session_state:
        st.download_button("⬇️ Λήψη PDF", st.session_state["pdf"],
                           file_name=f"Check-up_{int(ετος)}.pdf",
                           mime="application/pdf")
        st.success(
            "Έτοιμο. Επόμενο βήμα: αποστολή στον Ιατρό Εργασίας για ψηφιακή "
            "υπογραφή και σφραγίδα. Αν το διαγνωστικό κέντρο δεν δέχεται "
            "ψηφιακή υπογραφή, απαιτείται εκτύπωση και υπογραφή ανά σελίδα.")

st.caption(f"Εταιρεία: {config.ΕΤΑΙΡΕΙΑ} — τα στοιχεία ρυθμίζονται στο "
           "config.py. Τα δεδομένα επίδειξης είναι συνθετικά.")
