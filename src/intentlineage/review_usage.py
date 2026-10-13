"""Token observations and coverage; absent counters never mean observed zero."""
from copy import deepcopy

FIELDS=('input_tokens','output_tokens','total_tokens','cached_input_tokens')
CORE=('input_tokens','output_tokens','total_tokens')
ALIASES={key:(key,key.replace('_','')) for key in FIELDS}


def normalize_usage(raw):
    """Keep validated partial observations, exact metadata and derivation sources."""
    usage={};sources={};errors=[]
    if not isinstance(raw,dict):
        if raw is not None:errors.append({'field':None,'reason':'Usage metadata must be a dictionary.'})
        else:errors.append({'field':None,'reason':'Usage metadata is null, not reported counts.'})
        entries=[]
    else:
        # Keep each raw entry: a dict of lowercased keys would erase collisions
        # before validation. Sorting diagnostics makes order irrelevant.
        entries=sorted(((k,v) for k,v in raw.items() if isinstance(k,str)),key=lambda item:item[0])
    present=set()
    for key,names in ALIASES.items():
        matches=[(name,value) for name,value in entries if name.lower() in names]
        if not matches:continue
        present.add(key)
        valid=all(type(v) is int and v>=0 for _,v in matches)
        if not valid or len({v for _,v in matches})>1:
            errors.append({'field':key,'reason':'Reported counter must be an unambiguous nonnegative integer.',
                           'entries':[{'key':name,'value':deepcopy(value),'valid':type(value) is int and value>=0}
                                      for name,value in matches]})
        else:
            # Equal valid duplicates are one reported observation, including 0.
            usage[key]=matches[0][1];sources[key]='reported'
    if 'total_tokens' not in present and all(k in usage for k in ('input_tokens','output_tokens')):
        usage['total_tokens']=usage['input_tokens']+usage['output_tokens'];sources['total_tokens']='derived'
    complete=all(k in usage for k in CORE) and not errors
    return {'raw':deepcopy(raw),'values':usage,'sources':sources,'errors':errors,
            'available':bool(usage),'complete':complete,
            'field_complete':{k:k in usage for k in FIELDS},
            'status':'malformed' if errors else 'complete' if complete else 'partial' if usage else 'unavailable'}


def aggregate_usage(calls):
    """Observed subtotals only; denominators include every charged reasoning call."""
    charged=[c for c in calls if c['charged_reasoning']]
    coverage={};values={}
    for key in FIELDS:
        observed=[c['usage'][key] for c in charged if key in c['usage']]
        sources=[c['usage_observation']['sources'].get(key) for c in charged]
        coverage[key]={'charged_calls':len(charged),'known_calls':len(observed),
            'reported_calls':sources.count('reported'),'derived_calls':sources.count('derived'),
            'missing_calls':len(charged)-len(observed),
            'invalid_calls':sum(any(e['field']==key for e in c['usage_observation']['errors']) for c in charged),
            'complete':bool(charged) and len(observed)==len(charged)}
        values[key]=sum(observed) if observed else None
    return {'usage':values,'usage_coverage':coverage,
            'usage_complete':bool(charged) and all(c['usage_observation']['complete'] for c in charged),
            'usage_semantics':'Observed subtotals, not full totals when field coverage is incomplete; cached input is optional.'}
