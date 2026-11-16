# Development yardstick (10 twin faults per part; 'can't tell' 0%; wrong answers 0%)

| Set | Cases | Top-1 | Top-3 | Mean questions |
|---|---|---|---|---|
| twin (31 parts) | 310 | 40 % | 65 % | 5.0 |
| practice (real) | 1 | 0 % | 100 % | 4.0 |
| all | 311 | 40 % | 65 % | 5.0 |

## Why the wrong ones failed

| Failure type | Cases | Share of failures |
|---|---|---|
| knowledge | 155 | 83 % |
| question | 0 | 0 % |
| stop | 26 | 14 % |
| reading | 6 | 3 % |

## Per part (twin)

| Part | Top-1 | Top-3 | Questions | Main failure | Most often named instead |
|---|---|---|---|---|---|
| hotend_heater | 100 % | 100 % | 4.0 |  |  |
| hotend_thermistor | 30 % | 40 % | 4.5 | knowledge | bed_thermistor |
| nozzle | 80 % | 100 % | 3.7 | knowledge | extruder_gears_guidler |
| heatbreak_ptfe | 0 % | 100 % | 4.0 | stop | extruder_motor |
| extruder_motor | 40 % | 40 % | 4.6 | knowledge | nozzle |
| extruder_gears_guidler | 0 % | 100 % | 6.0 | stop | filament_material |
| hotend_fan | 0 % | 0 % | 4.0 | knowledge | extruder_motor |
| part_cooling_fan | 0 % | 0 % | 8.0 | knowledge | z_rails |
| xy_motors_drivers | 100 % | 100 % | 4.0 |  |  |
| xy_belts | 50 % | 50 % | 5.0 | knowledge | z_motor_leadscrew |
| xy_pulleys_idlers | 10 % | 50 % | 6.6 | knowledge | z_motor_leadscrew |
| x_linear_rail | 30 % | 100 % | 6.3 | knowledge | xy_motors_drivers |
| y_linear_rails | 30 % | 100 % | 5.4 | knowledge | xy_motors_drivers |
| toolhead | 0 % | 50 % | 6.5 | knowledge | z_motor_leadscrew |
| z_motor_leadscrew | 70 % | 70 % | 6.5 | knowledge | z_endstop |
| z_rails | 0 % | 40 % | 3.8 | knowledge | bed_plate_carrier |
| z_endstop | 60 % | 60 % | 6.4 | knowledge | bed_plate_carrier |
| bed_heater | 100 % | 100 % | 4.4 |  |  |
| bed_thermistor | 0 % | 50 % | 6.5 | knowledge | bed_plate_carrier |
| bed_plate_carrier | 100 % | 100 % | 5.0 |  |  |
| controller_board | 60 % | 100 % | 2.8 | knowledge | host_computer |
| umbilical_wiring | 40 % | 100 % | 4.4 | stop | hotend_thermistor |
| power_supply | 100 % | 100 % | 7.1 |  |  |
| host_computer | 30 % | 80 % | 5.8 | stop | bed_thermistor |
| filament_runout_sensor | 100 % | 100 % | 2.0 |  |  |
| firmware_config_macros | 40 % | 70 % | 7.0 | knowledge | part_cooling_fan |
| slicer_settings | 0 % | 0 % | 4.2 | knowledge | nozzle |
| filament_material | 0 % | 40 % | 6.6 | knowledge | slicer_settings |
| mains_power_input | 70 % | 70 % | 3.5 | knowledge | filament_runout_sensor |
| dc_power_wiring | 0 % | 10 % | 2.1 | knowledge | host_computer |
| bed_thermal_fuse | 0 % | 0 % | 5.0 | knowledge | bed_heater |

## Practice cases

| Case | Truth | Named | Result | Failure |
|---|---|---|---|---|
| P01 | hotend_fan | bed_thermal_fuse | top3 | reading |