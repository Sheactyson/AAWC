"""Read-only, per-file CK3 log summary; never combines duplicate log streams.

Use retained non-rotated logs from one documented session. A quiet log is not
proof that later simulation is error-free. This tool applies no release waivers.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re


def summarize(directory):
    reports = {}
    for name in ('debug.log', 'error.log', 'game.log'):
        path = directory / name
        if not path.exists():
            reports[name] = {'available': False}
            continue
        raw = path.read_bytes()
        text = raw.decode('utf-8-sig', errors='replace')
        blocks = re.split(r'(?m)(?=^\[\d\d:\d\d:\d\d\]\[)', text)
        errors = [b for b in blocks if 'Script system error!' in b]
        messages, sites = Counter(), Counter()
        cohort_error_blocks = []
        for block in errors:
            match = re.search(r'Error:\s*(.*?)\s*Script location:', block, re.S)
            messages[re.sub(r'\s+', ' ', match.group(1)).strip() if match else '(unparsed; inspect raw log)'] += 1
            location = re.search(r'Script location:\s*(.*)', block)
            sites[location.group(1).strip() if location else '(unparsed; inspect raw log)'] += 1
            if 'aawc_reforging_cohort' in block:
                cohort_error_blocks.append(block)
        times = re.findall(r'(?m)^\[(\d\d:\d\d:\d\d)\]', text)
        diagnostics = {}
        for marker in ('AAWC DIAG phase marker', 'AAWC DIAG world heartbeat', 'AAWC DIAG first invariant/accounting failure'):
            rows = [line for line in text.splitlines() if marker in line]
            diagnostics[marker] = {'count': len(rows), 'first': rows[0] if rows else None,
                                   'last': rows[-1] if rows else None}
        reports[name] = {
            'available': True, 'bytes': len(raw),
            'sha256': hashlib.sha256(raw).hexdigest().upper(),
            'first_log_clock': times[0] if times else None,
            'last_log_clock': times[-1] if times else None,
            'cohort_tick_pass': text.count('AAWC REFORGING STAGE1 cohort tick PASS:'),
            'cohort_tick_fail': text.count('AAWC REFORGING STAGE1 cohort tick FAIL:'),
            'script_error_headers': text.count('Script system error!'),
            'script_error_blocks': len(errors),
            'error_types': messages.most_common(),
            'error_sites': sites.most_common(),
            'cohort_script_error_blocks': cohort_error_blocks,
            'durable_diagnostic_log_markers': diagnostics,
        }
    return {'files': reports, 'limits': [
        'Per-file counts overlap; never sum debug.log and error.log as distinct errors.',
        'Clock strings carry no date and cannot establish coverage after logging ceases.',
        'Cohort PASS diagnostics do not certify integer transfers or all engine errors.',
        'No error is waived; inspect retained raw records for complete attribution.',
        'Sparse heartbeat log lines are not the saved counters; verify counters and failure snapshots in manual saves.',
    ]}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = summarize(args.directory)
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({n: {k: v for k, v in r.items() if k not in (
        'error_types', 'error_sites', 'cohort_script_error_blocks')}
        for n, r in result['files'].items()}, indent=2))
