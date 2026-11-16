# Development yardstick (6 twin faults per part; 'can't tell' 0%; wrong answers 0%)

| Set | Cases | Top-1 | Top-3 | Mean questions | Right after at most one 'this part is fine' | Questions then |
|---|---|---|---|---|---|---|
| twin (31 parts) | 186 | 67 % | 85 % | 5.2 | 78 % | 5.4 |
| all | 186 | 67 % | 85 % | 5.2 | 78 % | 5.4 |

## Why the wrong ones failed

| Failure type | Cases | Share of failures |
|---|---|---|
| knowledge | 27 | 44 % |
| question | 0 | 0 % |
| stop | 27 | 44 % |
| reading | 7 | 11 % |

## Per part (twin)

| Part | Top-1 | Top-3 | Questions | Main failure | Most often named instead |
|---|---|---|---|---|---|
| hotend_heater | 100 % | 100 % | 2.0 |  |  |
| hotend_thermistor | 17 % | 100 % | 7.7 | stop | firmware_config_macros |
| nozzle | 50 % | 100 % | 4.5 | stop | extruder_gears_guidler |
| heatbreak_ptfe | 0 % | 100 % | 5.7 | knowledge | extruder_motor |
| extruder_motor | 50 % | 100 % | 5.0 | stop | extruder_gears_guidler |
| extruder_gears_guidler | 100 % | 100 % | 6.0 |  |  |
| hotend_fan | 100 % | 100 % | 6.0 |  |  |
| part_cooling_fan | 100 % | 100 % | 4.0 |  |  |
| xy_motors_drivers | 100 % | 100 % | 7.3 |  |  |
| xy_belts | 67 % | 100 % | 7.0 | stop | z_motor_leadscrew |
| xy_pulleys_idlers | 67 % | 67 % | 5.2 | knowledge | xy_motors_drivers |
| x_linear_rail | 100 % | 100 % | 5.7 |  |  |
| y_linear_rails | 100 % | 100 % | 5.7 |  |  |
| toolhead | 33 % | 33 % | 5.0 | reading | xy_belts |
| z_motor_leadscrew | 67 % | 100 % | 4.8 | stop | z_rails |
| z_rails | 50 % | 83 % | 4.5 | knowledge | bed_plate_carrier |
| z_endstop | 83 % | 83 % | 4.8 | knowledge | bed_plate_carrier |
| bed_heater | 50 % | 50 % | 6.0 | stop | filament_material |
| bed_thermistor | 67 % | 100 % | 5.7 | stop | filament_material |
| bed_plate_carrier | 100 % | 100 % | 4.0 |  |  |
| controller_board | 67 % | 83 % | 4.2 | knowledge | host_computer |
| umbilical_wiring | 0 % | 17 % | 7.0 | stop | hotend_heater |
| power_supply | 100 % | 100 % | 7.0 |  |  |
| host_computer | 100 % | 100 % | 7.5 |  |  |
| filament_runout_sensor | 100 % | 100 % | 2.0 |  |  |
| firmware_config_macros | 0 % | 83 % | 6.0 | knowledge | toolhead |
| slicer_settings | 0 % | 0 % | 5.3 | stop | extruder_gears_guidler |
| filament_material | 33 % | 33 % | 5.2 | knowledge | nozzle |
| mains_power_input | 83 % | 100 % | 3.7 | knowledge | power_supply |
| dc_power_wiring | 100 % | 100 % | 6.0 |  |  |
| bed_thermal_fuse | 100 % | 100 % | 2.0 |  |  |