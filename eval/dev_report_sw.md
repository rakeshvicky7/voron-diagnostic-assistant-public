# Development yardstick (6 twin faults per part; 'can't tell' 0%; wrong answers 0%)

| Set | Cases | Top-1 | Top-3 | Mean questions | Right after at most one 'this part is fine' | Questions then |
|---|---|---|---|---|---|---|
| twin (31 parts) | 186 | 70 % | 87 % | 5.2 | 83 % | 5.3 |
| all | 186 | 70 % | 87 % | 5.2 | 83 % | 5.3 |

## Why the wrong ones failed

| Failure type | Cases | Share of failures |
|---|---|---|
| knowledge | 29 | 53 % |
| question | 0 | 0 % |
| stop | 19 | 35 % |
| reading | 7 | 13 % |

## Per part (twin)

| Part | Top-1 | Top-3 | Questions | Main failure | Most often named instead |
|---|---|---|---|---|---|
| hotend_heater | 100 % | 100 % | 2.0 |  |  |
| hotend_thermistor | 83 % | 100 % | 7.7 | stop | hotend_heater |
| nozzle | 83 % | 100 % | 4.8 | stop | extruder_gears_guidler |
| heatbreak_ptfe | 67 % | 100 % | 5.7 | reading | nozzle |
| extruder_motor | 50 % | 50 % | 5.0 | knowledge | nozzle |
| extruder_gears_guidler | 0 % | 100 % | 6.0 | stop | filament_material |
| hotend_fan | 100 % | 100 % | 6.0 |  |  |
| part_cooling_fan | 100 % | 100 % | 4.0 |  |  |
| xy_motors_drivers | 100 % | 100 % | 5.7 |  |  |
| xy_belts | 67 % | 100 % | 5.7 | stop | z_motor_leadscrew |
| xy_pulleys_idlers | 67 % | 67 % | 5.0 | knowledge | xy_motors_drivers |
| x_linear_rail | 100 % | 100 % | 5.8 |  |  |
| y_linear_rails | 100 % | 100 % | 5.8 |  |  |
| toolhead | 33 % | 33 % | 6.3 | reading | z_motor_leadscrew |
| z_motor_leadscrew | 67 % | 100 % | 4.8 | stop | z_rails |
| z_rails | 50 % | 83 % | 4.5 | knowledge | bed_plate_carrier |
| z_endstop | 83 % | 83 % | 4.8 | knowledge | bed_plate_carrier |
| bed_heater | 100 % | 100 % | 4.0 |  |  |
| bed_thermistor | 67 % | 100 % | 7.0 | stop | filament_material |
| bed_plate_carrier | 100 % | 100 % | 4.0 |  |  |
| controller_board | 67 % | 67 % | 4.3 | knowledge | host_computer |
| umbilical_wiring | 33 % | 50 % | 7.0 | stop | hotend_thermistor |
| power_supply | 100 % | 100 % | 4.3 |  |  |
| host_computer | 100 % | 100 % | 7.5 |  |  |
| filament_runout_sensor | 100 % | 100 % | 2.0 |  |  |
| firmware_config_macros | 0 % | 83 % | 6.3 | knowledge | toolhead |
| slicer_settings | 33 % | 50 % | 5.2 | knowledge | nozzle |
| filament_material | 33 % | 33 % | 5.2 | knowledge | nozzle |
| mains_power_input | 100 % | 100 % | 3.7 |  |  |
| dc_power_wiring | 100 % | 100 % | 6.0 |  |  |
| bed_thermal_fuse | 0 % | 100 % | 6.0 | knowledge | hotend_thermistor |