# G11–G13 GUI validation summary

Nine valid agent trials on three operating systems: **9 passed, 0 failed**. No new badcase. The previous four badcase tasks and 22 failure trajectories remain unchanged.

| Task | Ubuntu | macOS | Windows |
|---|---|---|---|
| G11 native report save | pass, 60 steps | pass, 42 steps | pass, 20 steps |
| G12 supplier selection | pass, 4 steps | pass, 5 steps | pass, 4 steps |
| G13 wide inventory grid | pass, 16 steps | pass, 16 steps | pass, 34 steps |

Model: gemini-3.5-flash, unchanged gui_native_v2, 60-action budget. All nine task/OS positive and actual wrong-result controls passed before the agent trials.

G11 repeatedly exported the same correct file (11 / 7 / 4 successful exports). Ubuntu exhausted the action budget but the delivered files passed the predeclared verifier; this is an efficiency observation, not a scored failure. G12 was solved directly from the visible candidate list without search. G13 required more navigation on Windows but the agent recovered and saved the exact three requested cells.

Each task/OS has one initial model trial; no stability or OS-causality claim. G11 is related to the G04 save/overwrite family; G12 shares entity ambiguity with G08.

[Agent run](https://github.com/TraceLite-AI/envshift-runner/actions/runs/34855526346). Tested source: `ec992aff90107f2fb50ba9f2917ae2022845fe6d`.

This commit contains aggregate results only. Full original screenshots, action logs, runtime records and archives are retained in the local evidence package; they are not republished in Git.
