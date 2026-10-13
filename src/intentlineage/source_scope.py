"""Conservative source agreement for bounded operators, not an English parser.

Inspect the clause containing the extracted predicate. Separate imperative clauses
retain their polarity; shared negative coordination and missing condition scope are
rejected. Unrecognized predicate structure is explicit uncertainty, never permission.
"""
import re

VERSION = '2.2.0'
NEGATIVE = re.compile(r"\b(?:not|never|no|without|cannot|\w+n['\u2019]t)\b", re.I)
CONDITION = re.compile(r'\b(?:if|unless|when|provided)\b', re.I)
HEAD = r'(?:pay|settle|draft|require\w*|need\w*|keep|preserve\w*|maintain\w*|leave|carry|reconcile\w*)'
INTRO = rf"(?:(?:do\s+not|don['\u2019]t|never|not)\s+)?{HEAD}\b"
BOUNDARY = re.compile(rf'[;!?\n]|\.(?!\d)|,?\s*\b(and|but|or)\b\s+(?={INTRO})|,\s*(?={INTRO})', re.I)
MODALITY = re.compile(r'\b(?:maybe|perhaps|possibly|potentially|may|might|could|optional(?:ly)?|at\s+(?:your|their)\s+discretion|if\s+(?:desired|needed|you\s+want))\b', re.I)
SEPARATE_OPERATION = re.compile(
    rf'\b(?:and|but)\s+(?=(?:(?:maybe|perhaps|possibly|optionally|you\s+may|you\s+might)\s+)?(?:{HEAD}|email|send|notify|write)\b)', re.I)
PREDICATES = {
    'pay': r'\b(?:pay|settle|payment)\b', 'draft': r'\bdraft\b',
    'bind': r'\b(?:require\w*|need\w*)\b',
    'preserve': r'\b(?:keep|preserve\w*|maintain\w*|leave)\b',
    'carry': r'\bcarry\b', 'reconcile': r'\breconcile\w*\b',
}


def _modal_clause(clause):
    # A following independent operation does not change this predicate's force.
    return bool(MODALITY.search(SEPARATE_OPERATION.split(clause, maxsplit=1)[0]))


def _regions(text, *, modality=False):
    start, inherited_negative, inherited_condition, inherited_modality = 0, False, False, False
    for boundary in BOUNDARY.finditer(text):
        clause = text[start:boundary.start()]
        yield start, boundary.start(), clause, inherited_negative, inherited_condition, inherited_modality
        connector = (boundary.group(1) or '').lower()
        inherited_negative = connector in {'and', 'or'} and (inherited_negative or bool(NEGATIVE.search(clause)))
        inherited_modality = modality and connector in {'and', 'or'} and (inherited_modality or _modal_clause(clause))
        # A condition prefix before a comma scopes the following imperative.
        inherited_condition = boundary.group(0).lstrip().startswith(',') and bool(CONDITION.search(clause))
        start = boundary.end()
    yield start, len(text), text[start:], inherited_negative, inherited_condition, inherited_modality


def agreement_reasons(text, span, role, meaning, condition_spans=(), *, policy_version=VERSION):
    if policy_version not in {'2.1.0', VERSION}:
        raise ValueError('Unsupported source agreement version')
    key = meaning.get('operator') if role == 'constraint' else meaning.get('action')
    predicate = PREDICATES.get(key)
    if not predicate:
        return [] if role == 'goal' else ['constraint_scope_uncertain']
    candidates = []
    for start, end, clause, inherited_negative, inherited_condition, inherited_modality in _regions(text, modality=policy_version==VERSION):
        for head in re.finditer(predicate, clause, re.I):
            absolute_start, absolute_end = start+head.start(), start+head.end()
            if span.start <= absolute_start < span.end or span.start < absolute_end <= span.end:
                candidates.append((start, end, clause, head, inherited_negative, inherited_condition, inherited_modality))
    if len(candidates) != 1:
        return [role+'_scope_uncertain']
    start, end, clause, head, inherited_negative, inherited_condition, inherited_modality = candidates[0]
    prefix = clause[:head.start()]
    # A preceding different predicate in this unsplit clause has uncertain scope.
    if re.search(rf'\b{HEAD}\b', prefix, re.I) or re.search(r'\b(?:say|quote|mention|ignore)\b', prefix, re.I):
        return [role+'_scope_uncertain']
    negative = bool(NEGATIVE.search(prefix))
    if key == 'bind' and re.search(r'\b(?:no|without)\s+(?:an?\s+)?approval\b', clause, re.I):
        negative = True
    if inherited_negative and not negative:
        return [role+'_coordination_scope_uncertain']
    reasons = []
    if policy_version == VERSION and (inherited_modality or _modal_clause(clause)):
        reasons.append(role+'_modality_scope_unsupported')
    if negative != meaning['negated']:
        reasons.append(role+'_polarity_scope_mismatch')
    if negative and not NEGATIVE.search(span.quote):
        reasons.append(role+'_negation_scope_not_quoted')
    if inherited_condition or CONDITION.search(clause):
        # Accepted condition atoms remain separately represented; dispatch abstains.
        if not any(s.start <= end and s.end >= start or inherited_condition and s.end <= start for s in condition_spans):
            reasons.append(role+'_condition_scope_not_extracted')
    return reasons
