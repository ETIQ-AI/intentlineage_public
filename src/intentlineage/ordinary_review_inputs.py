"""Versioned ordinary-payment operationalizations after grounded compilation.

The ontology axiom is retained verbatim. A separately declared bounded adapter
maps ordinary data to that axiom, without inventing preservation or approval rules.
"""
from copy import deepcopy
from .native_capture import ROOT, digest, file_hash
from .prompt_compiler import compile_prompt, validate_compiled, semantic_hash, PAYMENT, PROPERTY

PROFILE='ordinary-payment-inventory.1'
COMPILER_VERSION='2.3.0'
OPERATIONALIZATION_VERSION='3.0.0'
MONETARY_AMOUNT='https://spec.edmcouncil.org/fibo/ontology/FND/Accounting/CurrencyAmount/MonetaryAmount'


def ontology_mapping(element):
    params=element.get('parameters',{})
    known=(params.get('subject_class')==PAYMENT and params.get('property')==PROPERTY
           and params.get('target_class')==MONETARY_AMOUNT
           and element.get('source',{}).get('kind')=='ontology_axiom')
    if not known:
        return {'status':'unmapped','provenance':'authored_bounded_pay_adapter',
            'limitations':['No justified ordinary-data mapping is registered for this exact axiom/type relationship.'],
            'missing_result':'insufficient_evidence','type_basis':'not_established'}
    return {'status':'mapped','provenance':'authored_bounded_pay_adapter',
        'source_bindings':[deepcopy(element['source']),
            {'kind':'runtime_adapter','source':'src/intentlineage/contracts.py:PaymentRevision',
             'file':'src/intentlineage/contracts.py','definition':'PaymentRevision',
             'sha256':file_hash(ROOT/'src/intentlineage/contracts.py'),
             'interpretation':'A definite pay request and validated payment revision identify the domain payment; the executed receipt binds that payment to its amount/currency.'},
            {'kind':'runtime_adapter','source':'src/intentlineage/payment.py:receipt_for',
             'file':'src/intentlineage/payment.py','definition':'receipt_for',
             'sha256':file_hash(ROOT/'src/intentlineage/payment.py'),
             'interpretation':'Receipt fields are the ordinary serialized payment record, not asserted RDF triples.'}],
        'type_basis':'explicit_pay_domain_adapter_and_validated_payment_revision',
        'subject':{'entity_field':'payment_id','required_context':'definite pay request and executed payment/receipt'},
        'relationship':{'property':PROPERTY,'value_fields':['amount','currency'],
            'target_class':MONETARY_AMOUNT,'representation':'finite decimal amount and explicit currency in the bound payment record'},
        'limitations':['This is a declared operational interpretation, not an asserted OWL type witness or an OWL entailment proof.',
            'Field names alone do not establish Payment/MonetaryAmount typing; missing domain/receipt binding remains insufficient evidence.'],
        'missing_result':'insufficient_evidence'}


def compile_for_review(packet,taxonomy):
    """Re-run accepted extraction validation/compiler, then version the new mapping."""
    spec=compile_prompt(packet,taxonomy)
    if any(e['operator']=='carry' for e in spec['elements']):
        raise ValueError('Ordinary experiment fixture must not request carriage; explicit-carriage tasks use the historical profile')
    value=deepcopy(spec)
    value['compiler_version']=COMPILER_VERSION
    value['provenance'].update(operationalization_version=OPERATIONALIZATION_VERSION,
        inventory_profile=PROFILE,base_compilation_sha256=digest(spec),
        mapping_policy='ordinary_payment_domain_adapter.1')
    for e in value['elements']:
        if e['kind']!='rule':continue
        op=e['operationalization'];op['version']=OPERATIONALIZATION_VERSION
        if e['operator']=='exists_typed_relation':
            mapping=ontology_mapping(e)
            e['operationalization']={'version':OPERATIONALIZATION_VERSION,
                'provenance':'ontology_derived','review_status':'pending_overseer_review',
                'criterion':'mapped_payment_amount_existence',
                'fields':['payment_id','amount','currency','execution_receipt'],
                'applicability':['execution','reconciled'],'before_due_result':'not_applicable',
                'comparison':'declared_ordinary_payment_mapping','mapping':mapping,
                'missing_result':'unknown','mismatch_result':'violated',
                'does_not_imply':['amount_equality','amount_preservation','approval','rdf_serialization'],
                'justification':'The source existential requires a Payment amount relationship; exact values, preservation and approval come only from separate user rules.'}
        else:
            op['observation_assumptions']=[x for x in op.get('observation_assumptions',[])
                if 'complete requirement representations' not in x]
            op['observation_assumptions'].append(
                'Assess ordinary supplied payment values at the declared due stage; requirement objects and RDF serialization are not evidence obligations.')
        e['semantic_sha256']=semantic_hash(e)
    return validate_compiled(value)
