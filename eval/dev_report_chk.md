# Development yardstick (6 twin faults per part; 'can't tell' 0%; wrong answers 0%)

| Set | Cases | Top-1 | Top-3 | Mean questions | Right after at most one 'this part is fine' | Questions then |
|---|---|---|---|---|---|---|
| twin (31 parts) | 186 | 68 % | 89 % | 5.3 | 83 % | 5.4 |
| all | 186 | 68 % | 89 % | 5.3 | 83 % | 5.4 |

## Why the wrong ones failed

| Failure type | Cases | Share of failures |
|---|---|---|
| knowledge | 29 | 49 % |
| question | 0 | 0 % |
| stop | 24 | 41 % |
| reading | 6 | 10 % |

## Per part (twin)

| Part | Top-1 | Top-3 | Questions | Main failure | Most often named instead |
|---|---|---|---|---|---|
| hotend_heater | 100 % | 100 % | 2.0 |  |  |
| hotend_thermistor | 83 % | 100 % | 7.7 | stop | hotend_heater |
| nozzle | 83 % | 100 % | 4.5 | knowledge | extruder_gears_guidler |
| heatbreak_ptfe | 0 % | 100 % | 6.0 | knowledge | extruder_motor |
| extruder_motor | 50 % | 100 % | 5.0 | knowledge | nozzle |
| extruder_gears_guidler | 0 % | 100 % | 6.0 | stop | filament_material |
| hotend_fan | 100 % | 100 % | 6.0 |  |  |
| part_cooling_fan | 100 % | 100 % | 5.0 |  |  |
| xy_motors_drivers | 100 % | 100 % | 5.7 |  |  |
| xy_belts | 67 % | 100 % | 5.7 | stop | z_motor_leadscrew |
| xy_pulleys_idlers | 67 % | 67 % | 4.5 | knowledge | xy_motors_drivers |
| x_linear_rail | 100 % | 100 % | 5.8 |  |  |
| y_linear_rails | 100 % | 100 % | 5.8 |  |  |
| toolhead | 33 % | 33 % | 7.3 | reading | z_motor_leadscrew |
| z_motor_leadscrew | 67 % | 100 % | 4.8 | stop | z_rails |
| z_rails | 50 % | 83 % | 4.5 | knowledge | bed_plate_carrier |
| z_endstop | 83 % | 83 % | 4.8 | knowledge | bed_plate_carrier |
| bed_heater | 100 % | 100 % | 4.0 |  |  |
| bed_thermistor | 67 % | 100 % | 6.7 | stop | bed_plate_carrier |
| bed_plate_carrier | 100 % | 100 % | 4.3 |  |  |
| controller_board | 67 % | 67 % | 4.3 | knowledge | host_computer |
| umbilical_wiring | 33 % | 67 % | 7.2 | stop | hotend_thermistor |
| power_supply | 100 % | 100 % | 4.3 |  |  |
| host_computer | 100 % | 100 % | 6.8 |  |  |
| filament_runout_sensor | 100 % | 100 % | 2.0 |  |  |
| firmware_config_macros | 17 % | 50 % | 7.3 | knowledge | toolhead |
| slicer_settings | 33 % | 33 % | 5.2 | knowledge | nozzle |
| filament_material | 83 % | 83 % | 5.8 | knowledge | extruder_motor |
| mains_power_input | 100 % | 100 % | 3.7 |  |  |
| dc_power_wiring | 33 % | 100 % | 6.0 | knowledge | host_computer |
| bed_thermal_fuse | 0 % | 100 % | 6.0 | stop | hotend_thermistor |