# Development yardstick (2 twin faults per part; 'can't tell' 0%; wrong answers 0%)

| Set | Cases | Top-1 | Top-3 | Mean questions | Right after at most one 'this part is fine' | Questions then |
|---|---|---|---|---|---|---|
| twin (31 parts) | 62 | 52 % | 84 % | 4.5 | 74 % | 4.9 |
| practice (real) | 15 | 60 % | 87 % | 5.1 | 60 % | 5.2 |
| all | 77 | 53 % | 84 % | 4.6 | 71 % | 5.0 |

## Why the wrong ones failed

| Failure type | Cases | Share of failures |
|---|---|---|
| knowledge | 12 | 33 % |
| question | 0 | 0 % |
| stop | 5 | 14 % |
| reading | 19 | 53 % |

## Per part (twin)

| Part | Top-1 | Top-3 | Questions | Main failure | Most often named instead |
|---|---|---|---|---|---|
| hotend_heater | 100 % | 100 % | 4.0 |  |  |
| hotend_thermistor | 50 % | 100 % | 4.5 | stop | hotend_heater |
| nozzle | 50 % | 100 % | 5.5 | knowledge | extruder_gears_guidler |
| heatbreak_ptfe | 0 % | 50 % | 2.5 | reading | nozzle |
| extruder_motor | 0 % | 0 % | 6.0 | knowledge | nozzle |
| extruder_gears_guidler | 0 % | 100 % | 6.0 | knowledge | filament_material |
| hotend_fan | 0 % | 100 % | 1.0 | reading | extruder_gears_guidler |
| part_cooling_fan | 100 % | 100 % | 3.0 |  |  |
| xy_motors_drivers | 100 % | 100 % | 5.0 |  |  |
| xy_belts | 50 % | 100 % | 5.5 | stop | z_motor_leadscrew |
| xy_pulleys_idlers | 50 % | 50 % | 5.5 | knowledge | xy_motors_drivers |
| x_linear_rail | 100 % | 100 % | 6.5 |  |  |
| y_linear_rails | 100 % | 100 % | 6.5 |  |  |
| toolhead | 0 % | 50 % | 7.0 | reading | z_motor_leadscrew |
| z_motor_leadscrew | 100 % | 100 % | 3.0 |  |  |
| z_rails | 0 % | 50 % | 4.0 | knowledge | bed_plate_carrier |
| z_endstop | 0 % | 50 % | 5.0 | knowledge | toolhead |
| bed_heater | 100 % | 100 % | 5.0 |  |  |
| bed_thermistor | 50 % | 100 % | 6.0 | stop | bed_plate_carrier |
| bed_plate_carrier | 50 % | 100 % | 4.5 | stop | toolhead |
| controller_board | 50 % | 100 % | 2.5 | knowledge | host_computer |
| umbilical_wiring | 0 % | 50 % | 4.5 | reading | hotend_heater |
| power_supply | 100 % | 100 % | 4.5 |  |  |
| host_computer | 100 % | 100 % | 6.0 |  |  |
| filament_runout_sensor | 100 % | 100 % | 3.0 |  |  |
| firmware_config_macros | 0 % | 50 % | 6.0 | knowledge | hotend_thermistor |
| slicer_settings | 50 % | 100 % | 6.0 | stop | nozzle |
| filament_material | 50 % | 50 % | 1.5 | reading | extruder_gears_guidler |
| mains_power_input | 100 % | 100 % | 3.0 |  |  |
| dc_power_wiring | 50 % | 100 % | 4.0 | reading | host_computer |
| bed_thermal_fuse | 0 % | 100 % | 2.0 | reading | bed_heater |

## Practice cases

| Case | Truth | Named | Result | Failure |
|---|---|---|---|---|
| P01 | hotend_fan | heatbreak_ptfe | top3 | reading |
| P02 | umbilical_wiring | hotend_thermistor | TOP1 | correct |
| P03 | umbilical_wiring | extruder_motor | TOP1 | correct |
| P04 | firmware_config_macros | firmware_config_macros | TOP1 | correct |
| P05 | host_computer | power_supply | top3 | knowledge |
| P06 | umbilical_wiring | hotend_thermistor | TOP1 | correct |
| P07 | firmware_config_macros | bed_plate_carrier | top3 | knowledge |
| P08 | filament_material | bed_plate_carrier | miss | reading |
| P09 | xy_belts | xy_belts | TOP1 | correct |
| P10 | xy_pulleys_idlers | xy_belts | TOP1 | correct |
| P11 | xy_pulleys_idlers | xy_belts | TOP1 | correct |
| P12 | firmware_config_macros | hotend_heater | TOP1 | correct |
| P13 | bed_plate_carrier | z_motor_leadscrew | top3 | reading |
| P14 | z_motor_leadscrew | z_motor_leadscrew | TOP1 | correct |
| P15 | umbilical_wiring | host_computer | miss | reading |