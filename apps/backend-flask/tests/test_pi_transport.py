from pathlib import Path
import json

from pg_agent_progress.pi import run_pi_task


def test_full_diagnostics_survive_ui_bounds_and_credentials_are_redacted(tmp_path, monkeypatch):
    secret = 'sensitive-"quoted-key'
    monkeypatch.setenv('PG_PI_API_KEY', secret)
    worker = tmp_path/'worker.mjs'
    worker.write_text('''let input=''; for await (const c of process.stdin) input+=c;
const stage=JSON.parse(input).workflow;
console.error('underlying compiler exit code 127: '+process.env.PG_PI_API_KEY);
console.log(JSON.stringify({type:'error',stage,message:'x'.repeat(12000)+' original exception '+process.env.PG_PI_API_KEY,metadata:{activity:'status',is_error:true}})); process.exitCode=7;
''')
    monkeypatch.setenv('PG_PI_RUNNER', str(worker))
    events=[]
    audit=tmp_path/'events.raw.jsonl'
    assert run_pi_task(cwd=str(tmp_path), prompt='Build', workflow='builder', emit=events.append, audit_path=audit) == 1
    text=audit.read_text()
    assert secret not in text
    assert 'original exception' in text
    assert 'underlying compiler exit code 127' in text
    assert '[REDACTED]' in text
    assert 'exit code 7' in events[-1]['message']
    assert any(len(event['message']) > 12000 for event in events)
    for line in text.splitlines():
        json.loads(line)
