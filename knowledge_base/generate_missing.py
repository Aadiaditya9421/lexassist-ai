"""
knowledge_base/generate_missing.py
────────────────────────────────────
Fills any gaps left by scraper.py using the GROQ API (free tier).
Groq is free, requires no billing setup, and is fast (Llama 3.3 70B).

Setup (one time):
    1. Go to https://console.groq.com  →  sign up free
    2. Create an API key
    3. Add to your .env file:  GROQ_API_KEY=gsk_...

Run AFTER scraper.py:
    python knowledge_base/scraper.py
    python knowledge_base/generate_missing.py
"""

import os
import sys
import time
import logging
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("generate_missing")

DOCS_DIR = Path(__file__).parent / "docs"
DOCS_DIR.mkdir(parents=True, exist_ok=True)
MIN_WORDS = 500


# ── Document specs ─────────────────────────────────────────────────────────────

DOCS = [
    {
        "filename": "01_ipc_sections_1_to_120.txt",
        "title": "Indian Penal Code — Sections 1 to 120",
        "category": "criminal_law",
        "year": 1860,
        "prompt": """Write a detailed Indian legal reference document for IPC 1860 Sections 1-120.
Include all of the following:
CHAPTER I (S.1-5): title, extent, jurisdiction, extra-territorial offences.
CHAPTER II (S.6-52A): every general explanation — Judge (S.19), Public Servant (S.21 all 12 categories),
Wrongful gain/loss (S.23), Dishonestly (S.24), Fraudulently (S.25), Document (S.29), Good faith (S.52).
CHAPTER III (S.53-75): all punishments — death, life imprisonment, rigorous vs simple, fines,
default imprisonment (S.64-65), solitary confinement (S.73-74), enhanced punishment (S.75).
CHAPTER IV (S.76-106): all general exceptions — mistake of fact (S.76), judicial acts (S.77),
accident (S.80), necessity (S.81), insanity (S.84), intoxication (S.85-86), consent (S.87-90),
private defence body (S.96-102), private defence property (S.103-106).
CHAPTER V (S.107-120): abetment — definition (S.107), instigator (S.108), abetment abroad (S.108A),
punishment (S.109-117).
CHAPTER VA (S.120A-120B): criminal conspiracy definition and punishment.
For each section: number, heading, full provision text, key elements, illustration if any, punishment.
End with PRACTICAL NOTES: 5 citizen Q&A.
Use === for chapter headings, --- for section dividers."""
    },
    {
        "filename": "02_ipc_sections_121_to_300.txt",
        "title": "Indian Penal Code — Sections 121 to 300",
        "category": "criminal_law",
        "year": 1860,
        "prompt": """Write a detailed Indian legal reference for IPC 1860 Sections 121-300. Include:
CHAPTER VI (S.121-130): offences against the State — waging war (S.121, punishment: death/life),
sedition (S.124A — note Supreme Court stayed this in 2022), assaulting President/Governor.
CHAPTER VII (S.131-140): offences against army/navy/air force.
CHAPTER VIII (S.141-160): unlawful assembly (S.141 — 5 or more persons, common object),
rioting (S.146-147, S.148 with deadly weapon), promoting enmity (S.153A), affray (S.159-160).
CHAPTER IX (S.161-171H): public servant offences — bribery (S.161 now covered by Prevention
of Corruption Act), misconduct, personation of public servant (S.170).
CHAPTER X (S.172-190): contempt of lawful authority.
CHAPTER XI (S.191-229): false evidence — perjury (S.191-193, up to 7 years), fabricating
evidence (S.192), giving false info to public servant (S.203), harbouring offenders (S.212-216).
CHAPTER XII (S.230-263A): currency offences — counterfeiting coins (S.232-233).
CHAPTER XIV (S.268-294A): public nuisance, obscenity (S.292-294).
CHAPTER XV (S.295-298): offences against religion — injuring places of worship (S.295),
deliberate acts outraging religious feelings (S.295A), disturbing religious assembly (S.296).
CHAPTER XVI starts (S.299-300): culpable homicide vs murder — full distinction, all 5 exceptions
to murder converting it to culpable homicide not amounting to murder.
Each section: full text, elements, punishment. End with PRACTICAL NOTES: 5 Q&A."""
    },
    {
        "filename": "03_ipc_sections_301_to_511.txt",
        "title": "Indian Penal Code — Sections 301 to 511",
        "category": "criminal_law",
        "year": 1860,
        "prompt": """Write a detailed Indian legal reference for IPC 1860 Sections 301-511. Include:
S.301-318: death by negligence (S.304A), abetment of suicide (S.306), suicide attempt (S.309
— note Mental Healthcare Act 2017 effectively decriminalised), infanticide.
S.319-338: hurt (S.319), grievous hurt (S.320 — all 8 categories in full), punishments S.323-326B,
acid attack (S.326A minimum 10 years, fine to victim), custodial torture (S.330, up to 7 years).
S.339-348: wrongful restraint vs wrongful confinement — distinction and punishments.
S.349-358: force, criminal force (S.350), assault (S.351-358).
S.359-374: kidnapping from India vs from lawful guardianship, abduction, slavery, forced labour.
S.375-376E: rape — full post-2013 definition (S.375, 6 clauses), consent definition,
punishment S.376 (minimum 7 years, 10 years aggravated), gang rape S.376D (20 years to life).
S.378-402: theft (S.378-382), extortion (S.383-389), robbery (S.390-392, up to 10 years),
dacoity (S.391, 5+ persons, up to life), receiving stolen property (S.410-414).
S.403-409: criminal misappropriation and criminal breach of trust — embezzlement by clerk S.406,
by public servant S.409 (life imprisonment).
S.415-420: cheating (S.415), cheating with delivery of property S.420 (up to 7 years).
S.463-477A: forgery, using forged documents, forgery of court records.
S.499-502: defamation (S.499 — 10 exceptions), punishment S.500 (2 years).
S.503-510: criminal intimidation, insult, causing fear.
S.511: attempt to commit offences — half punishment of completed offence.
Include PUNISHMENT COMPARISON TABLE and PRACTICAL NOTES: 5 Q&A."""
    },
    {
        "filename": "04_crpc_arrest_bail_trial.txt",
        "title": "Code of Criminal Procedure 1973 — Arrest, Bail and Trial",
        "category": "criminal_law",
        "year": 1973,
        "prompt": """Write a detailed Indian legal reference for the Code of Criminal Procedure (CrPC) 1973
covering arrest, bail, and trial. Include:

ARREST (S.41-60):
S.41: 9 conditions for arrest without warrant; S.41A notice to appear (2009 amendment —
Arnesh Kumar guidelines 2014 SC: police must justify arrest necessity).
S.41B: procedure of arrest — name, designation of arresting officer.
S.41C: Control room at districts.
S.41D: Right to meet advocate during interrogation.
S.46: How arrest is made — no more restraint than necessary; woman arrested only by woman officer
after sunset only with magistrate permission.
S.49: No unnecessary restraint.
S.50: Grounds of arrest to be communicated; right to bail in bailable offence.
S.50A: Inform nominated person of arrest (2008 amendment).
S.54: Medical examination of arrested person.
S.57: Not to be detained beyond 24 hours without magistrate order.
S.167: Remand — judicial custody procedure; default bail (S.167(2)) if chargesheet
not filed within 60/90 days (magistrate/sessions triable).

BAIL (S.436-450):
S.436: Bailable offences — bail is a right, police/court MUST grant.
S.436A: Maximum detention — bail after half the maximum sentence period served.
S.437: Non-bailable offences — court's discretion; 7 factors; special provisions for
women, children under 16, sick/infirm persons.
S.437A: Bail on conclusion of trial before higher court.
S.438: Anticipatory bail — application to Sessions Court or High Court;
conditions court may impose; cannot be time-limited per SC (Sushila Aggarwal 2020).
S.439: Special powers of HC/Sessions Court — can cancel bail also.
S.440-450: Amount of bail, sureties, cash bail, cancellation.

FIR AND INVESTIGATION (S.154-176):
S.154: FIR — must be recorded in writing, read to informant, signed; zero FIR concept;
S.154(3) if officer refuses, send written complaint to SP.
S.155: Non-cognizable offences — police need magistrate order.
S.157-173: Investigation, spot inspection, inquest (S.174-176 — unnatural death).
S.173: Police report (chargesheet) — within 60 days (magistrate triable) or 90 days (sessions).

TRIAL PROCEDURE:
S.190-204: Cognizance of offences by magistrate; issue of process.
S.225-250: Sessions trial — charge (S.228), defence (S.233), judgment (S.235).
S.251-259: Warrant case trial before magistrate.
S.260-265L: Summary trials; plea bargaining (S.265A-265L, 2005 amendment).
S.300: Double jeopardy — once acquitted/convicted, cannot be tried for same offence.
S.313: Examination of accused — must be given opportunity to explain evidence.
S.321: Withdrawal from prosecution by public prosecutor.

Include BAIL TYPE COMPARISON TABLE and PRACTICAL NOTES with 6 citizen Q&A."""
    },
    {
        "filename": "05_constitution_fundamental_rights.txt",
        "title": "Constitution of India — Fundamental Rights (Articles 12–35)",
        "category": "constitutional_law",
        "year": 1950,
        "prompt": """Write a detailed Indian legal reference on Fundamental Rights — Constitution of India
Part III (Articles 12-35). Include every article:

Art.12: Definition of State — includes Government, Parliament, State Legislatures,
local authorities, and other authorities (Ajay Hasia test for instrumentality of State).
Art.13: Pre-constitutional and post-constitutional laws inconsistent with FR are void to
extent of inconsistency; judicial review basis; includes ordinances, bylaws, customs.
Art.14: Right to equality — equality before law AND equal protection of laws;
reasonable classification test (intelligible differentia + rational nexus).
Art.15: No discrimination on religion, race, caste, sex, place of birth;
Art.15(3) special provision for women/children; Art.15(4) backward classes;
Art.15(5) OBC/SC/ST in unaided private educational institutions (93rd Amendment);
Art.15(6) EWS 10% reservation (103rd Amendment 2019).
Art.16: Equality in public employment; Art.16(4) reservations for backward classes;
Art.16(4A) reservations in promotion for SC/ST; Art.16(4B) unfilled backlog vacancies.
Art.17: Abolition of untouchability — offence punishable under Protection of Civil Rights Act 1955.
Art.18: Abolition of titles — no military/academic titles from foreign states;
Bharat Ratna/Padma awards — SC upheld in Balaji Raghavan 1996.
Art.19: Six freedoms with reasonable restrictions:
19(1)(a) speech and expression — restrictions under 19(2): sovereignty, security, relations
with foreign states, public order, decency, morality, contempt of court, defamation, incitement;
19(1)(b) peaceful assembly without arms;
19(1)(c) form associations or unions;
19(1)(d) move freely throughout India;
19(1)(e) reside and settle in any part of India;
19(1)(g) practise any profession or carry on any trade.
Art.20: Protection in respect of conviction — no ex post facto law, no double jeopardy,
no self-incrimination (right to silence, cannot be compelled to be witness against self).
Art.21: Protection of life and personal liberty — expanded scope post Maneka Gandhi 1978
(procedure must be just, fair, reasonable); includes right to privacy (K.S. Puttaswamy 2017
9-judge bench), right to health, right to livelihood, right against custodial violence,
right to speedy trial, right to legal aid.
Art.21A: Free and compulsory education for 6-14 years (86th Amendment 2002);
implemented through Right to Education Act 2009.
Art.22: Protection against arbitrary arrest — inform grounds immediately, right to consult
advocate, produce before magistrate within 24 hours, preventive detention limits (3 months
without Advisory Board, maximum as per law up to 12 months typically).
Art.23: Prohibition of traffic in human beings, begar, forced labour;
Bonded Labour System (Abolition) Act 1976.
Art.24: No child below 14 in factories, mines, hazardous employment.
Art.25-28: Freedom of conscience, religion, manage religious affairs, no religious tax,
no religious instruction in state educational institutions.
Art.29-30: Minorities' right to conserve language, script, culture;
right to establish and administer educational institutions.
Art.32: Right to constitutional remedies — Dr Ambedkar: heart and soul of Constitution;
five writs — habeas corpus (produce body), mandamus (command to perform duty),
prohibition (stop inferior court from exceeding jurisdiction), certiorari (quash order),
quo warranto (by what authority do you hold office).
Art.33-35: Parliament may restrict FR for armed forces; martial law areas; power to legislate.

Include FIVE WRITS QUICK REFERENCE table and PRACTICAL NOTES with 6 Q&A."""
    },
    {
        "filename": "06_constitution_dpsp_amendments.txt",
        "title": "Constitution of India — DPSP, Fundamental Duties and Key Amendments",
        "category": "constitutional_law",
        "year": 1950,
        "prompt": """Write a detailed Indian legal reference on DPSP, Fundamental Duties and Amendments.

PART IV — DIRECTIVE PRINCIPLES (Art.36-51):
Art.37: Not justiciable but fundamental in governance; courts use to interpret laws.
Art.38: State to secure social order for welfare.
Art.39: Six sub-clauses — adequate livelihood, equal pay for equal work (39(d)),
no concentration of wealth (39(c)), children welfare (39(f)).
Art.39A: Free legal aid — Legal Services Authorities Act 1987 implements this.
Art.40: Panchayati Raj — implemented by 73rd Amendment 1992.
Art.41: Right to work, education, public assistance (not enforceable directly).
Art.42: Maternity relief and humane work conditions.
Art.43: Living wage; promotion of cottage industries.
Art.43A: Worker participation in management (added 42nd Amendment).
Art.44: Uniform Civil Code — meaning, current status, Goa Portuguese Civil Code as model,
Shah Bano controversy, Supreme Court repeatedly urged Parliament to enact UCC.
Art.45: Early childhood care till age 6 (amended post Art.21A).
Art.46: Promote SC/ST economic and educational interests.
Art.47: Raise nutrition, standard of living; prohibition of intoxicating drinks (alcohol policy).
Art.48: Agriculture, animal husbandry; cow slaughter — state subject, various HC judgments.
Art.48A: Protect and improve environment (42nd Amendment) — basis for environmental laws.
Art.49: Protection of national monuments (ASI).
Art.50: Separation of judiciary from executive — implemented in district courts.
Art.51: International peace; respect for international law and treaty obligations.

DPSP vs FUNDAMENTAL RIGHTS — conflict and resolution:
Champakam Dorairajan 1951 (FR prevailed) → 1st Amendment added 9th Schedule;
Golaknath 1967 (FR unamendable) → 24th Amendment overruled it;
Kesavananda Bharati 1973 (basic structure doctrine — harmony between FR and DPSP);
Minerva Mills 1980 (balance between FR and DPSP is basic structure).

PART IVA — FUNDAMENTAL DUTIES (Art.51A):
All 11 duties — (a) to (k) — with plain language explanation and enforceability note.
(a) abide by Constitution; (b) cherish national struggle ideals; (c) uphold sovereignty;
(d) defend country; (e) promote harmony; (f) value composite culture; (g) protect environment;
(h) develop scientific temper; (i) safeguard public property; (j) strive for excellence;
(k) provide education opportunities to children 6-14 years (86th Amendment).
Courts use duties to: uphold anti-flag desecration laws, environmental laws, etc.

KEY CONSTITUTIONAL AMENDMENTS:
1st (1951): 9th Schedule; restricted speech/trade freedoms.
7th (1956): State reorganisation on linguistic basis.
24th (1971): Parliament can amend any part including FRs.
25th (1971): Art.39(b)(c) DPSP override Art.14, 19.
42nd (1976): Added DPSP, Duties; changed Preamble (Socialist, Secular, Integrity).
44th (1978): Restored Art.19, 20, 21 protections; removed right to property from FRs.
52nd (1985): Anti-defection law — 10th Schedule.
61st (1988): Voting age 21→18.
69th (1991): Delhi as NCT with Legislative Assembly.
73rd/74th (1992): Panchayati Raj and Urban Local Bodies — mandatory elections.
86th (2002): Art.21A free education; Art.45 amended; Art.51A(k) added.
97th (2011): Co-operative societies — Part IXB.
99th (2014): NJAC — struck down (SC 2015, basic structure: judicial independence).
101st (2016): GST — Art.246A concurrent power; Art.269A, 279A.
102nd (2018): National Commission for Backward Classes — Art.338B.
103rd (2019): 10% EWS reservation — Art.15(6), 16(6).
105th (2021): Restored state/UT power to identify OBCs.

Include DPSP CLASSIFICATION TABLE (socialist/Gandhian/liberal-intellectual) and PRACTICAL NOTES."""
    },
    {
        "filename": "07_consumer_protection_act_2019.txt",
        "title": "Consumer Protection Act, 2019",
        "category": "civil_law",
        "year": 2019,
        "prompt": """Write a detailed Indian legal reference for the Consumer Protection Act, 2019.

DEFINITIONS (S.2):
Consumer (S.2(7)): buys goods or hires services for consideration; NOT for resale or
commercial purpose; includes online purchases; includes beneficiary of service.
Goods (S.2(21)): every kind of moveable property; includes food, shares, growing crops.
Service (S.2(42)): banking, financing, insurance, transport, processing, supply of power,
lodging, entertainment, amusement, education, telecom — excludes free services and
employer-employee contract.
Defect (S.2(10)): any fault in quality, quantity, potency, purity, standard.
Deficiency (S.2(11)): any fault, imperfection, shortcoming in manner of performance.
Unfair trade practice (S.2(47)): false representation, misleading ads, deceptive packaging,
unsolicited goods, unsafe goods, hoarding.
Restrictive trade practice (S.2(41)): manipulates price or affects flow of supplies.
Six consumer rights (S.2(9)):
1. Right to safety from hazardous goods/services.
2. Right to information about quality, quantity, price.
3. Right to choice among competitive goods at competitive prices.
4. Right to be heard in consumer forums.
5. Right to seek redress against unfair practices.
6. Right to consumer education.

CENTRAL CONSUMER PROTECTION AUTHORITY (CCPA) S.10-27:
S.10: CCPA — regulates unfair trade practices, misleading ads; headed by Chief Commissioner.
S.18: Powers — recall products, discontinue practices, impose penalties, file class complaints.
S.21: Endorser of misleading ads also liable (manufacturer AND celebrity endorser).
S.89: Penalty for misleading ads: up to ₹10 lakhs first offence, ₹50 lakhs repeat.

CONSUMER DISPUTES REDRESSAL COMMISSIONS (S.28-58):
District Commission (S.28-40):
- Jurisdiction: claims up to ₹1 crore.
- Composition: President + 2 members (one woman).
- S.35: Who can complain — consumer, registered consumer association,
  Central/State Govt, one consumer on behalf of many.
- S.36: File in writing or online via e-daakhil portal (edaakhil.nic.in).
- Fees: ₹100-2000 depending on claim amount (nil for BPL cardholders).
- Limitation: S.69 — 2 years from cause of action; delay can be condoned.
- S.38: Opposite party to respond within 30 days (extendable to 45).
- S.39: Relief — replacement, repair, refund, compensation, removal of deficiency,
  discontinuation of practice, punitive damages, payment of costs.
State Commission (S.47-55):
- Pecuniary jurisdiction: ₹1 crore to ₹10 crore.
- Appellate jurisdiction: appeals from District Commission within 45 days.
- 50% of award must be deposited to file appeal.
National Commission (S.58-73):
- Pecuniary jurisdiction: above ₹10 crore.
- Appellate jurisdiction: appeals from State Commission.
- Circuit benches in major cities.
Supreme Court: final appeal from National Commission.

PRODUCT LIABILITY (S.82-87):
S.82: Manufacturer liable if: product has manufacturing defect, design defect,
does not conform to express warranty, inadequate instructions.
S.83: Product service provider liable for deficient service.
S.84: Product seller liable if: altered product, did not exercise reasonable care.
S.85: Joint and several liability.
S.86: Exceptions — misuse by consumer, product used after expiry, failed to follow instructions.
S.87: Claimant must prove — defect, damage, defect caused damage.

E-COMMERCE RULES (Consumer Protection (E-Commerce) Rules 2020):
Mandatory disclosures: seller name, address, import details, customer care contact.
Prohibited: fake reviews, preferential listing without disclosure, flash sales to corner goods,
discriminatory pricing based on user profiling, pre-ticked checkboxes for additional charges.
Grievance Officer: appointed within India, respond to complaints within 48 hours, resolve in 1 month.
Fall-back liability: marketplace liable if does not provide seller information.

Include FORUM JURISDICTION TABLE and PRACTICAL NOTES with 6 citizen Q&A."""
    },
    {
        "filename": "08_rti_act_2005.txt",
        "title": "Right to Information Act, 2005",
        "category": "special_law",
        "year": 2005,
        "prompt": """Write a detailed Indian legal reference for the Right to Information Act, 2005.

DEFINITIONS (S.2):
Public authority (S.2(h)): body constituted by Constitution, Parliament, State Legislature,
Government notification; includes PSUs, nationalised banks, government-aided institutions,
regulatory bodies (SEBI, RBI, IRDAI, TRAI), bodies substantially financed by government.
NOT covered: private companies (unless substantially government-funded), judiciary's
administrative functions (but judicial decisions are public records).
Information (S.2(f)): any material in any form — records, documents, memos, emails,
opinions, advices, press releases, circulars, orders, logbooks, contracts, reports,
papers, samples, models, data in electronic form.
Right to Information (S.2(j)): inspection of work/documents/records; taking notes;
taking certified copies; taking certified samples; obtaining info in diskette/floppy/tape/video/CD.
Public Information Officer (PIO) (S.2(g)): designated officer in each public authority who
receives and processes RTI applications; must be designated by head of public authority (S.5).
First Appellate Authority (FAA): officer senior to PIO in same public authority.

HOW TO FILE AN RTI (S.6):
Written application in English, Hindi, or official language of the area.
No prescribed format — any written request with your name and contact address.
No need to give reason for seeking information.
Fees: Central Govt ₹10 application fee, ₹2/page copies, ₹5/hour inspection.
State-wise fees vary (usually ₹10-50).
BPL (Below Poverty Line): completely exempt from all fees (S.7(5)).
Mode: in person, by post, or electronically via RTI Online Portal (rtionline.gov.in).
Where to file: with PIO of public authority that holds the information.
Wrong authority: PIO must transfer to correct authority within 5 days (S.6(3)).
Do NOT file with CIC/SIC directly — file with public authority first.

TIMELINES (S.7):
Normal: 30 days from receipt of application.
Life or liberty matters: 48 hours (S.7(1) proviso).
If transferred by PIO: 35 days from original receipt.
Deemed refusal: if no response within 30 days (S.7(2)).
Fee not paid: PIO must intimate within 5 days of receipt.
Public authority head can extend by further period of time with written intimation.

FIRST APPEAL (S.19(1)):
To: First Appellate Authority (FAA) of same public authority.
When: within 30 days of receipt of PIO's decision or expiry of 30-day period.
FAA must decide within 30 days (extendable to 45 days with reasons).

SECOND APPEAL (S.19(3)):
To: Central Information Commission (CIC) or State Information Commission (SIC).
When: within 90 days of FAA decision or expiry of FAA's decision period.
CIC/SIC can: direct disclosure, impose penalty on PIO, recommend disciplinary action.

EXEMPTIONS (S.8):
(a) Sovereignty, security, strategic, scientific or economic interests of India.
(b) Information expressly forbidden by courts or disclosure would constitute contempt of court.
(c) Parliamentary/Legislature privilege — breach of privilege.
(d) Commercial confidence, trade secrets, intellectual property of third parties — unless
larger public interest justifies disclosure.
(e) Information held in fiduciary relationship.
(f) Information received in confidence from foreign government.
(g) Endangers life or physical safety of any person or identifies source of information.
(h) Impedes process of investigation, prosecution or apprehension of offender.
(i) Cabinet papers, Council of Ministers records — until decision is taken AND matter complete.
(j) Personal information — no relation to public activity, unwarranted invasion of privacy.
S.8(2): All exemptions subject to override if public interest in disclosure outweighs harm.
S.9: Can refuse if involves copyright infringement.

THIRD PARTY INFORMATION (S.11):
If information relates to third party: PIO gives third party written notice within 5 days.
Third party can make representation within 10 days.
PIO decides after considering representation; third party can appeal.

PENALTIES (S.20):
S.20(1): CIC/SIC may impose ₹250/day for delay (maximum ₹25,000 per complaint).
S.20(2): CIC/SIC may recommend disciplinary action against PIO.
Penalty imposed only after PIO given reasonable opportunity to be heard.
Burden on PIO to prove denial was justified.

SPECIAL PROVISIONS:
Intelligence/security organisations (S.24): RAW, IB, CRPF etc exempt EXCEPT for
allegations of corruption or human rights violations.
RTI to political parties: CIC ruled covered (2013); parties challenged; no Supreme Court
final ruling yet; effectively parties do not comply.

Include STEP-BY-STEP RTI GUIDE, PENALTY TABLE, PRACTICAL NOTES with 6 Q&A."""
    },
    {
        "filename": "09_labour_law_pf_gratuity.txt",
        "title": "Labour Law — EPF Act 1952 and Payment of Gratuity Act 1972",
        "category": "civil_law",
        "year": 1952,
        "prompt": """Write a detailed Indian legal reference on Indian Labour Law. Include:

EMPLOYEES' PROVIDENT FUNDS AND MISC. PROVISIONS ACT, 1952:
Coverage (S.1): establishments with 20+ employees; Central Govt can extend to smaller units;
once covered always covered even if headcount falls below 20.
Three Schemes: EPF Scheme 1952 (retirement savings), EPS 1995 (pension),
EDLI Scheme 1976 (life insurance).
Contribution rates:
Employee: 12% of basic wages + DA + retaining allowance.
Employer: 12% total — 3.67% to EPF, 8.33% to EPS (capped at ₹15,000 basis),
0.5% to EDLI, 0.5% to EPF admin charges.
Wage ceiling: ₹15,000/month (employees above this can voluntarily contribute).
International workers: contribute regardless of salary limit.
UAN: Universal Account Number — portable across employers; seeded with Aadhaar and bank.
Check balance: EPFO portal (epfindia.gov.in), UMANG app, SMS to 7738299899, missed call 011-22901406.

Withdrawal rules:
Full withdrawal: retirement at 58 years, permanent total disability, leaving India permanently,
unemployment for 2+ months (75% after 1 month, 25% after 2 months — 2020 rule).
Partial withdrawal triggers and limits:
- Housing: after 5 years, 24 months' wages, for purchase/construction.
- Marriage: after 7 years, 50% of own share, for self/children/siblings.
- Education: after 7 years, 50% of own share, post matriculation.
- Medical: no minimum service, 6 months basic+DA or employee's own share (whichever less).
- COVID advance: 3 months basic+DA or 75% of balance (whichever less) — one-time.
Forms: Form 19 for EPF withdrawal, Form 10C for EPS, Form 31 for partial withdrawal.
Online claims via EPFO portal — processing: 3 days (online) to 20 days (manual).

Dispute resolution:
S.7A: EPF Commissioner (quasi-judicial) for determination of dues.
S.7B: Review of EPF Commissioner's order.
High Court: writ petition against Commissioner's order.
Recovery: S.8F — recovery certificate, attachment of property, arrest.

PAYMENT OF GRATUITY ACT, 1972:
Coverage (S.1(3)): factories, mines, oilfields, plantations, ports, railways, shops,
educational institutions with 10+ employees; once covered, always covered.
Eligibility (S.4(1)):
- 5 years continuous service on: superannuation, retirement, resignation, termination.
- Death or disablement: 5-year condition waived; payable to nominee/legal heir.
- 4 years 240 days = 5 years for workers working underground or in establishments
  where worker works less than 6 days per week (Supreme Court Ruling).
Calculation (S.4(2)):
Gratuity = Last drawn Basic + DA × 15/26 × Completed years of service.
15 days wages per year; 26 working days per month (NOT 30).
Fractions: 6+ months rounds up to 1 year; less than 6 months ignored.
Maximum gratuity: ₹20 lakhs (Notification 2018; government employees have no ceiling).
Nomination (S.6): within 30 days of completing 1 year; update within 30 days of marriage.
Forfeiture (S.4(6)):
- Wholly: if terminated for offence involving moral turpitude (conviction required).
- Partially: loss/damage to property due to wilful negligence.
Employer's duty (S.7): determine gratuity within 30 days; pay within 30 days of determination.
Delay penalty: simple interest at bank rate on delayed amount; employer also penalised.
Controlling Authority: Regional Labour Commissioner or Asst Labour Commissioner.
Criminal penalty for non-payment (S.9): 6 months to 2 years imprisonment + fine.

WORKED EXAMPLE:
Last basic+DA: ₹50,000/month; Service: 8 years 7 months (rounds to 9 years).
Gratuity = 50,000 × 15/26 × 9 = ₹2,59,615.

OTHER KEY LABOUR LAWS:
Maternity Benefit Act 1961 (amended 2017):
- 26 weeks paid leave for first two children; 12 weeks for third child onwards.
- 12 weeks for adoptive/commissioning mothers.
- Crèche facility mandatory (50+ women employees).
- Work from home option may be offered (employer's discretion).

Minimum Wages Act 1948:
- State-specific scheduled employments; central sphere separately notified.
- Revision every 5 years; interim relief periodically.
- Non-payment is criminal offence.

Payment of Bonus Act 1965:
- Eligibility: salary up to ₹21,000/month.
- Minimum bonus: 8.33% of salary (or ₹100 whichever higher).
- Maximum bonus: 20% of salary.
- Payable within 8 months of financial year end.

Code on Wages 2019 (not yet fully enforced):
Consolidates Minimum Wages Act, Payment of Wages Act, Bonus Act, Equal Remuneration Act.

Include GRATUITY CALCULATOR TABLE (multiple examples) and PRACTICAL NOTES with 6 Q&A."""
    },
    {
        "filename": "10_it_act_2000_cyber_offences.txt",
        "title": "Information Technology Act 2000 — Cyber Offences and Data Protection",
        "category": "special_law",
        "year": 2000,
        "prompt": """Write a detailed Indian legal reference for IT Act 2000 focusing on cyber offences.

DEFINITIONS (S.2): electronic record, digital signature, electronic signature, computer,
computer network, computer resource, cyber café, data, information, intermediary,
originator, addressee, subscriber.

LEGAL RECOGNITION (S.3-15):
S.3A: Electronic signature — valid if reliable method used.
S.4: Electronic records have same legal effect as paper.
S.5: Electronic signatures have same legal validity as handwritten.
S.10A: Electronic contracts valid — offer and acceptance electronically legally binding.
S.11-13: Attribution, acknowledgement, time and place of sending/receiving electronic records.

CIVIL PENALTY (S.43):
Penalty up to ₹1 crore for: unauthorised access, downloading/copying without permission,
introducing virus/contaminant, damaging computer/data, disrupting computer systems,
denying access to authorised person, providing unauthorised assistance, stealing services,
charging another's account, destruction/deletion/alteration of data.
S.43A: Body corporate (company) that handles sensitive personal data — if negligent in
maintaining reasonable security practices — must pay compensation. No cap specified.
Adjudicating Officer (S.46): appointed by Central Govt; hears compensation claims up to ₹5 crore.
TDSAT (Telecom Disputes Settlement and Appellate Tribunal): appeals.

CYBER OFFENCES AND PUNISHMENTS:
S.65: Tampering with computer source code (concealing, destroying, altering) — 3 years + ₹2 lakhs.
S.66: Dishonest/fraudulent computer-related offences (mirroring S.43 acts) — 3 years + ₹5 lakhs.
S.66A: Offensive messages — STRUCK DOWN by Supreme Court in Shreya Singhal v. UOI 2015
(unconstitutional as violates Art.19(1)(a) — too vague and overbroad).
S.66B: Dishonestly receiving stolen computer resources — 3 years + ₹1 lakh.
S.66C: Identity theft — using another's electronic signature, password, unique ID dishonestly
— 3 years + ₹1 lakh; includes SIM swapping.
S.66D: Cheating by personation using computer (phishing, fake websites) — 3 years + ₹1 lakh.
S.66E: Violation of privacy — capturing, publishing, transmitting private images without consent
— 3 years + ₹2 lakhs; includes voyeurism, non-consensual intimate image sharing.
S.66F: Cyber terrorism — acts threatening unity, integrity, sovereignty of India through
computer means; denying access to authorised personnel, penetrating critical infrastructure
— LIFE IMPRISONMENT. Cognizable, non-bailable.
S.67: Publishing obscene material in electronic form — 3 years first, 5 years repeat + fine.
S.67A: Sexually explicit material — 5 years first, 7 years repeat + fine.
S.67B: Child pornography (CSAM) — 5 years first, 7 years repeat + ₹10 lakhs;
possession also punishable; cognizable, non-bailable.
S.69: Interception, monitoring, decryption — Central/State Govt can order for national security,
public order, sovereignty; ISPs and companies must comply.
S.69A: Blocking of information — Central Govt can direct blocking of websites/apps;
used to block TikTok, Chinese apps (June 2020), VPN services.
S.69B: Monitoring and collection of traffic data for cybersecurity.
S.70: Protected system (critical infrastructure — power grids, financial systems, telecom)
— unauthorised access: 10 years + fine. Government notifies protected systems.
S.72: Breach of confidentiality by intermediaries (disclosing information without consent)
— 2 years + ₹1 lakh.
S.72A: Disclosure of information in breach of lawful contract — 3 years + ₹5 lakhs.

INTERMEDIARY LIABILITY (S.79):
Safe harbour: intermediary not liable for third-party information if:
(a) does not initiate, select, or modify transmission;
(b) observes due diligence (IT Intermediary Guidelines).
Safe harbour LOST when intermediary has actual knowledge of unlawful content and
fails to expeditiously remove or disable access.
IT (Intermediary Guidelines and Digital Media Ethics Code) Rules 2021:
Significant Social Media Intermediaries (SSMI — 5 million+ users): must appoint
Chief Compliance Officer (Indian citizen), Nodal Contact Person, Grievance Officer (India-based,
respond in 24 hours, resolve in 15 days), monthly compliance reports.
Messaging platforms: must identify first originator of message on court/government order.
OTT platforms and digital news: subject to content code and three-tier grievance mechanism.

CERT-In (S.70B): Indian Computer Emergency Response Team — national cybersecurity agency.
CERT-In Directions April 2022: mandatory incident reporting within 6 hours (not 72 hours like GDPR);
5-year log retention; VPN providers must maintain subscriber info for 5 years even after cancellation;
data centres, cloud providers, crypto exchanges must also report.

DATA PROTECTION:
IT (Reasonable Security Practices and Procedures and SPDI) Rules 2011:
SPDI = passwords, financial info, health info, sexual orientation, biometric data.
Companies must obtain consent before collecting SPDI; publish privacy policy.
Digital Personal Data Protection Act 2023 (DPDPA):
Replaces SPDI rules; establishes Data Protection Board; rights of Data Principals;
obligations of Data Fiduciaries; significant data fiduciaries; cross-border transfer rules;
consent framework; children's data protection; penalties up to ₹250 crore.

Include CYBER OFFENCE QUICK REFERENCE TABLE (offence, section, punishment, cognizable/not)
and PRACTICAL NOTES with 6 citizen Q&A."""
    },
    {
        "filename": "11_domestic_violence_pocso.txt",
        "title": "PWDVA 2005 and POCSO Act 2012",
        "category": "special_law",
        "year": 2005,
        "prompt": """Write a detailed Indian legal reference covering two Acts:

PROTECTION OF WOMEN FROM DOMESTIC VIOLENCE ACT, 2005 (PWDVA):

Key Definitions (S.2):
Aggrieved person (S.2(a)): any woman who is or has been in a domestic relationship
with the respondent and alleges to have been subjected to domestic violence.
Domestic relationship (S.2(f)): relationship between two persons who live or have lived
together in a shared household, related by consanguinity, marriage, adoption, or
as members of joint family — explicitly includes live-in relationships
(D. Velusamy v. D. Patchaiammal 2010 SC — live-in must be like marriage).
Respondent (S.2(q)): adult male member; also female relative of husband/male partner
can be respondent (Supreme Court — can file against mother-in-law, sister-in-law).
Shared household (S.2(s)): household where aggrieved person lives or has lived with
respondent — includes owned or rented by either party; joint family property included.

Domestic Violence (S.3 + Explanation I):
Physical abuse: any act causing bodily pain, harm, danger to life/limb/health —
hitting, slapping, kicking, punching, biting, burning, throwing objects.
Sexual abuse: sexual conduct that abuses, humiliates, degrades — forced intercourse,
forced pornography, any unwanted sexual act.
Verbal and emotional abuse: insults, ridicule, humiliation regarding failure to bring
dowry, not having a child, having female child; name calling; threats to cause physical
pain to aggrieved person, children, relatives; repeated threats to cause hurt.
Economic abuse: depriving of financial resources needed for maintenance;
disposing of household assets without consent; preventing employment;
not providing maintenance/money for household expenses.

Key Functionaries:
Protection Officer (PO) (S.9): government designated officer; assists in filing application,
obtaining medical aid, shelter; files Domestic Incident Report (DIR) within 48 hours.
Service Provider (S.10): registered NGO authorised to provide shelter, medical, legal aid
and can record DIR.
Magistrate (S.12): First Class Judicial Magistrate or Metropolitan Magistrate — main forum.
Police (S.5): must inform aggrieved person of right to file complaint and seek help of PO.

Orders Available (S.18-22):
S.18 Protection Order: prohibit respondent from committing acts of DV; entering workplace,
school of child, aggrieved person's place; attempting to communicate; using assets.
S.19 Residence Order: respondent not to dispossess aggrieved from shared household;
alternate accommodation at respondent's cost; remove respondent from shared household.
S.20 Monetary Relief: maintenance, medical expenses, loss of earnings, loss to property.
Not limited by maintenance under other laws; can be in addition to maintenance under CrPC S.125.
S.21 Custody Order: temporary custody of children to aggrieved person.
S.22 Compensation Order: compensation for mental torture, emotional distress, injuries.
S.23 Interim Orders: ex parte orders on affidavit if prima facie case and need for urgency;
no need to serve notice on respondent for ex parte relief.

Procedure (S.12-28):
Application: by aggrieved person, PO, or any person on her behalf (unlike criminal law — no FIR needed).
First hearing: within 3 days (S.12(4)).
Disposal: within 60 days (S.12(5) proviso).
S.14: Magistrate may direct counselling.
S.28: Procedure under CrPC 1973 (as amended); but nature is civil (not criminal conviction).
S.31: Breach of protection order — cognizable, non-bailable offence; up to 1 year + ₹20,000 fine.
S.33: Protection officer failing duties — up to 1 year + ₹20,000 fine.

COMPARISON WITH IPC S.498A:
IPC S.498A: criminal offence by husband and relatives (cruelty — cognizable, non-bailable, 3 years);
results in criminal conviction.
PWDVA: civil remedy; results in orders (protection, residence, maintenance, compensation);
no criminal conviction; but breach is criminal offence.
Both can be used simultaneously by aggrieved person.

PROTECTION OF CHILDREN FROM SEXUAL OFFENCES ACT, 2012 (POCSO):

Scope: Protects all children below 18 years (regardless of gender) from sexual offences.
Gender neutral for victims; applies even when accused is also a child (tried as juvenile).

Key Offences and Punishments:
S.3-4: Penetrative sexual assault — minimum 10 years rigorous imprisonment, maximum life + fine.
S.5-6: Aggravated penetrative sexual assault (by police officer, armed forces, public servant,
teacher, relative, on child below 12 years, gang assault, during armed conflict,
pregnancy-causing, mentally disabled child, life-threatening injury) —
minimum 20 years RI to life imprisonment or death (for child below 12 — 2019 amendment).
S.7-8: Sexual assault (non-penetrative — touching private parts with sexual intent) —
minimum 3 years, maximum 5 years + fine.
S.9-10: Aggravated sexual assault — minimum 5 years, maximum 7 years + fine.
S.11-12: Sexual harassment (words, gestures, cyberstalking, showing pornography to child)
— up to 3 years + fine.
S.13-15: Using child for pornographic purposes — S.13 up to 5 years;
S.14 if penetrative assault also — minimum 10 years to life;
S.15 storage/possession of CSAM for commercial purpose — up to 3 years + fine.

Key Protective Provisions:
S.19: Mandatory reporting — ANY person who knows or believes an offence has been committed
MUST report to Special Juvenile Police Unit or local police. Failure to report: S.21 up to 6 months + fine.
S.22: False complaint — punishable (1 year/fine) but burden on accused to prove; protects children.
S.23: Media prohibited from disclosing identity of child (except for recovery purposes).
S.24: Statement of child to be recorded by Magistrate; interpreter if needed.
S.26: Child-friendly procedure — statement at child's residence or convenient place;
only one statement to be recorded; no repeat questioning; no aggressive questioning.
S.27: Medical examination in presence of parent/trusted adult; by woman doctor for girl child.
S.28: Special Courts designated for POCSO trials in every district.
S.29: Presumption — if sexual assault proved, court PRESUMES it was without consent
and the accused intended; burden shifts to accused to prove otherwise.
S.33: Child not to face accused directly; screen/video-link permitted; frequent breaks.
S.35: Trial must be completed within 1 year of taking cognizance.
S.36: Child's identity absolutely confidential — no publication by media.
S.42: Where POCSO offence is also IPC offence — higher punishment applies;
both can be charged simultaneously.

Include PWDVA vs IPC S.498A COMPARISON TABLE,
POCSO OFFENCE QUICK REFERENCE TABLE, and PRACTICAL NOTES with 6 Q&A."""
    },
    {
        "filename": "12_limitation_act_glossary.txt",
        "title": "Limitation Act 1963 and Indian Legal Glossary",
        "category": "reference",
        "year": 1963,
        "prompt": """Write a detailed Indian legal reference covering two parts:

PART A — LIMITATION ACT, 1963:

KEY PRINCIPLES:
S.2: Definitions — period of limitation, prescribed period, suit, application, appeal.
S.3: Bar — every suit/appeal/application filed after prescribed period shall be dismissed
even if defendant does not raise limitation as defence; court applies suo motu.
S.4: Expiry on court holiday — limitation extends to next day court is open.
S.5: Condonation of delay — court may condone delay for appeals and applications if
sufficient cause shown; does NOT apply to suits; discretionary.
S.6: Legal disability — minor, insane person or idiot — time runs from cessation of disability.
S.12: Exclusion of time — time spent obtaining copy of decree/order excluded from limitation.
S.14: Exclusion of time in bona fide proceedings — time spent prosecuting in wrong court
(with due diligence and in good faith) excluded.
S.15: Exclusion of time during injunction/stay order.
S.17: Fraud or mistake — limitation runs from discovery of fraud or mistake.
S.18: Acknowledgement — fresh period from date of signed acknowledgement of liability.
S.19: Part payment — fresh period from date of payment towards debt.
S.25: Acquisition of easement by prescription — 20 years uninterrupted enjoyment.

IMPORTANT LIMITATION PERIODS (from Schedule):
SUITS:
Money due on contract: 3 years from when money falls due.
Recovery of price of goods sold: 3 years from date of delivery.
Recovery of salary: 3 years from when salary due.
Money lent: 3 years from date of loan.
Compensation for breach of contract: 3 years from date of breach.
Compensation for personal injury (tort): 3 years from date of injury.
Compensation for libel/slander: 1 year.
Compensation for malicious prosecution: 3 years.
Recovery of specific moveable property: 3 years.
Recovery of immoveable property (based on title): 12 years.
Redemption of mortgage: 30 years.
Foreclosure of mortgage: 30 years.
Suit by government: 30 years.

APPEALS:
High Court appeal from District Court: 90 days.
High Court appeal from subordinate court (other): 30 days.
Supreme Court appeal from High Court: 90 days.
First appeal (civil): 30 days from date of decree/order.
Second appeal: 90 days.
Appeal under CPC: 30 or 90 days depending on court.

APPLICATIONS:
Execution of decree (moveable): 3 years from date decree becomes enforceable.
Execution of decree (immoveable/any other): 12 years.
Revision: 90 days.
Review: 30 days.
Setting aside ex parte decree: 30 days.

CONSUMER COMPLAINTS:
Consumer Protection Act 2019 S.69: 2 years from cause of action; delay can be condoned.

CRIMINAL LIMITATION (CrPC S.468):
Fine only offence: 6 months.
Up to 1 year imprisonment: 1 year.
Up to 3 years imprisonment: 3 years.
Above 3 years: no bar on cognizance.

PART B — LEGAL GLOSSARY (50+ terms, A-Z):
Accused: Person charged with a criminal offence; not yet convicted.
Acquittal: Court's finding that accused is not guilty; bars re-trial for same offence.
Adjournment: Postponement of hearing to a future date.
Affidavit: Written statement of facts sworn before an oath commissioner or notary.
Anticipatory Bail: Bail obtained before arrest; granted under CrPC S.438.
Bail: Temporary release of accused from custody on furnishing security.
Bail Bond: Written undertaking to appear in court and comply with bail conditions.
Bailable Offence: Offence where bail is a right (listed as bailable in 1st Schedule CrPC).
Burden of Proof: Obligation to prove a fact; in criminal law on prosecution (beyond reasonable doubt);
in civil law on plaintiff (balance of probabilities).
Cause of Action: Facts giving rise to a legal right to sue; determines limitation period.
Caveat: Notice filed in court requesting that no ex parte order be passed without hearing the caveator.
Chargesheet: Police report filed under CrPC S.173 after investigation; triggers trial.
Civil Suit: Legal proceedings to enforce civil rights or seek compensation; not criminal.
Cognizable Offence: Offence where police can arrest without warrant (listed in 1st Schedule CrPC).
Complaint: Oral or written allegation made to Magistrate.
Compoundable Offence: Offence that can be settled between parties (S.320 CrPC).
Conviction: Court's finding that accused is guilty of the offence charged.
Court: Includes Supreme Court, High Courts, District Courts, Subordinate Courts, Tribunals.
Culpable Homicide: Causing death with intent/knowledge; if amounts to murder = IPC S.302.
Decree: Formal expression of adjudication in civil suit; final/preliminary/preliminary-cum-final.
Default Bail: Bail granted under CrPC S.167(2) when chargesheet not filed within 60/90 days.
Defendant: Person against whom civil suit is filed (accused in criminal case).
Defamation: Making false statement of fact that harms reputation; civil and criminal remedy.
Ex Parte: Order/hearing in absence of one party (usually defendant who was served but absent).
FIR (First Information Report): Information given to police regarding cognizable offence (CrPC S.154).
Grievous Hurt: Eight specific categories under IPC S.320 — fractures, permanent loss of organs, etc.
Habeas Corpus: Writ directing production of detained person before court.
Injunction: Court order to do or refrain from doing an act; temporary or permanent.
Jurisdiction: Court's authority to hear a case — territorial, pecuniary, subject matter.
Locus Standi: Legal right/standing to bring an action in court.
Magistrate: Judicial officer who tries petty cases and commits serious cases to Sessions Court.
Mandamus: Writ commanding public authority to perform its public duty.
Mens Rea: Criminal intention or knowledge; required element of most offences.
Non-Bailable Offence: Offence where bail is discretionary, not a right.
Non-Cognizable Offence: Offence where police need magistrate's order to arrest.
Plaintiff: Person who files civil suit.
Pleadings: Written statements — plaint and written statement — exchanged between parties.
Prima Facie: On first appearance; sufficient evidence to proceed; may be rebutted.
Probation: Supervised release instead of prison for first-time or minor offenders.
Prohibition: Writ stopping inferior court from exceeding its jurisdiction.
Quo Warranto: Writ challenging by what authority a person holds a public office.
Remand: Sending accused into custody by Magistrate pending investigation or trial.
Sessions Court: Principal criminal court of a district; tries serious offences.
Stay Order: Court order temporarily halting proceedings or execution of order.
Sub Judice: Matter under consideration by court; cannot be commented upon prejudicially.
Summons: Court's written order directing person to appear before it.
Suo Motu: On its own motion; court takes action without application by any party.
Surety: Person who gives security for another's appearance in court.
Trial: Judicial examination of issues in civil or criminal proceedings.
Warrant: Court's written order directing police to arrest a person or search premises.
Writ: Written order issued by High Court or Supreme Court under Art.226 or Art.32.
Zero FIR: FIR filed at any police station regardless of territorial jurisdiction;
transferred to jurisdictional station afterwards.

Include LIMITATION PERIODS QUICK REFERENCE TABLE and end with DISCLAIMER note."""
    },
]


def file_needs_generation(filepath: Path) -> bool:
    if not filepath.exists():
        return True
    content = filepath.read_text(encoding="utf-8", errors="ignore")
    word_count = len(content.split())
    if word_count < MIN_WORDS:
        log.warning(f"  {filepath.name}: only {word_count} words — will regenerate")
        return True
    log.info(f"  {filepath.name}: {word_count} words — OK, skipping")
    return False


def build_frontmatter(doc: dict, word_count: int) -> str:
    return (
        f"---\n"
        f"title: {doc['title']}\n"
        f"category: {doc['category']}\n"
        f"source: Government of India — {doc['title']}\n"
        f"year: {doc['year']}\n"
        f"generated_at: {datetime.now().strftime('%Y-%m-%d')}\n"
        f"word_count: {word_count}\n"
        f"---"
    )


def generate_with_groq(doc: dict, client) -> bool:
    filepath = DOCS_DIR / doc["filename"]
    log.info(f"  Generating via Groq: {doc['filename']}")
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=4000,
            temperature=0.1,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a precise Indian legal reference writer. "
                        "Write accurate, thorough legal reference documents. "
                        "Use plain text: === for major headings, --- for sub-sections. "
                        "Include section numbers, full provisions, punishments, "
                        "illustrations, and practical citizen notes. Be complete."
                    )
                },
                {"role": "user", "content": doc["prompt"]}
            ]
        )
        content = response.choices[0].message.content.strip()
        word_count = len(content.split())
        frontmatter = build_frontmatter(doc, word_count)
        filepath.write_text(f"{frontmatter}\n\n{content}", encoding="utf-8")
        log.info(f"  Saved: {doc['filename']} ({word_count:,} words)")
        return True
    except Exception as e:
        log.error(f"  Groq failed for {doc['filename']}: {e}")
        return False


def main():
    groq_key = os.getenv("GROQ_API_KEY", "")
    if not groq_key:
        log.error(
            "GROQ_API_KEY not set.\n"
            "  1. Go to https://console.groq.com and sign up (free)\n"
            "  2. Create an API key\n"
            "  3. Add GROQ_API_KEY=gsk_... to your .env file\n"
            "  Then re-run this script."
        )
        sys.exit(1)

    try:
        from groq import Groq
        client = Groq(api_key=groq_key)
        log.info("Groq client initialised OK")
    except ImportError:
        log.error("groq package not installed. Run: pip install groq")
        sys.exit(1)

    log.info(f"\nChecking {len(DOCS)} documents in {DOCS_DIR}\n")
    to_generate = [d for d in DOCS if file_needs_generation(DOCS_DIR / d["filename"])]

    if not to_generate:
        log.info("\nAll documents present and sufficient. Nothing to generate.")
        return

    log.info(f"\n{len(to_generate)} document(s) need generation:")
    for d in to_generate:
        log.info(f"  - {d['filename']}")

    results = {"ok": [], "fail": []}
    for i, doc in enumerate(to_generate, 1):
        log.info(f"\n[{i}/{len(to_generate)}]")
        ok = generate_with_groq(doc, client)
        (results["ok"] if ok else results["fail"]).append(doc["filename"])
        if i < len(to_generate):
            time.sleep(2)

    log.info(f"\n{'='*50}")
    log.info(f"Done. Generated: {len(results['ok'])} | Failed: {len(results['fail'])}")
    if results["fail"]:
        for f in results["fail"]:
            log.error(f"  FAILED: {f}")
    log.info("\nNext step: python -m knowledge_base.ingest")


if __name__ == "__main__":
    main()
