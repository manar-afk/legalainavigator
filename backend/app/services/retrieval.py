import re
import math
from typing import List, Tuple, Optional, Dict, Set
from ..models.document import DocumentChunk
from ..models.situation import UserRole, RoleResolutionStatus
from ..core.storage import document_store
from ..core.config import settings

# Standard English stopwords
STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
    "below", "between", "both", "but", "by", "can", "can't", "cannot", "could", "did",
    "do", "does", "doing", "down", "during", "each", "few", "for", "from", "further",
    "had", "has", "have", "having", "he", "her", "here", "hers", "herself", "him",
    "himself", "his", "how", "i", "if", "in", "into", "is", "it", "its", "itself",
    "let's", "me", "more", "most", "my", "myself", "no", "nor", "not", "of", "off",
    "on", "once", "only", "or", "other", "ought", "our", "ours", "ourselves", "out",
    "over", "own", "same", "she", "should", "so", "some", "such", "than", "that",
    "the", "their", "theirs", "them", "themselves", "then", "there", "these", "they",
    "this", "those", "through", "to", "too", "under", "until", "up", "very", "was",
    "we", "were", "what", "when", "where", "which", "while", "who", "whom", "why",
    "with", "won't", "would", "you", "your", "yours", "yourself", "yourselves"
}

# Semantic Concept Clusters for Domain-Enhanced Retrieval
# Maps semantic intent & indirect queries to contract terms
CONCEPT_CLUSTERS = {
    "commercial_activity": {
        "query_triggers": ["restaurant", "shop", "business", "store", "commercial", "office", "cafe", "clinic"],
        "document_matches": ["residential", "dwelling", "commercial", "subletting", "permitted use", "use of premises"],
        "target_sections": ["5", "SECTION 5"]
    },
    "subletting": {
        "query_triggers": ["sublet", "sublease", "roommate", "sharing", "paying guest", "pg", "airbnb"],
        "document_matches": ["subletting", "sharing", "paying guests", "permitted use"],
        "target_sections": ["5", "SECTION 5"]
    },
    "early_termination_penalty": {
        "query_triggers": [
            "leave early", "break lease", "break the lease", "break my lease", "quit early",
            "quitting early", "lock-in", "minimum stay", "vacate during", "before 6 months",
            "end lease early", "terminate early", "vacate early"
        ],
        "document_matches": ["lock-in", "unexpired portion", "convenience", "termination"],
        "target_sections": ["4", "8", "SECTION 4", "SECTION 8"]
    },
    "deposit_refund_timeline": {
        "query_triggers": ["deposit return", "refund timeline", "get deposit back", "security deposit"],
        "document_matches": ["security deposit", "refundable", "deductions", "fourteen", "wear and tear", "handover"],
        "target_sections": ["3", "SECTION 3"]
    },
    "termination_notice": {
        "query_triggers": ["notice period", "asking to leave", "written notice", "days notice"],
        "document_matches": ["thirty", "30", "written notice", "termination for convenience", "cure notice"],
        "target_sections": ["8", "SECTION 8"]
    },
    "repairs_maintenance": {
        "query_triggers": ["repair", "maintenance", "leak", "plumbing", "fix", "damage"],
        "document_matches": ["maintenance", "repairs", "minor repairs", "structural repairs", "1000"],
        "target_sections": ["6", "SECTION 6"]
    }
}

# Role-based retrieval heuristic targets.
# NOTE: These are retrieval heuristics, not legal rules.
# They prioritize role-aligned covenants without suppressing or excluding counterparty covenants.
ROLE_HEURISTIC_TARGETS: Dict[UserRole, Dict[str, List[str]]] = {
    UserRole.TENANT: {
        "keywords": [
            "cure period", "cure notice", "deposit refund", "notice period",
            "peaceful enjoyment", "quiet possession", "tenant remedy", "lessor notice", "convenience"
        ],
        "sections": ["3", "SECTION 3", "8", "SECTION 8"]
    },
    UserRole.LANDLORD: {
        "keywords": [
            "rent default", "failure to pay", "re-entry", "permitted use",
            "inspection", "damage deduction", "lessee breach", "forfeiture"
        ],
        "sections": ["4", "SECTION 4", "5", "SECTION 5", "8", "SECTION 8"]
    },
    UserRole.EMPLOYEE: {
        "keywords": [
            "severance", "cure notice", "compensation", "notice period",
            "relief", "reimbursement"
        ],
        "sections": ["7", "SECTION 7", "8", "SECTION 8"]
    },
    UserRole.EMPLOYER: {
        "keywords": [
            "non-compete", "non-solicitation", "confidentiality",
            "intellectual property", "breach", "injunction"
        ],
        "sections": ["6", "SECTION 6", "7", "SECTION 7"]
    }
}


class DomainEnhancedRetriever:
    """
    Retrieval engine combining:
      1. Stopword-filtered BM25 lexical ranking.
      2. Domain semantic concept clusters for indirect / conceptual queries (e.g. 'restaurant' -> 'commercial use').
      3. Section header priority boosts.
      4. Role-based heuristic boosts (+1.5, prioritizing without suppressing counterparty covenants).
      5. Lexical false-positive protection.
    """

    @classmethod
    def tokenize(cls, text: str, filter_stopwords: bool = True) -> List[str]:
        raw_tokens = [w.lower() for w in re.findall(r"\b[a-zA-Z0-9\.\-]+\b", text) if len(w) > 1]
        if filter_stopwords:
            return [t for t in raw_tokens if t not in STOPWORDS and len(t) > 2]
        return raw_tokens

    @classmethod
    def identify_semantic_concepts(cls, query: str) -> List[str]:
        """Identifies applicable semantic concepts from user phrasing."""
        query_lower = query.lower()
        matched_concepts = []

        for concept_name, config in CONCEPT_CLUSTERS.items():
            for trigger in config["query_triggers"]:
                if trigger in query_lower:
                    matched_concepts.append(concept_name)
                    break

        return matched_concepts

    @classmethod
    def retrieve_chunks(
        cls,
        query: str,
        doc_ids: Optional[List[str]] = None,
        top_k: int = 4,
        min_threshold: float = 1.0,
        user_role: Optional[UserRole] = None,
        role_status: Optional[RoleResolutionStatus] = None
    ) -> List[Tuple[DocumentChunk, float]]:
        """
        Retrieves and ranks chunks from specified documents.
        Returns a list of (DocumentChunk, relevance_score) sorted by relevance descending.
        Applies role-based heuristic boost (+1.5) when a role is resolved without conflict.
        If role_status is UNRESOLVED_CONFLICT or user_role is GENERAL/None, executes role-neutral retrieval.
        NOTE: Role weighting prioritizes without suppressing: counterparty provisions remain retrievable.
        """
        chunks = document_store.get_all_chunks(doc_ids)
        if not chunks:
            return []

        query_tokens = cls.tokenize(query, filter_stopwords=True)
        if not query_tokens:
            return []

        # Identify any semantic concepts triggered by the query
        active_concepts = cls.identify_semantic_concepts(query)

        total_chunks = len(chunks)
        doc_freqs: Dict[str, int] = {}
        chunk_token_cache: Dict[str, List[str]] = {}

        for chunk in chunks:
            c_tokens = cls.tokenize(chunk.text, filter_stopwords=True)
            chunk_token_cache[chunk.chunk_id] = c_tokens
            unique_in_chunk = set(c_tokens)
            for term in query_tokens:
                if term in unique_in_chunk:
                    doc_freqs[term] = doc_freqs.get(term, 0) + 1

        scored_chunks: List[Tuple[DocumentChunk, float]] = []

        # Determine if role heuristic boost applies
        # Note: Role weighting is a retrieval heuristic that prioritizes without suppressing.
        # Counterparty covenants remain retrievable.
        apply_role_boost = (
            user_role is not None
            and user_role != UserRole.GENERAL
            and role_status != RoleResolutionStatus.UNRESOLVED_CONFLICT
            and user_role in ROLE_HEURISTIC_TARGETS
        )

        for chunk in chunks:
            c_tokens = chunk_token_cache[chunk.chunk_id]
            if not c_tokens:
                continue

            c_token_set = set(c_tokens)
            c_len = len(c_tokens)
            chunk_text_lower = chunk.text.lower()
            sec_ref = f"{chunk.section_number or ''} {chunk.section_title or ''}".lower()

            # 1. Lexical BM25 Score
            bm25_score = 0.0
            k1 = 1.2
            b = 0.75
            avg_len = sum(len(toks) for toks in chunk_token_cache.values()) / max(total_chunks, 1)

            matching_query_terms = set(query_tokens).intersection(c_token_set)
            for term in matching_query_terms:
                tf = c_tokens.count(term)
                df = doc_freqs.get(term, 0)
                idf = math.log(1.0 + (total_chunks - df + 0.5) / (df + 0.5))
                bm25_score += idf * ((tf * (k1 + 1.0)) / (tf + k1 * (1.0 - b + b * (c_len / max(avg_len, 1.0)))))

            # 2. Section Header Boost
            header_boost = 0.0
            for q_term in query_tokens:
                if q_term in sec_ref:
                    header_boost += 2.0

            # 3. Semantic Concept Boost (Indirect Query Matching)
            concept_boost = 0.0
            for concept in active_concepts:
                cfg = CONCEPT_CLUSTERS[concept]
                # Check if chunk text contains document matches for this concept
                for doc_match in cfg["document_matches"]:
                    if doc_match in chunk_text_lower:
                        concept_boost += 2.5
                # Check target sections
                for sec in cfg["target_sections"]:
                    if chunk.section_number and sec == chunk.section_number.replace("SECTION", "").strip():
                        concept_boost += 2.0

            # 4. Role-based Heuristic Boost (Prioritize without suppressing counterparty covenants)
            role_boost = 0.0
            if apply_role_boost:
                role_cfg = ROLE_HEURISTIC_TARGETS[user_role]
                for kw in role_cfg["keywords"]:
                    if kw in chunk_text_lower:
                        role_boost += 1.5
                        break
                if role_boost == 0.0:
                    for sec in role_cfg["sections"]:
                        if chunk.section_number and sec == chunk.section_number.replace("SECTION", "").strip():
                            role_boost += 1.5
                            break

            composite_score = bm25_score + header_boost + concept_boost + role_boost

            # 5. Lexical False-Positive Filter:
            # If the chunk ONLY matched on a single generic word (e.g. 'notice') while the query
            # had distinguishing modifier terms that are absent from the chunk and concept, penalize.
            if bm25_score > 0 and not concept_boost:
                # If query has > 2 tokens and chunk matches only 1 generic term
                if len(query_tokens) >= 2 and len(matching_query_terms) == 1:
                    matched_word = list(matching_query_terms)[0]
                    if matched_word in {"notice", "agreement", "party", "shall", "term"}:
                        composite_score *= 0.2  # Heavy downweight for superficial overlap

            if composite_score >= min_threshold:
                scored_chunks.append((chunk, composite_score))

        scored_chunks.sort(key=lambda x: x[1], reverse=True)
        return scored_chunks[:top_k]


domain_retriever = DomainEnhancedRetriever()
hybrid_retriever = domain_retriever
