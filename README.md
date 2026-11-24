# Planar truss stability: Abaqus reproduction

Scripts for the seven-member planar truss in the accompanying buckling verification and machine-learning reports. The code regenerates solver inputs and extracts report quantities. It does not contain student or laboratory measurement files, credentials, the online learning model, or Abaqus itself.

## Scope

| Suite | Abaqus jobs | Contents |
| --- | ---: | --- |
| `buckling` | 100 | 25 lengths of member 5 (370–150 mm), independently solved with no plate, the left plate, the right plate and both plates. B23; 16 elements per member. |
| `curves` | 100 | Ten mechanically independent imperfect specimens per job: 1,000 loading histories, recorded at 65 frames each. |
| `refined` | 5 | Independent checks at 32 elements per member. |

Units are N, mm and MPa. The other six members are 260 mm long. A plate shares the translations and rotations of the three adjoining ends, not their rotation with the ground. See `cases.json` for the precise lengths, run controls and SHA-256 of each accepted input.

## Reproduce a paired example

Prerequisites: Python 3.10+ for input preparation, and a licensed Abaqus 2026/Standard installation for solving and reading ODB files. Use the Abaqus command appropriate to your installation. Enter these commands from the repository root:

```text
python prepare.py
python prepare.py --case L260_260_none_n16 --case T305_none --out inputs
cd inputs
abaqus job=L260_260_none_n16 input=L260_260_none_n16.inp interactive
abaqus python ../extract_odb.py L260_260_none_n16 --out L260_260_none_n16.json
abaqus job=T305_none input=T305_none.inp interactive
abaqus python ../extract_odb.py T305_none --out T305_none.json
```

- `python prepare.py` checks all 205 input SHA-256 values without running the solver. To generate all decks, use `python prepare.py --out inputs`, or select a suite with `--suite buckling`, `--suite curves` or `--suite refined`.
- The linear example should report a first positive load of approximately 327.16 N. Mode groups are identified within 0.05% of the first positive load. The JSON reports unit-load balance, the leading rods and the archived reference result.
- The nonlinear example reports ten sets of `[F_N, rod1_ue, rod4_ue, rod5_ue, down_mm]` with frame 0 the unloaded state. `stop_frame` is the first recorded frame in which the absolute strain of any monitored member reaches 1200 microstrain; this is a recording rule, not an eigenvalue. All 65 frames are preserved.
- The extractor checks the input hash and successful solver status before reading the ODB. Numerical results do not require bit-identical ODB files across installations. Nominal linear verification and imperfect nonlinear curves refer to different model questions and should not be interchanged.

For the reports, the 100 linear cases check the idealized calculation, while the 1,000 simulated curves are inputs for possible data augmentation. The repository does not reproduce the separate experimental leave-group-out results without the controlled experimental records.
