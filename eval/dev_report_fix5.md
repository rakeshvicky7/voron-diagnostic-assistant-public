# Development yardstick (10 twin faults per part; 'can't tell' 0%; wrong answers 0%)

| Set | Cases | Top-1 | Top-3 | Mean questions | Right after at most one 'this part is fine' | Questions then |
|---|---|---|---|---|---|---|
| twin (31 parts) | 310 | 70 % | 90 % | 5.1 | 81 % | 5.2 |
| all | 310 | 70 % | 90 % | 5.1 | 81 % | 5.2 |

## Why the wrong ones failed

| Failure type | Cases | Share of failures |
|---|---|---|
| knowledge | 42 | 45 % |
| question | 0 | 0 % |
| stop | 39 | 42 % |
| reading | 12 | 13 % |

## Per part (twin)

| Part | Top-1 | Top-3 | Questions | Main failure | Most often named instead |
|---|---|---|---|---|---|
| hotend_heater | 100 % | 100 % | 2.0 |  |  |
| hotend_thermistor | 90 % | 100 % | 7.1 | stop | hotend_heater |
| nozzle | 30 % | 100 % | 5.2 | stop | extruder_motor |
| heatbreak_ptfe | 0 % | 100 % | 6.4 | knowledge | extruder_motor |
| extruder_motor | 100 % | 100 % | 5.2 |  |  |
| extruder_gears_guidler | 0 % | 100 % | 6.0 | stop | filament_material |
| hotend_fan | 100 % | 100 % | 6.0 |  |  |
| part_cooling_fan | 100 % | 100 % | 4.0 |  |  |
| xy_motors_drivers | 100 % | 100 % | 5.8 |  |  |
| xy_belts | 50 % | 100 % | 6.0 | stop | z_motor_leadscrew |
| xy_pulleys_idlers | 50 % | 50 % | 5.5 | knowledge | xy_motors_drivers |
| x_linear_rail | 100 % | 100 % | 5.9 |  |  |
| y_linear_rails | 100 % | 100 % | 5.9 |  |  |
| toolhead | 50 % | 50 % | 5.9 | reading | z_motor_leadscrew |
| z_motor_leadscrew | 70 % | 100 % | 4.8 | stop | z_rails |
| z_rails | 40 % | 80 % | 4.4 | knowledge | bed_plate_carrier |
| z_endstop | 60 % | 60 % | 4.6 | knowledge | bed_plate_carrier |
| bed_heater | 100 % | 100 % | 3.8 |  |  |
| bed_thermistor | 50 % | 100 % | 7.0 | stop | filament_material |
| bed_plate_carrier | 100 % | 100 % | 4.0 |  |  |
| controller_board | 50 % | 50 % | 4.8 | knowledge | host_computer |
| umbilical_wiring | 40 % | 60 % | 7.0 | stop | hotend_thermistor |
| power_supply | 100 % | 100 % | 4.5 |  |  |
| host_computer | 100 % | 100 % | 6.4 |  |  |
| filament_runout_sensor | 100 % | 100 % | 2.0 |  |  |
| firmware_config_macros | 0 % | 70 % | 6.1 | knowledge | toolhead |
| slicer_settings | 50 % | 70 % | 5.5 | knowledge | extruder_motor |
| filament_material | 60 % | 90 % | 4.1 | knowledge | slicer_settings |
| mains_power_input | 90 % | 100 % | 4.2 | knowledge | power_supply |
| dc_power_wiring | 90 % | 100 % | 6.0 | knowledge | host_computer |
| bed_thermal_fuse | 100 % | 100 % | 2.0 |  |  |