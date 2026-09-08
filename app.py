"""
Check-up Manager - διαχείριση περιοδικού ιατρικού ελέγχου εργαζομένων.

Τρέξε το με:  streamlit run app.py
"""
import io
from datetime import date

import altair as alt
import pandas as pd
import streamlit as st

import config
import costs
import documents
import rules
import schedule

st.set_page_config(page_title="Check-up Manager", page_icon="🩺",
                   layout="wide", initial_sidebar_state="expanded")

ΑΡΧΕΙΟ_DEMO = "demo_data.xlsx"

st.markdown("""
<style>
  .block-container {padding-top: 2.4rem; padding-bottom: 3rem; max-width: 1200px;}
  h1 {font-size: 1.75rem !important; font-weight: 600; letter-spacing: -.01em;}
  [data-testid="stMetric"] {
      background: #f4f6f6; border: 1px solid #e3e8e7;
      border-radius: 10px; padding: 14px 16px;
  }
  [data-testid="stMetricLabel"] p {
      font-size: .78rem; color: #5b6b68; text-transform: uppercase;
      letter-spacing: .04em;
  }
  [data-testid="stMetricValue"] {font-size: 1.6rem; font-weight: 600;}
  .stTabs [data-baseweb="tab-list"] {gap: 4px;}
  .stTabs [data-baseweb="tab"] {
      padding: 8px 16px; border-radius: 8px 8px 0 0;
  }
  section[data-testid="stSidebar"] {border-right: 1px solid #e3e8e7;}
  hr {margin: 1.6rem 0;}
</style>
""", unsafe_allow_html=True)


# ------------------------------------------------------------------ data

@st.cache_data(show_spinner=False)
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


# ------------------------------------------------------------------ sidebar

with st.sidebar:
    st.markdown("### Δεδομένα")
    ανεβασμα = st.file_uploader("Αρχείο προσωπικού", type=["xlsx"],
                               label_visibility="collapsed")
    πηγη = ανεβασμα if ανεβασμα else ΑΡΧΕΙΟ_DEMO
    if not ανεβασμα:
        st.caption("Χρήση συνθετικών δεδομένων επίδειξης "
                   "(263 πλασματικοί εργαζόμενοι).")

    st.markdown("### Παράμετροι")
    ετος = st.selectbox("Έτος check-up",
                        list(range(date.today().year, date.today().year + 6)))
    μονο_ενεργοι = st.toggle("Μόνο ενεργοί εργαζόμενοι", True)

    st.markdown("### Έντυπα")
    με_κατασταση = st.toggle("Συνοδευτική κατάσταση", True)
    με_συγκαταθεση = st.toggle("Έντυπο συγκατάθεσης ΓΚΠΔ", True)


# ------------------------------------------------------------------ compute

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


# ------------------------------------------------------------------ header

st.title("Check-up Manager")
st.caption("Προγραμματισμός περιοδικού ιατρικού ελέγχου, ανάθεση "
           "προγραμμάτων και παραγωγή εντολών εκτέλεσης")

κ1, κ2, κ3, κ4 = st.columns(4)
κ1.metric("Στο αρχείο", f"{len(προσωπικο):,}".replace(",", "."))
κ2.metric(f"Οφείλουν {int(ετος)}", len(αναθεσεις))
κ3.metric("Παραπεμπτικά", sum(len(α["παραπεμπτικα"]) for α in αναθεσεις))
κ4.metric("Εκτιμώμενο κόστος", f"{συνολο:,.0f} €".replace(",", "."))

st.divider()


# ------------------------------------------------------------------ tabs

καρτ1, καρτ2, καρτ3 = st.tabs(
    [f"Λίστα {int(ετος)}", "Κόστος", "Δεν οφείλουν"])

with καρτ1:
    if not αναθεσεις:
        st.info("Κανείς δεν οφείλει check-up αυτό το έτος.")
    else:
        πινακας = pd.DataFrame([{
            "Α.Μ.": α["αμ"],
            "Ονοματεπώνυμο": f'{α["επωνυμο"]} {α["ονομα"]}',
            "Φύλο": α["φυλο"].capitalize(),
            "Ηλικία": α["ετη"],
            "Χώρος": α["χωρος"].capitalize(),
            "Πρόγραμμα": α["προγραμμα"].replace("Πρόγραμμα ", ""),
            "Παραπεμπτικά": ", ".join(p["κωδικος"]
                                      for p in α["παραπεμπτικα"]),
            "Κόστος": costs.κοστος_εργαζομενου(α),
        } for α in αναθεσεις])
        st.dataframe(
            πινακας, use_container_width=True, hide_index=True, height=430,
            column_config={
                "Α.Μ.": st.column_config.NumberColumn(format="%d", width="small"),
                "Ηλικία": st.column_config.NumberColumn(format="%d ετ.",
                                                        width="small"),
                "Κόστος": st.column_config.NumberColumn(format="%.2f €",
                                                        width="small"),
            })

with καρτ2:
    if not αναλυση:
        st.info("Δεν υπάρχουν δεδομένα κόστους.")
    else:
        κοστ = pd.DataFrame([{
            "Πρόγραμμα": πρ.replace("Πρόγραμμα ", ""),
            "Άτομα": μ["ατομα"],
            "Κόστος/άτομο": μ["κοστος_ατομου"],
            "Εξαιρέσεις": μ["εξαιρεσεις"],
            "Σύνολο": μ["συνολο"],
        } for πρ, μ in sorted(αναλυση.items())])

        αρ, δεξ = st.columns([1.1, 1])
        with αρ:
            st.dataframe(
                κοστ, use_container_width=True, hide_index=True,
                column_config={
                    "Κόστος/άτομο": st.column_config.NumberColumn(
                        format="%.2f €"),
                    "Σύνολο": st.column_config.NumberColumn(format="%.2f €"),
                })
        with δεξ:
            γραφημα = (
                alt.Chart(κοστ)
                .mark_bar(cornerRadiusTopRight=3, cornerRadiusBottomRight=3,
                          color="#1f6f5c")
                .encode(
                    x=alt.X("Σύνολο:Q", title="Κόστος (€)",
                            axis=alt.Axis(format=",.0f", grid=True)),
                    y=alt.Y("Πρόγραμμα:N", sort="-x", title=None),
                    tooltip=["Πρόγραμμα", "Άτομα", "Σύνολο"])
                .properties(height=max(220, 26 * len(κοστ)))
                .configure_view(stroke=None)
                .configure_axis(labelColor="#5b6b68", titleColor="#5b6b68",
                                domainColor="#e3e8e7", tickColor="#e3e8e7"))
            st.altair_chart(γραφημα, use_container_width=True)

        st.caption("Οι τιμές είναι ενδεικτικές — βλ. `costs.py`. "
                   "Οι «εξαιρέσεις» είναι εργαζόμενοι με διαφορετικό "
                   "κόστος από το τυπικό του προγράμματος (π.χ. εξαίρεση "
                   "ακοομετρίας).")

with καρτ3:
    if not οχι:
        st.info("Όλοι οφείλουν check-up αυτό το έτος.")
    else:
        st.dataframe(pd.DataFrame([{
            "Α.Μ.": ε["αμ"],
            "Ονοματεπώνυμο": f'{ε["επωνυμο"]} {ε["ονομα"]}',
            "Αιτιολογία": ε["αιτιολογια"],
        } for ε in οχι]), use_container_width=True, hide_index=True,
            height=430,
            column_config={"Α.Μ.": st.column_config.NumberColumn(
                format="%d", width="small")})


# ------------------------------------------------------------------ export

st.divider()
st.markdown("### Παραγωγή εντύπων")

if not αναθεσεις:
    st.caption("Δεν υπάρχουν έντυπα προς παραγωγή για αυτό το έτος.")
else:
    σελιδες = sum(len(α["παραπεμπτικα"]) for α in αναθεσεις)
    if με_συγκαταθεση:
        σελιδες += len(αναθεσεις)
    if με_κατασταση:
        σελιδες += 1

    αρ, δεξ = st.columns([1, 2])
    with αρ:
        if st.button(f"Δημιουργία PDF ({σελιδες} σελίδες)",
                     type="primary", use_container_width=True):
            with st.spinner("Παραγωγή εντύπων..."):
                buf = io.BytesIO()
                documents.παραγωγη(αναθεσεις, buf, int(ετος), συνολο,
                                   με_συγκαταθεση=με_συγκαταθεση,
                                   με_κατασταση=με_κατασταση)
                st.session_state["pdf"] = buf.getvalue()
                st.session_state["pdf_ετος"] = int(ετος)

        if st.session_state.get("pdf_ετος") == int(ετος) \
                and "pdf" in st.session_state:
            st.download_button("Λήψη PDF", st.session_state["pdf"],
                               file_name=f"Check-up_{int(ετος)}.pdf",
                               mime="application/pdf",
                               use_container_width=True)
    with δεξ:
        if st.session_state.get("pdf_ετος") == int(ετος):
            st.success("**Επόμενο βήμα:** αποστολή στον Ιατρό Εργασίας για "
                       "υπογραφή και σφραγίδα. Αν το διαγνωστικό κέντρο δεν "
                       "δέχεται ψηφιακή υπογραφή, απαιτείται εκτύπωση και "
                       "υπογραφή ανά σελίδα.")

st.caption(f"Οργανισμός: {config.ΕΤΑΙΡΕΙΑ} — ρυθμίζεται στο `config.py`. "
           "Τα δεδομένα επίδειξης είναι συνθετικά.")
