"""Local infrastructure CLI. No live provider mode is exposed."""
import argparse
import json
from pathlib import Path

from intentlineage.experiment_faults import capture_bank,VARIANTS
from intentlineage.experiment_isolation import OfflineSandbox
from intentlineage.experiment_campaign import run_campaign,replay_campaign
from intentlineage.experiment_bundle import export_bundle,replay_bundle


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest='action',required=True)
    capture=commands.add_parser('capture');capture.add_argument('--output',type=Path,required=True)
    capture.add_argument('--seed',type=int,default=17);capture.add_argument('--batch-size',type=int,default=8)
    qualify=commands.add_parser('probe');qualify.add_argument('--output',type=Path,required=True)
    run=commands.add_parser('mock');run.add_argument('--bank',type=Path,required=True)
    run.add_argument('--output',type=Path,required=True);run.add_argument('--repeats',type=int,default=1)
    run.add_argument('--seed',type=int,default=17);run.add_argument('--resume',action='store_true')
    run.add_argument('--max-calls',type=int,default=5);run.add_argument('--max-operations',type=int,default=2)
    replay=commands.add_parser('replay');replay.add_argument('--campaign',type=Path,required=True)
    export=commands.add_parser('export');export.add_argument('--campaign',type=Path,required=True)
    export.add_argument('--output',type=Path,required=True)
    verify=commands.add_parser('verify-bundle');verify.add_argument('--bundle',type=Path,required=True)
    args=parser.parse_args()
    if args.action=='capture':
        result=capture_bank(args.output,seed=args.seed,batch_size=args.batch_size)
        print(json.dumps({'bank_sha256':result['bank_sha256'],'wrapper_scans':result['wrapper_scans'],
                          'qualified_cases':sum(c['qualified'] for c in result['cases']),
                          'experiment_qualified':False}))
    elif args.action=='probe':
        result=OfflineSandbox().qualify(args.output)
        print(json.dumps({'qualified':result['qualified'],'scope':result['scope'],'probes':result['probes']}))
    elif args.action=='mock':
        bank=json.loads(args.bank.read_bytes())
        result=run_campaign(bank,args.output,repeats=args.repeats,seed=args.seed,resume=args.resume,
                            max_calls=args.max_calls,max_operations=args.max_operations)
        print(json.dumps({'synthetic':True,'campaign_sha256':result['campaign_sha256'],
                          'units':result['completed_units'],'hosted_calls':0,
                          'logical_calls':result['score']['usage']['logical_calls']}))
    elif args.action=='replay':
        result=replay_campaign(args.campaign)
        print(json.dumps({'synthetic':True,'campaign_sha256':result['campaign_sha256'],'units':result['completed_units']}))
    elif args.action=='export':
        result=export_bundle(args.campaign,args.output)
        print(json.dumps({'synthetic':True,'bundle_sha256':result['bundle_sha256'],'files':len(result['files'])}))
    else:print(json.dumps(replay_bundle(args.bundle)))
    return 0


if __name__=='__main__':raise SystemExit(main())
