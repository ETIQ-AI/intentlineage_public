"""Synthetic scoring/replay plumbing against private mechanical qualifications.

No semantic assessor or empirical inference. Repeats/cases sharing a clean pair
are dependent; rates are descriptive and carry explicit scored denominators.
"""
from collections import defaultdict
from copy import deepcopy
import math

from .native_capture import digest
from .review_usage import normalize_usage, aggregate_usage, FIELDS, CORE

ARMS=('E','R-H','H','R-A','A')
KINDS=('persistent','repaired','clean','benign')
DATA_CLASSES=('synthetic','recorded_contract','empirical')


def receipt_usage(session):
    """Reuse M2 normalization/aggregation, validating raw receipt provenance."""
    calls=deepcopy(session.get('calls',[]))
    for call in calls:
        observation=normalize_usage(call.get('usage_raw',call.get('usage',{})))
        if 'usage_observation' in call and (call['usage_observation']!=observation or call['usage']!=observation['values']):
            raise ValueError('Usage receipt disagrees with its raw observation')
        call.update(usage=observation['values'],usage_observation=observation)
    return aggregate_usage(calls)


def rows_from_units(units,*,legacy=False,historical=False,data_class=None,evidence_root=None):
    if data_class is not None and data_class not in DATA_CLASSES:raise ValueError('Unknown review data class')
    rows=[]
    for unit in units:
        if data_class is not None:
            if unit.get('data_class')!=data_class or unit.get('synthetic') is not (data_class!='empirical'):
                raise ValueError('Mixed or edited unit review provenance')
            if data_class=='empirical':
                from .experiment_execution import validate_empirical_unit
                validate_empirical_unit(unit,evidence_root)
        for arm in ARMS:
            session=unit['matrix']['sessions'][arm]
            # H assesses separate frozen batches. Adaptive terminal evidence may
            # supersede earlier observations; controls use only their final pass.
            replies=session.get('replies',[]) if arm=='H' else ([session['terminal_assessment']] if session.get('terminal_assessment') else [])
            assessments=[deepcopy(a) for reply in replies for a in reply['assessments']]
            from .review_function import SESSION_VERSION as FUNCTION_SESSION
            function_mode=session.get('format_version') in {FUNCTION_SESSION,'m3-function-session.2'}
            if function_mode:
                replies=session.get('replies',[]) if arm in {'H','A'} else ([session['terminal_assessment']] if session.get('terminal_assessment') else [])
                assessments=deepcopy(session['effective_scoped_assessments'])
            failure_kinds={c.get('failure_kind') for c in session.get('calls',[])}
            known_usage={}
            for field in ['input_tokens','output_tokens','cached_input_tokens','total_tokens']:
                receipts=[c.get('usage',{}).get(field) for c in session.get('calls',[])
                          if c.get('charged_reasoning') and field in c.get('usage',{})]
                if receipts:known_usage[field]=sum(receipts)
            accounting={} if legacy else aggregate_usage(session['calls']) if historical else receipt_usage(session)
            if not legacy:
                known_usage={k:v for k,v in accounting['usage'].items() if v is not None}
            # Retried malformed replies are retained costs, not terminal failures.
            failed=not bool(replies) or session.get('stop_reason') in {'provider_error','provider_metadata','transport_failure','invalid_reply','context_budget','rejected_operation'}
            row={'case_id':unit['case_id'],'repeat_id':unit['repeat_id'],'arm':arm,
                'synthetic':True,'valid_review':bool(replies),'failed':failed,
                'assessments':assessments,'uncovered_elements':session.get('uncovered_elements',[]),
                'insufficient_elements':session.get('insufficient_elements',[]),
                'logical_calls':session['logical_calls'],'transport_failures':session.get('transport_failures',0),
                'controller_operations':session.get('controller_operations',0),
                'elapsed_seconds':sum(c['elapsed_seconds'] for c in session.get('calls',[])),
                'usage':known_usage,'usage_complete':session.get('usage_complete',False) if legacy else accounting['usage_complete'],
                **({} if legacy else {k:v for k,v in accounting.items() if k not in {'usage','usage_complete'}}),
                'evidence_bytes_added':session.get('evidence_bytes_added',0),
                'status':session.get('status'),'failure_kinds':sorted(k for k in failure_kinds if k),
                'unresolved_questions':len(session.get('unresolved_questions',[]))}
            if unit['matrix'].get('response_policy') or session.get('response_policy'):
                terminal=(unit['matrix'].get('terminal_outcomes') or {}).get(arm,session.get('terminal_outcome'))
                row.update(terminal_outcome=terminal,invalid_response_count=sum(c.get('failure_kind')=='invalid_response' for c in session['calls']) or int(terminal=='invalid_response'),partial_assessments=[{**deepcopy(a),'scope_id':c.get('function_scope','endpoint'),'attempt':c['attempt']} for c,r in zip([c for c in session['calls'] if not c['failure']],session.get('replies',[])) for a in r['assessments']])
            if function_mode:
                row.update(review_contract='m3-function-coverage.1',required_scopes=session['required_scopes'])
            if data_class is not None:
                row.update(data_class=data_class,synthetic=data_class!='empirical',
                    provenance={'kind':'verified-actual-provider' if data_class=='empirical' else 'recorded-contract-fixture' if data_class=='recorded_contract' else 'synthetic',
                                'unit_provenance_sha256':digest(unit.get('provenance',{}))})
            rows.append(row)
    return rows


def _outcome(record,row):
    if not record['qualified']:return 'unqualified'
    if row.get('terminal_outcome')=='invalid_response':return 'invalid_response'
    if row['failed']:return 'failed'
    if not row['valid_review']:return 'unknown'
    if row.get('review_contract')=='m3-function-coverage.1':
        from .review_function import scoped_outcome
        return scoped_outcome(record,row)
    observations=defaultdict(set)
    for assessment in row['assessments']:
        if assessment['element_id'] not in record.get('inventory_element_ids',record['target_element_ids']):
            raise ValueError('Assessment element is outside the declared inventory')
        status=assessment['assessment']
        if status not in {'supported','contradicted','insufficient_evidence'}:
            raise ValueError('Unknown assessment status')
        observations[assessment['element_id']].add(status)
    targets=record['target_element_ids']
    if record['kind'] in {'clean','benign'}:
        # Any explicit, structurally validated contradiction is a false alarm.
        if any('contradicted' in values for values in observations.values()):return 'false_alarm'
    else:
        if any(observations[i]=={'contradicted'} for i in targets):return 'detected'
    if not targets or any(observations[i]!={'supported'} for i in targets):
        return 'insufficient_evidence'
    return 'missed' if record['kind'] in {'persistent','repaired'} else 'no_alarm'


def score_rows(truth,rows,*,format_version='m3a-score.2',data_class=None):
    extended=format_version=='m3b-score.1'
    if format_version not in {'m3a-score.1','m3a-score.2','m3b-score.1'}:raise ValueError('Unknown scoring version')
    if extended:
        if data_class not in DATA_CLASSES:raise ValueError('Extended scoring requires an explicit review data class')
    elif data_class is not None:raise ValueError('Historical synthetic score contract cannot change provenance')
    legacy=format_version=='m3a-score.1'
    truth=deepcopy(truth);rows=deepcopy(rows)
    by={r['case_id']:r for r in truth}
    if len(by)!=len(truth) or any(r['kind'] not in KINDS for r in truth):
        raise ValueError('Duplicate or invalid mechanical truth')
    clean_pairs={r['pair_id'] for r in truth if r['kind']=='clean' and r['qualified']}
    for record in truth:
        if record['kind'] in {'persistent','repaired'} and record['qualified'] and record['pair_id'] not in clean_pairs:
            raise ValueError('Qualified fault has no mechanically qualified clean pair')
    arms={a:{k:{'scheduled':0,'detected':0,'missed':0,'false_alarms':0,'no_alarm':0,
                'insufficient_evidence':0,'failed':0,'unknown':0,'unqualified':0,**({'invalid_responses':0} if any('terminal_outcome' in r for r in rows) else {}),
                'scored_denominator':0,'qualified_denominator':0} for k in KINDS} for a in ARMS}
    keys=set();scored=[];usage=defaultdict(int);latencies=[]
    token_reporting={k:{'reported_rows':0,'unavailable_rows':0} for k in
                     ['input_tokens','output_tokens','cached_input_tokens','total_tokens']}
    coverage={k:{'charged_calls':0,'known_calls':0,'reported_calls':0,'derived_calls':0,
                 'missing_calls':0,'invalid_calls':0,'complete':False} for k in FIELDS}
    if not legacy:
        for counters in token_reporting.values():counters.update(known_rows=0,derived_rows=0,complete_rows=0)
    for row in rows:
        if extended:
            if row.get('data_class')!=data_class or row.get('synthetic') is not (data_class!='empirical'):
                raise ValueError('Synthetic/recorded/empirical reviewer results cannot be mixed or relabelled')
            expected='verified-actual-provider' if data_class=='empirical' else 'recorded-contract-fixture' if data_class=='recorded_contract' else 'synthetic'
            if row.get('provenance',{}).get('kind')!=expected:
                raise ValueError('Scoring requires bound reviewer provenance, not an edited label')
        elif row.get('synthetic') is not True:
            raise ValueError('M3A scoring only accepts explicitly synthetic reviewer results')
        if row['case_id'] not in by or row['arm'] not in ARMS or type(row['repeat_id']) is not int or row['repeat_id']<1:
            raise ValueError('Unknown case/arm/repeat')
        key=(row['case_id'],row['arm'],row['repeat_id'])
        if key in keys:raise ValueError('Duplicate scored case/arm/repeat')
        keys.add(key);record=by[row['case_id']];outcome=_outcome(record,row)
        bucket=arms[row['arm']][record['kind']];bucket['scheduled']+=1
        counter='false_alarms' if outcome=='false_alarm' else 'invalid_responses' if outcome=='invalid_response' else outcome
        bucket[counter]+=1
        bucket['qualified_denominator']+=bool(record['qualified'])
        bucket['scored_denominator']+=outcome in {'detected','missed','false_alarm','no_alarm'}
        if outcome=='unqualified':status=None
        elif outcome in {'detected','false_alarm'}:status=True
        elif outcome in {'missed','no_alarm'}:status=False
        else:status=None
        scored.append({**row,'kind':record['kind'],'pair_id':record['pair_id'],
                       'outcome':outcome,'definitive_alarm':status})
        for field in ['logical_calls','transport_failures','controller_operations']:
            value=row.get(field,0)
            if type(value) is not int or value<0:raise ValueError('Invalid cost count')
            usage[field]+=value
        elapsed=row.get('elapsed_seconds',0)
        if type(elapsed) not in (int,float) or not math.isfinite(elapsed) or elapsed<0:raise ValueError('Invalid latency')
        latencies.append(elapsed)
        row_coverage=row.get('usage_coverage')
        if not legacy and row_coverage is None:
            # Legacy aggregate-only synthetic fixtures cannot supply per-call provenance.
            # Preserve their observed fields without deriving totals from subtotals.
            charged=row.get('logical_calls',0)
            row_coverage={k:{'charged_calls':charged,'known_calls':int(row.get('usage',{}).get(k) is not None and charged>0),
                'reported_calls':int(row.get('usage',{}).get(k) is not None and charged>0),'derived_calls':0,
                'missing_calls':charged-int(row.get('usage',{}).get(k) is not None and charged>0),'invalid_calls':0,
                'complete':charged==1 and row.get('usage',{}).get(k) is not None} for k in FIELDS}
        complete=row.get('usage_complete') if legacy else bool(row.get('usage_complete')) and all(row_coverage[k]['complete'] for k in CORE)
        if complete:
            usage['reported_rows']+=1
        else:usage['unavailable_rows']+=1
        # Partial receipts still contribute known costs. Never impute missing tokens.
        for field in token_reporting:
            value=row.get('usage',{}).get(field)
            if value is None:
                token_reporting[field]['unavailable_rows']+=1
            else:
                if type(value) is not int or value<0:raise ValueError('Invalid reported token count')
                usage[field]+=value
                if legacy:token_reporting[field]['reported_rows']+=1
            if not legacy:
                observed=row_coverage[field]
                for key in coverage[field]:
                    if key=='complete':continue
                    counter=observed[key]
                    if type(counter) is not int or counter<0:raise ValueError('Invalid token field coverage')
                    coverage[field][key]+=counter
                if observed['known_calls']+observed['missing_calls']!=observed['charged_calls'] or observed['reported_calls']+observed['derived_calls']!=observed['known_calls']:
                    raise ValueError('Token field coverage does not reconcile')
                if (value is None)!=(observed['known_calls']==0):raise ValueError('Token subtotal disagrees with field coverage')
                token_reporting[field]['known_rows']+=value is not None
                token_reporting[field]['reported_rows']+=observed['reported_calls']>0
                token_reporting[field]['derived_rows']+=observed['derived_calls']>0
                token_reporting[field]['complete_rows']+=observed['complete']
        usage['uncovered_elements']+=len(row.get('uncovered_elements',[]))
        usage['insufficient_elements']+=len(row.get('insufficient_elements',[]))
        usage['unresolved_questions']+=row.get('unresolved_questions',0)
    for arm in ARMS:
        for kind,bucket in arms[arm].items():
            numerator=bucket['detected'] if kind in {'persistent','repaired'} else bucket['false_alarms']
            bucket['rate']=numerator/bucket['scored_denominator'] if bucket['scored_denominator'] else None
            bucket['insufficient_fraction']=bucket['insufficient_evidence']/bucket['qualified_denominator'] if bucket['qualified_denominator'] else None
    outcomes={(r['case_id'],r['repeat_id'],r['arm']):r['definitive_alarm'] for r in scored}
    contrasts={}
    for first,second in [('H','E'),('A','E'),('H','R-H'),('A','R-A')]:
        pairs=[]
        for r in scored:
            if r['arm']!=first or r['kind'] not in {'persistent','repaired'}:continue
            one=r['definitive_alarm'];two=outcomes.get((r['case_id'],r['repeat_id'],second))
            if one is not None and two is not None:pairs.append((one,two))
        contrasts[first+'/'+second]={'paired_denominator':len(pairs),
            'first_only':sum(a and not b for a,b in pairs),'second_only':sum(b and not a for a,b in pairs),
            'both':sum(a and b for a,b in pairs),'neither':sum(not a and not b for a,b in pairs)}
    if not legacy:
        for field,counters in coverage.items():
            counters['complete']=bool(counters['charged_calls']) and counters['known_calls']==counters['charged_calls']
            if counters['known_calls']==0:usage[field]=None
    result={'format_version':format_version,'synthetic':True,'arms':arms,'rows':scored,
        'contrasts':contrasts,'usage':{**dict(usage),'token_reporting':token_reporting},'elapsed_seconds':sum(latencies),
        'independent_case_count':len({r['pair_id'] for r in truth}),
        'truth_sha256':digest(truth),'input_rows_sha256':digest(rows),
        'limits':['Synthetic plumbing outputs are not empirical model-performance findings.',
                  'Cases sharing clean inputs and repeated reviews are dependent; no independence-based interval is computed.',
                  'Mechanical qualification bounds truth to observed injected effects, not universal semantic correctness.',
                  'Missing or partial token reports remain unavailable; zeros are not inferred.']}
    if not legacy:result['usage'].update(usage_coverage=coverage,usage_semantics='Observed subtotals with charged-call coverage; reported and derived observations remain distinct.')
    if extended:
        result.update(data_class=data_class,synthetic=data_class!='empirical',empirical_admissible=data_class=='empirical')
        result['limits'][0]=('Descriptive actual-review results within the qualified frozen protocol.' if data_class=='empirical'
                            else 'Recorded/synthetic contract results are not empirical model-performance findings.')
    result['score_sha256']=digest(result)
    return result
