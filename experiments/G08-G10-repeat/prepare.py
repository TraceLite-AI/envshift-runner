"""Prepare repeat evaluation without changing any model-visible task or agent code."""
import hashlib, json, pathlib, shutil

ROOT = pathlib.Path(__file__).resolve().parent
BASE = ROOT.parent / 'EnvShift-GUI第三批-20260914'
SOURCE_COMMIT = 'c230fc6a1c2fb98a336b7154ba8d15b16e6605c0'
names = ['gui_batch3.py', 'gui_agent_loop.py', 'task_world.py', 'app.js', 'app.css']
sources = ROOT / 'source'
sources.mkdir(exist_ok=True)
for name in names:
    shutil.copyfile(BASE / name, sources / name)
workflow = (BASE / 'gui-run.yml').read_text()
workflow = workflow.replace("      arm: { description:", "      trials: { description: independent fresh-runner trials, default: '[1,2,3,4,5]' }\n      arm: { description:")
workflow = workflow.replace("        task: ${{ fromJSON(inputs.tasks) }}", "        task: ${{ fromJSON(inputs.tasks) }}\n        trial: ${{ fromJSON(inputs.trials) }}")
workflow = workflow.replace("with: { persist-credentials: false }", "with: { persist-credentials: false, ref: '" + SOURCE_COMMIT + "' }")
workflow = workflow.replace("      - name: run GUI task", """      - name: record runtime before the trial
        shell: bash
        env:
          TRIAL_INDEX: ${{ matrix.trial }}
          TASK_ID: ${{ matrix.task }}
        run: |
          mkdir -p repeat_metadata
          python -m pip freeze > repeat_metadata/pip-freeze.txt
          python - <<'PY'
          import hashlib, json, os, pathlib, platform, subprocess, sys
          names = ['gui_batch3.py','gui_agent_loop.py','task_world.py','app.js','app.css']
          result = {'trial': os.environ['TRIAL_INDEX'], 'task': os.environ['TASK_ID'],
                    'source_commit': subprocess.check_output(['git','rev-parse','HEAD'], text=True).strip(),
                    'source_sha256': {n: hashlib.sha256(pathlib.Path(n).read_bytes()).hexdigest() for n in names},
                    'python': sys.version, 'platform': platform.platform(), 'machine': platform.machine(),
                    'runner_image': {k: os.environ.get(k) for k in ['ImageOS','ImageVersion','RUNNER_OS','RUNNER_ARCH']}}
          pathlib.Path('repeat_metadata/runtime.json').write_text(json.dumps(result, indent=2))
          PY
      - name: run GUI task""")
workflow = workflow[:workflow.index('      - uses: actions/upload-artifact@v4')] + """      - name: pack complete evidence without changing original bytes
        if: always()
        shell: bash
        run: |
          python - <<'PY'
          import hashlib, json, pathlib, shutil, tarfile
          out = pathlib.Path('gui_batch3_out')
          out.mkdir(exist_ok=True)
          if pathlib.Path('repeat_metadata').exists():
              shutil.copytree('repeat_metadata', out / 'repeat_metadata', dirs_exist_ok=True)
          manifest = {str(p.relative_to(out)): hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in sorted(out.rglob('*')) if p.is_file()}
          (out / 'EVIDENCE_SHA256.json').write_text(json.dumps(manifest, indent=2))
          packet = pathlib.Path('repeat_packet')
          packet.mkdir(exist_ok=True)
          with tarfile.open(packet / 'evidence.tar.xz', 'w:xz') as tar:
              tar.add(out, arcname='evidence')
          PY
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: gui-repeat-${{ matrix.task }}-${{ matrix.os }}-${{ inputs.arm }}-trial${{ matrix.trial }}
          path: repeat_packet/
          compression-level: 0
"""
(ROOT / 'gui-run.yml').write_text(workflow)
experiment = {
    'experiment': 'G08-G10 fixed-configuration repeat evaluation',
    'status': 'prepared', 'repo': 'TraceLite-AI/envshift-runner',
    'branch': 'codex/gui-repeat-20260914', 'parent_commit': 'b16cdf13c04f4444b26699f55c185f0527c92fa7',
    'source_commit': SOURCE_COMMIT,
    'source_sha256': {name: hashlib.sha256((sources / name).read_bytes()).hexdigest() for name in names},
    'tasks': ['G08','G10'], 'runner': 'ubuntu-24.04', 'viewport': [1280,900],
    'model': 'gemini-3.5-flash', 'gateway': 'https://api.llmgateway.io/v1',
    'tool_version': 'gui_native_v2', 'steps': 60,
    'sampling': 'Original request unchanged: temperature and seed omitted; provider defaults and model alias are not immutable snapshots.',
    'history': 'Latest screenshot and last six actions, no notebook.',
    'new_trials_per_task': 5, 'max_parallel': 3,
    'controls': 'One oracle and one materialized wrong-result control per task before model runs.',
    'validity': 'Exclude channel failures, missing trace, blind-image responses, setup errors; retain excluded evidence and report separately.',
    'stopping_rule': 'Collect five new valid trials per task. Replace at most two invalid infrastructure trials per task; never replace a valid failure or stop on desired results.',
    'interpretation': '0/5 successes establishes observed repeated failure under this configuration, not universal impossibility or an OS-specific effect.',
    'previous_trials': 'Exploratory baseline and notebook diagnostics remain separate from these prospective repeats.',
    'stable_os_failure_proven': False,
}
(ROOT / 'EXPERIMENT.json').write_text(json.dumps(experiment, ensure_ascii=False, indent=2) + '\n')
(ROOT / 'README.md').write_text('''# G08 / G10 GUI 固定配置复测

沿用原版 agent，在 Ubuntu 上每题新增 5 次独立运行，每次使用干净的 GitHub runner。
模型为 gemini-3.5-flash，60 步，gui_native_v2；不启用 notebook，不改变题面、工具说明或判据。
执行源码固定在 c230fc6a1c2fb98a336b7154ba8d15b16e6605c0。

先重跑两题的 oracle / wrong-result 对照，要求正确状态通过、实际产生的错误状态被拒绝。
先前探索样本单独保留，不混入新增 5 次的分母；有效失败不会被替换。
记录每次的软件版本、源码 SHA256、全部截图、动作、最终业务状态和判分。
本轮只检验固定配置下是否反复失败，不声称跨操作系统翻转或无限次必败。
网关后端和模型别名无法冻结；请求仍不显式指定温度或随机种子，与原版一致。
''')
print(json.dumps({'prepared': str(ROOT), 'source_sha256': experiment['source_sha256']}, indent=2))
