from typing import Optional, List, Dict, Any
from ..models.query import QueryRequest, IntentClassification, OperationalMode, QueryCategory
from ..models.response import GroundedAnswer, EvidenceSnippet, MissingInfoItem
from .guardrails import guardrail_service


class GeneralQAService:
    """
    Handles Mode 3 (General / No-Document Legal Information) queries.
    Strictly preserves the 5-way information separation:
      - document_facts (always empty in Mode 3)
      - user_provided_facts (stated by user in situation context)
      - external_law (statutory provisions or prepared retrieval specs)
      - plain_language_interpretation (accessible plain-English explanation)
      - uncertainty_and_gaps (missing jurisdiction, unstated circumstances)
    """

    @classmethod
    def answer_general_query(
        cls,
        request: QueryRequest,
        intent: IntentClassification
    ) -> GroundedAnswer:
        query_text = request.query.strip()
        query_lower = query_text.lower()

        # Audit for prompt injection in user query
        injection_flags = guardrail_service.inspect_untrusted_document(query_text)

        # Extract user-provided facts if situation was provided
        user_facts = []
        if request.situation and request.situation.raw_description.strip():
            user_facts.append(f"User stated situation: {request.situation.raw_description.strip()}")
            if request.situation.declared_role:
                user_facts.append(f"User declared role: {request.situation.declared_role.value}")

        # Case 1: Missing Jurisdiction for Statutory/Legal Rule Question
        if intent.is_jurisdiction_missing:
            return cls._handle_missing_jurisdiction(request, intent, user_facts, injection_flags)

        # Case 2: Jurisdiction-Specific External Law Question
        if intent.requires_external_law and intent.target_jurisdiction:
            return cls._handle_jurisdiction_specific(request, intent, user_facts, injection_flags)

        # Case 3: Pure Conceptual Question (e.g., "What is an indemnity clause?")
        return cls._handle_conceptual_question(request, intent, user_facts, injection_flags)

    @classmethod
    def _handle_conceptual_question(
        cls,
        request: QueryRequest,
        intent: IntentClassification,
        user_facts: List[str],
        injection_flags: List[str]
    ) -> GroundedAnswer:
        query_lower = request.query.lower()

        # Identify core concept
        if "indemnity" in query_lower:
            concept_title = "Indemnity Clause"
            meaning = (
                "An indemnity clause is a contractual promise where one party (the indemnifying party) "
                "agrees to reimburse or shield the other party (the indemnified party) against specific "
                "losses, damages, or third-party liabilities that arise from the performance or breach of the contract."
            )
            why_it_matters = (
                "Indemnity clauses shift financial risk between contracting parties. If a third party sues "
                "or if a specified event occurs, the indemnifying party may be responsible for paying legal fees "
                "and financial damages."
            )
            check_next = [
                "Review whether the clause contains a monetary liability cap (financial limit).",
                "Check whether the indemnity covers direct losses only or extends to indirect/consequential damages.",
                "Verify whether both parties provide mutual indemnities or if it is one-sided.",
                "Locate any specific exclusions (such as losses resulting from gross negligence or willful misconduct)."
            ]
        elif "lock-in" in query_lower:
            concept_title = "Lock-in Period"
            meaning = (
                "A lock-in period is a defined timeframe in a lease or commercial agreement during which "
                "neither party is permitted to terminate the contract for convenience without incurring a penalty."
            )
            why_it_matters = (
                "If a party terminates or vacates prior to the expiration of the lock-in period, the contract "
                "frequently requires paying the balance of rent for the remaining unexpired months or forfeiting the security deposit."
            )
            check_next = [
                "Verify the exact start date and expiration date of the lock-in period.",
                "Check whether exceptions exist for termination due to uncured material breach by the counterparty.",
                "Review deposit forfeiture provisions upon early departure."
            ]
        elif "liquidated damages" in query_lower:
            concept_title = "Liquidated Damages"
            meaning = (
                "Liquidated damages are a predetermined, contractually agreed sum that one party must pay "
                "if they breach specific contractual obligations (such as missing project delivery milestones)."
            )
            why_it_matters = (
                "Liquidated damages allow parties to establish compensation in advance without having to prove "
                "actual monetary losses in court, provided the sum represents a reasonable pre-estimate of loss rather than an unlawful penalty."
            )
            check_next = [
                "Verify whether the agreed sum is a genuine pre-estimate of loss under applicable contract law.",
                "Check whether proof of actual loss is required by local governing courts."
            ]
        else:
            concept_title = "Legal Contract Concept"
            meaning = (
                f"This concept pertains to contractual rights and obligations in commercial and personal agreements: '{request.query}'. "
                "In contract law, clauses are interpreted based on their plain language and surrounding context."
            )
            why_it_matters = "Contract clauses allocate risk, define timelines, and establish performance obligations between parties."
            check_next = [
                "Examine the exact text of the provision in your specific contract.",
                "Check governing law and dispute resolution clauses to understand applicable interpretations."
            ]

        labels = ["Important", "Informational"]
        if injection_flags:
            labels.append("Security Audit Flag")

        return GroundedAnswer(
            document_facts=[],  # Strictly empty in Mode 3
            user_provided_facts=user_facts,
            external_law=[],    # Conceptual questions do not require external citations
            plain_language_interpretation=meaning,
            uncertainty_and_gaps=[
                "This is general legal information describing standard commercial contract concepts.",
                "How a clause operates in practice depends on the precise wording of your signed contract and governing jurisdiction."
            ],
            answer=f"{concept_title}: {meaning.split('.')[0]}.",
            what_the_document_says=None,
            what_this_means_in_plain_language=meaning,
            why_it_matters_to_your_situation=why_it_matters,
            what_is_unclear_or_missing=(
                "No specific document or governing jurisdiction was provided. The exact legal effect "
                "depends on your specific contract wording and local law."
            ),
            what_to_check_next=check_next,
            sources=[],
            missing_info_details=[],
            inconsistencies=[],
            neutral_labels=labels,
            operational_mode=OperationalMode.MODE_3_GENERAL_NO_DOC,
            query_category=QueryCategory.B_DOCUMENT_INTERPRETATION,
            evidence_sufficiency_passed=True,
            professional_review_recommended=False
        )

    @classmethod
    def _handle_jurisdiction_specific(
        cls,
        request: QueryRequest,
        intent: IntentClassification,
        user_facts: List[str],
        injection_flags: List[str]
    ) -> GroundedAnswer:
        jurisdiction = intent.target_jurisdiction or "Specified Jurisdiction"
        query_lower = request.query.lower()
        situation_lower = (request.situation.raw_description.lower() if request.situation and request.situation.raw_description else "")
        combined_text = f"{query_lower} {situation_lower}".strip()

        # Domain classification
        is_tenancy = any(k in combined_text for k in ["tenan", "lease", "landlord", "rent", "evict", "vacate", "demised", "premises", "flat", "apartment"])
        is_pf = any(k in combined_text for k in ["provident", "pf", "epf", "provident fund", "gratuity", "pension"])
        is_employment = is_pf or any(k in combined_text for k in ["employ", "job", "salary", "bonus", "wage", "severance", "workplace", "labor", "labour", "resignation", "fired"]) or (request.situation and request.situation.declared_role and request.situation.declared_role.value in ["employee", "employer"])

        external_law_data = []

        if is_pf and "india" in jurisdiction.lower():
            # Domain: Indian Provident Fund / EPF
            external_law_data.append({
                "statute": "Employees' Provident Funds and Miscellaneous Provisions Act, 1952",
                "section": "Section 6 / Section 14B",
                "enactment_year": 1952,
                "summary": (
                    "Under the Employees' Provident Funds and Miscellaneous Provisions Act, 1952, accumulated provident fund "
                    "contributions (both employee deductions and employer contributions) are statutory entitlements held in trust. "
                    "An employer has a mandatory duty to remit statutory contributions to the EPFO and cannot arbitrarily deny, "
                    "withhold, or forfeit statutory provident fund savings upon separation, subject to establishment coverage under the Act (generally 20 or more employees)."
                ),
                "currency_status": "Active central legislation; administered under the Employees' Provident Fund Organisation (EPFO) regulations."
            })
            statutory_summary = (
                f"Under Indian employment law ({jurisdiction}), statutory provident fund (EPF) benefits are protected by statute "
                "under the Employees' Provident Funds and Miscellaneous Provisions Act, 1952. An employer cannot unilaterally deny or "
                "forfeit an employee's statutory provident fund accumulations upon termination or resignation. Both the employee's deducted "
                "share and the employer's statutory contribution belong to the employee's provident fund account held in trust. However, "
                "whether your employer establishment is subject to the Act (requires 20+ employees), whether contributions were properly credited "
                "to your Universal Account Number (UAN), and whether voluntary non-statutory benefits are at issue must be formally verified."
            )
            why_it_matters = (
                "Provident fund savings are legally protected statutory retirement benefits. If an employer has deducted PF from salary but failed "
                "to remit it, or is withholding final settlement disbursement, the employee may initiate statutory grievance proceedings through the EPFO."
            )
            unclear_missing = (
                "Whether your employer is an establishment covered under the EPF Act (20+ employees), your active Universal Account Number (UAN) status, "
                "and whether a formal written refusal or deduction discrepancy was issued by the employer."
            )
            check_next = [
                "Check your EPFO Member Passbook online using your UAN to verify monthly employer and employee contributions.",
                "Review your monthly salary slips to confirm whether PF deductions were subtracted from your pay.",
                "Check your appointment letter, offer letter, and formal relieving/exit documentation.",
                "If statutory PF is being withheld unlawfully, file a grievance on the EPFiGMS portal or consult an employment law advocate."
            ]
            uncertainties = [
                f"Identified governing jurisdiction: {jurisdiction}.",
                "Statutory coverage applies to establishments employing 20 or more persons under the EPF Act, 1952.",
                "Factual records (e.g. UAN passbook entries, appointment letters, salary slips) have not been verified against documentary evidence."
            ]
        elif is_employment:
            # Domain: General Employment / Labor
            external_law_data.append({
                "statute": f"{jurisdiction} Employment Standards & Labor Law",
                "section": "Governing Employment Statutes",
                "summary": f"Statutory rights, termination guidelines, and wage/benefit protections under {jurisdiction} employment legislation.",
                "currency_status": "Verification required against current gazetted labor codes."
            })
            statutory_summary = (
                f"Under {jurisdiction} employment law, statutory regulations provide baseline employee protections regarding notice periods, "
                "lawful termination procedures, and payment of accrued wages and statutory benefits. Written employment contracts define individual "
                "terms, but cannot contract out of mandatory statutory protections."
            )
            why_it_matters = (
                "Employment standards establish minimum protections that apply regardless of informal employer statements. Formal documentation "
                "determines whether standard procedures or statutory remedies apply."
            )
            unclear_missing = (
                "Whether an executed employment contract, appointment letter, or written termination notice exists, and the specific terms stated therein."
            )
            check_next = [
                "Locate your written employment contract, offer letter, or employee handbook.",
                "Preserve all formal written communications, separation letters, and HR correspondence.",
                "Gather salary slips and terminal benefit documentation."
            ]
            uncertainties = [
                f"Identified governing jurisdiction: {jurisdiction}.",
                "Written contracts can provide terms more favorable than statutory minimums, but cannot contract out of mandatory protections.",
                "Factual status (e.g. employment contract terms, wage records) has not been verified against an uploaded document."
            ]
        elif is_tenancy and "india" in jurisdiction.lower():
            # Domain: Indian Tenancy Law
            external_law_data.append({
                "statute": "Transfer of Property Act, 1882",
                "section": "Section 106",
                "enactment_year": 1882,
                "summary": (
                    "In the absence of a contract or local law to the contrary, a lease of immovable property for "
                    "any other purpose (such as residential or commercial) shall be deemed to be a lease from month to month, "
                    "terminable on fifteen (15) days' notice expiring with the end of a month of the tenancy."
                ),
                "currency_status": "Active statutory framework; subject to state rent control acts and Model Tenancy Act provisions where adopted."
            })
            statutory_summary = (
                f"Under Indian law ({jurisdiction}), the baseline statutory notice period for month-to-month residential tenancies "
                "is 15 days under Section 106 of the Transfer of Property Act, 1882, UNLESS the parties have agreed in writing "
                "to a different notice period (such as 30 or 60 days). Written contract terms generally govern notice duration."
            )
            why_it_matters = (
                "Statutory provisions establish baseline rights, but written contracts may provide different notice periods. "
                "You should verify whether a written agreement exists and what notice period it specifies."
            )
            unclear_missing = (
                "Whether a signed lease agreement exists, the lease commencement date, and whether any default occurred."
            )
            check_next = [
                "Check whether you have an executed written lease agreement.",
                "Determine the start date and duration of your tenancy.",
                "Verify whether local state tenancy or rent control acts apply to your property."
            ]
            uncertainties = [
                f"Identified governing jurisdiction: {jurisdiction}.",
                "Written agreements can alter statutory notice periods unless mandatory public policy or local rent control applies.",
                "Factual status (e.g. lease duration, written contract existence) has not been verified against an uploaded document."
            ]
        elif is_tenancy and "california" in jurisdiction.lower():
            # Domain: California Tenancy Law
            external_law_data.append({
                "statute": "California Civil Code",
                "section": "Section 1946 / 1946.1",
                "summary": (
                    "Landlords are required to give 30 days written notice for tenancies under one year, "
                    "and 60 days written notice for residential tenancies of one year or more, subject to Tenant Protection Act of 2019 just-cause requirements."
                ),
                "currency_status": "Active statutory law; amended by California Tenant Protection Act (AB 1482)."
            })
            statutory_summary = (
                f"Under California law ({jurisdiction}), statutory notice requirements depend on tenancy duration "
                "(30 days for tenancies under 1 year; 60 days for tenancies over 1 year), and may require statutory 'just cause' "
                "under the California Tenant Protection Act."
            )
            why_it_matters = (
                "Statutory notice thresholds in California protect tenants from abrupt termination, but depend on whether the tenancy exceeds 12 months."
            )
            unclear_missing = (
                "The duration of the tenancy, whether the property is subject to AB 1482 rent caps/just-cause rules, and whether written notice was properly served."
            )
            check_next = [
                "Determine the precise move-in date to verify whether tenancy exceeds 12 months.",
                "Check whether your rental unit is exempt from the California Tenant Protection Act.",
                "Verify how written notice was formally served."
            ]
            uncertainties = [
                f"Identified governing jurisdiction: {jurisdiction}.",
                "Applicability of 30 vs 60 days depends on verified duration.",
                "Factual status has not been verified against an uploaded document."
            ]
        else:
            # Domain: Neutral Statutory Framework
            external_law_data.append({
                "statute": f"{jurisdiction} Statutory Framework",
                "section": "Applicable governing law",
                "summary": f"Statutory rules under {jurisdiction} legislation.",
                "currency_status": "Verification required against current gazetted statutes."
            })
            statutory_summary = (
                f"Under {jurisdiction} law, statutory rules provide default guidelines and mandatory legal protections. "
                "Where a valid written agreement exists, its terms typically govern the parties' relationship unless statutory mandates prescribe minimum standards."
            )
            why_it_matters = (
                "Statutory provisions establish baseline legal rights, but individual contract terms or specific factual circumstances often determine applicable remedies."
            )
            unclear_missing = (
                "No specific document or factual record was provided. The exact legal effect depends on your specific contract wording, factual circumstances, and local governing law."
            )
            check_next = [
                "Gather and review any relevant written agreements, correspondence, or notices.",
                "Clarify the specific factual timeline and communication history with the counterparty.",
                "Consult legal counsel in your jurisdiction with the relevant records."
            ]
            uncertainties = [
                f"Identified governing jurisdiction: {jurisdiction}.",
                "Factual status has not been verified against an uploaded document.",
                "Written agreements can alter statutory baselines unless mandatory statutory protections apply."
            ]

        labels = ["Important", "Review", "External Law Framework"]
        if injection_flags:
            labels.append("Security Audit Flag")

        return GroundedAnswer(
            document_facts=[],  # Strictly empty in Mode 3
            user_provided_facts=user_facts,
            external_law=external_law_data,
            plain_language_interpretation=statutory_summary,
            uncertainty_and_gaps=uncertainties,
            answer=statutory_summary,
            what_the_document_says=None,
            what_this_means_in_plain_language=statutory_summary,
            why_it_matters_to_your_situation=why_it_matters,
            what_is_unclear_or_missing=unclear_missing,
            what_to_check_next=check_next,
            sources=[],
            missing_info_details=[],
            inconsistencies=[],
            neutral_labels=labels,
            operational_mode=OperationalMode.MODE_3_GENERAL_NO_DOC,
            query_category=QueryCategory.E_EXTERNAL_LEGAL_INFO,
            evidence_sufficiency_passed=True,
            professional_review_recommended=True
        )

    @classmethod
    def _handle_missing_jurisdiction(
        cls,
        request: QueryRequest,
        intent: IntentClassification,
        user_facts: List[str],
        injection_flags: List[str]
    ) -> GroundedAnswer:
        query_lower = request.query.lower()
        situation_lower = (request.situation.raw_description.lower() if request.situation and request.situation.raw_description else "")
        combined_text = f"{query_lower} {situation_lower}".strip()

        is_tenancy = any(k in combined_text for k in ["tenan", "lease", "landlord", "rent", "evict", "vacate"])
        is_employment = any(k in combined_text for k in ["employ", "job", "salary", "bonus", "provident", "pf", "epf", "gratuity", "wage", "severance"])

        if is_tenancy:
            explanation = (
                "Statutory notice periods, eviction procedures, and tenant protections vary fundamentally by jurisdiction, "
                "often depending on whether the tenancy is periodic or month-to-month, local statutory frameworks, and whether written notice is mandatory. "
                "Because notice requirements differ across states, provinces, and countries, an applicable rule cannot be provided without knowing the governing jurisdiction. "
                "Please specify your jurisdiction (city, state, or country) to receive accurate legal information."
            )
            field_desc = "The state, province, or country where the property or agreement is located."
            check_doc = "Optionally upload your agreement if you have a written lease."
        elif is_employment:
            explanation = (
                "Statutory employment standards, termination notice periods, and mandatory benefits (such as severance or retirement protections) "
                "vary fundamentally by jurisdiction. Because labor legislation differs across states and countries, an applicable rule cannot be "
                "provided without knowing the governing jurisdiction. Please specify your jurisdiction (city, state, or country) to receive accurate legal context."
            )
            field_desc = "The state, province, or country where the employment is situated."
            check_doc = "Optionally upload your employment agreement or appointment letter."
        else:
            explanation = (
                "Statutory requirements, mandatory notice periods, and governing legal protections vary fundamentally by jurisdiction. "
                "Because governing rules differ across states, provinces, and countries, an applicable rule cannot be provided without knowing "
                "the governing jurisdiction. Please specify your jurisdiction (city, state, or country) to receive accurate legal information."
            )
            field_desc = "The state, province, or country governing your situation."
            check_doc = "Optionally upload your agreement or document if you have one."

        missing_items = [
            MissingInfoItem(
                field_name="jurisdiction",
                description=field_desc,
                why_it_matters="Statutory rights, notice periods, and mandatory protections are entirely jurisdiction-specific.",
                framework_context="Statutory Legal Framework Requirement"
            )
        ]

        labels = ["Missing Information", "Unclear", "Clarification Required"]
        if injection_flags:
            labels.append("Security Audit Flag")

        return GroundedAnswer(
            document_facts=[],
            user_provided_facts=user_facts,
            external_law=[],
            plain_language_interpretation=explanation,
            uncertainty_and_gaps=[
                "Missing required parameter: Jurisdiction.",
                "Cannot determine applicable statutory rule without state/country jurisdiction."
            ],
            answer="Jurisdiction required: Statutory notice rules differ substantially across states and countries. Please specify your jurisdiction.",
            what_the_document_says=None,
            what_this_means_in_plain_language=explanation,
            why_it_matters_to_your_situation=(
                "Providing your location allows the system to identify the governing legislation rather than providing inapplicable legal information."
            ),
            what_is_unclear_or_missing="Applicable jurisdiction (city, state, country) is not specified.",
            what_to_check_next=[
                "Specify your city, state, or country (e.g., State/Province, Country).",
                check_doc
            ],
            sources=[],
            missing_info_details=missing_items,
            inconsistencies=[],
            neutral_labels=labels,
            operational_mode=OperationalMode.MODE_3_GENERAL_NO_DOC,
            query_category=QueryCategory.F_INSUFFICIENT_INFO,
            evidence_sufficiency_passed=False,
            professional_review_recommended=False
        )


general_qa_service = GeneralQAService()
