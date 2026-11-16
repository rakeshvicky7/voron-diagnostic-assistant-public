# Development yardstick (6 twin faults per part; 'can't tell' 0%; wrong answers 10%)

| Set | Cases | Top-1 | Top-3 | Mean questions | Right after at most one 'this part is fine' | Questions then |
|---|---|---|---|---|---|---|
| twin (31 parts) | 186 | 58 % | 82 % | 5.2 | 75 % | 5.5 |
| all | 186 | 58 % | 82 % | 5.2 | 75 % | 5.5 |

## Why the wrong ones failed

| Failure type | Cases | Share of failures |
|---|---|---|
| knowledge | 27 | 34 % |
| question | 0 | 0 % |
| stop | 44 | 56 % |
| reading | 8 | 10 % |

## Per part (twin)

| Part | Top-1 | Top-3 | Questions | Main failure | Most often named instead |
|---|---|---|---|---|---|
| hotend_heater | 100 % | 100 % | 2.0 |  |  |
| hotend_thermistor | 17 % | 83 % | 7.3 | stop | hotend_heater |
| nozzle | 50 % | 83 % | 4.8 | stop | extruder_gears_guidler |
| heatbreak_ptfe | 0 % | 83 % | 5.7 | knowledge | extruder_motor |
| extruder_motor | 33 % | 100 % | 5.0 | knowledge | nozzle |
| extruder_gears_guidler | 0 % | 67 % | 6.2 | stop | filament_material |
| hotend_fan | 67 % | 100 % | 5.0 | stop | extruder_motor |
| part_cooling_fan | 83 % | 83 % | 5.3 | stop | slicer_settings |
| xy_motors_drivers | 100 % | 100 % | 5.8 |  |  |
| xy_belts | 83 % | 100 % | 5.5 | stop | z_motor_leadscrew |
| xy_pulleys_idlers | 67 % | 83 % | 4.3 | knowledge | xy_motors_drivers |
| x_linear_rail | 50 % | 83 % | 6.0 | stop | z_motor_leadscrew |
| y_linear_rails | 50 % | 83 % | 6.0 | stop | z_motor_leadscrew |
| toolhead | 33 % | 33 % | 7.3 | reading | z_motor_leadscrew |
| z_motor_leadscrew | 67 % | 100 % | 4.5 | stop | z_rails |
| z_rails | 50 % | 83 % | 4.7 | knowledge | bed_plate_carrier |
| z_endstop | 67 % | 83 % | 5.7 | knowledge | bed_plate_carrier |
| bed_heater | 100 % | 100 % | 4.2 |  |  |
| bed_thermistor | 50 % | 83 % | 7.0 | stop | bed_plate_carrier |
| bed_plate_carrier | 83 % | 100 % | 4.8 | stop | z_motor_leadscrew |
| controller_board | 67 % | 67 % | 4.0 | knowledge | host_computer |
| umbilical_wiring | 17 % | 67 % | 6.5 | stop | hotend_thermistor |
| power_supply | 67 % | 100 % | 3.8 | stop | mains_power_input |
| host_computer | 67 % | 67 % | 7.3 | knowledge | bed_thermistor |
| filament_runout_sensor | 100 % | 100 % | 2.7 |  |  |
| firmware_config_macros | 17 % | 50 % | 7.2 | knowledge | hotend_heater |
| slicer_settings | 17 % | 17 % | 5.3 | knowledge | nozzle |
| filament_material | 67 % | 67 % | 6.2 | knowledge | extruder_motor |
| mains_power_input | 83 % | 100 % | 3.7 | stop | power_supply |
| dc_power_wiring | 67 % | 100 % | 6.0 | knowledge | host_computer |
| bed_thermal_fuse | 67 % | 83 % | 2.5 | stop | bed_heater |