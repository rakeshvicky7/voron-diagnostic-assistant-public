# Development yardstick (10 twin faults per part; 'can't tell' 0%; wrong answers 0%)

| Set | Cases | Top-1 | Top-3 | Mean questions | Right after at most one 'this part is fine' | Questions then |
|---|---|---|---|---|---|---|
| twin (31 parts) | 310 | 70 % | 89 % | 5.2 | 82 % | 5.3 |
| all | 310 | 70 % | 89 % | 5.2 | 82 % | 5.3 |

## Why the wrong ones failed

| Failure type | Cases | Share of failures |
|---|---|---|
| knowledge | 52 | 56 % |
| question | 0 | 0 % |
| stop | 32 | 34 % |
| reading | 9 | 10 % |

## Per part (twin)

| Part | Top-1 | Top-3 | Questions | Main failure | Most often named instead |
|---|---|---|---|---|---|
| hotend_heater | 100 % | 100 % | 2.0 |  |  |
| hotend_thermistor | 90 % | 100 % | 7.2 | stop | hotend_heater |
| nozzle | 80 % | 100 % | 4.7 | knowledge | extruder_gears_guidler |
| heatbreak_ptfe | 0 % | 100 % | 6.0 | knowledge | extruder_motor |
| extruder_motor | 40 % | 100 % | 5.0 | knowledge | nozzle |
| extruder_gears_guidler | 0 % | 100 % | 6.0 | stop | filament_material |
| hotend_fan | 100 % | 100 % | 6.0 |  |  |
| part_cooling_fan | 100 % | 100 % | 5.0 |  |  |
| xy_motors_drivers | 100 % | 100 % | 5.8 |  |  |
| xy_belts | 50 % | 100 % | 6.0 | stop | z_motor_leadscrew |
| xy_pulleys_idlers | 50 % | 50 % | 5.1 | knowledge | xy_motors_drivers |
| x_linear_rail | 100 % | 100 % | 5.9 |  |  |
| y_linear_rails | 100 % | 100 % | 5.9 |  |  |
| toolhead | 50 % | 50 % | 7.1 | reading | z_motor_leadscrew |
| z_motor_leadscrew | 70 % | 100 % | 4.8 | stop | z_rails |
| z_rails | 40 % | 80 % | 4.4 | knowledge | bed_plate_carrier |
| z_endstop | 60 % | 60 % | 4.6 | knowledge | bed_plate_carrier |
| bed_heater | 100 % | 100 % | 4.2 |  |  |
| bed_thermistor | 50 % | 100 % | 6.5 | stop | bed_plate_carrier |
| bed_plate_carrier | 100 % | 100 % | 4.5 |  |  |
| controller_board | 50 % | 50 % | 4.3 | knowledge | host_computer |
| umbilical_wiring | 40 % | 80 % | 7.1 | stop | hotend_thermistor |
| power_supply | 100 % | 100 % | 4.5 |  |  |
| host_computer | 100 % | 100 % | 6.3 |  |  |
| filament_runout_sensor | 100 % | 100 % | 2.0 |  |  |
| firmware_config_macros | 30 % | 60 % | 7.4 | knowledge | toolhead |
| slicer_settings | 50 % | 50 % | 5.5 | knowledge | nozzle |
| filament_material | 90 % | 90 % | 5.1 | knowledge | extruder_motor |
| mains_power_input | 90 % | 100 % | 4.2 | knowledge | power_supply |
| dc_power_wiring | 40 % | 100 % | 5.9 | knowledge | host_computer |
| bed_thermal_fuse | 100 % | 100 % | 2.0 |  |  |