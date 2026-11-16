# Development yardstick (2 twin faults per part; 'can't tell' 0%; wrong answers 0%)

| Set | Cases | Top-1 | Top-3 | Mean questions | Right after at most one 'this part is fine' | Questions then |
|---|---|---|---|---|---|---|
| twin (31 parts) | 62 | 63 % | 84 % | 5.3 | 81 % | 5.4 |
| practice (real) | 15 | 67 % | 80 % | 5.7 | 67 % | 5.9 |
| all | 77 | 64 % | 83 % | 5.4 | 78 % | 5.5 |

## Why the wrong ones failed

| Failure type | Cases | Share of failures |
|---|---|---|
| knowledge | 14 | 50 % |
| question | 0 | 0 % |
| stop | 10 | 36 % |
| reading | 4 | 14 % |

## Per part (twin)

| Part | Top-1 | Top-3 | Questions | Main failure | Most often named instead |
|---|---|---|---|---|---|
| hotend_heater | 100 % | 100 % | 2.0 |  |  |
| hotend_thermistor | 50 % | 100 % | 7.0 | stop | hotend_heater |
| nozzle | 50 % | 100 % | 5.5 | stop | extruder_gears_guidler |
| heatbreak_ptfe | 50 % | 100 % | 5.5 | reading | nozzle |
| extruder_motor | 0 % | 0 % | 6.0 | knowledge | nozzle |
| extruder_gears_guidler | 0 % | 100 % | 6.0 | stop | filament_material |
| hotend_fan | 100 % | 100 % | 6.0 |  |  |
| part_cooling_fan | 100 % | 100 % | 4.0 |  |  |
| xy_motors_drivers | 100 % | 100 % | 6.0 |  |  |
| xy_belts | 50 % | 100 % | 6.0 | stop | z_motor_leadscrew |
| xy_pulleys_idlers | 50 % | 50 % | 5.5 | knowledge | xy_motors_drivers |
| x_linear_rail | 100 % | 100 % | 6.5 |  |  |
| y_linear_rails | 100 % | 100 % | 6.5 |  |  |
| toolhead | 50 % | 50 % | 6.0 | reading | z_motor_leadscrew |
| z_motor_leadscrew | 50 % | 100 % | 5.0 | stop | z_rails |
| z_rails | 50 % | 100 % | 4.5 | knowledge | bed_plate_carrier |
| z_endstop | 50 % | 50 % | 4.5 | knowledge | bed_plate_carrier |
| bed_heater | 100 % | 100 % | 5.0 |  |  |
| bed_thermistor | 50 % | 100 % | 7.0 | stop | filament_material |
| bed_plate_carrier | 100 % | 100 % | 4.0 |  |  |
| controller_board | 50 % | 50 % | 5.0 | knowledge | host_computer |
| umbilical_wiring | 0 % | 0 % | 7.0 | stop | hotend_heater |
| power_supply | 100 % | 100 % | 4.5 |  |  |
| host_computer | 100 % | 100 % | 7.5 |  |  |
| filament_runout_sensor | 100 % | 100 % | 2.0 |  |  |
| firmware_config_macros | 0 % | 50 % | 5.5 | knowledge | hotend_heater |
| slicer_settings | 50 % | 100 % | 6.0 | stop | nozzle |
| filament_material | 50 % | 50 % | 4.0 | knowledge | heatbreak_ptfe |
| mains_power_input | 100 % | 100 % | 3.0 |  |  |
| dc_power_wiring | 100 % | 100 % | 6.0 |  |  |
| bed_thermal_fuse | 0 % | 100 % | 6.0 | knowledge | hotend_thermistor |

## Practice cases

| Case | Truth | Named | Result | Failure |
|---|---|---|---|---|
| P01 | hotend_fan | heatbreak_ptfe | miss | reading |
| P02 | umbilical_wiring | hotend_thermistor | TOP1 | correct |
| P03 | umbilical_wiring | extruder_motor | TOP1 | correct |
| P04 | firmware_config_macros | firmware_config_macros | TOP1 | correct |
| P05 | host_computer | host_computer | TOP1 | correct |
| P06 | umbilical_wiring | hotend_thermistor | TOP1 | correct |
| P07 | firmware_config_macros | bed_plate_carrier | top3 | knowledge |
| P08 | filament_material | firmware_config_macros | miss | knowledge |
| P09 | xy_belts | xy_belts | TOP1 | correct |
| P10 | xy_pulleys_idlers | xy_pulleys_idlers | TOP1 | correct |
| P11 | xy_pulleys_idlers | xy_pulleys_idlers | TOP1 | correct |
| P12 | firmware_config_macros | hotend_heater | TOP1 | correct |
| P13 | bed_plate_carrier | z_rails | top3 | knowledge |
| P14 | z_motor_leadscrew | z_motor_leadscrew | TOP1 | correct |
| P15 | umbilical_wiring | controller_board | miss | knowledge |