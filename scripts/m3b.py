"""Preparation is pure/local; explicit operator commands require real gates.

The implementation developer uses local/offline commands only. The separately
authorized Experiment Developer may use the operator commands after review.
Legacy human-* names remain compatible and are never invoked by preparation.
"""
import argparse
import json
from pathlib import Path

from intentlineage.experiment_protocol import draft_protocol, validate_protocol
from intentlineage.experiment_preflight import preflight, prepare_commands
from intentlineage.experiment_qualification import qualify_offline
from intentlineage.review_runner import _write
from intentlineage.review_contract import _strict_load


def load(path):
    return _strict_load(Path(path).read_bytes())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    draft = sub.add_parser('draft'); draft.add_argument('--output', required=True)
    validate = sub.add_parser('validate'); validate.add_argument('--protocol', required=True)
    validate.add_argument('--frozen', action='store_true')
    for name in ['preflight', 'prepare']:
        command = sub.add_parser(name)
        command.add_argument('--protocol', required=True)
        command.add_argument('--gates', required=True)
        command.add_argument('--qualification')
        if name == 'prepare': command.add_argument('--output', required=True)
    probe = sub.add_parser('probe-offline'); probe.add_argument('--output', required=True)
    inspect=sub.add_parser('inspect-runtime');inspect.add_argument('--output',required=True);inspect.add_argument('--cli')
    for name in ['execution-preflight','prepare-qualification','human-qualify','human-campaign']:
        command=sub.add_parser(name);command.add_argument('--protocol',required=True)
        if name in {'execution-preflight','human-campaign'}:
            command.add_argument('--gates',required=True);command.add_argument('--qualification')
        if name!='execution-preflight':command.add_argument('--output',required=True)
        if name=='human-campaign':command.add_argument('--bank',required=True);command.add_argument('--resume',action='store_true')
    proposal=sub.add_parser('propose-protocol');proposal.add_argument('--bank',required=True);proposal.add_argument('--output',required=True)
    args = parser.parse_args()
    try:
        if args.command == 'draft':
            result = draft_protocol(); _write(args.output, result)
        elif args.command == 'validate':
            result = validate_protocol(load(args.protocol), require_frozen=args.frozen)
        elif args.command == 'probe-offline':
            result = qualify_offline(args.output)
        elif args.command=='inspect-runtime':
            from intentlineage.experiment_isolation import OfflineSandbox
            sandbox=OfflineSandbox()
            result=sandbox._call({'action':'inspect-provider','cli_binary':args.cli}) if args.cli else sandbox.inspect_runtime()
            _write(args.output,result)
        elif args.command=='propose-protocol':
            from intentlineage.experiment_execution import propose_protocol
            result=propose_protocol(load(args.bank),output=args.output)
        elif args.command=='prepare-qualification':
            from intentlineage.experiment_execution import prepare_qualification_plan
            result=prepare_qualification_plan(load(args.protocol),output=args.output)
        elif args.command=='execution-preflight':
            from intentlineage.experiment_preflight import execution_preflight
            result=execution_preflight(load(args.protocol),load(args.gates),load(args.qualification) if args.qualification else None)
        elif args.command in {'human-qualify','human-campaign'}:
            # These are explicit operator actions, separate from command generation.
            # Credentials never appear in argv, output JSON or reviewer mounts.
            protocol=load(args.protocol)
            from intentlineage.experiment_chatgpt import qualify_chatgpt_provider,ChatGPTProviderFactory,CHATGPT_FORMAT
            if protocol.get('format_version') not in {CHATGPT_FORMAT,'m3b-chatgpt-function-protocol.1','m3b-chatgpt-function-protocol.2'} or protocol.get('reviewer',{}).get('authentication')!='chatgpt':
                raise ValueError('Current authorization requires ChatGPT cached Codex authentication; no API keys or fallback')
            if args.command=='human-campaign':
                from intentlineage.experiment_execution import validate_execution_contract
                context={'protocol':protocol,'gates':load(args.gates),'qualification':load(args.qualification) if args.qualification else None}
                validate_execution_contract(**context) # Fail before credential access/staging.
            if args.command=='human-qualify':
                result=qualify_chatgpt_provider(protocol,args.output)
            else:
                from intentlineage.experiment_campaign import run_campaign
                result=run_campaign(load(args.bank),args.output,mode='empirical',resume=args.resume,
                    provider_factory=ChatGPTProviderFactory(context),execution_contract=context)
        else:
            protocol = load(args.protocol); gates = load(args.gates)
            qualification = load(args.qualification) if args.qualification else None
            if args.command == 'preflight': result = preflight(protocol, gates, qualification)
            else:
                result = prepare_commands(protocol, gates, qualification, output=args.output,
                    protocol_path=args.protocol, gates_path=args.gates, qualification_path=args.qualification or '<pending-real-provider-qualification>')
        print(json.dumps(result, sort_keys=True, indent=2))
        if args.command in {'preflight', 'prepare','execution-preflight'}: return 0 if result.get('ready', result.get('executable')) else 2
        return 0
    except (OSError, ValueError, RuntimeError) as error:
        print(json.dumps({'ready': False, 'error': str(error)}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
