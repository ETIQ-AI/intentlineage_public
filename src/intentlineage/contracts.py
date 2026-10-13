"""Versioned specification and exact synthetic-payment data contracts."""
from decimal import Decimal
from typing import Annotated, Literal
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, StrictBool, StrictInt, StrictStr, StringConstraints, model_validator


def exact_amount(value):
    if isinstance(value, (float, bool)) or not isinstance(value, (str, int, Decimal)):
        raise ValueError('Amount must be an exact decimal string, Decimal or integer')
    return value


Amount = Annotated[Decimal, BeforeValidator(exact_amount), Field(gt=0, allow_inf_nan=False)]
Currency = Annotated[str, StringConstraints(pattern=r'^[A-Z]{3}$')]
Identifier = Annotated[str, StringConstraints(min_length=1)]
Version = Annotated[str, StringConstraints(pattern=r'^\d+\.\d+\.\d+$')]
Revision = Annotated[StrictInt, Field(ge=1)]
Stage = Literal['draft', 'intake', 'po_matched', 'supplier_validated', 'joined', 'approved', 'execution', 'reconciled']
Operator = Literal['equals', 'preserve', 'bind', 'carry', 'reconcile']
ParameterIdentifier = Annotated[str, StringConstraints(strict=True, min_length=1, pattern=r'\S')]
ParameterIdentifiers = Annotated[list[ParameterIdentifier], Field(strict=True, min_length=1)]
AUTHORISED_FIELDS = {'payment_id', 'revision', 'amount', 'currency', 'supplier_id', 'account_id', 'purchase_order_id'}


class Contract(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)


class EqualsParameters(Contract):
    field: ParameterIdentifier
    value: StrictStr | StrictInt | StrictBool


class EvidenceParameters(Contract):
    fields: ParameterIdentifiers
    expected_from: ParameterIdentifier


class CarryParameters(Contract):
    required: ParameterIdentifiers


OPERATOR_PARAMETERS = {
    'equals': EqualsParameters,
    'preserve': EvidenceParameters,
    'bind': EvidenceParameters,
    'carry': CarryParameters,
    'reconcile': EvidenceParameters,
}


class ParameterizedElement(Contract):
    """Validate concrete elements without changing their serialized dictionaries."""

    @model_validator(mode='after')
    def rule_parameters(self):
        if self.kind == 'rule':
            if self.operator is None:
                raise ValueError('Rule requires an operator')
            OPERATOR_PARAMETERS[self.operator].model_validate(self.parameters)
        else:
            if self.operator is not None:
                raise ValueError('Only rules have operators')
            if self.parameters:
                raise ValueError('Only rules have parameters')
        return self

    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema, handler):
        schema = handler.resolve_ref_schema(handler(core_schema))
        choices = [
            {'properties': {
                'kind': {'const': 'rule'}, 'operator': {'const': operator},
                'parameters': model.model_json_schema(),
             }, 'required': ['kind', 'operator', 'parameters']}
            for operator, model in OPERATOR_PARAMETERS.items()
        ]
        choices.append({'properties': {
            'kind': {'enum': ['intent', 'concept']},
            'operator': {'type': 'null'},
            'parameters': {'type': 'object', 'maxProperties': 0},
        }, 'required': ['kind']})
        schema.setdefault('allOf', []).append({'oneOf': choices})
        return schema


class PaymentRevision(Contract):
    payment_id: Identifier
    invoice_id: Identifier
    revision: Revision
    amount: Amount
    currency: Currency
    supplier_id: Identifier
    account_id: Identifier
    purchase_order_id: Identifier
    required_constraints: list[str] = Field(default_factory=list)


class Approval(Contract):
    approval_id: Identifier
    policy_version: Version
    payment_id: Identifier
    revision: Revision
    amount: Amount
    currency: Currency
    supplier_id: Identifier
    account_id: Identifier
    purchase_order_id: Identifier


class PaymentParameters(Contract):
    amount: Amount
    currency: Currency
    initial_revision: Revision
    approval_policy_version: Version
    approval_bind_fields: list[str]

    @model_validator(mode='after')
    def full_approval_binding(self):
        if set(self.approval_bind_fields) != AUTHORISED_FIELDS or len(self.approval_bind_fields) != len(AUTHORISED_FIELDS):
            raise ValueError('Approval must bind every authorised field exactly once')
        return self


class SourceSpan(Contract):
    document: str
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)


class OntologyBinding(Contract):
    term: str
    status: Literal['resolved', 'local_extension', 'unresolved']
    iri: str | None
    candidates: list[str]
    provenance: dict | None
    declaration_line: int | None = None
    reason: str | None = None


class ElementInput(ParameterizedElement):
    key: Annotated[str, StringConstraints(pattern=r'^[a-z][a-z0-9_]*$')]
    kind: Literal['intent', 'concept', 'rule']
    text: Identifier
    stages: list[Stage] = Field(min_length=1)
    ontology_terms: list[str]
    operator: Operator | None = None
    parameters: dict = Field(default_factory=dict)


class SpecificationInput(Contract):
    document_id: Annotated[str, StringConstraints(pattern=r'^[a-z][a-z0-9_-]*$')]
    version: Version
    ontology_version: Version
    payment_parameters: PaymentParameters
    elements: list[ElementInput] = Field(min_length=1)


class SpecificationElement(ParameterizedElement):
    element_id: str
    key: str
    revision: str
    supersedes: str | None = None
    kind: Literal['intent', 'concept', 'rule']
    text: str
    source: SourceSpan
    stages: list[Stage]
    operator: Operator | None
    parameters: dict
    bindings: list[OntologyBinding]


class CompiledSpecification(Contract):
    document_id: str
    version: Version
    ontology_version: Version
    compiler_version: Version
    source_sha256: str
    semantic_sha256: str
    ontology_manifest_sha256: str
    payment_parameters: PaymentParameters
    elements: list[SpecificationElement]
