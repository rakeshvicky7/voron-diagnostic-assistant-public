# Development yardstick (10 twin faults per part; 'can't tell' 0%; wrong answers 0%)

| Set | Cases | Top-1 | Top-3 | Mean questions | Right after at most one 'this part is fine' | Questions then |
|---|---|---|---|---|---|---|
| practice (real) | 15 | 67 % | 73 % | 5.9 | 67 % | 6.1 |
| all | 15 | 67 % | 73 % | 5.9 | 67 % | 6.1 |

## Why the wrong ones failed

| Failure type | Cases | Share of failures |
|---|---|---|
| knowledge | 4 | 80 % |
| question | 0 | 0 % |
| stop | 0 | 0 % |
| reading | 1 | 20 % |

## Per part (twin)

| Part | Top-1 | Top-3 | Questions | Main failure | Most often named instead |
|---|---|---|---|---|---|

## Practice cases

| Case | Truth | Named | Result | Failure |
|---|---|---|---|---|
| P01 | hotend_fan | heatbreak_ptfe | miss | reading |
| P02 | umbilical_wiring | hotend_thermistor | TOP1 | correct |
| P03 | umbilical_wiring | extruder_motor | TOP1 | correct |
| P04 | firmware_config_macros | firmware_config_macros | TOP1 | correct |
| P05 | host_computer | host_computer | TOP1 | correct |
| P06 | umbilical_wiring | hotend_thermistor | TOP1 | correct |
| P07 | firmware_config_macros | bed_plate_carrier | miss | knowledge |
| P08 | filament_material | firmware_config_macros | miss | knowledge |
| P09 | xy_belts | xy_belts | TOP1 | correct |
| P10 | xy_pulleys_idlers | xy_pulleys_idlers | TOP1 | correct |
| P11 | xy_pulleys_idlers | xy_pulleys_idlers | TOP1 | correct |
| P12 | firmware_config_macros | hotend_heater | TOP1 | correct |
| P13 | bed_plate_carrier | z_rails | top3 | knowledge |
| P14 | z_motor_leadscrew | z_motor_leadscrew | TOP1 | correct |
| P15 | umbilical_wiring | controller_board | miss | knowledge |