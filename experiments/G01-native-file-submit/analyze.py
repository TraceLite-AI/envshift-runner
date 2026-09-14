"""Summarize explicitly selected corrected runs; excluded pilot runs stay excluded."""
import argparse
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--run', action='append', required=True, help='RUN_ID:artifact_directory')
args = parser.parse_args()
root = Path(__file__).resolve().parent
rows = []
for spec in args.run:
    run_id, directory = spec.split(':', 1)
    for path in sorted((root / directory).rglob('meta.json')):
        meta = json.loads(path.read_text(encoding='utf-8'))
        if meta.get('arm') != 'agent':
            continue
        loop_path = path.parent / 'agent' / 'loop.json'
        try:
            loop = json.loads(loop_path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            loop = {}
        history = loop.get('history', [])
        valid = bool(meta.get('valid_model_run')) and loop.get('coordinate_mode') == 'normalized_0_1000'
        last_action = history[-1].get('action') if history else None
        claimed_done = bool(last_action and last_action.get('action') == 'done')
        if not valid:
            classification = 'excluded_invalid_run'
        elif meta['reward'] == 1:
            classification = 'correct_submission'
        elif meta.get('submissions'):
            classification = 'incorrect_submission'
        elif claimed_done:
            classification = 'claimed_done_without_submission'
        else:
            classification = 'no_submission_within_action_budget'
        row = {
            **meta, 'run_id': int(run_id), 'artifact_meta': str(path.relative_to(root)),
            'protocol_valid': valid, 'coordinate_mode': loop.get('coordinate_mode'),
            'screen_size': loop.get('screen_size'), 'classification': classification,
            'last_action': last_action, 'claimed_done': claimed_done,
            'execution_errors': [h for h in history if '执行失败' in h.get('result', '')],
            'action_parse_errors': sum(h.get('action', {}).get('action') == '?' for h in history),
        }
        rows.append(row)
        print(row['platform'], 'reward=' + str(row['reward']), 'valid=' + str(valid),
              'steps=' + str(row['steps']), classification)
(root / 'AGENT_RESULTS.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
