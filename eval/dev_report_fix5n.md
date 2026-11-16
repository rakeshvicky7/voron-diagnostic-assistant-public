# Development yardstick (10 twin faults per part; 'can't tell' 15%; wrong answers 10%)

| Set | Cases | Top-1 | Top-3 | Mean questions | Right after at most one 'this part is fine' | Questions then |
|---|---|---|---|---|---|---|
| twin (31 parts) | 310 | 54 % | 81 % | 5.5 | 72 % | 5.6 |
| all | 310 | 54 % | 81 % | 5.5 | 72 % | 5.6 |

## Why the wrong ones failed

| Failure type | Cases | Share of failures |
|---|---|---|
| knowledge | 46 | 32 % |
| question | 0 | 0 % |
| stop | 81 | 57 % |
| reading | 15 | 11 % |

## Per part (twin)

| Part | Top-1 | Top-3 | Questions | Main failure | Most often named instead |
|---|---|---|---|---|---|
| hotend_heater | 100 % | 100 % | 2.3 |  |  |
| hotend_thermistor | 40 % | 80 % | 6.8 | stop | firmware_config_macros |
| nozzle | 30 % | 90 % | 5.0 | stop | extruder_motor |
| heatbreak_ptfe | 0 % | 80 % | 6.0 | knowledge | extruder_motor |
| extruder_motor | 80 % | 100 % | 5.4 | stop | filament_material |
| extruder_gears_guidler | 10 % | 70 % | 6.0 | stop | filament_material |
| hotend_fan | 60 % | 90 % | 5.3 | stop | extruder_motor |
| part_cooling_fan | 70 % | 100 % | 6.1 | stop | slicer_settings |
| xy_motors_drivers | 100 % | 100 % | 5.8 |  |  |
| xy_belts | 70 % | 100 % | 5.8 | stop | z_motor_leadscrew |
| xy_pulleys_idlers | 40 % | 60 % | 5.6 | knowledge | xy_motors_drivers |
| x_linear_rail | 50 % | 70 % | 6.2 | stop | xy_motors_drivers |
| y_linear_rails | 40 % | 70 % | 6.2 | stop | xy_motors_drivers |
| toolhead | 50 % | 50 % | 6.7 | reading | hotend_thermistor |
| z_motor_leadscrew | 80 % | 90 % | 6.6 | stop | bed_plate_carrier |
| z_rails | 30 % | 70 % | 5.0 | knowledge | z_motor_leadscrew |
| z_endstop | 50 % | 60 % | 5.8 | knowledge | bed_plate_carrier |
| bed_heater | 80 % | 80 % | 4.5 | stop | filament_material |
| bed_thermistor | 30 % | 90 % | 7.1 | stop | filament_material |
| bed_plate_carrier | 80 % | 100 % | 4.7 | stop | z_motor_leadscrew |
| controller_board | 50 % | 50 % | 4.8 | knowledge | host_computer |
| umbilical_wiring | 20 % | 70 % | 6.2 | stop | hotend_thermistor |
| power_supply | 70 % | 100 % | 4.7 | stop | mains_power_input |
| host_computer | 60 % | 70 % | 7.0 | stop | bed_thermistor |
| filament_runout_sensor | 100 % | 100 % | 2.5 |  |  |
| firmware_config_macros | 0 % | 60 % | 6.4 | knowledge | toolhead |
| slicer_settings | 30 % | 30 % | 5.6 | stop | nozzle |
| filament_material | 50 % | 70 % | 4.7 | knowledge | extruder_motor |
| mains_power_input | 70 % | 100 % | 5.0 | stop | power_supply |
| dc_power_wiring | 60 % | 100 % | 6.1 | knowledge | host_computer |
| bed_thermal_fuse | 80 % | 100 % | 3.5 | stop | bed_heater |