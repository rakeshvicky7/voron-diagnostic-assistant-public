# Development yardstick (6 twin faults per part; 'can't tell' 15%; wrong answers 10%)

| Set | Cases | Top-1 | Top-3 | Mean questions | Right after at most one 'this part is fine' | Questions then |
|---|---|---|---|---|---|---|
| twin (31 parts) | 186 | 55 % | 75 % | 5.5 | 70 % | 5.8 |
| all | 186 | 55 % | 75 % | 5.5 | 70 % | 5.8 |

## Why the wrong ones failed

| Failure type | Cases | Share of failures |
|---|---|---|
| knowledge | 27 | 32 % |
| question | 0 | 0 % |
| stop | 48 | 57 % |
| reading | 9 | 11 % |

## Per part (twin)

| Part | Top-1 | Top-3 | Questions | Main failure | Most often named instead |
|---|---|---|---|---|---|
| hotend_heater | 100 % | 100 % | 2.3 |  |  |
| hotend_thermistor | 50 % | 83 % | 8.0 | stop | umbilical_wiring |
| nozzle | 50 % | 83 % | 5.0 | stop | extruder_gears_guidler |
| heatbreak_ptfe | 17 % | 83 % | 5.0 | knowledge | extruder_motor |
| extruder_motor | 33 % | 100 % | 5.3 | knowledge | nozzle |
| extruder_gears_guidler | 0 % | 50 % | 6.2 | stop | filament_material |
| hotend_fan | 67 % | 83 % | 5.3 | stop | extruder_motor |
| part_cooling_fan | 67 % | 83 % | 7.0 | stop | z_motor_leadscrew |
| xy_motors_drivers | 100 % | 100 % | 5.5 |  |  |
| xy_belts | 83 % | 100 % | 6.0 | stop | xy_motors_drivers |
| xy_pulleys_idlers | 67 % | 83 % | 4.3 | knowledge | xy_motors_drivers |
| x_linear_rail | 50 % | 67 % | 6.5 | stop | z_motor_leadscrew |
| y_linear_rails | 33 % | 67 % | 6.5 | reading | x_linear_rail |
| toolhead | 33 % | 33 % | 7.7 | reading | hotend_thermistor |
| z_motor_leadscrew | 83 % | 100 % | 6.3 | stop | bed_plate_carrier |
| z_rails | 50 % | 83 % | 5.3 | knowledge | z_motor_leadscrew |
| z_endstop | 67 % | 83 % | 6.5 | knowledge | bed_plate_carrier |
| bed_heater | 83 % | 83 % | 4.5 | stop | bed_plate_carrier |
| bed_thermistor | 33 % | 67 % | 7.0 | stop | bed_plate_carrier |
| bed_plate_carrier | 83 % | 83 % | 5.7 | stop | z_motor_leadscrew |
| controller_board | 67 % | 67 % | 3.8 | knowledge | host_computer |
| umbilical_wiring | 17 % | 33 % | 6.8 | stop | hotend_thermistor |
| power_supply | 67 % | 100 % | 4.3 | stop | mains_power_input |
| host_computer | 50 % | 50 % | 7.2 | stop | mains_power_input |
| filament_runout_sensor | 100 % | 100 % | 2.8 |  |  |
| firmware_config_macros | 0 % | 33 % | 6.7 | knowledge | hotend_heater |
| slicer_settings | 0 % | 0 % | 5.3 | stop | nozzle |
| filament_material | 67 % | 67 % | 5.7 | knowledge | extruder_motor |
| mains_power_input | 83 % | 100 % | 4.7 | stop | power_supply |
| dc_power_wiring | 67 % | 100 % | 5.8 | knowledge | host_computer |
| bed_thermal_fuse | 33 % | 67 % | 2.8 | stop | bed_heater |