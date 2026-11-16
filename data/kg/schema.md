# Structured model schema (arm C)

Fixed schema, decided before building, so the graph is the same kind of object for any machine.

| Node type | What it holds | Where it comes from |
|---|---|---|
| Component | a physical part or board section (e.g. hotend heater, X belt) | BOM, config sections, assembly manual |
| Function | what the component does, one sentence | assembly manual, Voron docs |
| Parameter | a correct value and its unit/limit (e.g. max_temp = 270) | Klipper config (automatic) |
| Connection | electrical (board pin) or mechanical link to another component | config pins (automatic); manual (by hand) |
| FailureMode | a way the component can fail and the symptom it produces | derived from function + design docs (NOT from test cases) |
| Check | a test that confirms or rules out a failure mode | manual, Voron/Klipper docs |
| Source | document + page/line for every fact | all of the above |

Edges: Component-HAS_FUNCTION->Function, Component-HAS_PARAMETER->Parameter,
Component-CONNECTED_TO->Component (via Connection), Component-CAN_FAIL_AS->FailureMode,
FailureMode-CONFIRMED_BY->Check, every node -CITES->Source.

**Leakage rule:** nothing from evaluation/Test_Set is ever copied into this graph.
