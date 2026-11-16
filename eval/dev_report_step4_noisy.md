# Development yardstick (10 twin faults per part; 'can't tell' 15%; wrong answers 10%)

| Set | Cases | Top-1 | Top-3 | Mean questions | Right after at most one 'this part is fine' | Questions then |
|---|---|---|---|---|---|---|
| twin (31 parts) | 310 | 54 % | 78 % | 5.4 | 75 % | 5.6 |
| all | 310 | 54 % | 78 % | 5.4 | 75 % | 5.6 |

## Why the wrong ones failed

| Failure type | Cases | Share of failures |
|---|---|---|
| knowledge | 55 | 39 % |
| question | 0 | 0 % |
| stop | 74 | 52 % |
| reading | 13 | 9 % |

## Per part (twin)

| Part | Top-1 | Top-3 | Questions | Main failure | Most often named instead |
|---|---|---|---|---|---|
| hotend_heater | 100 % | 100 % | 2.3 |  |  |
| hotend_thermistor | 30 % | 80 % | 6.8 | stop | hotend_heater |
| nozzle | 50 % | 80 % | 5.0 | stop | extruder_gears_guidler |
| heatbreak_ptfe | 10 % | 80 % | 5.4 | knowledge | extruder_motor |
| extruder_motor | 50 % | 100 % | 5.6 | knowledge | nozzle |
| extruder_gears_guidler | 0 % | 50 % | 6.1 | stop | filament_material |
| hotend_fan | 60 % | 90 % | 5.4 | stop | extruder_motor |
| part_cooling_fan | 90 % | 90 % | 6.6 | stop | slicer_settings |
| xy_motors_drivers | 100 % | 100 % | 5.7 |  |  |
| xy_belts | 70 % | 100 % | 5.9 | stop | z_motor_leadscrew |
| xy_pulleys_idlers | 40 % | 70 % | 5.2 | knowledge | xy_motors_drivers |
| x_linear_rail | 50 % | 70 % | 6.2 | stop | xy_motors_drivers |
| y_linear_rails | 40 % | 70 % | 6.2 | stop | xy_motors_drivers |
| toolhead | 40 % | 50 % | 7.0 | reading | hotend_thermistor |
| z_motor_leadscrew | 90 % | 90 % | 6.8 | stop | z_rails |
| z_rails | 40 % | 70 % | 4.7 | knowledge | z_motor_leadscrew |
| z_endstop | 40 % | 60 % | 5.8 | knowledge | bed_plate_carrier |
| bed_heater | 80 % | 80 % | 4.6 | stop | bed_plate_carrier |
| bed_thermistor | 30 % | 80 % | 6.5 | knowledge | bed_plate_carrier |
| bed_plate_carrier | 80 % | 100 % | 5.1 | stop | z_motor_leadscrew |
| controller_board | 50 % | 50 % | 4.5 | knowledge | host_computer |
| umbilical_wiring | 30 % | 50 % | 6.7 | stop | hotend_thermistor |
| power_supply | 70 % | 100 % | 4.7 | stop | mains_power_input |
| host_computer | 60 % | 60 % | 6.4 | stop | mains_power_input |
| filament_runout_sensor | 100 % | 100 % | 2.5 |  |  |
| firmware_config_macros | 10 % | 70 % | 6.8 | knowledge | toolhead |
| slicer_settings | 20 % | 20 % | 5.6 | stop | nozzle |
| filament_material | 70 % | 70 % | 5.3 | knowledge | extruder_motor |
| mains_power_input | 80 % | 100 % | 4.7 | stop | power_supply |
| dc_power_wiring | 60 % | 100 % | 5.7 | knowledge | host_computer |
| bed_thermal_fuse | 40 % | 80 % | 2.7 | stop | bed_heater |